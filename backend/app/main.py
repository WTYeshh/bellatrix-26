import datetime
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.future import select

from backend.app.config import settings
from backend.app.database import engine, Base, AsyncSessionLocal
from backend.app.models import Organization, User, Collector, PrivacyPolicy
from backend.app.auth.security import hash_password
from backend.app.ingestion.pipeline import STRICT_ALLOWED_FIELDS

# Import routers
from backend.app.api.auth_routes import router as auth_router
from backend.app.api.org_routes import router as org_router
from backend.app.api.collector_routes import router as collector_router
from backend.app.api.ingestion_routes import router as ingestion_router
from backend.app.api.observability_routes import router as obs_router
from backend.app.api.incident_routes import router as incident_router
from backend.app.api.aiops_routes import router as aiops_router
from backend.app.api.recommendation_routes import router as rec_router
from backend.app.api.privacy_routes import router as privacy_router
from backend.app.api.egress_routes import router as egress_router
from backend.app.api.audit_routes import router as audit_router
from backend.app.api.recovery_routes import router as recovery_router
from backend.app.api.dashboard_routes import router as dashboard_router
from backend.app.api.stream_routes import router as stream_router
from backend.app.api.demo_routes import router as demo_router

async def seed_initial_data():
    """Seeds default organization, users, and collector if database is clean."""
    async with AsyncSessionLocal() as session:
        # Check if org exists
        res = await session.execute(select(Organization).where(Organization.tenant_id == "ORG_001"))
        if not res.scalar_one_or_none():
            org = Organization(
                tenant_id="ORG_001",
                name="AEGIS Demo Corp",
                region="us-east-1",
                timezone="UTC"
            )
            session.add(org)

            # Seed demo users
            demo_users = [
                ("admin@aegis.io", "Veeresh M V", "Organization Owner"),
                ("security@aegis.io", "Priya Sharma", "Security Engineer"),
                ("devops@aegis.io", "Rahul Kumar", "DevOps Engineer"),
            ]
            for email, name, role in demo_users:
                u = User(
                    tenant_id="ORG_001",
                    email=email,
                    password_hash=hash_password("aegis2026"),
                    full_name=name,
                    role=role,
                    is_active=True
                )
                session.add(u)

            # Seed default Tier 1 collector
            col = Collector(
                collector_id="COLLECTOR_001",
                tenant_id="ORG_001",
                host_identifier="prod-edge-node-01",
                version="1.0.0",
                status="Online",
                auth_token="aegis-collector-token-001",
                os_info="Windows 11 / x86_64",
                cpu_usage=32.4,
                memory_usage=58.2,
                pending_buffered=0,
                last_heartbeat=datetime.datetime.now(datetime.timezone.utc)
            )
            session.add(col)

            # Seed default Privacy Policy
            pol = PrivacyPolicy(
                tenant_id="ORG_001",
                version="v1.0",
                name="Strict Enterprise Allow-List & Redaction",
                allowed_fields=str(list(STRICT_ALLOWED_FIELDS)),
                redaction_rules="{}",
                is_active=True
            )
            session.add(pol)

            await session.commit()
            print("[AEGIS Backend] Seeded initial organization ORG_001 and demo users.")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await seed_initial_data()
    yield
    # Shutdown
    await engine.dispose()

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# Enable CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health endpoint at root and /api/health
@app.get("/health")
@app.get("/api/health")
@app.get("/api/v1/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "AEGIS Central SaaS Tier 2",
        "version": settings.VERSION,
        "timestamp_utc": datetime.datetime.now(datetime.timezone.utc).isoformat()
    }

# Mount routers under both /api and /api/v1 for maximum client compatibility
routers = [
    auth_router,
    org_router,
    collector_router,
    ingestion_router,
    obs_router,
    incident_router,
    aiops_router,
    rec_router,
    privacy_router,
    egress_router,
    audit_router,
    recovery_router,
    dashboard_router,
    stream_router,
    demo_router
]

for r in routers:
    app.include_router(r, prefix="/api")
    app.include_router(r, prefix="/api/v1")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.app.main:app", host="0.0.0.0", port=8000, reload=True)
