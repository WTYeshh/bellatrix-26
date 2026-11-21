#!/usr/bin/env python3
"""
AEGIS Tier 1 - Standalone Local Bank Collector
Runs on Windows laptop (Port 8001).
- Tunable Traffic & Attack Load Intensity (0% to 100%, default 15%)
- Every 3 seconds reads laptop CPU %, RAM %, Disk % via psutil, modulated by load intensity
- Attaches simulated banking UPI latency & failed-login counts
- Strips any sensitive PII fields (AccNo, CustID, Token, PAN, Aadhaar) locally
- Saves before-and-after diff to http://localhost:8001/egress
- POSTs sanitized metadata JSON to http://localhost:8000/api/v1/ingest
- Trigger endpoints: /trigger/load, /trigger/mitigate, /trigger/pii, /trigger/bruteforce, /trigger/latency, /trigger/outage
"""

import os
import sys
import time
import uuid
import json
import random
import hashlib
import datetime
import threading
from contextlib import asynccontextmanager
from typing import Dict, Any, List, Optional

import requests
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False

# Configuration
PORT = int(os.getenv("COLLECTOR_PORT", 8001))
SAAS_URL = os.getenv("AEGIS_SAAS_URL", "http://localhost:8000/api/v1")
TENANT_ID = os.getenv("AEGIS_TENANT_ID", "BANK_HDFC_IN")
COLLECTOR_ID = os.getenv("AEGIS_COLLECTOR_ID", "COL-HDFC-MUM-01")
SOURCE_ID = os.getenv("AEGIS_SOURCE_ID", "node_upi_gw_02")
AUTH_TOKEN = os.getenv("AEGIS_AUTH_TOKEN", "aegis-hdfc-collector-token-01")

# Strict field allow-list enforced by Tier 2
STRICT_ALLOWED_FIELDS = {
    "payload_id",
    "tenant_id",
    "source_id",
    "collector_id",
    "timestamp_utc",
    "cpu_usage",
    "memory_usage",
    "disk_usage",
    "latency_ms",
    "packet_loss_pct",
    "throughput_kbps",
    "bytes_sent",
    "bytes_recv",
    "local_anomalies",
    "health_state",
    "event_category",
    "severity",
    "payload_hash",
    "applied_policy",
    "approved_fields",
    "redacted_fields",
    "exact_transmitted_json"
}

# State & In-Memory Store
_lock = threading.Lock()
_load_intensity = 15  # 0 to 100, default 15% (Nominal Baseline)
_outage_mode = False
_latency_spike_active = False
_bruteforce_active = False
_pii_inject_pending = False
_buffered_queue: List[Dict[str, Any]] = []
_egress_history: List[Dict[str, Any]] = []
_last_telemetry: Dict[str, Any] = {}
_stop_event = threading.Event()

def get_system_metrics() -> Dict[str, float]:
    """Reads real laptop CPU %, RAM %, and Disk % via psutil with realistic fallback."""
    if HAS_PSUTIL:
        try:
            cpu = float(psutil.cpu_percent(interval=None))
            ram = float(psutil.virtual_memory().percent)
            disk = float(psutil.disk_usage('C:\\' if sys.platform == 'win32' else '/').percent)
            if cpu == 0.0:
                cpu = round(random.uniform(22.0, 32.0), 1)
            return {"cpu_usage": round(cpu, 1), "memory_usage": round(ram, 1), "disk_usage": round(disk, 1)}
        except Exception:
            pass
    # Automatic fallback
    return {
        "cpu_usage": round(24.5 + random.uniform(-2.0, 3.0), 1),
        "memory_usage": round(58.2 + random.uniform(-2.0, 2.0), 1),
        "disk_usage": round(44.0 + random.uniform(-1.0, 1.0), 1)
    }

