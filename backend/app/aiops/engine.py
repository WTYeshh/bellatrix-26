import math
import json
import datetime
from typing import List, Dict, Any, Optional, Tuple
import numpy as np
from sklearn.ensemble import IsolationForest

class AIOpsEngine:
    def __init__(self):
        # In-memory historical buffers per (tenant_id, source_id, metric) for fast statistical baselining
        self._history: Dict[str, List[float]] = {}
        # ML Isolation Forest models per tenant
        self._ml_models: Dict[str, IsolationForest] = {}
        self._ml_training_data: Dict[str, List[List[float]]] = {}

    def _get_key(self, tenant_id: str, source_id: str, metric: str) -> str:
        return f"{tenant_id}:{source_id}:{metric}"

    def record_observation(self, tenant_id: str, source_id: str, metric: str, value: float):
        key = self._get_key(tenant_id, source_id, metric)
        if key not in self._history:
            self._history[key] = []
        self._history[key].append(value)
        # Keep rolling window of last 60 observations
        if len(self._history[key]) > 60:
            self._history[key].pop(0)

    def calculate_statistical_baseline(self, tenant_id: str, source_id: str, metric: str) -> Dict[str, float]:
        key = self._get_key(tenant_id, source_id, metric)
        data = self._history.get(key, [])
        if not data or len(data) < 3:
            # Fallback baseline when history is minimal
            default_baselines = {
                "cpu_usage": 40.0,
                "memory_usage": 55.0,
                "disk_usage": 50.0,
                "latency_ms": 25.0,
                "packet_loss_pct": 0.0
            }
            base = default_baselines.get(metric, 30.0)
            return {
                "mean": base,
                "median": base,
                "std": 8.0,
                "mad": 6.0,
                "count": len(data)
            }

        arr = np.array(data, dtype=float)
        mean_val = float(np.mean(arr))
        median_val = float(np.median(arr))
        std_val = float(np.std(arr)) or 1.0  # avoid div by zero
        mad_val = float(np.median(np.abs(arr - median_val))) or 1.0

        return {
            "mean": round(mean_val, 2),
            "median": round(median_val, 2),
            "std": round(std_val, 2),
            "mad": round(mad_val, 2),
            "count": len(data)
        }

    def detect_statistical_anomaly(
        self,
        tenant_id: str,
        source_id: str,
        metric: str,
        current_value: float
    ) -> Optional[Dict[str, Any]]:
        """
        Computes robust Z-Score and MAD to detect anomalies beyond static thresholds.
        """
        stats = self.calculate_statistical_baseline(tenant_id, source_id, metric)
        mean = stats["mean"]
        median = stats["median"]
        std = stats["std"]
        mad = stats["mad"]

        # Z-score = (X - mean) / std
        z_score = abs(current_value - mean) / std
        # Robust Z-score using MAD: 0.6745 * (X - median) / MAD
        robust_z = 0.6745 * abs(current_value - median) / mad

        # Record this value into history for continuous learning
        self.record_observation(tenant_id, source_id, metric, current_value)

        # Deviation criteria: robust_z > 2.8 or z_score > 2.5 and substantial absolute value
        is_anomaly = (robust_z >= 2.8 or z_score >= 2.5) and (
            (metric in ["cpu_usage", "memory_usage"] and current_value > 75.0) or
            (metric == "latency_ms" and current_value > 80.0) or
            (metric == "packet_loss_pct" and current_value > 5.0) or
            (metric == "disk_usage" and current_value > 88.0)
        )

        if not is_anomaly:
            return None

        # Determine severity and anomaly score (normalized 0.0 - 1.0)
        anomaly_score = min(0.99, max(0.50, round(0.5 + (robust_z / 10.0), 2)))
        
        if anomaly_score >= 0.85 or current_value >= 90.0:
            severity = "Critical" if current_value >= 95.0 else "High"
        elif anomaly_score >= 0.70:
            severity = "Medium"
        else:
            severity = "Low"

        reason = (
            f"{metric.replace('_', ' ').upper()} observed at {current_value} "
            f"deviates significantly by {round(robust_z, 1)}σ from historical baseline ({median} ± {mad})."
        )

        return {
            "source_id": source_id,
            "metric": metric,
            "observed_value": current_value,
            "baseline_value": median,
            "deviation_sigma": round(robust_z, 2),
            "anomaly_score": anomaly_score,
            "severity": severity,
            "reason": reason,
            "contributing_signals": [f"elevated_{metric}", f"deviation_{round(robust_z, 1)}sigma"]
        }

    def train_isolation_forest(self, tenant_id: str, feature_matrix: List[List[float]]):
        """Trains an Isolation Forest model for multi-dimensional anomaly detection."""
        if len(feature_matrix) < 10:
            return  # Need sufficient observations
        
        clf = IsolationForest(n_estimators=50, contamination=0.1, random_state=42)
        X = np.array(feature_matrix, dtype=float)
        clf.fit(X)
        self._ml_models[tenant_id] = clf

    def score_multivariate_ml(self, tenant_id: str, features: List[float]) -> Tuple[bool, float]:
        """
        Runs scikit-learn Isolation Forest on multi-metric vector:
        [cpu_usage, memory_usage, disk_usage, latency_ms, packet_loss_pct]
        Returns (is_anomaly, anomaly_score)
        """
        model = self._ml_models.get(tenant_id)
        if not model:
            # Populate training buffer
            if tenant_id not in self._ml_training_data:
                self._ml_training_data[tenant_id] = []
            self._ml_training_data[tenant_id].append(features)
            if len(self._ml_training_data[tenant_id]) >= 15:
                self.train_isolation_forest(tenant_id, self._ml_training_data[tenant_id])
            return False, 0.2

        X = np.array([features], dtype=float)
        pred = model.predict(X)[0]  # -1 for anomaly, 1 for normal
        decision_score = model.decision_function(X)[0]
        # Normalize decision score: negative values indicate anomalies
        norm_score = round(max(0.0, min(1.0, 0.5 - (decision_score * 2.0))), 2)
        is_anomaly = bool(pred == -1)
        return is_anomaly, norm_score

    def correlate_incident_dna(
        self,
        tenant_id: str,
        anomalies: List[Dict[str, Any]],
        existing_active_incidents: List[Any]
    ) -> Optional[Dict[str, Any]]:
        """
        INCIDENT DNA ENGINE:
        Groups temporally and operationally related alert signals into a single incident,
        suppressing duplicate alert spam and extracting root-cause correlation.
        """
        if not anomalies:
            return None

        # Check if an active incident already exists for this source or affected service
        sources = list(set(a["source_id"] for a in anomalies))
        metrics = list(set(a["metric"] for a in anomalies))

        # Check existing active incidents to prevent duplicates
        for inc in existing_active_incidents:
            if inc.status in ["Active", "Investigating"]:
                try:
                    inc_collectors = json.loads(inc.affected_collectors) if isinstance(inc.affected_collectors, str) else inc.affected_collectors
                except:
                    inc_collectors = []
                # If any source matches, attach to existing incident rather than duplicating
                if any(s in inc_collectors for s in sources):
                    return None

        # Correlate contributing signals
        signals = []
        for a in anomalies:
            signals.extend(a.get("contributing_signals", []))
        signals = list(set(signals))

        max_sev = "Medium"
        for a in anomalies:
            if a.get("severity") == "Critical":
                max_sev = "Critical"
                break
            elif a.get("severity") == "High":
                max_sev = "High"

        # Determine likely operational cause based on correlated metrics
        if "cpu_usage" in metrics and "latency_ms" in metrics:
            title = f"Performance Saturation & Latency Surge on {', '.join(sources)}"
            likely_cause = "Thread pool exhaustion and compute contention causing cascading request latency."
            investigation = "Inspect active process thread counts, database connection pool limits, and CPU governor state."
            confidence = 0.92
        elif "memory_usage" in metrics:
            title = f"Memory Pressure & Growth Anomaly on {', '.join(sources)}"
            likely_cause = "Potential uncollected memory allocation or heap leak in active server workers."
            investigation = "Analyze resident set size (RSS) per process and verify garbage collection metrics."
            confidence = 0.88
        elif "latency_ms" in metrics and "packet_loss_pct" in metrics:
            title = f"Network Pathway Degradation on {', '.join(sources)}"
            likely_cause = "Congestion on intermediate switch port or upstream network gateway."
            investigation = "Verify MTU settings, traceroute hop latency, and interface drop counters."
            confidence = 0.90
        elif "cpu_usage" in metrics:
            title = f"Sustained CPU Anomaly Spike on {', '.join(sources)}"
            likely_cause = "CPU usage exceeded historical baseline by multiple standard deviations."
            investigation = "Check background worker workloads, cron executions, and top CPU consuming processes."
            confidence = 0.85
        else:
            title = f"Multi-Signal Telemetry Anomaly Detected across {', '.join(sources)}"
            likely_cause = "Coordinated deviations across multiple operational signals within the same temporal window."
            investigation = "Correlate server telemetry with application access logs."
            confidence = 0.82

        now_str = datetime.datetime.now(datetime.timezone.utc).isoformat()
        incident_id = f"INC-{int(datetime.datetime.now(datetime.timezone.utc).timestamp())}"

        timeline = [
            {
                "timestamp": now_str,
                "event": "Telemetry breach detected by AIOps anomaly detector",
                "details": f"Observed metrics: {', '.join(metrics)}"
            },
            {
                "timestamp": now_str,
                "event": "Incident DNA Correlation Engine triggered",
                "details": f"Correlated {len(anomalies)} telemetry anomalies from source(s) {', '.join(sources)}"
            }
        ]

        return {
            "incident_id": incident_id,
            "title": title,
            "severity": max_sev,
            "status": "Active",
            "affected_service": f"Service-{sources[0] if sources else 'Fleet'}",
            "affected_collectors": sources,
            "related_alerts": anomalies,
            "timeline": timeline,
            "likely_cause": likely_cause,
            "recommended_investigation": investigation,
            "confidence": confidence
        }

    def generate_explainable_recommendation(
        self,
        incident: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        DIFFERENTIATOR: EXPLAINABLE AI RECOMMENDATION
        Provides transparent, evidence-backed recommendations explaining:
        - Why it was flagged
        - What evidence supports it
        - Exactly what action is recommended
        """
        title = f"Mitigation Strategy for {incident['title']}"
        inc_id = incident.get("incident_id", "INC-001")
        evidence = []

        for alert in incident.get("related_alerts", []):
            evidence.append({
                "metric": alert.get("metric"),
                "observed": alert.get("observed_value"),
                "baseline": alert.get("baseline_value"),
                "deviation": f"+{alert.get('deviation_sigma', 3.0)}σ",
                "severity": alert.get("severity")
            })

        action = (
            f"1. Scale worker replicas or adjust resource throttles for {', '.join(incident.get('affected_collectors', []))}.\n"
            f"2. {incident.get('recommended_investigation')}\n"
            f"3. Run safe recovery simulation prior to production rollout."
        )

        reason = (
            f"Generated based on {len(evidence)} verified telemetry signals. "
            f"Likely operational factor: {incident.get('likely_cause')} "
            f"Calculated correlation confidence: {int(incident.get('confidence', 0.85) * 100)}%."
        )

        return {
            "recommendation_id": f"REC-{inc_id}",
            "incident_id": inc_id,
            "title": title,
            "reason": reason,
            "severity": incident.get("severity", "Medium"),
            "confidence": incident.get("confidence", 0.85),
            "supporting_evidence": evidence,
            "suggested_action": action
        }

# Global singleton
aiops_engine = AIOpsEngine()
