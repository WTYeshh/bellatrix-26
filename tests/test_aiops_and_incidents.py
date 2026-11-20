import pytest
from backend.app.aiops.engine import AIOpsEngine

def test_statistical_baselines_and_zscore():
    """TEST: Statistical baselines and robust Z-score / MAD anomaly detection."""
    engine = AIOpsEngine()
    tenant = "ORG_TEST"
    source = "SERVER_01"
    metric = "cpu_usage"

    # Feed normal historical CPU values: ~40% ± 4%
    normal_history = [38.0, 42.0, 39.5, 41.0, 40.0, 38.5, 43.0, 39.0, 41.5, 40.5]
    for val in normal_history:
        engine.record_observation(tenant, source, metric, val)

    stats = engine.calculate_statistical_baseline(tenant, source, metric)
    assert 39.0 <= stats["mean"] <= 41.5
    assert stats["std"] < 3.0

    # Test nominal value: 42% should NOT trigger anomaly
    no_anom = engine.detect_statistical_anomaly(tenant, source, metric, 42.0)
    assert no_anom is None

    # Test massive spike: 96% CPU should trigger anomaly with high deviation sigma
    anomaly = engine.detect_statistical_anomaly(tenant, source, metric, 96.0)
    assert anomaly is not None
    assert anomaly["severity"] in ["High", "Critical"]
    assert anomaly["deviation_sigma"] >= 3.0
    assert anomaly["observed_value"] == 96.0
    assert "historical baseline" in anomaly["reason"] or "acceleration" in anomaly["reason"]
    print("✅ Statistical baselines & robust Z-Score anomaly detection verified.")

def test_isolation_forest_ml_scoring():
    """TEST: Scikit-Learn Isolation Forest multivariate anomaly scoring."""
    engine = AIOpsEngine()
    tenant = "ORG_TEST_ML"

    # Train with normal cluster of vectors: [cpu, mem, disk, lat, loss]
    normal_training = [
        [35.0, 50.0, 40.0, 20.0, 0.0],
        [38.0, 52.0, 40.5, 22.0, 0.0],
        [36.0, 51.0, 40.2, 19.0, 0.0],
        [37.0, 49.0, 40.8, 21.0, 0.0],
        [39.0, 53.0, 41.0, 23.0, 0.0],
        [35.5, 50.5, 40.1, 20.5, 0.0],
        [38.2, 51.5, 40.9, 21.5, 0.0],
        [36.8, 49.8, 40.3, 19.8, 0.0],
        [37.4, 52.2, 40.7, 22.2, 0.0],
        [39.1, 53.1, 41.1, 23.5, 0.0],
        [36.2, 50.8, 40.4, 20.2, 0.0],
        [38.0, 51.0, 40.6, 21.0, 0.0],
    ]
    engine.train_isolation_forest(tenant, normal_training)

    # Normal point
    is_anom_norm, score_norm = engine.score_multivariate_ml(tenant, [37.0, 51.0, 40.0, 21.0, 0.0])
    assert is_anom_norm is False

    # Outlier anomaly point: extreme CPU, memory, and latency spike
    is_anom_spike, score_spike = engine.score_multivariate_ml(tenant, [98.0, 95.0, 90.0, 450.0, 15.0])
    assert is_anom_spike is True
    assert score_spike > score_norm
    print("✅ Scikit-Learn Isolation Forest multivariate anomaly scoring verified.")

def test_incident_dna_correlation():
    """TEST: Correlating multiple alert signals into a single unified incident."""
    engine = AIOpsEngine()
    tenant = "ORG_DNA"

    anomalies = [
        {
            "source_id": "SERVER_01",
            "metric": "cpu_usage",
            "observed_value": 96.0,
            "baseline_value": 40.0,
            "deviation_sigma": 4.2,
            "severity": "High",
            "contributing_signals": ["elevated_cpu_usage", "deviation_4.2sigma"]
        },
        {
            "source_id": "SERVER_01",
            "metric": "latency_ms",
            "observed_value": 280.0,
            "baseline_value": 25.0,
            "deviation_sigma": 5.1,
            "severity": "High",
            "contributing_signals": ["elevated_latency_ms", "deviation_5.1sigma"]
        }
    ]

    incident = engine.correlate_incident_dna(tenant, anomalies, existing_active_incidents=[])
    assert incident is not None
    assert incident["severity"] == "High"
    assert "SERVER_01" in incident["affected_collectors"]
    assert len(incident["related_alerts"]) == 2
    assert "Latency Surge" in incident["title"] or "Saturation" in incident["title"]
    assert incident["confidence"] >= 0.85
    print("✅ Incident DNA alert correlation verified.")

