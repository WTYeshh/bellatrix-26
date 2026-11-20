import pytest
import datetime
import uuid
from httpx import AsyncClient, ASGITransport
from sqlalchemy.future import select

from backend.app.main import app, seed_initial_data
from backend.app.database import AsyncSessionLocal, engine, Base
from backend.app.models import Organization, User, Collector, MetricRecord, Incident

@pytest.mark.asyncio
async def test_saas_multitenant_isolation():
    """
    TEST: Multi-tenant SaaS isolation between ORG_001 (Acme) and ORG_002 (Globex).
    Verifies that all API queries, metrics, collectors, incidents, and org profiles
    are strictly isolated with zero cross-tenant data leakage.
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await seed_initial_data()

    async with AsyncSessionLocal() as session:
        # Verify both organizations exist in database
        org1 = (await session.execute(select(Organization).where(Organization.tenant_id == "ORG_001"))).scalar_one_or_none()
        org2 = (await session.execute(select(Organization).where(Organization.tenant_id == "ORG_002"))).scalar_one_or_none()
        assert org1 is not None, "ORG_001 must exist"
        assert org2 is not None, "ORG_002 must exist"
        assert org1.name == "AEGIS Demo Corp"
        assert org2.name == "Globex Industries"

        # Seed isolated metrics for ORG_001 and ORG_002
        m1 = MetricRecord(
            payload_id=str(uuid.uuid4()),
            tenant_id="ORG_001",
            source_id="ACME_SRV_01",
            collector_id="COLLECTOR_LOCAL_WIN",
            timestamp_utc=datetime.datetime.now(datetime.timezone.utc),
            cpu_usage=55.5,
            memory_usage=60.0,
            disk_usage=45.0,
            latency_ms=12.0,
            health_state="Good"
        )
        m2 = MetricRecord(
            payload_id=str(uuid.uuid4()),
            tenant_id="ORG_002",
            source_id="GLOBEX_SRV_99",
            collector_id="COLLECTOR_GLOBEX_01",
            timestamp_utc=datetime.datetime.now(datetime.timezone.utc),
            cpu_usage=88.8,
            memory_usage=77.0,
            disk_usage=65.0,
            latency_ms=45.0,
            health_state="Warning"
        )
        session.add(m1)
        session.add(m2)

        # Seed isolated incident for ORG_002
        inc2 = Incident(
            incident_id=f"INC-{uuid.uuid4().hex[:8].upper()}",
            tenant_id="ORG_002",
            title="Globex Cluster Degraded",
            severity="Medium",
            status="Active",
            affected_service="globex-api-gateway",
            affected_collectors='["COLLECTOR_GLOBEX_01"]',
            related_alerts='[]',
            timeline='[]',
            likely_cause="Test isolation incident for Globex",
            recommended_investigation="Inspect Globex gateway logs"
        )
        session.add(inc2)
        await session.commit()

    # Create test client
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # 1. Test Organization Profile isolation
        resp_acme_org = await ac.get("/api/v1/organizations/profile", headers={"Authorization": "Bearer demo-token"})
        assert resp_acme_org.status_code == 200
        data_acme_org = resp_acme_org.json()
        assert data_acme_org["tenant_id"] == "ORG_001"
        assert data_acme_org["name"] == "AEGIS Demo Corp"

        resp_globex_org = await ac.get("/api/v1/organizations/profile", headers={"Authorization": "Bearer demo-token-globex"})
        assert resp_globex_org.status_code == 200
        data_globex_org = resp_globex_org.json()
        assert data_globex_org["tenant_id"] == "ORG_002"
        assert data_globex_org["name"] == "Globex Industries"

        # 2. Test Collectors isolation
        resp_acme_cols = await ac.get("/api/v1/collectors", headers={"Authorization": "Bearer demo-token"})
        assert resp_acme_cols.status_code == 200
        acme_col_ids = [c["collector_id"] for c in resp_acme_cols.json()]
        assert "COLLECTOR_001" in acme_col_ids
        assert "COLLECTOR_GLOBEX_01" not in acme_col_ids

        resp_globex_cols = await ac.get("/api/v1/collectors", headers={"Authorization": "Bearer demo-token-globex"})
        assert resp_globex_cols.status_code == 200
        globex_col_ids = [c["collector_id"] for c in resp_globex_cols.json()]
        assert "COLLECTOR_GLOBEX_01" in globex_col_ids
        assert "COLLECTOR_001" not in globex_col_ids

        # 3. Test Metrics isolation
        resp_acme_metrics = await ac.get("/api/v1/metrics", headers={"Authorization": "Bearer demo-token"})
        assert resp_acme_metrics.status_code == 200
        acme_sources = [m["source_id"] for m in resp_acme_metrics.json()]
        assert "ACME_SRV_01" in acme_sources
        assert "GLOBEX_SRV_99" not in acme_sources

        resp_globex_metrics = await ac.get("/api/v1/metrics", headers={"Authorization": "Bearer demo-token-globex"})
        assert resp_globex_metrics.status_code == 200
        globex_sources = [m["source_id"] for m in resp_globex_metrics.json()]
        assert "GLOBEX_SRV_99" in globex_sources
        assert "ACME_SRV_01" not in globex_sources

        # 4. Test Incidents isolation
        resp_acme_inc = await ac.get("/api/v1/incidents", headers={"Authorization": "Bearer demo-token"})
        assert resp_acme_inc.status_code == 200
        acme_inc_titles = [i["title"] for i in resp_acme_inc.json()]
        assert "Globex Cluster Degraded" not in acme_inc_titles

        resp_globex_inc = await ac.get("/api/v1/incidents", headers={"Authorization": "Bearer demo-token-globex"})
        assert resp_globex_inc.status_code == 200
        globex_inc_titles = [i["title"] for i in resp_globex_inc.json()]
        assert "Globex Cluster Degraded" in globex_inc_titles

    print("✅ Multi-tenant isolation verified: zero leakage across ORG_001 and ORG_002.")
