from typing import Dict, List, Any
import numpy as np

class FleetBaselineEngine:
    """
    Tier 2 Central AIOps: Computes dynamic rolling baselines
    across tenant infrastructure fleets.
    """
    def __init__(self, window_size: int = 40):
        self.window_size = window_size
        self._history: Dict[str, List[float]] = {}
        self._last_values: Dict[str, float] = {}

    def _key(self, tenant_id: str, source_id: str, metric: str) -> str:
        return f"{tenant_id}:{source_id}:{metric}"

    def record(self, tenant_id: str, source_id: str, metric: str, value: float) -> Dict[str, float]:
        k = self._key(tenant_id, source_id, metric)
        if k not in self._history:
            self._history[k] = []
        buf = self._history[k]
        buf.append(float(value))
        if len(buf) > self.window_size:
            buf.pop(0)

        last = self._last_values.get(k, value)
        rate = round(value - last, 2)
        self._last_values[k] = value

        arr = np.array(buf, dtype=float)
        mean_val = float(np.mean(arr))
        median_val = float(np.median(arr))
        std_val = float(np.std(arr)) if len(buf) > 1 else 1.0
        if std_val < 0.1:
            std_val = 1.0

        mad_val = float(np.median(np.abs(arr - median_val)))
        if mad_val < 0.1:
            mad_val = 1.0

        return {
            "mean": round(mean_val, 2),
            "median": round(median_val, 2),
            "std": round(std_val, 2),
            "mad": round(mad_val, 2),
            "rate_of_change": rate,
            "sample_count": len(buf)
        }

    def get_baseline(self, tenant_id: str, source_id: str, metric: str) -> Dict[str, float]:
        k = self._key(tenant_id, source_id, metric)
        buf = self._history.get(k, [])
        if not buf or len(buf) < 3:
            default_baselines = {
                "cpu_usage": 38.0,
                "memory_usage": 52.0,
                "disk_usage": 48.0,
                "latency_ms": 22.0,
                "packet_loss_pct": 0.0,
                "throughput_kbps": 120.0
            }
            base = default_baselines.get(metric, 30.0)
            return {
                "mean": base,
                "median": base,
                "std": 6.0,
                "mad": 4.5,
                "rate_of_change": 0.0,
                "sample_count": len(buf)
            }

        arr = np.array(buf, dtype=float)
        med = float(np.median(arr))
        mad = float(np.median(np.abs(arr - med))) or 1.0
        return {
            "mean": round(float(np.mean(arr)), 2),
            "median": round(med, 2),
            "std": round(float(np.std(arr)), 2) or 1.0,
            "mad": round(mad, 2),
            "rate_of_change": 0.0,
            "sample_count": len(buf)
        }
