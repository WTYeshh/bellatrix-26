import os
import pytest
import numpy as np
from collector.aiops.baseline import RollingBaselineTracker
from collector.aiops.feature_engineering import LocalFeatureEngineer, FeatureEngineer
from collector.aiops.model_manager import LocalModelManager
from collector.aiops.anomaly_detector import LocalAnomalyDetector
from collector.aiops.local_analysis import LocalAIOpsCoordinator
from backend.app.aiops.engine import UnifiedAIOpsEngine
from backend.app.aiops.baseline_engine import FleetBaselineEngine
from backend.app.aiops.model_manager import CentralModelManager
from backend.app.aiops.anomaly_engine import CentralAnomalyEngine
from backend.app.aiops.correlation_engine import IncidentCorrelationEngine
from backend.app.aiops.explanation_engine import ExplanationEngine
from backend.app.aiops.recommendation_engine import RecommendationEngine
from collector.storage.local_db import LocalCollectorStorage

# -------------------------------------------------------------
# 1. Normal metric baseline calculation
# -------------------------------------------------------------
def test_normal_metric_baseline_calculation():
    """Verify rolling mean, median, std dev, and MAD calculations."""
    tracker = RollingBaselineTracker(window_size=30)
    # Feed steady readings around 40.0 with minor variance
    normal_values = [40.0, 41.0, 39.0, 40.5, 39.5, 40.2, 40.8, 39.8, 40.1, 40.3]
    for val in normal_values:
        tracker.update("cpu_usage", val)

    metrics = tracker.get_baseline("cpu_usage")
    assert metrics is not None
    assert 39.5 <= metrics["mean"] <= 40.5
    assert 39.5 <= metrics["median"] <= 40.5
    assert metrics["std"] < 1.0
    assert metrics["mad"] < 1.0
    assert tracker.is_ready("cpu_usage", min_samples=5) is True


# -------------------------------------------------------------
# 2. Sudden CPU anomaly (rapid delta jump)
# -------------------------------------------------------------
def test_sudden_cpu_anomaly_rapid_jump():
    """Detect immediate rapid delta jump in CPU usage."""
    tracker = RollingBaselineTracker(window_size=30)
    detector = LocalAnomalyDetector(zscore_threshold=3.0)
    
    # Establish stable baseline at ~20% CPU
    for _ in range(10):
        stats = tracker.update("cpu_usage", 20.0)
    
    # Sudden jump from 20% to 85%
    stats = tracker.update("cpu_usage", 85.0)
    anom = detector.evaluate_metric("SERVER_01", "cpu_usage", 85.0, stats)
    assert anom is not None
    assert anom["severity"] in ["High", "Critical"]
    assert anom["observed_value"] == 85.0


# -------------------------------------------------------------
# 3. Sustained CPU anomaly (consecutive breaches)
# -------------------------------------------------------------
def test_sustained_cpu_anomaly():
    """Detect sustained metric breach across multiple cycles."""
    tracker = RollingBaselineTracker(window_size=30)
    detector = LocalAnomalyDetector(zscore_threshold=3.0)
    
    for _ in range(10):
        tracker.update("cpu_usage", 25.0)
        
    anoms_found = []
    for _ in range(4):
        stats = tracker.update("cpu_usage", 92.0)
        anom = detector.evaluate_metric("SERVER_01", "cpu_usage", 92.0, stats)
        if anom:
            anoms_found.append(anom)
            
    assert len(anoms_found) >= 2
    assert any(a["severity"] in ["High", "Critical"] for a in anoms_found)


# -------------------------------------------------------------
# 4. Memory anomaly detection
# -------------------------------------------------------------
def test_memory_anomaly_detection():
    """Detect abnormal memory climb exceeding dynamic thresholds."""
    tracker = RollingBaselineTracker(window_size=30)
    detector = LocalAnomalyDetector(zscore_threshold=3.0)
    
    for _ in range(10):
        tracker.update("memory_usage", 45.0)
        
    stats = tracker.update("memory_usage", 94.5)
    anom = detector.evaluate_metric("SERVER_01", "memory_usage", 94.5, stats)
    assert anom is not None
    assert anom["observed_value"] == 94.5
    assert anom["severity"] in ["High", "Critical"]


