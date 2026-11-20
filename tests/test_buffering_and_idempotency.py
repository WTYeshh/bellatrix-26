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

if __name__ == "__main__":
    test_sqlite_buffering_and_draining()
    asyncio.run(test_backend_idempotency_and_duplicate_prevention())
    print("All Buffering & Idempotency tests passed!")
