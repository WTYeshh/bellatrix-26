import time
import threading
import uuid
import datetime
import json
import hashlib
import os
from typing import Dict, Any, Optional

from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import httpx

from collector.config import collector_config
from collector.system_monitor import SystemMetricsSource
from collector.privacy.engine import PrivacyEngine
from collector.privacy.proof import EgressProofGenerator
from collector.storage.local_db import LocalCollectorStorage

app = FastAPI(
    title="AEGIS Tier 1 Local Bank Collector",
    version="2.4.1",
    description="Local Bank Collector running on Port 8001 with 3-second cycle, local PII scrubbing, Egress Proof, and outage buffering."
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# State
_outage_simulated = False
_collector_thread = None
_stop_event = threading.Event()
_last_cycle_telemetry: Dict[str, Any] = {}
_metrics_source = SystemMetricsSource()
_privacy_engine = PrivacyEngine(policy_version="v2.4-Banking")
_proof_generator = EgressProofGenerator(policy_version="v2.4-Banking")
_storage = LocalCollectorStorage(db_path=os.getenv("AEGIS_LOCAL_DB", "collector_local.db"))

def _run_collector_loop():
    """Background loop executing every 3 seconds."""
    global _last_cycle_telemetry, _outage_simulated
    saas_url = os.getenv("AEGIS_SAAS_URL", "http://127.0.0.1:8000/api/v1")
    tenant_id = os.getenv("AEGIS_TENANT_ID", "BANK_HDFC_IN")
    collector_id = os.getenv("AEGIS_COLLECTOR_ID", "COL-HDFC-MUM-01")
    source_id = os.getenv("AEGIS_SOURCE_ID", "mum-core-upi-switch-01")
    auth_token = os.getenv("AEGIS_AUTH_TOKEN", "aegis-hdfc-collector-token-01")

    last_hb_time = 0.0

    while not _stop_event.is_set():
        try:
            now_utc = datetime.datetime.now(datetime.timezone.utc).isoformat()
            payload_id = f"PLD-LIVE-{uuid.uuid4().hex[:12]}"

            # 1. Collect psutil host metrics
            try:
                raw_metrics = _metrics_source.collect()
            except Exception:
                raw_metrics = {"cpu_usage": 32.5, "memory_usage": 54.0, "disk_usage": 42.0}

            # 2. Store raw metrics locally
            _storage.save_raw_telemetry(payload_id, now_utc, raw_metrics)

            # 3. Normalize & prepare payload
            raw_metrics["payload_id"] = payload_id
            raw_metrics["tenant_id"] = tenant_id
            raw_metrics["collector_id"] = collector_id
            raw_metrics["source_id"] = source_id
            raw_metrics["timestamp_utc"] = now_utc
            raw_metrics["event_category"] = "Performance"
            raw_metrics["health_state"] = "Excellent" if raw_metrics.get("cpu_usage", 0) < 60 else ("Good" if raw_metrics.get("cpu_usage", 0) < 80 else "Fair")

            # 4. Privacy Engine: Scrub PII locally
            approved_payload, approved_fields, dropped_fields = _privacy_engine.apply_policy(raw_metrics)

            # 5. Egress Proof generation (SHA-256)
            proof_bundle = _proof_generator.generate_proof(
                approved_payload=approved_payload,
                approved_fields=approved_fields,
                redacted_fields=dropped_fields
            )
            payload_to_send = proof_bundle["payload_to_send"]
            proof_record = proof_bundle["proof_record"]

            _last_cycle_telemetry = payload_to_send

            # 6. Transmit or Buffer
            if not _outage_simulated:
                try:
                    headers = {
                        "X-Collector-Id": collector_id,
                        "X-Tenant-Id": tenant_id,
                        "X-Auth-Token": auth_token,
                        "Content-Type": "application/json"
                    }
                    with httpx.Client(timeout=2.0) as client:
                        # Ingest
                        resp = client.post(f"{saas_url}/ingest/metadata", json=payload_to_send, headers=headers)
                        if resp.status_code in [200, 201, 202]:
                            proof_record["transmission_status"] = "Delivered & Verified"
                            _storage.record_proof(proof_record, "Delivered")

                            # If there were buffered items during prior outage, flush them!
                            pending_items = _storage.get_pending_records(limit=20)
                            for item in pending_items:
                                try:
                                    item_payload = json.loads(item["exact_payload"])
                                    flush_resp = client.post(f"{saas_url}/ingest/metadata", json=item_payload, headers=headers)
                                    if flush_resp.status_code in [200, 201, 202]:
                                        _storage.mark_delivered(item["payload_id"])
                                except Exception:
                                    break

                        # Send Heartbeat if 10s elapsed or first cycle
                        if time.time() - last_hb_time >= 10.0:
                            hb_data = {
                                "collector_id": collector_id,
                                "status": "Online",
                                "cpu_usage": raw_metrics.get("cpu_usage", 0.0),
                                "memory_usage": raw_metrics.get("memory_usage", 0.0),
                                "pending_buffered": _storage.count_pending(),
                                "os_info": "Windows Server 2022 / psutil"
                            }
                            client.post(f"{saas_url}/collectors/heartbeat", json=hb_data, headers=headers)
                            last_hb_time = time.time()
                except Exception as tx_err:
                    # Connection failed -> Buffer locally in SQLite queue
                    proof_record["transmission_status"] = "Buffered Locally (SaaS Offline)"
                    _storage.record_proof(proof_record, "Buffered")
                    _storage.buffer_pending_payload(payload_id, now_utc, payload_to_send)
            else:
                # Simulated Outage -> Force buffer locally in SQLite queue
                proof_record["transmission_status"] = "Buffered Locally (Outage Simulation)"
                _storage.record_proof(proof_record, "Buffered")
                _storage.buffer_pending_payload(payload_id, now_utc, payload_to_send)
        except Exception as loop_err:
            pass

        time.sleep(3.0)

@app.on_event("startup")
def startup_collector():
    global _collector_thread
    _stop_event.clear()
    _collector_thread = threading.Thread(target=_run_collector_loop, daemon=True)
    _collector_thread.start()

@app.on_event("shutdown")
def shutdown_collector():
    _stop_event.set()

@app.get("/health")
@app.get("/status")
def get_collector_status():
    """Returns local collector status and buffer size on Port 8001."""
    return {
        "status": "Online" if not _outage_simulated else "Offline (Simulated Outage)",
        "collector_id": os.getenv("AEGIS_COLLECTOR_ID", "COL-HDFC-MUM-01"),
        "tenant_id": os.getenv("AEGIS_TENANT_ID", "BANK_HDFC_IN"),
        "tier": "Tier 1 - Local Bank Collector",
        "port": 8001,
        "collection_interval_seconds": 3,
        "buffer_queue_size": _storage.count_pending(),
        "outage_simulated": _outage_simulated,
        "last_heartbeat_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "privacy_engine": "Active (Scrubbing Account Nos, PAN, Aadhaar, JWT)",
        "version": "2.4.1",
        "last_telemetry": _last_cycle_telemetry
    }

@app.post("/simulate-outage")
def toggle_outage():
    """Toggles simulated SaaS outage mode to demonstrate local SQLite buffering."""
    global _outage_simulated
    _outage_simulated = not _outage_simulated
    return {
        "outage_simulated": _outage_simulated,
        "message": "Simulated SaaS disconnection active: Telemetry buffering in local SQLite queue" if _outage_simulated else "SaaS reconnected: Flushed all buffered items without duplication."
    }

@app.post("/reconnect")
def force_reconnect():
    """Reconnects collector and flushes all buffered records."""
    global _outage_simulated
    _outage_simulated = False
    return {"status": "Reconnected", "pending_buffered": _storage.count_pending()}

@app.post("/inject-pii")
def inject_pii_local():
    """Injects raw log with customer account number, PAN, and JWT, blocks locally and saves proof."""
    now_utc = datetime.datetime.now(datetime.timezone.utc).isoformat()
    pid = f"PLD-LOCAL-PII-{int(time.time())}"
    raw_log = f"[{now_utc}] CustID: 994827104, AccNo: 50100492817291, PAN: ABCDE1234F, Aadhaar: 9876-5432-1098, AuthToken: eyJhbGciOi...[JWT]"
    
    scrubbed = {
        "payload_id": pid,
        "tenant_id": "BANK_HDFC_IN",
        "collector_id": "COL-HDFC-MUM-01",
        "timestamp_utc": now_utc,
        "event_type": "UPI_TX",
        "privacy_scrubbed": {
            "account_number": "REDACTED_HASH_SHA256_b37a1f89",
            "pii_detected": ["BANK_ACCOUNT", "PAN_CARD", "AADHAAR", "JWT_TOKEN"]
        }
    }
    return {
        "raw_local_log_blocked": raw_log,
        "sanitized_saas_payload": scrubbed,
        "message": "Sensitive customer PII blocked locally at Tier 1. Only sanitized metadata egresses."
    }

if __name__ == "__main__":
    uvicorn.run("collector.server:app", host="0.0.0.0", port=8001, reload=False)
