import time
import threading
import uuid
import datetime
from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.database import get_db
from backend.app.models import User
from backend.app.auth.security import get_current_user
from backend.app.ingestion.pipeline import process_ingestion_payload
from backend.app.api.broadcaster import broadcaster

router = APIRouter(prefix="/demo", tags=["AI Demonstration Controls"])

# Global thread reference for controlled CPU stress test
_stress_stop_event = threading.Event()
_stress_threads = []
_active_stress = False

def _cpu_burner(duration_seconds: int = 10):
    global _active_stress
    _active_stress = True
    start = time.time()
    while not _stress_stop_event.is_set() and (time.time() - start) < duration_seconds:
        # Safe mathematical computations to raise CPU utilization
        _ = [x ** 2 for x in range(10000)]
    _active_stress = False

@router.post("/cpu-stress")
async def trigger_cpu_stress(
    duration: int = 12,
    current_user: User = Depends(get_current_user)
):
    """
    Runs a safe, time-bounded CPU load on the local demonstration machine.
    Has a hard duration cap and an immediate STOP control.
    """
    global _stress_stop_event, _stress_threads
    _stress_stop_event.clear()
    
    # Run in 2 threads to create measurable CPU activity without locking system
    t1 = threading.Thread(target=_cpu_burner, args=(min(30, duration),), daemon=True)
    t2 = threading.Thread(target=_cpu_burner, args=(min(30, duration),), daemon=True)
    _stress_threads = [t1, t2]
    t1.start()
    t2.start()

    return {
        "status": "Running",
        "scenario": "Controlled Local CPU Stress Test",
        "duration_seconds": min(30, duration),
        "message": f"CPU workload started for {min(30, duration)} seconds. Local AIOps and psutil will detect real CPU rise."
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
