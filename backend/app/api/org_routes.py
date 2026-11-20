from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from backend.app.database import get_db
from backend.app.models import Organization, User
from backend.app.auth.security import get_current_user

router = APIRouter(prefix="/organizations", tags=["Organizations"])

@router.get("/profile")
async def get_org_profile(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(Organization).where(Organization.tenant_id == current_user.tenant_id)
    org = (await db.execute(stmt)).scalar_one_or_none()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found.")
    
    return {
        "tenant_id": org.tenant_id,
        "name": org.name,
        "region": org.region,
        "timezone": org.timezone,
        "created_at": org.created_at.isoformat() if org.created_at else None
    }