# -------------------------------------------------------------
# 5. Latency anomaly detection
# -------------------------------------------------------------
def test_latency_anomaly_detection():
    """Detect abnormal network socket latency surge."""
    tracker = RollingBaselineTracker(window_size=30)
    detector = LocalAnomalyDetector(zscore_threshold=3.0)
    
    for _ in range(10):
        tracker.update("latency_ms", 18.0)
        
    stats = tracker.update("latency_ms", 350.0)
    anom = detector.evaluate_metric("SERVER_01", "latency_ms", 350.0, stats)
    assert anom is not None
    assert anom["observed_value"] == 350.0


# -------------------------------------------------------------
# 6. Missing telemetry handling
# -------------------------------------------------------------
def test_missing_telemetry_handling():
    """AIOps pipeline gracefully handles None or missing metric keys without crashing."""
    coordinator = LocalAIOpsCoordinator()
    
    # Missing CPU and Latency completely
    sparse_raw = {"memory_usage": 50.0}
    anomalies = coordinator.process_telemetry("NODE_TEST", sparse_raw)
    assert isinstance(anomalies, list)


# -------------------------------------------------------------
# 7. Insufficient training data fallback (COLLECTING_BASELINE status)
# -------------------------------------------------------------
def test_insufficient_training_data_fallback():
    """Returns collecting baseline status when samples are under min threshold."""
    temp_path = "test_fresh_iforest.pkl"
    if os.path.exists(temp_path):
        os.remove(temp_path)
    manager = LocalModelManager(persistence_path=temp_path)
    # Fresh manager with only 2 samples
    manager.add_sample([10.0, 20.0, 30.0, 40.0, 50.0, 0.0, 0.0])
    manager.add_sample([11.0, 21.0, 31.0, 41.0, 51.0, 1.0, 1.0])
    
    is_anom, score, status = manager.predict([10.0, 20.0, 30.0, 40.0, 50.0, 0.0, 0.0])
    assert is_anom is False
    assert "COLLECTING_BASELINE" in status
    if os.path.exists(temp_path):
        os.remove(temp_path)


# -------------------------------------------------------------
# 8. Isolation Forest multivariate anomaly detection
# -------------------------------------------------------------
def test_isolation_forest_multivariate_detection():
    """Scikit-Learn IsolationForest identifies multidimensional outlier vectors."""
    temp_model_path = "test_temp_iforest.pkl"
    if os.path.exists(temp_model_path):
        os.remove(temp_model_path)
        
    manager = LocalModelManager(persistence_path=temp_model_path)
    engineer = LocalFeatureEngineer()
    
    # Train on tight normal cluster (>= 15 samples)
    for _ in range(20):
        vec = engineer.extract_features({
            "cpu_usage": 35.0 + np.random.uniform(-1, 1),
            "memory_usage": 50.0 + np.random.uniform(-1, 1),
            "disk_usage": 40.0,
            "latency_ms": 20.0 + np.random.uniform(-1, 1),
            "throughput_kbps": 120.0
        })
        manager.add_sample(vec)
        
    assert manager._model is not None
    
    # Test normal point
    norm_vec = [35.5, 50.2, 40.0, 20.2, 120.0, 0.5, 0.2]
    is_anom_norm, score_norm, _ = manager.predict(norm_vec)
    assert is_anom_norm is False
    
    # Test multi-factor corrupted anomaly
    outlier_vec = [98.0, 96.0, 92.0, 480.0, 5000.0, 60.0, 45.0]
    is_anom_out, score_out, _ = manager.predict(outlier_vec)
    assert is_anom_out is True
    assert score_out > score_norm
    
    if os.path.exists(temp_model_path):
        os.remove(temp_model_path)


