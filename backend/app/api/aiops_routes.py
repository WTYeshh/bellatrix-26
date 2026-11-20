import json
from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import desc

from backend.app.database import get_db
from backend.app.models import AnomalyRecord, User, MetricRecord
from backend.app.schemas import AnomalyOut
from backend.app.auth.security import get_current_user
from backend.app.aiops.engine import aiops_engine

router = APIRouter(prefix="/aiops", tags=["AIOps Engine"])

@router.get("/anomalies", response_model=List[AnomalyOut])
async def list_anomalies(
    current_user: User = Depends(get_current_user),
    limit: int = 50,
    db: AsyncSession = Depends(get_db)
):
    stmt = (
        select(AnomalyRecord)
        .where(AnomalyRecord.tenant_id == current_user.tenant_id)
        .order_by(desc(AnomalyRecord.timestamp_utc))
        .limit(limit)
    )
    records = (await db.execute(stmt)).scalars().all()
    out = []
    for r in records:
        try:
            sigs = json.loads(r.contributing_signals) if isinstance(r.contributing_signals, str) else r.contributing_signals
        except:
            sigs = []
        out.append(AnomalyOut(
            anomaly_id=r.anomaly_id,
            source_id=r.source_id,
            metric=r.metric,
            observed_value=r.observed_value,
            baseline_value=r.baseline_value,
            anomaly_score=r.anomaly_score,
            severity=r.severity,
            reason=r.reason,
            contributing_signals=sigs,
            timestamp_utc=r.timestamp_utc.isoformat() if r.timestamp_utc else ""
        ))
    return out

@router.get("/baselines")
async def get_baselines(
    current_user: User = Depends(get_current_user),
    source_id: str = "SERVER_01"
):
    """Returns real-time computed statistical baselines (mean, median, std, MAD) for a source."""
    metrics = ["cpu_usage", "memory_usage", "disk_usage", "latency_ms"]
    baselines = {}
    for m in metrics:
        baselines[m] = aiops_engine.calculate_statistical_baseline(current_user.tenant_id, source_id, m)
    return {
        "tenant_id": current_user.tenant_id,
        "source_id": source_id,
        "baselines": baselines
    }

@router.get("/pipeline-status")
async def get_pipeline_status(current_user: User = Depends(get_current_user)):
    """AIOps 5-stage roadmap status."""
    return {
        "observe": {"status": "Active", "description": "Continuous telemetry streaming from Tier 1 collectors"},
        "detect": {"status": "Active", "description": "Dual engine: Rolling Robust Z-Score + Scikit-Learn Isolation Forest"},
        "correlate": {"status": "Active", "description": "Incident DNA temporal & topological graph correlation"},
        "recommend": {"status": "Active", "description": "Transparent evidence-backed remediation suggestions"},
        "act": {"status": "Human-Approved", "description": "Safe recovery simulation sandbox with policy audit & rollback"}
    }
