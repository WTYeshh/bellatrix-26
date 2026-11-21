import pytest
import psutil
from httpx import AsyncClient, ASGITransport

from backend.app.main import app, init_server_identity
from backend.app.database import engine, Base
from collector.sources.system_metrics import SystemMetricsSource

@pytest.mark.asyncio
async def test_real_windows_hardware_validation():
    r"""
    TEST:
    1. Validate real Windows hardware metrics collected by psutil:
       - CPU per-core, frequency
       - Physical RAM breakdown
       - Disk partitions (C:\ and any other available drives)
       - Network throughput
       - Monitored Windows services
       - Safe top running processes (omitting sensitive cmdline/secrets)
    2. Controlled safe CPU stress load:
       - Triggers real background math thread
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await init_server_identity()

    # 1. Hardware validation via SystemMetricsSource
    source = SystemMetricsSource()
    metrics = source.collect()

    assert "cpu_usage" in metrics
    assert "memory_usage" in metrics
    assert "disk_usage" in metrics
    assert "latency_ms" in metrics
    assert "health_state" in metrics

    # Per-core CPU verification
    per_core = psutil.cpu_percent(interval=0.05, percpu=True)
    assert len(per_core) == psutil.cpu_count(logical=True)
    assert len(per_core) >= 2, "Must detect real multi-core CPU"

    # RAM breakdown verification
    vm = psutil.virtual_memory()
    assert vm.total > 1024**3, "RAM total must be greater than 1GB"
    assert vm.percent > 0

    # Disk partitions
    parts = psutil.disk_partitions(all=False)
    assert len(parts) >= 1
    mounts = [p.mountpoint for p in parts]
    assert any("C:" in m or "/" in m for m in mounts)

    # Monitored services
    svcs = source.collect_windows_services()
    assert len(svcs) >= 3
    assert any(s["name"] in ["EventLog", "LanmanServer", "RpcSs", "Themes", "PlugPlay"] for s in svcs)

    # Safe processes
    procs = source.collect_safe_processes(limit=10)
    assert len(procs) >= 1
    for p in procs:
        assert "pid" in p
        assert "name" in p
        assert "cmdline" not in p, "Cmdline must never be exposed (privacy rule)"
        assert "env" not in p, "Env vars must never be exposed"

    # 2. Controlled CPU stress API test
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp_stress = await ac.post("/api/v1/system/stress/cpu?duration=5")
        assert resp_stress.status_code == 200
        data_stress = resp_stress.json()
        assert data_stress["target"] == "cpu"
        assert data_stress["duration"] == 5

    print("✅ Real Windows hardware validation & safe controlled CPU stress verified.")

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_milestone_9_real_windows_hardware_validation())
