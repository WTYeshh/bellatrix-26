import uuid
import datetime
from typing import Dict, Any, List, Optional
from backend.app.aiops.baseline_engine import FleetBaselineEngine
from backend.app.aiops.model_manager import CentralModelManager

class CentralAnomalyEngine:
    """
    Tier 2 Fleet Anomaly Engine:
    Combines statistical baselines (MAD, Robust Z-Score, Sudden Shifts)
    with Scikit-Learn Isolation Forest multivariate anomaly detection.
    """
    def __init__(self, baseline_engine: FleetBaselineEngine, model_manager: CentralModelManager):
        self.baselines = baseline_engine
        self.models = model_manager
        self._sustained_counts: Dict[str, int] = {}

    def analyze(self, tenant_id: str, payload: Dict[str, Any]) -> List[Dict[str, Any]]:
        source_id = payload.get("source_id", "SERVER_01")
        anomalies: List[Dict[str, Any]] = []

        # 1. Statistical evaluations across monitored signals
        metrics = [
            ("cpu_usage", float(payload.get("cpu_usage", 0.0))),
            ("memory_usage", float(payload.get("memory_usage", 0.0))),
            ("disk_usage", float(payload.get("disk_usage", 0.0))),
            ("latency_ms", float(payload.get("latency_ms", 0.0))),
            ("packet_loss_pct", float(payload.get("packet_loss_pct", 0.0))),
        ]

        for metric_name, val in metrics:
            stats = self.baselines.record(tenant_id, source_id, metric_name, val)
            median = stats["median"]
            mad = stats["mad"]
            rate = stats.get("rate_of_change", 0.0)

            # Robust Z-Score: 0.6745 * |val - median| / MAD
            robust_z = round(0.6745 * abs(val - median) / mad, 2)
            deviation = round(abs(val - median), 2)

            # Check sudden shift
            sudden_spike = (
                abs(rate) >= 28.0 and
                (
                    (metric_name in ["cpu_usage", "memory_usage"] and val >= 75.0) or
                    (metric_name == "latency_ms" and val >= 100.0)
                )
            )

            # Check statistical breach
            stat_breach = (
                robust_z >= 2.5 and
                (
                    (metric_name in ["cpu_usage", "memory_usage"] and val >= 75.0) or
                    (metric_name == "latency_ms" and val >= 80.0) or
                    (metric_name == "packet_loss_pct" and val >= 4.0) or
                    (metric_name == "disk_usage" and val >= 88.0)
                )
            )

            # Check sustained deviation
            k_sustained = f"{tenant_id}:{source_id}:{metric_name}"
            if (metric_name in ["cpu_usage", "memory_usage"] and val >= 80.0) or (metric_name == "latency_ms" and val >= 90.0):
                self._sustained_counts[k_sustained] = self._sustained_counts.get(k_sustained, 0) + 1
            else:
                self._sustained_counts[k_sustained] = 0

            sustained = self._sustained_counts.get(k_sustained, 0) >= 3

            if sudden_spike or stat_breach or sustained:
                # Calculate anomaly score (0.50 - 0.99)
                score = min(0.99, max(0.50, round(0.5 + (robust_z / 10.0), 2)))
                if val >= 95.0 or robust_z >= 5.0 or sustained:
                    severity = "Critical" if val >= 95.0 else "High"
                elif val >= 85.0 or robust_z >= 3.5:
                    severity = "High"
                else:
                    severity = "Medium"

                method = "MAD"
                if sudden_spike:
                    method = "Sudden-Shift"
                    reason = f"Sudden positive acceleration of +{rate}% detected on {metric_name} ({val}%)."
                elif sustained:
                    method = "Sustained-Threshold"
                    reason = f"{metric_name.replace('_', ' ').title()} sustained at elevated level ({val}) for {self._sustained_counts[k_sustained]} cycles."
                else:
                    reason = f"{metric_name.replace('_', ' ').title()} ({val}) deviates from historical baseline ({median} ± {mad}) by {robust_z}σ."

                now_utc = datetime.datetime.now(datetime.timezone.utc).isoformat()
                anomalies.append({
                    "anomaly_id": f"ANOM-{uuid.uuid4().hex[:8].upper()}",
                    "source_id": source_id,
                    "metric": metric_name,
                    "observed_value": val,
                    "baseline_value": median,
                    "deviation": deviation,
                    "deviation_sigma": robust_z,
                    "anomaly_score": score,
                    "severity": severity,
                    "detection_method": method,
                    "reason": reason,
                    "contributing_signals": [f"elevated_{metric_name}", f"deviation_{robust_z}sigma"],
                    "timestamp_utc": now_utc
                })

        # 2. Multivariate Isolation Forest ML evaluation
        feature_vector = [
            float(payload.get("cpu_usage", 0.0)),
            float(payload.get("memory_usage", 0.0)),
            float(payload.get("disk_usage", 0.0)),
            float(payload.get("latency_ms", 0.0)),
            float(payload.get("throughput_kbps", 0.0))
        ]
        self.models.add_training_vector(tenant_id, feature_vector)
        is_ml_anom, ml_score, ml_status = self.models.score(tenant_id, feature_vector)

        if is_ml_anom and not anomalies:
            now_utc = datetime.datetime.now(datetime.timezone.utc).isoformat()
            anomalies.append({
                "anomaly_id": f"ANOM-ML-{uuid.uuid4().hex[:8].upper()}",
                "source_id": source_id,
                "metric": "multivariate_telemetry",
                "observed_value": float(payload.get("cpu_usage", 0.0)),
                "baseline_value": self.baselines.get_baseline(tenant_id, source_id, "cpu_usage")["median"],
                "deviation": round(ml_score, 2),
                "deviation_sigma": round(ml_score * 4.0, 1),
                "anomaly_score": ml_score,
                "severity": "High" if ml_score >= 0.75 else "Medium",
                "detection_method": "IsolationForest",
                "reason": f"Multivariate Isolation Forest detected abnormal multi-metric feature correlation (score: {ml_score}).",
                "contributing_signals": ["multivariate_cluster_deviation"],
                "timestamp_utc": now_utc
            })

        return anomalies
