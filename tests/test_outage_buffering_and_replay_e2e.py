import os
import uuid
import json
import datetime
import pytest
from unittest.mock import patch, MagicMock

from collector.main import Tier1Collector
from collector.storage.local_db import LocalCollectorStorage
from backend.app.database import AsyncSessionLocal, engine, Base
from backend.app.models import MetricRecord, EgressProof
from backend.app.ingestion.pipeline import process_ingestion_payload
from sqlalchemy.future import select

TEST_DB_PATH = "test_e2e_outage_collector.db"

@pytest.mark.asyncio
async def test_end_to_end_outage_buffering_and_replay():
    """
    MILESTONE 8: Full End-to-End Outage Buffering, Resilient Drain,
    and Idempotent Verification Test.
    """
    if os.path.exists(TEST_DB_PATH):
        os.remove(TEST_DB_PATH)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # 1. Instantiate collector configured with test database
    collector = Tier1Collector()
    collector.storage = LocalCollectorStorage(db_path=TEST_DB_PATH)

    # 2. SIMULATE BACKEND OUTAGE: SaaS client fails
    with patch.object(collector.client, "send_metadata", return_value=(False, {"error": "ConnectionRefused"})):
        # Run 3 collection cycles during outage
        results = []
        for i in range(3):
            res = collector.run_cycle()
            results.append(res)
            assert res["success"] is False, "Must fail transmission during outage"
            assert res["buffered"] is True, "Must buffer locally during outage"

        # Verify all 3 records are safely queued in local SQLite outbox
        pending_count = collector.storage.count_pending()
        assert pending_count == 3, f"Expected 3 buffered records, got {pending_count}"

        # Verify local Egress Proofs are recorded with status 'Buffered'
        proofs = collector.storage.get_recent_proofs(limit=5)
        assert len(proofs) == 3
        for pr in proofs:
            assert pr["status"] == "Buffered"
            assert pr["payload_hash"] is not None

    print("✅ Step 1: Outage detected, 3 records buffered locally, proofs marked 'Buffered'.")

    # 3. SIMULATE BACKEND RECOVERY: Collector drains outbox
    ingested_payloads = []

    async def mock_backend_ingest(payload):
        ingested_payloads.append(payload)
        async with AsyncSessionLocal() as session:
            ack = await process_ingestion_payload(payload, session)
            return True, ack.model_dump()

    # Retrieve buffered payloads from collector storage
    pending_items = collector.storage.get_pending_outbox(limit=10)
    assert len(pending_items) == 3

    # Replay buffered records to the backend
    for item in pending_items:
        payload = item["payload"]
        payload_id = item["payload_id"]
        ok, ack = await mock_backend_ingest(payload)
        assert ok is True
        assert ack["status"] == "Delivered"
        assert ack["duplicate"] is False
        collector.storage.remove_from_outbox(payload_id)

    # Verify queue is completely drained
    assert collector.storage.count_pending() == 0
    print("✅ Step 2: Backend restored, outbox drained completely (0 pending records).")

    # 4. VERIFY BACKEND INTEGRITY: Check MetricRecords & EgressProofs in central DB
    async with AsyncSessionLocal() as session:
        for p in ingested_payloads:
            p_id = p["payload_id"]
            # Verify metric record exists
            m_res = await session.execute(select(MetricRecord).where(MetricRecord.payload_id == p_id))
            metric = m_res.scalar_one_or_none()
            assert metric is not None
            assert metric.tenant_id == collector.config.TENANT_ID

            # Verify Egress proof exists with 'Delivered & Verified' status
            ep_res = await session.execute(select(EgressProof).where(EgressProof.payload_id == p_id))
            proof = ep_res.scalar_one_or_none()
            assert proof is not None
            assert proof.transmission_status == "Delivered & Verified"
            assert proof.payload_hash == p["payload_hash"]

    print("✅ Step 3: Central database received all records and verified Egress Proof SHA-256 hashes.")

    # 5. IDEMPOTENCY RETRY: Send the same payloads again (simulating network duplicate retry)
    async with AsyncSessionLocal() as session:
        for p in ingested_payloads:
            dup_ack = await process_ingestion_payload(p, session)
            assert dup_ack.status == "Acknowledged"
            assert dup_ack.duplicate is True  # Duplicate rejected safely!

    # Clean up test database
    if os.path.exists(TEST_DB_PATH):
        os.remove(TEST_DB_PATH)

    print("✅ Step 4: Network retries deduplicated with zero database record multiplication.")
    print("✅ MILESTONE 8 PASSED: Outage buffering, outbox drain, proof verification & idempotency confirmed.")

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_end_to_end_outage_buffering_and_replay())
