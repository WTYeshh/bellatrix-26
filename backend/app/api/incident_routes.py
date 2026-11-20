import json
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import desc

from backend.app.database import get_db
from backend.app.models import Incident, User
from backend.app.schemas import IncidentOut
from backend.app.auth.security import get_current_user

router = APIRouter(prefix="/incidents", tags=["Incidents"])

@router.get("", response_model=List[IncidentOut])
async def list_incidents(
    current_user: User = Depends(get_current_user),
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    stmt = select(Incident).where(Incident.tenant_id == current_user.tenant_id)
    if status:
        stmt = stmt.where(Incident.status == status)
    stmt = stmt.order_by(desc(Incident.created_at))

    incidents = (await db.execute(stmt)).scalars().all()
    out = []
    for inc in incidents:
        try:
            aff_cols = json.loads(inc.affected_collectors) if isinstance(inc.affected_collectors, str) else inc.affected_collectors
        except:
            aff_cols = []
        try:
            rel_alerts = json.loads(inc.related_alerts) if isinstance(inc.related_alerts, str) else inc.related_alerts
        except:
            rel_alerts = []
        try:
            timeline = json.loads(inc.timeline) if isinstance(inc.timeline, str) else inc.timeline
        except:
            timeline = []

        out.append(IncidentOut(
            incident_id=inc.incident_id,
            title=inc.title,
            severity=inc.severity,
            status=inc.status,
            affected_service=inc.affected_service,
            affected_collectors=aff_cols,
            related_alerts=rel_alerts,
            timeline=timeline,
            likely_cause=inc.likely_cause,
            recommended_investigation=inc.recommended_investigation,
            confidence=inc.confidence,
            created_at=inc.created_at.isoformat() if inc.created_at else "",
            resolved_at=inc.resolved_at.isoformat() if inc.resolved_at else None
        ))
    return out

@router.post("/{incident_id}/resolve")
async def resolve_incident(
    incident_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(Incident).where(
        Incident.incident_id == incident_id,
        Incident.tenant_id == current_user.tenant_id
    )
    inc = (await db.execute(stmt)).scalar_one_or_none()
    if not inc:
        raise HTTPException(status_code=404, detail="Incident not found.")
    
    inc.status = "Resolved"
    await db.commit()
    return {"status": "Resolved", "incident_id": incident_id}
