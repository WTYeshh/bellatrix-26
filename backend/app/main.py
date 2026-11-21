import datetime
import json
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.config import settings
from backend.app.database import engine, Base, AsyncSessionLocal
from backend.app.models import (
    Organization, User, Collector, PrivacyPolicy,
    Incident, RecoverySimulation, EgressProof, AuditRecord, MetricRecord, SecuritySummary
)
from backend.app.auth.security import hash_password
from backend.app.ingestion.pipeline import STRICT_ALLOWED_FIELDS

# Import active routers
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
from backend.app.api.system_routes import router as system_router

async def init_server_identity():
    """Initializes authentic server-01 node identity in database."""
    async with AsyncSessionLocal() as session:
        res = await session.execute(select(Organization).where(Organization.tenant_id == "default"))
        if not res.scalar_one_or_none():
            org = Organization(
                tenant_id="default",
                name="AEGIS Server Node",
                region="local",
                timezone="UTC"
            )
            session.add(org)

            admin_user = User(
                tenant_id="default",
                email="admin@aegis.local",
                password_hash=hash_password("aegis2026"),
                full_name="System Administrator",
                role="System Administrator",
                is_active=True
            )
            session.add(admin_user)

            col = Collector(
                collector_id="COLLECTOR_SERVER_01",
                tenant_id="default",
                host_identifier="server-01",
                version="1.0.0",
                status="Online",
                auth_token="aegis-collector-token-server01",
                os_info="Windows Host (Physical Laptop)",
                cpu_usage=0.0,
                memory_usage=0.0,
                pending_buffered=0,
                last_heartbeat=datetime.datetime.now(datetime.timezone.utc)
            )
            session.add(col)

            pol = PrivacyPolicy(
                tenant_id="default",
                version="v1.0",
                name="Strict Allow-List & Redaction",
                allowed_fields=str(list(STRICT_ALLOWED_FIELDS)),
                redaction_rules="{}",
                is_active=True
            )
            session.add(pol)
            await session.commit()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: ensure tables created and initial node identity registered
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await init_server_identity()
    yield
    # Shutdown
    await engine.dispose()

app = FastAPI(
    title="AEGIS Privacy-First Server Observability Platform",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?",
    allow_credentials=True,
    allow_private_network=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
@app.get("/api/health")
@app.get("/api/v1/health")
async def health_check():
    from sqlalchemy import text
    db_status = "disconnected"
    db_type = "sqlite"
    try:
        async with AsyncSessionLocal() as session:
            res = await session.execute(text("SELECT 1"))
            val = res.scalar()
            if val == 1:
                db_status = "connected"
    except Exception as e:
        db_status = f"disconnected: {str(e)}"

    is_healthy = db_status == "connected"
    return {
        "status": "healthy" if is_healthy else "degraded",
        "database": db_status,
        "database_type": db_type,
        "service": "AEGIS Server Observability Backend",
        "node_id": "server-01",
        "version": "1.0.0",
        "timestamp_utc": datetime.datetime.now(datetime.timezone.utc).isoformat()
    }

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
    system_router
]

for r in routers:
    app.include_router(r, prefix="/api")
    app.include_router(r, prefix="/api/v1")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.app.main:app", host="0.0.0.0", port=8000, reload=True)
