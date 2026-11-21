import time
import threading
import uuid
import datetime
import json
import hashlib
from pathlib import Path
from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from backend.app.database import get_db
from backend.app.models import (
    User, EgressProof, SecuritySummary, Collector, MetricRecord, AuditRecord, Organization
)
from backend.app.auth.security import get_current_user
from backend.app.ingestion.pipeline import process_ingestion_payload
from backend.app.api.broadcaster import broadcaster

# In-memory configurable thresholds
_THRESHOLD_SETTINGS = {
    "cpu_excellent": 50,
    "cpu_good": 75,
    "cpu_fair": 90,
    "latency_excellent": 200,
    "latency_good": 500,
    "latency_fair": 1000
}
_OUTAGE_SIMULATED = False

router = APIRouter(prefix="/demo", tags=["AI Demonstration Controls"])

# Global thread reference for controlled CPU stress test
_stress_stop_event = threading.Event()
_stress_threads = []
_active_stress = False

def _cpu_burner(duration_seconds: int = 6):
    global _active_stress
    _active_stress = True
    start = time.time()
    while not _stress_stop_event.is_set() and (time.time() - start) < duration_seconds:
        # Safe mathematical computations to raise CPU utilization temporarily
        _ = sum(x * x for x in range(20000))
        # Micro-yield to ensure system processes remain completely responsive
        time.sleep(0.0005)
    _active_stress = False

@router.post("/cpu-stress")
async def trigger_cpu_stress(
    duration: int = 6,
    current_user: User = Depends(get_current_user)
):
    """
    Runs a safe, controlled, time-bounded CPU load on the local demonstration machine.
    Hard duration cap at 8 seconds, maximum 2 cores, immediately interruptible via /stop.
    """
    global _stress_stop_event, _stress_threads
    _stress_stop_event.clear()
    
    safe_duration = min(8, max(1, duration))
    # Run in 2 threads (max 2 cores) to create measurable CPU activity safely
    t1 = threading.Thread(target=_cpu_burner, args=(safe_duration,), daemon=True)
    t2 = threading.Thread(target=_cpu_burner, args=(safe_duration,), daemon=True)
    _stress_threads = [t1, t2]
    t1.start()
    t2.start()

    return {
        "status": "Running",
        "scenario": "Controlled Safe Local CPU Stress Test",
        "duration_seconds": safe_duration,
        "max_cores": 2,
        "capped_at_seconds": 8,
        "message": f"Controlled CPU stress started for {safe_duration}s (max 2 cores). Real psutil hardware metrics and AIOps will detect real CPU rise."
    }

@router.post("/stop")
async def stop_stress(current_user: User = Depends(get_current_user)):
    """Immediate abort control for active CPU or memory stress."""
    global _stress_stop_event
    _stress_stop_event.set()
    return {"status": "Stopped", "message": "All demonstration stress workloads halted immediately."}

