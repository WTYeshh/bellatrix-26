import datetime
import os
import json
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.future import select

from backend.app.config import settings
from backend.app.database import engine, Base, AsyncSessionLocal
from backend.app.models import (
    Organization, User, Collector, PrivacyPolicy, MetricRecord,
    Incident, RecoverySimulation, EgressProof, SecuritySummary, AuditRecord
)
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
from backend.app.api.system_routes import router as system_router

async def seed_initial_data():
    """Seeds default banking organizations, users, collectors, and INC-2026-089 from banking_seed_data.json."""
    seed_path = Path(__file__).parent.parent / "banking_seed_data.json"
    if not seed_path.exists():
        seed_path = Path("backend/banking_seed_data.json")

    async with AsyncSessionLocal() as session:
        # Check if banking tenant exists
        res = await session.execute(select(Organization).where(Organization.tenant_id == "BANK_HDFC_IN"))
        if not res.scalar_one_or_none():
            now_utc = datetime.datetime.now(datetime.timezone.utc)
            
            if seed_path.exists():
                with open(seed_path, "r", encoding="utf-8") as f:
                    seed_data = json.load(f)

                # 1. Organizations
                for org_d in seed_data.get("organizations", []):
                    session.add(Organization(**org_d))

                # Also ensure legacy ORG_001 exists for backwards compatibility
                legacy_res = await session.execute(select(Organization).where(Organization.tenant_id == "ORG_001"))
                if not legacy_res.scalar_one_or_none():
                    session.add(Organization(tenant_id="ORG_001", name="AEGIS Demo Corp", region="us-east-1"))

                legacy_user_res = await session.execute(select(User).where(User.tenant_id == "ORG_001"))
                if not legacy_user_res.scalar_one_or_none():
                    session.add(User(
                        tenant_id="ORG_001",
                        email="admin@acme.corp",
                        password_hash=hash_password("aegis2026"),
                        full_name="Acme Admin",
                        role="Organization Owner",
                        is_active=True
                    ))

                # 2. Users
                for u_d in seed_data.get("users", []):
                    u = User(
                        tenant_id=u_d["tenant_id"],
                        email=u_d["email"],
                        password_hash=hash_password(u_d.get("password", "aegis2026")),
                        full_name=u_d["full_name"],
                        role=u_d.get("role", "Organization Owner"),
                        is_active=True
                    )
                    session.add(u)

                # Collectors from seed + explicit COLLECTOR_MUM_01 and COLLECTOR_BLR_02
                for c_d in seed_data.get("collectors", []):
                    offset = c_d.get("last_heartbeat_offset_sec", 10)
                    col = Collector(
                        collector_id=c_d["collector_id"],
                        tenant_id=c_d["tenant_id"],
                        host_identifier=c_d["host_identifier"],
                        version=c_d.get("version", "2.4.1"),
                        status=c_d.get("status", "Online"),
                        environment=c_d.get("environment", "production"),
                        pending_buffered=c_d.get("pending_buffered", 0),
                        cpu_usage=c_d.get("cpu_usage", 30.0),
                        memory_usage=c_d.get("memory_usage", 50.0),
                        os_info=c_d.get("os_info", "Windows Server 2022"),
                        auth_token=c_d.get("auth_token", "demo-token"),
                        last_heartbeat=now_utc - datetime.timedelta(seconds=offset),
                        last_delivery_success=now_utc - datetime.timedelta(seconds=offset)
                    )
                    session.add(col)

                # Explicit named collectors for BANK_HDFC_IN
                session.add(Collector(
                    collector_id="COLLECTOR_MUM_01",
                    tenant_id="BANK_HDFC_IN",
                    host_identifier="node_upi_gw_02",
                    version="2.4.1",
                    status="Online",
                    environment="production",
                    pending_buffered=0,
                    cpu_usage=42.5,
                    memory_usage=64.2,
                    os_info="Windows Server 2022 Datacenter",
                    auth_token="aegis-hdfc-collector-token-01",
                    last_heartbeat=now_utc - datetime.timedelta(seconds=5),
                    last_delivery_success=now_utc - datetime.timedelta(seconds=5)
                ))
                session.add(Collector(
                    collector_id="COLLECTOR_BLR_02",
                    tenant_id="BANK_HDFC_IN",
                    host_identifier="node_core_db_01",
                    version="2.4.1",
                    status="Online",
                    environment="production",
                    pending_buffered=3,
                    cpu_usage=28.1,
                    memory_usage=48.0,
                    os_info="Windows 11 Enterprise",
                    auth_token="aegis-hdfc-collector-token-02",
                    last_heartbeat=now_utc - datetime.timedelta(seconds=75), # >60s to demonstrate status degradation
                    last_delivery_success=now_utc - datetime.timedelta(seconds=75)
                ))

                # Legacy collector
                session.add(Collector(
                    collector_id="COLLECTOR_001",
                    tenant_id="ORG_001",
                    host_identifier="prod-edge-node-01",
                    version="1.0.0",
                    status="Online",
                    auth_token="aegis-collector-token-001",
                    os_info="Windows 11 / x86_64",
                    last_heartbeat=now_utc
                ))

                # 4. Privacy Policies
                for p_d in seed_data.get("privacy_policies", []):
                    pol = PrivacyPolicy(
                        tenant_id=p_d["tenant_id"],
                        version=p_d.get("version", "v2.4"),
                        name=p_d.get("name", "RBI Strict Allow-List"),
                        allowed_fields=json.dumps(p_d.get("allowed_fields", list(STRICT_ALLOWED_FIELDS))),
                        redaction_rules=json.dumps(p_d.get("redaction_rules", {})),
                        is_active=True
                    )
                    session.add(pol)

                # 5. Incidents (including INC-2026-089)
                for inc_d in seed_data.get("incidents", []):
                    inc = Incident(
                        incident_id=inc_d["incident_id"],
                        tenant_id=inc_d["tenant_id"],
                        title=inc_d["title"],
                        severity=inc_d.get("severity", "Critical"),
                        status=inc_d.get("status", "Active"),
                        affected_service=inc_d.get("affected_service", "UPI-Payment-Switch-v3"),
                        affected_collectors=json.dumps(inc_d.get("affected_collectors", [])),
                        related_alerts=json.dumps(inc_d.get("related_alerts", [])),
                        timeline=json.dumps(inc_d.get("timeline", [])),
                        likely_cause=inc_d.get("likely_cause", ""),
                        recommended_investigation=inc_d.get("recommended_investigation", ""),
                        confidence=inc_d.get("confidence", 0.94),
                        created_at=now_utc - datetime.timedelta(minutes=25)
                    )
                    session.add(inc)

                # 6. Recovery Simulations
                for r_d in seed_data.get("recovery_simulations", []):
                    sim = RecoverySimulation(
                        simulation_id=r_d["simulation_id"],
                        tenant_id=r_d["tenant_id"],
                        incident_id=r_d["incident_id"],
                        recommendation_text=r_d["recommendation_text"],
                        status=r_d.get("status", "Pending Approval"),
                        approver=r_d.get("approver"),
                        simulated_action=r_d.get("simulated_action", ""),
                        policy_check=r_d.get("policy_check", "Passed"),
                        simulation_result=r_d.get("simulation_result", ""),
                        rollback_info=r_d.get("rollback_info", ""),
                        created_at=now_utc - datetime.timedelta(minutes=10)
                    )
                    session.add(sim)

                # 7. Egress Proofs (with raw_local_log_blocked)
                for e_d in seed_data.get("egress_proofs", []):
                    ep = EgressProof(
                        payload_id=e_d["payload_id"],
                        tenant_id=e_d["tenant_id"],
                        source_id=e_d["source_id"],
                        timestamp_utc=now_utc - datetime.timedelta(minutes=5),
                        raw_local_log_blocked=e_d.get("raw_local_log_blocked", ""),
                        approved_fields=json.dumps(e_d.get("approved_fields", [])),
                        redacted_fields=json.dumps(e_d.get("redacted_fields", [])),
                        applied_policy=e_d.get("applied_policy", "Standard-v1"),
                        exact_transmitted_json=e_d["exact_transmitted_json"],
                        payload_hash=e_d["payload_hash"],
                        transmission_status=e_d.get("transmission_status", "Delivered & Verified"),
                        server_ack_utc=now_utc - datetime.timedelta(minutes=5)
                    )
                    session.add(ep)

                # 8. Security Summaries
                for s_d in seed_data.get("security_summaries", []):
                    ss = SecuritySummary(
                        payload_id=f"SEC-{s_d['source_id']}-{int(now_utc.timestamp())}",
                        tenant_id=s_d["tenant_id"],
                        source_id=s_d["source_id"],
                        event_category=s_d.get("event_category", "Authentication"),
                        severity=s_d.get("severity", "High"),
                        failed_login_count=s_d.get("failed_login_count", 15),
                        time_window_sec=s_d.get("time_window_sec", 60),
                        description=s_d["description"],
                        timestamp_utc=now_utc - datetime.timedelta(minutes=12)
                    )
                    session.add(ss)

                # 9. Audit Records
                for a_d in seed_data.get("audit_records", []):
                    ar = AuditRecord(
                        tenant_id=a_d["tenant_id"],
                        actor=a_d["actor"],
                        action=a_d["action"],
                        target=a_d["target"],
                        result=a_d.get("result", "Success"),
                        details=json.dumps(a_d.get("details", {})),
                        timestamp_utc=now_utc - datetime.timedelta(minutes=8)
                    )
                    session.add(ar)

                # 10. Historical Metrics
                for idx, m_d in enumerate(seed_data.get("historical_metrics", [])):
                    m_ts = now_utc + datetime.timedelta(minutes=m_d["offset_min"])
                    m = MetricRecord(
                        payload_id=f"HIST-{m_d['tenant_id']}-{idx}",
                        tenant_id=m_d["tenant_id"],
                        source_id=f"core-node-{m_d['tenant_id'][:8]}",
                        collector_id=f"COL-{m_d['tenant_id'][:8]}-01",
                        timestamp_utc=m_ts,
                        cpu_usage=m_d["cpu"],
                        memory_usage=m_d["ram"],
                        disk_usage=45.0,
                        latency_ms=m_d["latency"],
                        packet_loss_pct=m_d["packet_loss"],
                        health_state=m_d["state"],
                        event_category="Performance",
                        severity="Low" if m_d["state"] in ["Excellent", "Good"] else ("Medium" if m_d["state"] == "Fair" else "Critical")
                    )
                    session.add(m)

                # Explicit nodes for Banking Infrastructure cards (node_upi_gw_02 & node_core_db_01)
                session.add(MetricRecord(
                    payload_id="LIVE-HDFC-NODE-UPI-GW-02",
                    tenant_id="BANK_HDFC_IN",
                    source_id="node_upi_gw_02",
                    collector_id="COLLECTOR_MUM_01",
                    timestamp_utc=now_utc - datetime.timedelta(seconds=2),
                    cpu_usage=88.5,
                    memory_usage=76.2,
                    disk_usage=48.0,
                    latency_ms=1420.0,
                    packet_loss_pct=2.4,
                    health_state="Poor",
                    event_category="UPI Gateway Latency Breach",
                    severity="Critical"
                ))
                session.add(MetricRecord(
                    payload_id="LIVE-HDFC-NODE-CORE-DB-01",
                    tenant_id="BANK_HDFC_IN",
                    source_id="node_core_db_01",
                    collector_id="COLLECTOR_BLR_02",
                    timestamp_utc=now_utc - datetime.timedelta(seconds=15),
                    cpu_usage=42.0,
                    memory_usage=68.5,
                    disk_usage=62.0,
                    latency_ms=24.0,
                    packet_loss_pct=0.0,
                    health_state="Good",
                    event_category="Core Oracle DB Telemetry",
                    severity="Low"
                ))

                await session.commit()
                print("[AEGIS Backend] Seeded Banking Dataset (BANK_HDFC_IN, BANK_ICICI_IN, INC-2026-089) successfully.")

        # Check if secondary isolated organization exists (for multi-tenant testing)
        res2 = await session.execute(select(Organization).where(Organization.tenant_id == "ORG_002"))
        if not res2.scalar_one_or_none():
            org2 = Organization(
                tenant_id="ORG_002",
                name="Globex Industries",
                region="eu-west-1",
                timezone="UTC"
            )
            session.add(org2)
            u2 = User(
                tenant_id="ORG_002",
                email="admin@globex.io",
                password_hash=hash_password("GlobexPass2026!"),
                full_name="Hank Scorpio",
                role="Organization Owner",
                is_active=True
            )
            session.add(u2)
            col2 = Collector(
                collector_id="COLLECTOR_GLOBEX_01",
                tenant_id="ORG_002",
                host_identifier="globex-core-prod-01",
                version="1.0.0",
                status="Online",
                auth_token="globex-collector-token-001",
                os_info="Ubuntu 22.04 LTS",
                cpu_usage=18.5,
                memory_usage=42.0,
                pending_buffered=0,
                last_heartbeat=datetime.datetime.now(datetime.timezone.utc)
            )
            session.add(col2)
            pol2 = PrivacyPolicy(
                tenant_id="ORG_002",
                version="v1.0",
                name="Globex Strict Allow-List",
                allowed_fields=str(list(STRICT_ALLOWED_FIELDS)),
                redaction_rules="{}",
                is_active=True
            )
            session.add(pol2)
            await session.commit()
            print("[AEGIS Backend] Seeded secondary isolated organization ORG_002 (Globex Industries).")

        # Check if legacy ORG_001 user exists (for backwards compatibility tests)
        res_u1 = await session.execute(select(User).where(User.tenant_id == "ORG_001"))
        if not res_u1.scalar_one_or_none():
            u1 = User(
                tenant_id="ORG_001",
                email="admin@acme.corp",
                password_hash=hash_password("aegis2026"),
                full_name="Acme Admin",
                role="Organization Owner",
                is_active=True
            )
            session.add(u1)
            await session.commit()
            print("[AEGIS Backend] Seeded legacy organization user for ORG_001.")

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

# Enable CORS for frontend integration with explicit origins and Private Network Access
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

# Health endpoint at root, /api/health, and /api/v1/health with genuine SELECT 1 db check
@app.get("/health")
@app.get("/api/health")
@app.get("/api/v1/health")
@app.get("/api/v1/system/health")
@app.get("/system/health")
async def health_check():
    from sqlalchemy import text
    db_status = "disconnected"
    db_type = "postgresql" if "postgresql" in settings.DATABASE_URL else "sqlite"
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
    demo_router,
    system_router
]

for r in routers:
    app.include_router(r, prefix="/api")
    app.include_router(r, prefix="/api/v1")

# Explicit aliases for ingestion endpoints
app.include_router(ingestion_router, prefix="/api/ingest")
app.include_router(ingestion_router, prefix="/api/v1/ingest")
app.include_router(ingestion_router, prefix="/api/ingestion")
app.include_router(ingestion_router, prefix="/api/v1/ingestion")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.app.main:app", host="0.0.0.0", port=8000, reload=True)
