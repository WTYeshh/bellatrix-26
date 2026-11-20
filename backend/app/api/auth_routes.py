from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from backend.app.database import get_db
from backend.app.models import User, Organization
from backend.app.schemas import LoginRequest, RegisterRequest, TokenResponse, UserOut
from backend.app.auth.security import (
    hash_password, verify_password, create_access_token, get_current_user
)

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/login", response_model=TokenResponse)
async def login(req: LoginRequest, db: AsyncSession = Depends(get_db)):
    stmt = select(User).where(User.email == req.email)
    res = await db.execute(stmt)
    user = res.scalar_one_or_none()

    if not user or not verify_password(req.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password."
        )

    # Fetch organization name
    org_stmt = select(Organization).where(Organization.tenant_id == user.tenant_id)
    org = (await db.execute(org_stmt)).scalar_one_or_none()
    org_name = org.name if org else "AEGIS Organization"

    token = create_access_token({"sub": str(user.id), "tenant_id": user.tenant_id, "role": user.role})
    
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user={
            "id": user.id,
            "email": user.email,
            "name": user.full_name,
            "role": user.role,
            "org": org_name,
            "orgId": user.tenant_id
        }
    )

@router.post("/register")
async def register(req: RegisterRequest, db: AsyncSession = Depends(get_db)):
    # Check if user already exists
    stmt = select(User).where(User.email == req.admin_email)
    if (await db.execute(stmt)).scalar_one_or_none():
        raise HTTPException(status_code=400, detail="A user with this email already exists.")

    tenant_id = f"ORG_{req.org_name.lower().replace(' ', '_')[:12]}_{abs(hash(req.admin_email)) % 1000:03d}"

    # Create Organization
    org = Organization(
        tenant_id=tenant_id,
        name=req.org_name,
        region=req.region or "us-east-1",
        timezone=req.timezone or "UTC"
    )
    db.add(org)

    # Create Admin User
    user = User(
        tenant_id=tenant_id,
        email=req.admin_email,
        password_hash=hash_password(req.password),
        full_name=req.admin_name,
        role="Organization Owner",
        is_active=True
    )
    db.add(user)
    await db.commit()

    return {"message": "Organization registered successfully.", "tenant_id": tenant_id}

@router.get("/me", response_model=UserOut)
async def get_me(current_user: User = Depends(get_current_user)):
    return UserOut(
        id=current_user.id,
        tenant_id=current_user.tenant_id,
        email=current_user.email,
        full_name=current_user.full_name,
        role=current_user.role,
        is_active=current_user.is_active
    )
