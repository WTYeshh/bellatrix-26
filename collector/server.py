import asyncio
import datetime
import json
import uuid
from typing import Dict, Any, Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from collector.main import Tier1Collector
from collector.config import collector_config

app = FastAPI(title="AEGIS Tier 1 Bank Collector", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

collector = Tier1Collector()
_simulated_outage = False
_loop_task: Optional[asyncio.Task] = None

class RawLogPayload(BaseModel):
    service: str = "system-auth"
    user_identifier: Optional[str] = "admin_user"
    session_id: Optional[str] = "SESS-50100492817291"
    secret_token: Optional[str] = "ABCDE1234F"
    masked_id: Optional[str] = "XXXX-XXXX-9821"
    auth_token: Optional[str] = "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
    client_ip: Optional[str] = "103.21.144.12"
    cpu_usage: Optional[float] = 45.2
    memory_usage: Optional[float] = 68.0
    disk_usage: Optional[float] = 52.0
    latency_ms: Optional[float] = 32.5

@app.get("/status")
@app.get("/health")
async def get_status():
    pending_cnt = collector.storage.count_pending()
    return {
        "collector_id": collector.config.COLLECTOR_ID,
        "tenant_id": collector.config.TENANT_ID,
        "status": "Online",
        "simulated_outage": _simulated_outage,
        "pending_buffered": pending_cnt,
        "collection_interval_sec": collector.config.COLLECTION_INTERVAL_SECONDS,
        "heartbeat_interval_sec": collector.config.HEARTBEAT_INTERVAL_SECONDS,
        "host": "Windows 11 Live Collector (psutil)",
        "timestamp_utc": datetime.datetime.now(datetime.timezone.utc).isoformat()
    }

@app.post("/simulate/outage")
async def simulate_outage():
    global _simulated_outage
    _simulated_outage = True
    return {
        "status": "Outage Simulated",
        "message": "Tier 2 uplink disabled. Telemetry is now buffering locally in Tier 1 SQLite outbox.",
        "pending_buffered": collector.storage.count_pending()
    }

@app.post("/simulate/reconnect")
async def simulate_reconnect():
    global _simulated_outage
    _simulated_outage = False
    collector.drain_outbox_backlog()
    return {
        "status": "Reconnected",
        "message": "Tier 2 uplink restored. Flushed local buffer without duplicates.",
        "pending_buffered": collector.storage.count_pending()
    }

@app.post("/inject/raw-pii")
async def inject_raw_pii_log(payload: RawLogPayload):
    """
    Simulates receiving raw banking log with sensitive PII in Tier 1.
    Scrubs PII locally, sends only canonical approved metadata to Tier 2,
    and returns cryptographic egress proof diff.
    """
    raw_dict = payload.model_dump()
    raw_str = json.dumps(raw_dict, indent=2)
    payload_id = f"PAYLOAD-PII-{uuid.uuid4().hex[:8].upper()}"
    raw_dict["payload_id"] = payload_id
    raw_dict["tenant_id"] = collector.config.TENANT_ID
    raw_dict["collector_id"] = collector.config.COLLECTOR_ID
    raw_dict["source_id"] = collector.config.SOURCE_ID
    raw_dict["timestamp_utc"] = datetime.datetime.now(datetime.timezone.utc).isoformat()

    # Apply Tier 1 Privacy Engine
    approved_payload, approved_fields, dropped_fields = collector.privacy_engine.apply_policy(raw_dict)

    # Generate deterministic egress proof
    proof_bundle = collector.proof_gen.generate_proof(approved_payload, approved_fields, dropped_fields)
    proof_rec = proof_bundle["proof_record"]
    proof_rec["raw_local_log_blocked"] = raw_str

    # Attempt transmission
    if not _simulated_outage:
        success, resp = collector.client.send_metadata(proof_bundle["payload_to_send"])
        if success:
            proof_rec["transmission_status"] = "Delivered & Acknowledged"
            collector.storage.record_proof(proof_rec, "Delivered")
        else:
            collector.storage.enqueue_outbox(payload_id, proof_bundle["payload_to_send"], raw_dict["timestamp_utc"])
            proof_rec["transmission_status"] = "Buffered Locally"
            collector.storage.record_proof(proof_rec, "Buffered")
    else:
        collector.storage.enqueue_outbox(payload_id, proof_bundle["payload_to_send"], raw_dict["timestamp_utc"])
        proof_rec["transmission_status"] = "Buffered Locally (Outage Simulation)"
        collector.storage.record_proof(proof_rec, "Buffered")

    return {
        "payload_id": payload_id,
        "raw_local_log_blocked": raw_str,
        "exact_transmitted_json": proof_rec["exact_transmitted_json"],
        "payload_hash": proof_rec["payload_hash"],
        "approved_fields": approved_fields,
        "redacted_fields": dropped_fields,
        "status": proof_rec["transmission_status"],
        "pending_buffered": collector.storage.count_pending()
    }

@app.get("/host/inventory")
async def get_host_inventory():
    """Exposes real discovered Windows host hardware inventory."""
    return await asyncio.to_thread(collector.host_inventory.collect_full_inventory)

@app.get("/host/cpu")
async def get_host_cpu():
    """Exposes live CPU metrics from psutil."""
    return await asyncio.to_thread(collector.metrics_source.cpu_monitor.collect)

@app.get("/host/memory")
async def get_host_memory():
    """Exposes live RAM and Swap metrics from psutil."""
    return await asyncio.to_thread(collector.metrics_source.memory_monitor.collect)

@app.get("/host/disk")
async def get_host_disk():
    """Exposes partition capacity and disk I/O throughput."""
    return await asyncio.to_thread(collector.metrics_source.disk_monitor.collect)

@app.get("/host/network")
async def get_host_network():
    """Exposes network throughput and latency probe."""
    return await asyncio.to_thread(collector.metrics_source.network_monitor.collect)

@app.get("/host/processes")
async def get_host_processes(limit: int = 15):
    """Exposes top resource-consuming processes in safe privacy mode."""
    return await asyncio.to_thread(collector.metrics_source.process_monitor.collect, limit)

@app.get("/host/services")
async def get_host_services():
    """Exposes monitored Windows service states."""
    return await asyncio.to_thread(collector.metrics_source.service_monitor.collect)

async def background_telemetry_loop():
    last_hb = 0.0
    while True:
        try:
            now = asyncio.get_event_loop().time()
            if not _simulated_outage:
                await asyncio.to_thread(collector.run_cycle)
            else:
                # Still collect and buffer
                raw_telemetry = await asyncio.to_thread(collector.metrics_source.collect)
                pid = str(uuid.uuid4())
                ts = datetime.datetime.now(datetime.timezone.utc).isoformat()
                raw_telemetry["payload_id"] = pid
                raw_telemetry["tenant_id"] = collector.config.TENANT_ID
                raw_telemetry["collector_id"] = collector.config.COLLECTOR_ID
                raw_telemetry["source_id"] = collector.config.SOURCE_ID
                raw_telemetry["timestamp_utc"] = ts
                approved, app_f, drop_f = collector.privacy_engine.apply_policy(raw_telemetry)
                collector.storage.enqueue_outbox(pid, approved, ts)

            if now - last_hb >= collector.config.HEARTBEAT_INTERVAL_SECONDS:
                if not _simulated_outage:
                    await asyncio.to_thread(collector.heartbeat_cycle)
                last_hb = now
        except Exception as e:
            print(f"[Tier 1 Collector Server] Error in loop: {e}")
        await asyncio.sleep(collector.config.COLLECTION_INTERVAL_SECONDS)

@app.on_event("startup")
async def startup_event():
    global _loop_task
    _loop_task = asyncio.create_task(background_telemetry_loop())

@app.on_event("shutdown")
async def shutdown_event():
    if _loop_task:
        _loop_task.cancel()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("collector.server:app", host="0.0.0.0", port=8001, reload=False)
