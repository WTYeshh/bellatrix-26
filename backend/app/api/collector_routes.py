import datetime
from typing import List
from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from backend.app.database import get_db
from backend.app.models import Collector, User
from backend.app.schemas import CollectorRegister, CollectorHeartbeat, CollectorOut
from backend.app.auth.security import get_current_user
from backend.app.config import settings

router = APIRouter(prefix="/collectors", tags=["Collectors"])

@router.get("", response_model=List[CollectorOut])
async def list_collectors(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Lists all collectors belonging to the authorized user's tenant."""
    stmt = select(Collector).where(Collector.tenant_id == current_user.tenant_id)
    collectors = (await db.execute(stmt)).scalars().all()
    
    now_utc = datetime.datetime.now(datetime.timezone.utc)
    out = []
    for c in collectors:
        # Check if collector has missed heartbeats > threshold
        is_offline = False
        if c.last_heartbeat:
            delta = (now_utc - c.last_heartbeat.replace(tzinfo=datetime.timezone.utc if not c.last_heartbeat.tzinfo else None)).total_seconds()
            if delta > settings.COLLECTOR_OFFLINE_THRESHOLD_SECONDS:
                is_offline = True
        else:
            is_offline = True

        status_str = "Offline" if is_offline else c.status
        out.append(CollectorOut(
            collector_id=c.collector_id,
            tenant_id=c.tenant_id,
            host_identifier=c.host_identifier,
            version=c.version,
            status=status_str,
            last_heartbeat=c.last_heartbeat.isoformat() if c.last_heartbeat else "Never",
            pending_buffered=c.pending_buffered,
            cpu_usage=c.cpu_usage,
            memory_usage=c.memory_usage,
            os_info=c.os_info,
            last_delivery_success=c.last_delivery_success.isoformat() if c.last_delivery_success else None
        ))
    return out

@router.post("/register")
async def register_collector(
    req: CollectorRegister,
    x_tenant_id: str = Header(..., alias="X-Tenant-Id"),
    x_auth_token: str = Header(..., alias="X-Auth-Token"),
    db: AsyncSession = Depends(get_db)
):
    """Registers a new Tier 1 collector for a tenant."""
    stmt = select(Collector).where(Collector.collector_id == req.collector_id, Collector.tenant_id == x_tenant_id)
    existing = (await db.execute(stmt)).scalar_one_or_none()
    now_utc = datetime.datetime.now(datetime.timezone.utc)

    if existing:
        existing.host_identifier = req.host_identifier
        existing.version = req.version
        existing.os_info = req.os_info or existing.os_info
        existing.last_heartbeat = now_utc
        existing.status = "Online"
        await db.commit()
        return {"status": "Updated", "collector_id": req.collector_id}

    new_collector = Collector(
        collector_id=req.collector_id,
        tenant_id=x_tenant_id,
        host_identifier=req.host_identifier,
        version=req.version,
        status="Online",
        last_heartbeat=now_utc,
        auth_token=x_auth_token,
        os_info=req.os_info or "Unknown"
    )
    db.add(new_collector)
    await db.commit()
    return {"status": "Registered", "collector_id": req.collector_id}

@router.post("/heartbeat")
async def collector_heartbeat(
    req: CollectorHeartbeat,
    x_tenant_id: str = Header(..., alias="X-Tenant-Id"),
    x_auth_token: str = Header(..., alias="X-Auth-Token"),
    db: AsyncSession = Depends(get_db)
):
    """Heartbeat endpoint called periodically by Tier 1 collector."""
    stmt = select(Collector).where(
        Collector.collector_id == req.collector_id,
        Collector.tenant_id == x_tenant_id
    )
    collector = (await db.execute(stmt)).scalar_one_or_none()
    if not collector:
        # Auto-register if valid token format
        now_utc = datetime.datetime.now(datetime.timezone.utc)
        collector = Collector(
            collector_id=req.collector_id,
            tenant_id=x_tenant_id,
            host_identifier=req.collector_id,
            status="Online",
            last_heartbeat=now_utc,
            auth_token=x_auth_token,
            pending_buffered=req.pending_buffered,
            cpu_usage=req.cpu_usage,
            memory_usage=req.memory_usage,
            os_info=req.os_info or "Linux/Windows"
        )
        db.add(collector)
        await db.commit()
        return {"status": "Heartbeat Received (Auto-Registered)", "server_time": now_utc.isoformat()}

    now_utc = datetime.datetime.now(datetime.timezone.utc)
    collector.last_heartbeat = now_utc
    collector.status = req.status
    collector.cpu_usage = req.cpu_usage
    collector.memory_usage = req.memory_usage
    collector.pending_buffered = req.pending_buffered
    if req.os_info:
        collector.os_info = req.os_info

    await db.commit()
    return {"status": "Heartbeat Received", "server_time": now_utc.isoformat()}
