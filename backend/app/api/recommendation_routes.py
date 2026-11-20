import json
from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from backend.app.database import get_db
from backend.app.models import Incident, User, AnomalyRecord
from backend.app.schemas import RecommendationOut
from backend.app.auth.security import get_current_user
from backend.app.aiops.engine import aiops_engine

router = APIRouter(prefix="/recommendations", tags=["Recommendations"])

@router.get("", response_model=List[RecommendationOut])
async def list_recommendations(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    DIFFERENTIATOR 4: EXPLAINABLE AI INSIGHTS
    Returns structured recommendations tied directly to real backend incidents and anomaly evidence.
    """
    # Fetch active incidents
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

        recommendations.append(RecommendationOut(
            recommendation_id=rec_dict["recommendation_id"],
            incident_id=rec_dict["incident_id"],
            title=rec_dict["title"],
            reason=rec_dict["reason"],
            severity=rec_dict["severity"],
            confidence=rec_dict["confidence"],
            supporting_evidence=rec_dict["supporting_evidence"],
            suggested_action=rec_dict["suggested_action"]
        ))

    return recommendations
