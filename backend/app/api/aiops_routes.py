import json
from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import desc

from backend.app.database import get_db
from backend.app.models import AnomalyRecord, User, MetricRecord, Incident
from backend.app.schemas import AnomalyOut, RecommendationOut
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

@router.get("/recommendations", response_model=List[RecommendationOut])
async def list_aiops_recommendations(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Explainable AIOps recommendations alias under /aiops/recommendations."""
    stmt = select(Incident).where(
        Incident.tenant_id == current_user.tenant_id,
        Incident.status.in_(["Active", "Investigating"])
    )
    incidents = (await db.execute(stmt)).scalars().all()
    recommendations = []

    for inc in incidents:
        try:
            rel_alerts = json.loads(inc.related_alerts) if isinstance(inc.related_alerts, str) else inc.related_alerts
        except:
            rel_alerts = []
        try:
            aff_cols = json.loads(inc.affected_collectors) if isinstance(inc.affected_collectors, str) else inc.affected_collectors
        except:
            aff_cols = []

        rec_dict = aiops_engine.generate_explainable_recommendation({
            "incident_id": inc.incident_id,
            "title": inc.title,
            "severity": inc.severity,
            "likely_cause": inc.likely_cause,
            "recommended_investigation": inc.recommended_investigation,
            "confidence": inc.confidence,
            "related_alerts": rel_alerts,
            "affected_collectors": aff_cols
        })
        recommendations.append(RecommendationOut(**rec_dict))

    return recommendations

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

from pydantic import BaseModel
from typing import Optional, Dict, Any

class CopilotChatRequest(BaseModel):
    message: str
    include_telemetry: bool = True

@router.post("/copilot/chat")
async def copilot_chat(
    req: CopilotChatRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    AI Copilot chat endpoint powered by Google Gemini (gemini-3.8-flash).
    Provides real-time answers grounded in the host's actual Windows telemetry.
    """
    telemetry_context = {}
    if req.include_telemetry:
        latest_stmt = (
            select(MetricRecord)
            .where(MetricRecord.tenant_id == current_user.tenant_id)
            .order_by(desc(MetricRecord.timestamp_utc))
            .limit(5)
        )
        recent_records = (await db.execute(latest_stmt)).scalars().all()
        if recent_records:
            latest = recent_records[0]
            telemetry_context = {
                "source": latest.source_id,
                "cpu_usage_pct": latest.cpu_usage,
                "memory_usage_pct": latest.memory_usage,
                "disk_usage_pct": latest.disk_usage,
                "latency_ms": latest.latency_ms,
                "health_state": latest.health_state,
                "timestamp": latest.timestamp_utc.isoformat() if latest.timestamp_utc else None
            }

    ai_reply = aiops_engine.explanation_engine.ask_copilot(
        question=req.message,
        telemetry_context=telemetry_context
    )

    return {
        "reply": ai_reply,
        "model": aiops_engine.explanation_engine.model_name,
        "grounded_telemetry": telemetry_context,
        "tenant_id": current_user.tenant_id
    }

@router.post("/incidents/{incident_id}/ai-analysis")
async def incident_ai_analysis(
    incident_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Generates an on-demand Gemini AI root cause analysis for a specific incident.
    """
    stmt = select(Incident).where(
        Incident.tenant_id == current_user.tenant_id,
        Incident.incident_id == incident_id
    )
    inc = (await db.execute(stmt)).scalar_one_or_none()
    if not inc:
        return {"error": "Incident not found"}

    try:
        rel_alerts = json.loads(inc.related_alerts) if isinstance(inc.related_alerts, str) else inc.related_alerts
    except:
        rel_alerts = []
    try:
        aff_cols = json.loads(inc.affected_collectors) if isinstance(inc.affected_collectors, str) else inc.affected_collectors
    except:
        aff_cols = []

    ai_analysis = aiops_engine.explanation_engine.generate_ai_explanation({
        "incident_id": inc.incident_id,
        "title": inc.title,
        "severity": inc.severity,
        "likely_cause": inc.likely_cause,
        "recommended_investigation": inc.recommended_investigation,
        "confidence": inc.confidence,
        "related_alerts": rel_alerts,
        "affected_collectors": aff_cols
    })

    return {
        "incident_id": incident_id,
        "ai_analysis": ai_analysis,
        "model": aiops_engine.explanation_engine.model_name
    }