# -------------------------------------------------------------
# 9. False-positive handling & threshold sanity
# -------------------------------------------------------------
def test_false_positive_handling():
    """Normal natural metric variance (±3%) must NOT trigger false alerts."""
    tracker = RollingBaselineTracker(window_size=30)
    detector = LocalAnomalyDetector(zscore_threshold=3.0)
    
    for v in [39.0, 41.0, 40.0, 38.5, 41.5, 39.5, 40.5, 40.0]:
        tracker.update("cpu_usage", v)
        
    stats = tracker.update("cpu_usage", 42.0)
    anom = detector.evaluate_metric("SERVER_01", "cpu_usage", 42.0, stats)
    assert anom is None


# -------------------------------------------------------------
# 10. Alert correlation into Incident DNA
# -------------------------------------------------------------
def test_alert_correlation_incident_dna():
    """Correlate concurrent CPU and latency anomalies into one unified Incident DNA."""
    correlator = IncidentCorrelationEngine()
    
    anomalies = [
        {
            "source_id": "SRV_ALPHA",
            "metric": "cpu_usage",
            "observed_value": 95.0,
            "baseline_value": 35.0,
            "deviation_sigma": 4.5,
            "severity": "High",
            "contributing_signals": ["elevated_cpu_usage", "deviation_4.5sigma"]
        },
        {
            "source_id": "SRV_ALPHA",
            "metric": "latency_ms",
            "observed_value": 290.0,
            "baseline_value": 22.0,
            "deviation_sigma": 5.2,
            "severity": "High",
            "contributing_signals": ["elevated_latency_ms", "deviation_5.2sigma"]
        }
    ]
    
    incident = correlator.correlate("ORG_TEST_DNA", anomalies, existing_active_incidents=[])
    assert incident is not None
    assert incident["severity"] == "High"
    assert "SRV_ALPHA" in incident["affected_collectors"]
    assert len(incident["related_alerts"]) == 2
    assert "Latency Surge" in incident["title"] or "Saturation" in incident["title"]
    assert incident["confidence"] >= 0.85


# -------------------------------------------------------------
# 11. Duplicate incident prevention
# -------------------------------------------------------------
def test_duplicate_incident_prevention():
    """Recurring anomalies on the same source/incident must update existing incident, not spawn duplicate."""
    correlator = IncidentCorrelationEngine()
    
    active_incident = {
        "id": "INC-EXISTING-001",
        "title": "Severe Host Saturation & Latency Surge",
        "tenant_id": "ORG_DUP_TEST",
        "affected_collectors": ["SRV_BETA"],
        "severity": "High",
        "status": "Active",
        "related_alerts": [{"metric": "cpu_usage", "observed_value": 90.0}],
        "recommended_action": "Check process table"
    }
    
    new_anomalies = [
        {
            "source_id": "SRV_BETA",
            "metric": "latency_ms",
            "observed_value": 310.0,
            "baseline_value": 20.0,
            "severity": "High",
            "contributing_signals": ["elevated_latency_ms"]
        }
    ]
    
    # Should attach to existing incident / suppress duplicate new incident creation
    incident = correlator.correlate("ORG_DUP_TEST", new_anomalies, existing_active_incidents=[active_incident])
    assert incident is None  # Duplicate suppressed to prevent alert noise


# -------------------------------------------------------------
# 12. Recommendation evidence verification
# -------------------------------------------------------------
def test_recommendation_evidence_verification():
    """Explanation engine generates empirical facts vs inferred hypotheses without fake AI."""
    explanation_engine = ExplanationEngine()
    rec_engine = RecommendationEngine(explanation_engine)
    
    mock_incident = {
        "id": "INC-VERIFY-123",
        "title": "Severe Host Saturation & Latency Surge",
        "severity": "Critical",
        "affected_collectors": ["NODE_PROD_1"],
        "primary_symptom": "cpu_saturation",
        "related_alerts": [
            {
                "metric": "cpu_usage",
                "observed_value": 98.2,
                "baseline_value": 30.0,
                "deviation_sigma": 4.8,
                "severity": "Critical"
            },
            {
                "metric": "latency_ms",
                "observed_value": 412.0,
                "baseline_value": 18.0,
                "deviation_sigma": 6.1,
                "severity": "Critical"
            }
        ]
    }
    
    rec = rec_engine.generate(mock_incident)
    assert rec["incident_id"] == "INC-VERIFY-123"
    assert rec["title"] is not None
    assert len(rec["actionable_steps"]) > 0
    assert rec["confidence"] >= 0.8
    assert rec["rollback_safe"] is True
    
    # Evidence must contain empirical facts citing observed metric deviations
    evidence = rec["evidence"]
    assert "empirical_facts" in evidence
    assert len(evidence["empirical_facts"]) >= 2
    assert any("98.2%" in f for f in evidence["empirical_facts"])
    assert any("412.0ms" in f for f in evidence["empirical_facts"])


