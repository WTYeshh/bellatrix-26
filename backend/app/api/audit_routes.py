import json
import datetime
from typing import List, Dict, Any
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import desc

from backend.app.database import get_db
from backend.app.models import AuditRecord, User
from backend.app.schemas import AuditRecordOut
from backend.app.auth.security import get_current_user

router = APIRouter(prefix="/audit", tags=["Audit Center"])

@router.get("", response_model=List[AuditRecordOut])
@router.get("/", response_model=List[AuditRecordOut])
@router.get("/records", response_model=List[AuditRecordOut])
async def list_audit_logs(
    current_user: User = Depends(get_current_user),
    limit: int = 50,
    db: AsyncSession = Depends(get_db)
):
    stmt = (
        select(AuditRecord)
        .where(AuditRecord.tenant_id == current_user.tenant_id)
        .order_by(desc(AuditRecord.timestamp_utc))
        .limit(limit)
    )
    records = (await db.execute(stmt)).scalars().all()
    out = []
    for r in records:
        try:
            details = json.loads(r.details) if isinstance(r.details, str) else r.details
        except:
            details = {}
        out.append(AuditRecordOut(
            id=r.id,
            actor=r.actor,
            action=r.action,
            target=r.target,
            result=r.result,
            details=details,
            timestamp_utc=r.timestamp_utc.isoformat() if r.timestamp_utc else ""
        ))
    return out

@router.post("/log")
async def create_audit_log(
    entry: Dict[str, Any],
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    record = AuditRecord(
        tenant_id=current_user.tenant_id,
        actor=entry.get("actor", current_user.email),
        action=entry.get("action", "Configuration Change"),
        target=entry.get("target", "System Settings"),
        result=entry.get("result", "Success"),
        details=json.dumps(entry.get("details", {})),
        timestamp_utc=datetime.datetime.now(datetime.timezone.utc)
    )
    db.add(record)
    await db.commit()
    return {"status": "Audit Record Created", "id": record.id}