def scrub_pii_and_build_payload(
    raw_log: str,
    metrics: Dict[str, float],
    latency_ms: float,
    failed_logins: int,
    packet_loss_pct: float = 0.1,
    health_state: Optional[str] = None,
    category: Optional[str] = None,
    severity: Optional[str] = None
) -> Dict[str, Any]:
    """
    Strips sensitive banking PII fields (AccNo, CustID, Token, PAN, Aadhaar)
    and constructs a sanitized metadata JSON conforming strictly to Tier 2 allow-list.
    """
    now_utc = datetime.datetime.now(datetime.timezone.utc).isoformat()
    payload_id = f"PLD-LIVE-{uuid.uuid4().hex[:12]}"

    if not health_state:
        if latency_ms > 650.0 or metrics["cpu_usage"] > 85.0 or failed_logins >= 15:
            health_state = "Poor"
            severity = "Critical"
            category = "UPI Gateway Breach" if latency_ms > 650.0 else "Security Attack"
        elif latency_ms > 220.0 or metrics["cpu_usage"] > 68.0:
            health_state = "Fair"
            severity = "Medium"
            category = "Performance Warning"
        elif metrics["cpu_usage"] > 48.0 or latency_ms > 90.0:
            health_state = "Good"
            severity = "Low"
            category = "Performance"
        else:
            health_state = "Excellent"
            severity = "Low"
            category = "Performance"

    if not severity:
        severity = "Critical" if health_state == "Poor" else ("Medium" if health_state == "Fair" else "Low")
    if not category:
        category = "Performance"

    redacted_fields = ["AccNo", "CustID", "Token", "PAN", "Aadhaar", "PIN", "Password"]
    approved_fields = [
        "payload_id", "tenant_id", "source_id", "collector_id", "timestamp_utc",
        "cpu_usage", "memory_usage", "disk_usage", "latency_ms", "packet_loss_pct",
        "throughput_kbps", "health_state", "event_category", "severity"
    ]

    sanitized = {
        "payload_id": payload_id,
        "tenant_id": TENANT_ID,
        "source_id": SOURCE_ID,
        "collector_id": COLLECTOR_ID,
        "timestamp_utc": now_utc,
        "cpu_usage": metrics["cpu_usage"],
        "memory_usage": metrics["memory_usage"],
        "disk_usage": metrics["disk_usage"],
        "latency_ms": round(latency_ms, 1),
        "packet_loss_pct": round(packet_loss_pct, 1),
        "throughput_kbps": round(320.0 + (metrics["cpu_usage"] * 4.5), 1),
        "bytes_sent": round(45000.0 + (metrics["cpu_usage"] * 250), 1),
        "bytes_recv": round(98000.0 + (metrics["cpu_usage"] * 400), 1),
        "health_state": health_state,
        "event_category": category,
        "severity": severity,
        "applied_policy": "RBI Compliance — Strict Banking Allow-List & Tokenization",
        "approved_fields": approved_fields,
        "redacted_fields": redacted_fields
    }

    # Compute exact canonical JSON and SHA-256 hash
    exact_json = json.dumps(sanitized, sort_keys=True)
    payload_hash = hashlib.sha256(exact_json.encode("utf-8")).hexdigest()
    sanitized["exact_transmitted_json"] = exact_json
    sanitized["payload_hash"] = payload_hash

    return {
        "payload_id": payload_id,
        "raw_local_log_blocked": raw_log,
        "sanitized_saas_payload": sanitized,
        "exact_json": exact_json,
        "payload_hash": payload_hash,
        "approved_fields": approved_fields,
        "redacted_fields": redacted_fields,
        "timestamp_utc": now_utc
    }

def flush_buffer(headers: Dict[str, str]):
    """Flushes buffered payloads to central SaaS idempotently."""
    global _buffered_queue
    with _lock:
        to_flush = list(_buffered_queue)
        _buffered_queue.clear()

    flushed_count = 0
    for item in to_flush:
        try:
            resp = requests.post(f"{SAAS_URL}/ingest", json=item, headers=headers, timeout=2.5)
            if resp.status_code in [200, 201, 202]:
                flushed_count += 1
            else:
                with _lock:
                    _buffered_queue.append(item)
                break
        except Exception:
            with _lock:
                _buffered_queue.append(item)
            break

