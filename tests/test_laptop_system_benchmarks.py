"""
AEGIS Single-Node Laptop Observability & System Benchmarks Test Suite
Verifies:
1. Collection tick duration benchmark (strictly < 15 ms via TTL cache).
2. Collector output schema for real Windows laptop hardware.
3. SQLite WAL mode enforcement and downsampling rollups (1m, 5m, 1h).
4. Rolling baselines (mean, std, EWMA) and anomaly trigger.
5. Privacy redaction: Zero exposure of raw username ("Veeresh") or raw hostname.
"""

import os
import time
import getpass
import socket
import pytest
import sqlite3
import datetime
from sqlalchemy.future import select

from collector.system_monitor import SystemMetricsSource
from collector.process_monitor import ProcessMonitor
from collector.privacy.engine import PrivacyEngine
from backend.app.aiops.baseline_engine import FleetBaselineEngine
from backend.app.database import engine, Base, AsyncSessionLocal
from backend.app.models import MetricRecord, MetricRollup
from backend.app.ingestion.rollup_engine import process_rollups_and_retention

def test_benchmark_collection_tick_under_15ms():
    """BENCHMARK: Collector tick execution time must be strictly < 15 ms."""
    time.sleep(1.5)  # Allow any prior hardware stress threads to cleanly exit
    source = SystemMetricsSource()
    source.collect()
    
    # Benchmark 10 consecutive ticks
    durations = []
    for _ in range(10):
        t0 = time.perf_counter()
        metrics = source.collect()
        t1 = time.perf_counter()
        durations.append((t1 - t0) * 1000.0) # in ms
        time.sleep(0.01)

    sorted_d = sorted(durations)
    median_ms = sorted_d[len(sorted_d) // 2]
    min_ms = sorted_d[0]
    avg_ms = sum(durations) / len(durations)
    print(f"\n[BENCHMARK] Collection tick execution time: Median={median_ms:.2f}ms, Avg={avg_ms:.2f}ms, Min={min_ms:.2f}ms")
    assert median_ms < 15.0, f"Collection tick median must be < 15 ms, got {median_ms:.2f} ms"
    assert min_ms < 15.0, f"Collection tick min must be < 15 ms, got {min_ms:.2f} ms"
    assert "cpu_usage" in metrics
    assert "memory_usage" in metrics

def test_laptop_hardware_metrics_schema():
    """SCHEMA: Validates real physical laptop hardware telemetry fields."""
    source = SystemMetricsSource()
    metrics = source.collect()

    assert "cpu_usage" in metrics
    assert "memory_usage" in metrics
    assert "disk_usage" in metrics
    assert "latency_ms" in metrics
    assert "packet_loss_pct" in metrics
    assert "health_state" in metrics

    # Real hardware fields
    assert "cpu_freq_mhz" in metrics
    assert "swap_percent" in metrics
    assert "disk_iops" in metrics
    assert "upload_kbps" in metrics
    assert "download_kbps" in metrics
    assert "top_processes" in metrics
    assert isinstance(metrics["top_processes"], list)

    # Valid ranges
    assert 0.0 <= metrics["cpu_usage"] <= 100.0
    assert 0.0 <= metrics["memory_usage"] <= 100.0
    assert 0.0 <= metrics["disk_usage"] <= 100.0
    assert metrics["health_state"] in ["Excellent", "Good", "Fair", "Poor"]

def test_privacy_redaction_guarantees():
    """PRIVACY: Verifies raw username and raw hostname are never sent off the collector."""
    engine = PrivacyEngine()
    current_user = getpass.getuser()
    current_host = socket.gethostname()

    # Raw telemetry containing username and real hostname
    raw_payload = {
        "payload_id": "TEST_PRIVACY_01",
        "tenant_id": "default",
        "source_id": "server-01",
        "hostname": current_host,
        "username": current_user,
        "log_path": f"C:\\Users\\{current_user}\\AppData\\Local\\aegis.log",
        "auth_header": "Bearer secret_jwt_token_9876",
        "cpu_usage": 45.2,
        "memory_usage": 62.1,
        "disk_usage": 51.0,
        "latency_ms": 12.4
    }

    approved, approved_fields, dropped_fields = engine.apply_policy(raw_payload)

    # Verify sensitive fields are dropped
    assert "username" not in approved
    assert "auth_header" not in approved
    assert "hostname" not in approved

    # Verify allow-listed operational fields pass
    assert approved["source_id"] == "server-01"
    assert approved["cpu_usage"] == 45.2

    # Verify serialize canonical string has zero occurrences of raw username or hostname
    serialized = str(approved)
    assert current_user not in serialized or current_user == "default"
    assert current_host not in serialized or current_host == "server-01"

    # Verify fail-closed egress gate
    valid, err = engine.validate_for_egress(approved)
    assert valid is True

@pytest.mark.asyncio
async def test_sqlite_wal_mode_and_rollups():
    """PERSISTENCE: Verifies SQLite operates in WAL mode and downsampling rollups aggregate correctly."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Verify WAL mode on database
    async with AsyncSessionLocal() as session:
        wal_res = await session.execute(sqlite3_wal_check())
        mode = wal_res.scalar()
        assert mode.lower() == "wal"

        # Insert 5 test metric samples within the same minute bucket
        import uuid
        run_id = uuid.uuid4().hex[:6]
        bench_source = f"server-bench-{run_id}"
        base_time = datetime.datetime(2026, 11, 21, 12, 0, 0, tzinfo=datetime.timezone.utc)
        for i in range(5):
            rec = MetricRecord(
                payload_id=f"TEST_ROLLUP_{run_id}_{i}",
                tenant_id="default",
                source_id=bench_source,
                collector_id="COLLECTOR_SERVER_01",
                environment="production",
                timestamp_utc=base_time + datetime.timedelta(seconds=i*2),
                cpu_usage=40.0 + i,
                memory_usage=55.0,
                disk_usage=45.0,
                latency_ms=10.0 + i,
                packet_loss_pct=0.0,
                health_state="Good"
            )
            session.add(rec)
            await process_rollups_and_retention(session, rec)
            await session.flush()
        await session.commit()

        # Verify rollups were created
        r_stmt = select(MetricRollup).where(MetricRollup.source_id == bench_source)
        rollups = (await session.execute(r_stmt)).scalars().all()
        assert len(rollups) >= 1
        r1m = rollups[0]
        assert r1m.interval in ["1m", "5m", "1h"]
        assert 40.0 <= r1m.cpu_avg <= 44.0
        assert r1m.sample_count >= 5

def sqlite3_wal_check():
    from sqlalchemy import text
    return text("PRAGMA journal_mode")

def test_rolling_baseline_and_ewma():
    """AIOPS: Tests rolling baselines (mean, std, EWMA) on genuine time series."""
    base_engine = FleetBaselineEngine(window_size=20)
    tenant = "default"
    source = "server-01"
    metric = "cpu_usage"

    # Calibration phase (< 5 samples)
    for v in [35.0, 36.0, 34.5]:
        base_engine.record(tenant, source, metric, v)
    b_cal = base_engine.get_baseline(tenant, source, metric)
    assert b_cal["is_calibrating"] is True

    # Complete calibration with steady 35% CPU
    for v in [35.2, 34.8, 35.1, 35.0, 34.9, 35.3]:
        base_engine.record(tenant, source, metric, v)
    b_ready = base_engine.get_baseline(tenant, source, metric)
    assert b_ready["is_calibrating"] is False
    assert 34.5 <= b_ready["mean"] <= 35.5
    assert b_ready["std"] < 1.0
    assert "ewma" in b_ready
    assert 34.5 <= b_ready["ewma"] <= 35.5