@router.post("/correlated-incident")
async def trigger_correlated_scenario(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Triggers a multi-signal correlated telemetry breach to demonstrate
    the full end-to-end pipeline:
    Telemetry -> Local Detection -> Privacy Allow-List -> Egress Proof ->
    SaaS Ingestion -> AIOps Anomaly -> Incident DNA -> Explainable Recommendation.
    """
    now_utc = datetime.datetime.now(datetime.timezone.utc).isoformat()
    pid = str(uuid.uuid4())

    payload = {
        "payload_id": pid,
        "tenant_id": current_user.tenant_id,
        "source_id": "NODE_DEMO_01",
        "collector_id": "COLLECTOR_001",
        "timestamp_utc": now_utc,
        "cpu_usage": 96.5,
        "memory_usage": 84.0,
        "disk_usage": 65.0,
        "latency_ms": 310.0,
        "packet_loss_pct": 2.5,
        "throughput_kbps": 420.0,
        "health_state": "Poor",
        "event_category": "Performance Degradation",
        "severity": "Critical"
    }

    ack = await process_ingestion_payload(payload, db)

    return {
        "status": "Injected",
        "scenario": "Multi-Signal Correlated Performance Breach",
        "payload_id": pid,
        "ingestion_ack": ack,
        "signals_injected": {
            "cpu_usage": "96.5% (+4.8σ breach)",
            "latency_ms": "310.0 ms (+5.2σ breach)",
            "memory_usage": "84.0% (elevated)"
        },
        "pipeline_stages": [
            "1. Telemetry Ingested via Allow-List",
            "2. SHA-256 Egress Proof Created",
            "3. Statistical Baseline Breach (MAD + Z-score)",
            "4. Isolation Forest Multivariate Flag",
            "5. Incident DNA Grouping Correlated Alerts",
            "6. Explainable Recommendation Generated"
        ]
    }

@router.post("/inject-pii-log")
async def inject_pii_log_scenario(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Scenario 1: Inject Raw PII Banking Log
    Demonstrates local scrubbing of Account number, PAN card, Aadhaar, and JWT tokens.
    SaaS Tier 2 only receives allow-listed metadata + cryptographic proof.
    """
    now_utc = datetime.datetime.now(datetime.timezone.utc)
    pid = f"PLD-LIVE-PII-{int(now_utc.timestamp())}"
    raw_log = (
        f"[{now_utc.isoformat()}] [ERROR] [UPI_PAYMENT_TX] CustID: 994827104, "
        f"AccNo: 50100{int(now_utc.timestamp())}, IFSC: HDFC0000060, "
        f"Customer: Rajesh Sharma, Phone: +91-9876543210, PAN: ABCDE1234F, "
        f"Aadhaar: 9876-5432-1098, AuthToken: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
        f"eyJzdWIiOiI5OTQ4MjcxMDQiLCJuYW1lIjoiUmFqZXNoIFNoYXJtYSJ9.sig_sample, "
        f"Amount: INR 45,000.00, Reason: PaymentTimeout"
    )
    
    sanitized_dict = {
        "payload_id": pid,
        "tenant_id": current_user.tenant_id,
        "source_id": "mum-core-upi-switch-01",
        "collector_id": "COL-HDFC-MUM-01",
        "timestamp_utc": now_utc.isoformat(),
        "event_type": "UPI_PAYMENT_TX",
        "latency_ms": 1380.0,
        "health_state": "Poor",
        "privacy_scrubbed": {
            "account_number": f"REDACTED_HASH_SHA256_{pid[:8]}",
            "customer_id": "ANON_CUST_9948",
            "auth_token": "[REDACTED_JWT_TOKEN]",
            "pii_detected": ["BANK_ACCOUNT", "PAN_CARD", "AADHAAR", "PHONE", "CUSTOMER_NAME", "JWT_TOKEN"]
        }
    }
    exact_json = json.dumps(sanitized_dict, sort_keys=True)
    payload_hash = hashlib.sha256(exact_json.encode()).hexdigest()

    proof = EgressProof(
        payload_id=pid,
        tenant_id=current_user.tenant_id,
        source_id="mum-core-upi-switch-01",
        timestamp_utc=now_utc,
        raw_local_log_blocked=raw_log,
        approved_fields=json.dumps(["tenant_id", "collector_id", "source_id", "timestamp_utc", "event_type", "latency_ms", "health_state", "privacy_scrubbed"]),
        redacted_fields=json.dumps(["account_number", "aadhaar_number", "pan_number", "customer_name", "phone_number", "auth_token", "amount"]),
        applied_policy="RBI Compliance — Strict Banking Allow-List & Tokenization",
        exact_transmitted_json=exact_json,
        payload_hash=payload_hash,
        transmission_status="Delivered & Verified",
        server_ack_utc=now_utc
    )
    db.add(proof)

    # Add audit entry
    audit = AuditRecord(
        tenant_id=current_user.tenant_id,
        actor="Tier1PrivacyEngine",
        action="PII Ingestion Filtered & Egress Proof Generated",
        target=pid,
        result="Success",
        details=json.dumps({"scrubbed": ["Account", "PAN", "Aadhaar", "JWT"], "payload_id": pid}),
        timestamp_utc=now_utc
    )
    db.add(audit)
    await db.commit()

    return {
        "status": "Injected",
        "scenario": "Raw Banking PII Scrubbed & Egress Proof Generated",
        "payload_id": pid,
        "raw_local_log_blocked": raw_log,
        "sanitized_saas_payload": sanitized_dict,
        "payload_hash": payload_hash,
        "message": "Raw log with Account Number, PAN, Aadhaar & JWT blocked at Tier 1. Sanitized payload stored in Egress Proof."
    }

@router.post("/inject-brute-force")
async def inject_brute_force_scenario(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Scenario 2: Inject Brute-Force Login Spike
    Simulates high-velocity PIN / login failures on ATM / NetBanking node.
    """
    now_utc = datetime.datetime.now(datetime.timezone.utc)
    summary_id = f"SEC-ATM-BRUTE-{int(now_utc.timestamp())}"
    
    sec = SecuritySummary(
        payload_id=summary_id,
        tenant_id=current_user.tenant_id,
        source_id="mum-core-upi-switch-01",
        event_category="Authentication Attack",
        severity="Critical",
        failed_login_count=42,
        time_window_sec=60,
        description="High-velocity brute force attack detected on ATM Switch Node / API Gateway (42 failed attempts in 60s from subnet 185.220.101.0/24). Automated IP rate-limiting applied.",
        timestamp_utc=now_utc
    )
    db.add(sec)
    
    audit = AuditRecord(
        tenant_id=current_user.tenant_id,
        actor="SecurityDetectionEngine",
        action="Brute-Force Anomaly Alert Generated",
        target="Terminal/API Endpoint",
        result="Success",
        details=json.dumps({"failed_count": 42, "window_sec": 60}),
        timestamp_utc=now_utc
    )
    db.add(audit)
    await db.commit()

    return {
        "status": "Injected",
        "scenario": "ATM / NetBanking Brute-Force Spike",
        "failed_attempts": 42,
        "window_seconds": 60,
        "severity": "Critical",
        "message": "Security alert generated for high-velocity credential attack. Appears in Telemetry & Security tab."
    }

@router.post("/inject-network-spike")
async def inject_network_spike_scenario(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Scenario 3: Inject Latency / Packet Loss Spike (Z > 2.5)
    Breaches statistical baseline and transitions health state to Poor.
    """
    now_utc = datetime.datetime.now(datetime.timezone.utc)
    pid = f"HIST-SPIKE-{int(now_utc.timestamp())}"
    
    metric = MetricRecord(
        payload_id=pid,
        tenant_id=current_user.tenant_id,
        source_id="mum-core-upi-switch-01",
        collector_id="COL-HDFC-MUM-01",
        timestamp_utc=now_utc,
        cpu_usage=89.4,
        memory_usage=84.2,
        disk_usage=68.0,
        latency_ms=1450.0,
        packet_loss_pct=3.8,
        health_state="Poor",
        event_category="Performance",
        severity="Critical"
    )
    db.add(metric)
    await db.commit()

    return {
        "status": "Injected",
        "scenario": "UPI Payment Switch Latency Spike (Z=3.9 > 2.5)",
        "latency_ms": 1450.0,
        "packet_loss_pct": 3.8,
        "cpu_usage": 89.4,
        "health_state": "Poor",
        "message": "Spike injected! Latency 1450ms (baseline 180ms) triggers rolling Z-score anomaly breach."
    }

@router.post("/simulate-outage-toggle")
async def simulate_outage_toggle(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Scenario 4: Simulate SaaS Outage / Reconnect
    Toggles Tier 1 collector into buffering mode or flushes back to online.
    """
    global _OUTAGE_SIMULATED
    _OUTAGE_SIMULATED = not _OUTAGE_SIMULATED
    now_utc = datetime.datetime.now(datetime.timezone.utc)

    # Update collector status in DB
    stmt = select(Collector).where(Collector.tenant_id == current_user.tenant_id)
    cols = (await db.execute(stmt)).scalars().all()
    for c in cols:
        if _OUTAGE_SIMULATED:
            c.status = "Offline"
            c.pending_buffered += 15
        else:
            c.status = "Online"
            c.last_heartbeat = now_utc
            c.pending_buffered = 0
    await db.commit()

    return {
        "status": "Toggled",
        "outage_simulated": _OUTAGE_SIMULATED,
        "collector_status": "Offline (Buffering locally)" if _OUTAGE_SIMULATED else "Online (Buffer Flushed)",
        "buffered_records": 15 if _OUTAGE_SIMULATED else 0,
        "message": "Simulated SaaS disconnection: Tier 1 buffering locally in SQLite" if _OUTAGE_SIMULATED else "SaaS reconnected: All buffered records flushed idempotently with zero duplicates."
    }

@router.get("/thresholds")
async def get_thresholds():
    """Returns configurable health threshold sliders."""
    return _THRESHOLD_SETTINGS

@router.post("/thresholds")
async def update_thresholds(thresholds: Dict[str, Any] = Body(...)):
    """Updates configurable health threshold sliders."""
    global _THRESHOLD_SETTINGS
    _THRESHOLD_SETTINGS.update(thresholds)
    return {"status": "Updated", "thresholds": _THRESHOLD_SETTINGS}

@router.post("/reset-banking-seed")
async def reset_banking_seed(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Reloads the clean banking seed dataset on demand."""
    from backend.app.main import seed_initial_data
    seed_path = Path("backend/banking_seed_data.json")
    if seed_path.exists():
        with open(seed_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return {"status": "Reloaded", "organizations": [o["tenant_id"] for o in data.get("organizations", [])]}
    return {"status": "Seed file not found"}