def test_explainable_recommendation():
    """TEST: Transparent AI recommendation with evidence trail."""
    engine = AIOpsEngine()
    sample_incident = {
        "incident_id": "INC-TEST-001",
        "title": "Compute Saturation & Latency Surge on SERVER_01",
        "severity": "High",
        "likely_cause": "Thread pool exhaustion and compute contention.",
        "recommended_investigation": "Inspect thread counts and database pool limits.",
        "confidence": 0.92,
        "affected_collectors": ["SERVER_01"],
        "related_alerts": [
            {
                "metric": "cpu_usage",
                "observed_value": 95.0,
                "baseline_value": 41.0,
                "deviation_sigma": 4.1,
                "severity": "High"
            }
        ]
    }

    rec = engine.generate_explainable_recommendation(sample_incident)
    assert rec["incident_id"] == "INC-TEST-001"
    assert len(rec["supporting_evidence"]) == 1
    assert rec["supporting_evidence"][0]["metric"] == "cpu_usage"
    assert "92%" in rec["reason"]
    assert "Inspect thread counts" in rec["suggested_action"]
    print("✅ Explainable AI recommendation verified.")

@pytest.mark.asyncio
async def test_end_to_end_automated_aiops_ingestion():
    """TEST: Full end-to-end automated AIOps execution on payload ingestion."""
    from backend.app.database import engine, Base, AsyncSessionLocal
    from backend.app.ingestion.pipeline import process_ingestion_payload
    from backend.app.models import AnomalyRecord, Incident
    from backend.app.aiops.engine import aiops_engine
    from sqlalchemy.future import select
    import uuid
    import datetime

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    tenant = "ORG_E2E_AIOPS"
    source = "NODE_SRV_99"

    # Establish normal baseline
    for i in range(12):
        aiops_engine.record_observation(tenant, source, "cpu_usage", 40.0 + (i % 3))
        aiops_engine.record_observation(tenant, source, "latency_ms", 20.0 + (i % 2))

    # Ingest a severe multi-signal anomaly payload
    payload = {
        "payload_id": f"P-E2E-{uuid.uuid4()}",
        "tenant_id": tenant,
        "source_id": source,
        "collector_id": "COLLECTOR_001",
        "timestamp_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "cpu_usage": 98.0,
        "memory_usage": 88.0,
        "disk_usage": 45.0,
        "latency_ms": 350.0,
        "packet_loss_pct": 5.0,
        "throughput_kbps": 120.0,
        "health_state": "Poor"
    }

    async with AsyncSessionLocal() as session:
        ack = await process_ingestion_payload(payload, session)
        assert ack.status == "Delivered"
        assert ack.verified is True

        # Verify automated AnomalyRecords created in DB
        anoms = (await session.execute(
            select(AnomalyRecord).where(AnomalyRecord.tenant_id == tenant)
        )).scalars().all()
        assert len(anoms) >= 1
        metrics_flagged = [a.metric for a in anoms]
        assert "cpu_usage" in metrics_flagged or "latency_ms" in metrics_flagged

        # Verify Incident DNA correlated into an Incident
        incs = (await session.execute(
            select(Incident).where(Incident.tenant_id == tenant)
        )).scalars().all()
        assert len(incs) >= 1
        latest_inc = incs[-1]
        assert latest_inc.severity in ["High", "Critical"]
        assert source in latest_inc.affected_collectors
        assert latest_inc.confidence >= 0.85

    print("✅ Automated end-to-end AIOps ingestion and Incident DNA correlation verified.")

if __name__ == "__main__":
    test_statistical_baselines_and_zscore()
    test_isolation_forest_ml_scoring()
    test_incident_dna_correlation()
    test_explainable_recommendation()
    print("All AIOps & Incident tests passed!")
