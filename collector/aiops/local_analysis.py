from typing import Dict, Any, List
from collector.aiops.baseline import RollingBaselineTracker
from collector.aiops.feature_engineering import LocalFeatureEngineer
from collector.aiops.anomaly_detector import LocalAnomalyDetector
from collector.aiops.model_manager import LocalModelManager

class LocalAIOpsCoordinator:
    """
    Tier 1 Local AIOps Coordinator:
    Runs continuously on customer infrastructure.
    - Evaluates CPU, RAM, disk, network throughput
    - Maintains local dynamic baselines
    - Executes statistical and Isolation Forest ML anomaly checks
    - Operates 100% autonomously during SaaS network disconnects
    """
    def __init__(self):
        self.baseline_tracker = RollingBaselineTracker(window_size=30)
        self.feature_engineer = LocalFeatureEngineer()
        self.detector = LocalAnomalyDetector(zscore_threshold=3.0)
        self.model_manager = LocalModelManager()

    def process_telemetry(self, source_id: str, raw_metrics: Dict[str, Any]) -> List[Dict[str, Any]]:
        anomalies: List[Dict[str, Any]] = []

        # 1. Update rolling baselines and run statistical detection for each core metric
        metrics_to_eval = [
            ("cpu_usage", float(raw_metrics.get("cpu_usage", 0.0))),
            ("memory_usage", float(raw_metrics.get("memory_usage", 0.0))),
            ("disk_usage", float(raw_metrics.get("disk_usage", 0.0))),
            ("latency_ms", float(raw_metrics.get("latency_ms", 0.0))),
        ]

        for m_name, val in metrics_to_eval:
            stats = self.baseline_tracker.update(m_name, val)
            anom = self.detector.evaluate_metric(source_id, m_name, val, stats)
            if anom:
                anomalies.append(anom)

        # 2. Extract multi-metric feature vector and run Isolation Forest
        feature_vec = self.feature_engineer.extract_features(raw_metrics)
        self.model_manager.add_sample(feature_vec)
        is_ml_anom, ml_score, ml_status = self.model_manager.predict(feature_vec)

        if is_ml_anom and not anomalies:
            # Multi-metric anomaly detected by Isolation Forest
            import uuid, datetime
            anomalies.append({
                "anomaly_id": f"LOC-ML-{uuid.uuid4().hex[:8].upper()}",
                "source_id": source_id,
                "metric": "multivariate_telemetry",
                "observed_value": round(float(raw_metrics.get("cpu_usage", 0.0)), 1),
                "baseline_value": round(self.baseline_tracker.get_baseline("cpu_usage")["median"], 1),
                "deviation": round(ml_score, 2),
                "anomaly_score": ml_score,
                "severity": "High" if ml_score >= 0.75 else "Medium",
                "detection_method": "IsolationForest",
                "reason": f"Multivariate Isolation Forest detected abnormal multi-metric distribution (score: {ml_score}).",
                "timestamp_utc": datetime.datetime.now(datetime.timezone.utc).isoformat()
            })

        return anomalies
