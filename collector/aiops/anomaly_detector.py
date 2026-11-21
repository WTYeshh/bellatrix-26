import uuid
import datetime
from typing import Dict, Any, Optional, List

class LocalAnomalyDetector:
    """
    Tier 1 Statistical Anomaly Detector:
    Applies Median Absolute Deviation (MAD), robust Z-score,
    sudden shift detection, and sustained threshold deviation tracking.
    """
    def __init__(self, zscore_threshold: float = 3.0):
        self.zscore_threshold = zscore_threshold
        self._sustained_counts: Dict[str, int] = {}

    def evaluate_metric(
        self,
        source_id: str,
        metric: str,
        observed_value: float,
        baseline_stats: Dict[str, float]
    ) -> Optional[Dict[str, Any]]:
        median = baseline_stats.get("median", observed_value)
        mad = baseline_stats.get("mad", 1.0)
        mean = baseline_stats.get("mean", observed_value)
        std = baseline_stats.get("std", 1.0)
        rate = baseline_stats.get("rate_of_change", 0.0)
        samples = baseline_stats.get("sample_count", 1)

        deviation = round(abs(observed_value - median), 2)
        # Robust Z-Score: 0.6745 * |X - median| / MAD
        robust_z = round(0.6745 * (abs(observed_value - median) / mad), 2)

        # 1. Sudden Spike Check (rapid acceleration)
        sudden_spike = (
            abs(rate) >= 30.0 and
            (
                (metric in ["cpu_usage", "memory_usage"] and observed_value >= 75.0) or
                (metric == "latency_ms" and observed_value >= 120.0)
            )
        )

        # 2. Robust Z-score breach check
        statistical_breach = (
            robust_z >= self.zscore_threshold and
            (
                (metric in ["cpu_usage", "memory_usage"] and observed_value >= 75.0) or
                (metric == "latency_ms" and observed_value >= 80.0) or
                (metric == "disk_usage" and observed_value >= 90.0)
            )
        )

        # 3. Sustained anomaly check
        is_high = (
            (metric in ["cpu_usage", "memory_usage"] and observed_value >= 80.0) or
            (metric == "latency_ms" and observed_value >= 100.0)
        )
        if is_high:
            self._sustained_counts[metric] = self._sustained_counts.get(metric, 0) + 1
        else:
            self._sustained_counts[metric] = 0

        sustained = self._sustained_counts.get(metric, 0) >= 3

        if not (sudden_spike or statistical_breach or sustained):
            return None

        # Severity categorization
        anomaly_score = min(0.99, max(0.50, round(0.5 + (robust_z / 10.0), 2)))
        if observed_value >= 95.0 or robust_z >= 5.0 or sustained:
            severity = "Critical" if observed_value >= 95.0 else "High"
        elif observed_value >= 85.0 or robust_z >= 3.5:
            severity = "High"
        else:
            severity = "Medium"

        detection_method = "MAD"
        if sudden_spike:
            detection_method = "Sudden-Shift"
            reason = f"Sudden positive acceleration of +{rate}% detected on {metric} (observed: {observed_value}%)."
        elif sustained:
            detection_method = "Sustained-Threshold"
            reason = f"{metric.replace('_', ' ').title()} sustained at elevated level ({observed_value}) for {self._sustained_counts[metric]} consecutive cycles."
        else:
            reason = f"{metric.replace('_', ' ').title()} ({observed_value}) exceeds recorded baseline ({median} ± {mad}) by {robust_z}σ."

        now_utc = datetime.datetime.now(datetime.timezone.utc).isoformat()
        return {
            "anomaly_id": f"LOC-ANOM-{uuid.uuid4().hex[:8].upper()}",
            "source_id": source_id,
            "metric": metric,
            "observed_value": observed_value,
            "baseline_value": median,
            "deviation": deviation,
            "anomaly_score": anomaly_score,
            "severity": severity,
            "detection_method": detection_method,
            "reason": reason,
            "timestamp_utc": now_utc
        }
