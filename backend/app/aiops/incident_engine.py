import json
import datetime
from typing import Dict, Any, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import desc

from backend.app.models import Incident

class IncidentLifecycleEngine:
    """
    Manages incident persistence, state transitions, and timeline chronology.
    """
    async def create_or_update(
        self,
        tenant_id: str,
        incident_data: Dict[str, Any],
        db: AsyncSession
    ) -> Incident:
        now_utc = datetime.datetime.now(datetime.timezone.utc)
        
        inc = Incident(
            incident_id=incident_data["incident_id"],
            tenant_id=tenant_id,
            title=incident_data["title"],
            severity=incident_data["severity"],
            status=incident_data.get("status", "Active"),
            affected_service=incident_data.get("affected_service", "Fleet"),
            affected_collectors=json.dumps(incident_data.get("affected_collectors", [])),
            related_alerts=json.dumps(incident_data.get("related_alerts", [])),
            timeline=json.dumps(incident_data.get("timeline", [])),
            likely_cause=incident_data.get("likely_cause", "Operational anomaly"),
            recommended_investigation=incident_data.get("recommended_investigation", "Inspect metrics"),
            confidence=incident_data.get("confidence", 0.85),
            created_at=now_utc
        )
        db.add(inc)
        await db.commit()
        return inc

    async def get_active_incidents(self, tenant_id: str, db: AsyncSession) -> List[Incident]:
        stmt = (
            select(Incident)
            .where(Incident.tenant_id == tenant_id, Incident.status.in_(["Active", "Investigating"]))
            .order_by(desc(Incident.created_at))
        )
        return (await db.execute(stmt)).scalars().all()