# -------------------------------------------------------------
# 13. Tenant isolation enforcement
# -------------------------------------------------------------
def test_tenant_isolation_enforcement():
    """Tenant B cannot view, modify, or corrupt Tenant A's baselines or models."""
    engine = UnifiedAIOpsEngine()
    
    # Train Tenant A with high baseline
    for _ in range(10):
        engine.record_observation("TENANT_A", "SRV_A", "cpu_usage", 80.0)
        
    # Train Tenant B with low baseline
    for _ in range(10):
        engine.record_observation("TENANT_B", "SRV_B", "cpu_usage", 15.0)
        
    base_a = engine.calculate_statistical_baseline("TENANT_A", "SRV_A", "cpu_usage")
    base_b = engine.calculate_statistical_baseline("TENANT_B", "SRV_B", "cpu_usage")
    
    assert base_a["mean"] == 80.0
    assert base_b["mean"] == 15.0
    
    # Querying Tenant A from Tenant B's scope must yield empty / default
    empty_b = engine.calculate_statistical_baseline("TENANT_B", "SRV_A", "cpu_usage")
    assert empty_b["sample_count"] == 0
    assert empty_b["mean"] != 80.0  # Tenant B cannot see Tenant A's baseline!


# -------------------------------------------------------------
# 14. SaaS outage buffering
# -------------------------------------------------------------
def test_saas_outage_buffering():
    """Collector stores payloads in SQLite outbox during simulated SaaS outage."""
    test_db = "test_saas_outage_buffer.db"
    try:
        if os.path.exists(test_db):
            os.remove(test_db)
    except Exception:
        pass
        
    storage = LocalCollectorStorage(db_path=test_db)
    
    # Enqueue 3 payloads during outage
    for i in range(1, 4):
        storage.enqueue_outbox(f"P_OUT_{i}", {"cpu": 50.0 + i}, "2026-11-20T12:00:00Z")
        
    assert storage.count_pending() == 3
    
    # Draining after restoration
    items = storage.get_pending_outbox()
    assert len(items) == 3
    for it in items:
        storage.remove_from_outbox(it["payload_id"])
        
    assert storage.count_pending() == 0
    try:
        if os.path.exists(test_db):
            os.remove(test_db)
    except Exception:
        pass


# -------------------------------------------------------------
# 15. Local detection during outage
# -------------------------------------------------------------
def test_local_detection_during_outage():
    """Collector detects anomalies locally without any SaaS connectivity."""
    coordinator = LocalAIOpsCoordinator()
    
    # Feed historical data locally
    for _ in range(12):
        coordinator.process_telemetry("NODE_OFFLINE", {
            "cpu_usage": 25.0, "memory_usage": 40.0, "disk_usage": 30.0, "latency_ms": 15.0
        })
        
    # Severe spike occurs while offline
    offline_spike = {"cpu_usage": 98.0, "memory_usage": 92.0, "disk_usage": 30.0, "latency_ms": 380.0}
    anomalies = coordinator.process_telemetry("NODE_OFFLINE", offline_spike)
    
    assert len(anomalies) >= 1
    assert any(a["metric"] == "cpu_usage" for a in anomalies)
    assert any(a["severity"] in ["High", "Critical"] for a in anomalies)
