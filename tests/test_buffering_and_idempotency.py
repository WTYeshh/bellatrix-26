import os
import asyncio
import uuid
import pytest
from collector.storage.local_db import LocalCollectorStorage
from backend.app.ingestion.pipeline import process_ingestion_payload
from backend.app.database import AsyncSessionLocal, engine, Base
from backend.app.models import MetricRecord, EgressProof
from sqlalchemy.future import select

TEST_DB_PATH = "test_collector_buffer.db"

def test_sqlite_buffering_and_draining():
    """TEST 2 SCENARIO: Local metadata buffering during outages and queue draining."""
    if os.path.exists(TEST_DB_PATH):
        os.remove(TEST_DB_PATH)

    storage = LocalCollectorStorage(db_path=TEST_DB_PATH)

    # 1. Enqueue 3 payloads during simulated outage
    p1 = {"payload_id": "P1", "cpu": 50.0}
    p2 = {"payload_id": "P2", "cpu": 60.0}
    p3 = {"payload_id": "P3", "cpu": 70.0}

    storage.enqueue_outbox("P1", p1, "2026-11-20T12:00:00Z")
    storage.enqueue_outbox("P2", p2, "2026-11-20T12:00:05Z")
    storage.enqueue_outbox("P3", p3, "2026-11-20T12:00:10Z")

    assert storage.count_pending() == 3

    # 2. Simulate reconnection: retrieve outbox and acknowledge
    pending = storage.get_pending_outbox()
    assert len(pending) == 3
    assert pending[0]["payload_id"] == "P1"

    # Drain P1
    storage.remove_from_outbox("P1")
    assert storage.count_pending() == 2

    # Drain P2, P3
    storage.remove_from_outbox("P2")
    storage.remove_from_outbox("P3")
    assert storage.count_pending() == 0

    if os.path.exists(TEST_DB_PATH):
        os.remove(TEST_DB_PATH)
    print("✅ Local SQLite outage buffering and backlog replay verified.")

@pytest.mark.asyncio
async def test_backend_idempotency_and_duplicate_prevention():
    """TEST 7 SCENARIO: Sending identical payload twice must not duplicate records."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    payload_id = str(uuid.uuid4())
    payload = {
        "payload_id": payload_id,
        "tenant_id": "ORG_IDEMP_TEST",
        "source_id": "NODE_TEST_IDEMP",
        "collector_id": "COLLECTOR_001",
        "timestamp_utc": "2026-11-20T12:00:00Z",
        "cpu_usage": 45.0,
        "memory_usage": 55.0,
        "disk_usage": 50.0,
        "latency_ms": 20.0,
        "packet_loss_pct": 0.0,
        "health_state": "Good",
        "event_category": "Performance",
        "severity": "Low"
    }

    async with AsyncSessionLocal() as session:
        # 1. First delivery
        ack1 = await process_ingestion_payload(payload, session)
        assert ack1.status == "Delivered"
        assert ack1.duplicate is False

    async with AsyncSessionLocal() as session:
        # 2. Re-send duplicate delivery (simulating network retry)
        ack2 = await process_ingestion_payload(payload, session)
        assert ack2.status == "Acknowledged"
        assert ack2.duplicate is True  # Duplicate flagged!

        # 3. Verify exactly ONE metric record exists in database
        stmt = select(MetricRecord).where(MetricRecord.payload_id == payload_id)
        records = (await session.execute(stmt)).scalars().all()
        assert len(records) == 1

    print("✅ Backend idempotency and duplicate prevention verified.")

@pytest.mark.asyncio
async def test_collector_heartbeat_and_stale_detection():
    """TEST: Collector heartbeat updates and stale detection (>45s marks collector Offline)."""
    import datetime
    from httpx import AsyncClient, ASGITransport
    from backend.app.main import app, seed_initial_data
    from backend.app.models import Collector

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await seed_initial_data()

    now_utc = datetime.datetime.now(datetime.timezone.utc)
    stale_time = now_utc - datetime.timedelta(seconds=55)
    cid_active = f"COL_ACT_{uuid.uuid4().hex[:6]}"
    cid_stale = f"COL_STL_{uuid.uuid4().hex[:6]}"

    async with AsyncSessionLocal() as session:
        # Seed an active collector and a stale collector
        c_active = Collector(
            collector_id=cid_active,
            tenant_id="ORG_001",
            host_identifier="win-host-active",
            version="1.0.0",
            status="Online",
            auth_token="token-act",
            cpu_usage=1.2,
            memory_usage=38.5,
            pending_buffered=0,
            last_heartbeat=now_utc
        )
        c_stale = Collector(
            collector_id=cid_stale,
            tenant_id="ORG_001",
            host_identifier="win-host-stale",
            version="1.0.0",
            status="Online",  # DB says Online, but last heartbeat was 55s ago!
            auth_token="token-stale",
            cpu_usage=0.0,
            memory_usage=0.0,
            pending_buffered=3,
            last_heartbeat=stale_time
        )
        session.add(c_active)
        session.add(c_stale)
        await session.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/api/v1/collectors", headers={"Authorization": "Bearer demo-token"})
        assert resp.status_code == 200
        cols = {c["collector_id"]: c for c in resp.json()}

        # Verify active collector is Online
        assert cid_active in cols
        assert cols[cid_active]["status"] == "Online"
        assert cols[cid_active]["cpu_usage"] == 1.2
        assert cols[cid_active]["memory_usage"] == 38.5

        # Verify stale collector is detected and dynamically reported as Offline
        assert cid_stale in cols
        assert cols[cid_stale]["status"] == "Offline"
        assert cols[cid_stale]["pending_buffered"] == 3

    print("✅ Collector heartbeat tracking and 45s stale detection verified.")

if __name__ == "__main__":
    test_sqlite_buffering_and_draining()
    asyncio.run(test_backend_idempotency_and_duplicate_prevention())
    print("All Buffering & Idempotency tests passed!")
