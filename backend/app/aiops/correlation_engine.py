import json
import datetime
from typing import List, Dict, Any, Optional

class IncidentCorrelationEngine:
    """
    DIFFERENTIATOR: INCIDENT DNA CORRELATION ENGINE
    Groups temporally and topologically related alert signals across sources
    into unified incidents, suppressing duplicate notification noise.
    """
    def correlate(
        self,
        tenant_id: str,
        anomalies: List[Dict[str, Any]],
        existing_active_incidents: List[Any]
    ) -> Optional[Dict[str, Any]]:
        if not anomalies:
            return None

        sources = list(set(a["source_id"] for a in anomalies))
        metrics = list(set(a["metric"] for a in anomalies))

        # 1. Deduplication check against active incidents
        for inc in existing_active_incidents:
            status = getattr(inc, "status", None) if not isinstance(inc, dict) else inc.get("status")
            if status in ["Active", "Investigating"]:
                try:
                    cols = getattr(inc, "affected_collectors", None) if not isinstance(inc, dict) else inc.get("affected_collectors")
                    inc_cols = json.loads(cols) if isinstance(cols, str) else cols
                    if not isinstance(inc_cols, list):
                        inc_cols = [str(inc_cols)]
                except Exception:
                    inc_cols = []
                if any(s in inc_cols for s in sources):
                    # Attach to existing incident instead of creating duplicate spam
                    return None

        # 2. Correlate severity
        max_sev = "Medium"
        for a in anomalies:
            if a.get("severity") == "Critical":
                max_sev = "Critical"
                break
            elif a.get("severity") == "High":
                max_sev = "High"

        # 3. Determine operational pattern from correlated metrics
        if "cpu_usage" in metrics and "latency_ms" in metrics:
            title = f"Compute Saturation & Latency Surge across {', '.join(sources)}"
            likely_cause = "Thread pool exhaustion and compute contention causing cascading application request latency."
            investigation = "Inspect active worker process thread counts, database connection pool limits, and CPU throttling."
            confidence = 0.94
        elif "memory_usage" in metrics and "latency_ms" in metrics:
            title = f"Memory Exhaustion & GC Latency Surge on {', '.join(sources)}"
            likely_cause = "Severe memory pressure triggering aggressive garbage collection pauses."
            investigation = "Profile heap memory allocation per worker and inspect resident set size (RSS)."
            confidence = 0.91
        elif "latency_ms" in metrics and "packet_loss_pct" in metrics:
            title = f"Network Pathway Congestion & Packet Degradation on {', '.join(sources)}"
            likely_cause = "Intermediate switch port buffering or upstream network gateway saturation."
            investigation = "Examine network interface drop counters, MTU settings, and routing hop latency."
            confidence = 0.90
        elif "cpu_usage" in metrics:
            title = f"Sustained CPU Anomaly on {', '.join(sources)}"
            likely_cause = "Compute utilization exceeded historical baseline by multiple standard deviations."
            investigation = "Check top consuming processes, background cron tasks, and thread contention."
            confidence = 0.88
        else:
            title = f"Multi-Signal Telemetry Deviation on {', '.join(sources)}"
            likely_cause = "Coordinated deviations across multiple operational signals within the same temporal window."
            investigation = "Correlate host telemetry with application access and error logs."
            confidence = 0.84

        now_str = datetime.datetime.now(datetime.timezone.utc).isoformat()
        incident_id = f"INC-{int(datetime.datetime.now(datetime.timezone.utc).timestamp())}"

        timeline = [
            {
                "timestamp": now_str,
                "event": "Telemetry breach detected by AIOps anomaly detector",
                "details": f"Metrics flagged: {', '.join(metrics)}"
            },
            {
                "timestamp": now_str,
                "event": "Incident DNA Correlation triggered",
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