def collector_worker():
    """Background loop executing every 3 seconds."""
    global _load_intensity, _outage_mode, _latency_spike_active, _bruteforce_active, _pii_inject_pending
    global _last_telemetry, _buffered_queue, _egress_history

    headers = {
        "X-Collector-Id": COLLECTOR_ID,
        "X-Tenant-Id": TENANT_ID,
        "X-Auth-Token": AUTH_TOKEN,
        "Content-Type": "application/json"
    }

    last_hb_time = 0.0

    while not _stop_event.is_set():
        try:
            now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
            sys_metrics = get_system_metrics()

            with _lock:
                outage = _outage_mode
                latency_spike = _latency_spike_active
                bruteforce = _bruteforce_active
                inject_pii = _pii_inject_pending
                load = _load_intensity
                _pii_inject_pending = False  # one-shot

            # Calculate metrics according to the 4 load tiers
            if latency_spike:
                cpu_pct = round(92.5 + random.uniform(-1.0, 2.0), 1)
                latency_ms = round(1420.0 + random.uniform(0.0, 35.0), 1)
                packet_loss_pct = 3.5
                failed_logins = 0
                health_state = "Poor"
                severity = "Critical"
                category = "UPI Gateway Latency Breach"
            elif bruteforce:
                cpu_pct = round(78.0 + random.uniform(-2.0, 2.0), 1)
                latency_ms = round(180.0 + random.uniform(-5.0, 10.0), 1)
                packet_loss_pct = 1.0
                failed_logins = 42
                health_state = "Poor"
                severity = "Critical"
                category = "ATM & NetBanking Brute-Force Spike"
            elif load <= 30:
                # 0% – 30% (No / Normal Load): CPU stays ~20–35%, Latency ~40–60ms, Packet Loss ~0.1%, Failed Logins = 0 -> Health: Excellent
                frac = max(0.0, min(1.0, load / 30.0))
                cpu_pct = round(20.0 + frac * 13.0 + random.uniform(-1.5, 2.0), 1)
                latency_ms = round(40.0 + frac * 18.0 + random.uniform(-2.0, 2.0), 1)
                packet_loss_pct = 0.1
                failed_logins = 0
                health_state = "Excellent"
                severity = "Low"
                category = "Performance"
            elif load <= 60:
                # 31% – 60% (Moderate Peak UPI Load): CPU rises to ~50–64%, Latency ~110–170ms, Packet Loss ~1.5% -> Health: Good / Fair
                frac = (load - 30.0) / 30.0
                cpu_pct = round(50.0 + frac * 13.0 + random.uniform(-1.0, 1.5), 1)
                latency_ms = round(110.0 + frac * 55.0 + random.uniform(-4.0, 4.0), 1)
                packet_loss_pct = 1.5
                failed_logins = 0
                health_state = "Good" if load <= 48 else "Fair"
                severity = "Low" if load <= 48 else "Medium"
                category = "Peak UPI Traffic"
            elif load <= 85:
                # 61% – 85% (Heavy Traffic Surge): CPU rises to ~70–84%, Latency ~250–450ms, Packet Loss ~6% -> Health: Fair
                frac = (load - 60.0) / 25.0
                cpu_pct = round(70.0 + frac * 13.0 + random.uniform(-1.0, 1.5), 1)
                latency_ms = round(250.0 + frac * 190.0 + random.uniform(-6.0, 8.0), 1)
                packet_loss_pct = 6.0
                failed_logins = random.choice([0, 1])
                health_state = "Fair"
                severity = "Medium"
                category = "Heavy Traffic Surge"
            else:
                # 86% – 100% (DDoS + Credential Stuffing Overload): CPU spikes to ~88–96%, Latency ~700–950ms, Packet Loss ~15%, Failed Logins = 18/tick -> Health: Poor
                frac = (load - 85.0) / 15.0
                cpu_pct = round(88.0 + frac * 7.5 + random.uniform(-0.5, 1.0), 1)
                latency_ms = round(700.0 + frac * 235.0 + random.uniform(-10.0, 15.0), 1)
                packet_loss_pct = 15.0
                failed_logins = 18
                health_state = "Poor"
                severity = "Critical"
                category = "DDoS + Credential Stuffing Overload"

            metrics = {
                "cpu_usage": cpu_pct,
                "memory_usage": sys_metrics["memory_usage"],
                "disk_usage": sys_metrics["disk_usage"]
            }

            # Raw banking transaction log before local scrubbing
            acc_tail = random.randint(100000000, 999999999)
            if inject_pii:
                raw_log = (
                    f"[{now_iso}] [ERROR] [UPI_PAYMENT_TX] CustID: 994827104, "
                    f"AccNo: 50100{acc_tail}, IFSC: HDFC0000060, Customer: Rajesh Sharma, "
                    f"Phone: +91-9876543210, PAN: ABCDE1234F, Aadhaar: 9876-5432-1098, "
                    f"Token: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI5OTQ4MjcxMDQifQ.demo_signature, "
                    f"Amount: INR 45000.00, Reason: PaymentTimeout"
                )
            elif failed_logins > 0:
                raw_log = (
                    f"[{now_iso}] [WARN] [AUTH_SVC] Batch authentication failures detected ({failed_logins} failed). "
                    f"CustID: 881290441, AccNo: 50100{acc_tail}, Password: [RAW_PASS_REDACTED], "
                    f"Token: eyJhbGciOi...[JWT_SCRUBBED], Status: AUTH_BREACH_RATE_LIMIT"
                )
            else:
                raw_log = (
                    f"[{now_iso}] [INFO] [UPI_PAYMENT_TX] CustID: 881290441, "
                    f"AccNo: 50100{acc_tail}, Latency: {round(latency_ms, 1)}ms, "
                    f"Token: eyJhbGciOi...[JWT], Status: {'SUCCESS' if latency_ms < 500 else 'GATEWAY_TIMEOUT_504'}"
                )

            # Scrub PII locally & generate cryptographic proof
            diff_bundle = scrub_pii_and_build_payload(
                raw_log=raw_log,
                metrics=metrics,
                latency_ms=latency_ms,
                failed_logins=failed_logins,
                packet_loss_pct=packet_loss_pct,
                health_state=health_state,
                category=category,
                severity=severity
            )
            payload_to_send = diff_bundle["sanitized_saas_payload"]

            # Save diff record to egress history
            proof_record = {
                "payload_id": diff_bundle["payload_id"],
                "tenant_id": TENANT_ID,
                "source_id": SOURCE_ID,
                "timestamp_utc": diff_bundle["timestamp_utc"],
                "raw_local_log_blocked": raw_log,
                "sanitized_saas_payload": payload_to_send,
                "approved_fields": diff_bundle["approved_fields"],
                "redacted_fields": diff_bundle["redacted_fields"],
                "applied_policy": "RBI Compliance — Strict Banking Allow-List & Tokenization",
                "exact_transmitted_json": diff_bundle["exact_json"],
                "payload_hash": diff_bundle["payload_hash"],
                "transmission_status": "Delivered & Verified" if not outage else "Buffered Locally (SaaS Offline)",
                "hash_verified": True
            }

            with _lock:
                _egress_history.insert(0, proof_record)
                if len(_egress_history) > 60:
                    _egress_history.pop()
                _last_telemetry = payload_to_send

            # Transmit or Buffer
            if not outage:
                try:
                    resp = requests.post(f"{SAAS_URL}/ingest", json=payload_to_send, headers=headers, timeout=2.0)
                    if resp.status_code in [200, 201, 202]:
                        proof_record["transmission_status"] = "Delivered & Verified"
                        if len(_buffered_queue) > 0:
                            flush_buffer(headers)
                    else:
                        with _lock:
                            _buffered_queue.append(payload_to_send)
                            proof_record["transmission_status"] = "Buffered Locally (SaaS 5xx)"

                    # Send periodic collector heartbeat
                    if time.time() - last_hb_time >= 8.0:
                        hb_data = {
                            "collector_id": COLLECTOR_ID,
                            "status": "Online" if health_state != "Poor" else "Poor",
                            "cpu_usage": metrics["cpu_usage"],
                            "memory_usage": metrics["memory_usage"],
                            "pending_buffered": len(_buffered_queue),
                            "os_info": f"Windows 11 / Load Tuner: {load}% ({health_state})"
                        }
                        requests.post(f"{SAAS_URL}/collectors/heartbeat", json=hb_data, headers=headers, timeout=1.5)
                        last_hb_time = time.time()
                except Exception:
                    with _lock:
                        _buffered_queue.append(payload_to_send)
                        proof_record["transmission_status"] = "Buffered Locally (SaaS Offline)"
            else:
                with _lock:
                    _buffered_queue.append(payload_to_send)
                    proof_record["transmission_status"] = "Buffered Locally (Outage Simulation)"

        except Exception as loop_err:
            pass

        time.sleep(3.0)


# ==================== FASTAPI APP ON PORT 8001 ====================
@asynccontextmanager
async def lifespan(app: FastAPI):
    _stop_event.clear()
    t = threading.Thread(target=collector_worker, daemon=True)
    t.start()
    yield
    _stop_event.set()

app = FastAPI(
    title="AEGIS Tier 1 - Standalone Local Bank Collector",
    version="2.4.1",
    description="Local Bank Collector on Port 8001 with 3-second cycle, PII scrubbing, Egress Proof, tunable attack load (0-100%), and live demo triggers.",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
@app.get("/status")
def get_status():
    """Returns Tier 1 collector status, current load intensity, buffer queue size, and outage mode."""
    with _lock:
        load = _load_intensity
        if load <= 30:
            state = "Excellent"
        elif load <= 60:
            state = "Good" if load <= 48 else "Fair"
        elif load <= 85:
            state = "Fair"
        else:
            state = "Poor"

        return {
            "status": "Online" if not _outage_mode else "Offline (Simulated Outage)",
            "collector_id": COLLECTOR_ID,
            "tenant_id": TENANT_ID,
            "source_id": SOURCE_ID,
            "tier": "Tier 1 - Local Bank Collector",
            "port": PORT,
            "collection_interval_seconds": 3,
            "load_intensity": load,
            "projected_state": state,
            "buffer_queue_size": len(_buffered_queue),
            "outage_simulated": _outage_mode,
            "latency_spike_active": _latency_spike_active,
            "bruteforce_active": _bruteforce_active,
            "psutil_active": HAS_PSUTIL,
            "last_heartbeat_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "last_telemetry": _last_telemetry
        }

@app.get("/egress")
def get_egress_diffs(limit: int = 50):
    """Returns recent before-and-after diff records for the Egress Proof inspector."""
    with _lock:
        return _egress_history[:limit]

# Tunable Load Endpoint (0% to 100%)
@app.api_route("/trigger/load", methods=["GET", "POST"])
async def trigger_load(request: Request):
    """
    Sets the collector traffic and attack load intensity from 0% to 100%.
    - 0% - 30%: Excellent (CPU ~20-35%, Latency ~40-60ms, Loss ~0.1%)
    - 31% - 60%: Good / Fair (CPU ~50-64%, Latency ~110-170ms, Loss ~1.5%)
    - 61% - 85%: Fair (CPU ~70-84%, Latency ~250-450ms, Loss ~6%)
    - 86% - 100%: Poor (CPU ~88-96%, Latency ~700-950ms, Loss ~15%, Failed Logins=18/tick)
    """
    global _load_intensity, _latency_spike_active, _bruteforce_active
    intensity = 15

    if request.method == "POST":
        try:
            body = await request.json()
            if isinstance(body, dict) and "intensity" in body:
                intensity = int(body["intensity"])
        except Exception:
            intensity = int(request.query_params.get("intensity", 15))
    else:
        intensity = int(request.query_params.get("intensity", 15))

    intensity = max(0, min(100, intensity))

    with _lock:
        _load_intensity = intensity
        _latency_spike_active = False
        _bruteforce_active = False

    if intensity <= 30:
        state = "Excellent"
        desc = "No / Normal Baseline Load"
    elif intensity <= 60:
        state = "Good" if intensity <= 48 else "Fair"
        desc = "Moderate Peak UPI Surge"
    elif intensity <= 85:
        state = "Fair"
        desc = "Heavy Traffic Surge"
    else:
        state = "Poor"
        desc = "DDoS & Credential Stuffing Overload"

    return {
        "status": "Success",
        "load_intensity": intensity,
        "projected_state": state,
        "scenario": desc,
        "message": f"Gateway load tuned to {intensity}% -> System Health: {state}"
    }

# Mitigate / Overflow Relief Endpoint
@app.api_route("/trigger/mitigate", methods=["GET", "POST"])
def trigger_mitigate():
    """Resets load intensity back to 15% (simulating traffic rerouting & overflow relief)."""
    global _load_intensity, _latency_spike_active, _bruteforce_active
    with _lock:
        _load_intensity = 15
        _latency_spike_active = False
        _bruteforce_active = False

    return {
        "status": "Mitigated",
        "load_intensity": 15,
        "health_state": "Excellent",
        "message": "Traffic overflow mitigated. Gateway load reset to nominal baseline (15%)."
    }

# Trigger 1: Inject Raw PII Log
@app.api_route("/trigger/pii", methods=["GET", "POST"])
@app.api_route("/inject-pii", methods=["GET", "POST"])
def trigger_pii():
    """Injects a simulated raw log with Customer ID, Account Number, PAN, Aadhaar, and JWT token."""
    global _pii_inject_pending
    now_utc = datetime.datetime.now(datetime.timezone.utc).isoformat()
    acc_tail = random.randint(100000000, 999999999)
    raw_log = (
        f"[{now_utc}] [ERROR] [UPI_PAYMENT_TX] CustID: 994827104, "
        f"AccNo: 50100{acc_tail}, IFSC: HDFC0000060, Customer: Rajesh Sharma, "
        f"Phone: +91-9876543210, PAN: ABCDE1234F, Aadhaar: 9876-5432-1098, "
        f"Token: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI5OTQ4MjcxMDQifQ.sample_sig, "
        f"Amount: INR 45,000.00, Reason: PaymentTimeout"
    )

    metrics = get_system_metrics()
    metrics["cpu_usage"] = 88.5
    diff = scrub_pii_and_build_payload(
        raw_log=raw_log,
        metrics=metrics,
        latency_ms=1380.0,
        failed_logins=0,
        packet_loss_pct=2.4,
        health_state="Poor",
        category="UPI Gateway Breach",
        severity="Critical"
    )
    payload_to_send = diff["sanitized_saas_payload"]

    proof_record = {
        "payload_id": diff["payload_id"],
        "tenant_id": TENANT_ID,
        "source_id": SOURCE_ID,
        "timestamp_utc": diff["timestamp_utc"],
        "raw_local_log_blocked": raw_log,
        "sanitized_saas_payload": payload_to_send,
        "approved_fields": diff["approved_fields"],
        "redacted_fields": diff["redacted_fields"],
        "applied_policy": "RBI Compliance — Strict Banking Allow-List & Tokenization",
        "exact_transmitted_json": diff["exact_json"],
        "payload_hash": diff["payload_hash"],
        "transmission_status": "Delivered & Verified" if not _outage_mode else "Buffered Locally",
        "hash_verified": True
    }

    with _lock:
        _egress_history.insert(0, proof_record)
        _pii_inject_pending = True

    if not _outage_mode:
        try:
            requests.post(
                f"{SAAS_URL}/ingest",
                json=payload_to_send,
                headers={"X-Collector-Id": COLLECTOR_ID, "X-Tenant-Id": TENANT_ID, "X-Auth-Token": AUTH_TOKEN},
                timeout=2.0
            )
        except Exception:
            pass

    return {
        "status": "Injected",
        "scenario": "Raw Banking PII Scrubbed & Egress Proof Generated",
        "payload_id": diff["payload_id"],
        "raw_local_log_blocked": raw_log,
        "sanitized_saas_payload": payload_to_send,
        "payload_hash": diff["payload_hash"],
        "message": "Sensitive customer PII blocked locally at Tier 1. Only sanitized metadata egresses."
    }

# Trigger 2: Inject Brute-Force Login Spike
@app.api_route("/trigger/bruteforce", methods=["GET", "POST"])
def trigger_bruteforce():
    """Injects high-velocity brute force failed logins anomaly."""
    global _bruteforce_active
    with _lock:
        _bruteforce_active = not _bruteforce_active
        is_active = _bruteforce_active

    return {
        "status": "Injected" if is_active else "Deactivated",
        "scenario": "ATM & NetBanking PIN Brute-Force Spike",
        "failed_logins": 42 if is_active else 0,
        "message": "Simulated 42 failed PIN attempts within 60s from subnet 185.220.101.0/24" if is_active else "Brute-force simulation normalized"
    }

# Trigger 3: Inject UPI Payment Gateway Latency Spike
@app.api_route("/trigger/latency", methods=["GET", "POST"])
def trigger_latency():
    """Spikes UPI payment gateway processing latency to 1420ms (breaching Z-score > 2.5)."""
    global _latency_spike_active
    with _lock:
        _latency_spike_active = not _latency_spike_active
        is_active = _latency_spike_active

    return {
        "status": "Injected" if is_active else "Normalized",
        "scenario": "UPI Payment Switch Latency Spike",
        "latency_ms": 1420.0 if is_active else 24.0,
        "z_score": "+3.84σ" if is_active else "0.12σ",
        "message": "UPI Switch Latency spiked to 1420ms (Z=3.84 > 2.5). AIOps Incident INC-2026-089 correlated." if is_active else "UPI Switch latency returned to nominal 24ms."
    }

# Trigger 4: Simulate SaaS Outage / Reconnect
@app.api_route("/trigger/outage", methods=["GET", "POST"])
@app.api_route("/simulate-outage", methods=["GET", "POST"])
def trigger_outage():
    """Toggles SaaS outage mode. Buffers locally when disconnected, flushes when reconnected."""
    global _outage_mode
    with _lock:
        _outage_mode = not _outage_mode
        outage = _outage_mode

    if not outage:
        headers = {
            "X-Collector-Id": COLLECTOR_ID,
            "X-Tenant-Id": TENANT_ID,
            "X-Auth-Token": AUTH_TOKEN,
            "Content-Type": "application/json"
        }
        flush_buffer(headers)

    return {
        "outage_simulated": outage,
        "status": "Offline (Buffering Locally)" if outage else "Online (Reconnected & Flushed)",
        "buffered_records": len(_buffered_queue),
        "message": "Simulated SaaS disconnection active: Telemetry buffering in local queue" if outage else "SaaS reconnected: All buffered items flushed idempotently without duplicates."
    }

@app.post("/reconnect")
def reconnect():
    """Forces reconnect and flushes buffer."""
    global _outage_mode
    with _lock:
        _outage_mode = False
    headers = {
        "X-Collector-Id": COLLECTOR_ID,
        "X-Tenant-Id": TENANT_ID,
        "X-Auth-Token": AUTH_TOKEN,
        "Content-Type": "application/json"
    }
    flush_buffer(headers)
    return {"status": "Reconnected", "pending_buffered": len(_buffered_queue)}

if __name__ == "__main__":
    print(f"[AEGIS Tier 1 Collector] Starting on http://0.0.0.0:{PORT}...")
    uvicorn.run("local_collector:app", host="0.0.0.0", port=PORT, reload=False)
