from typing import Dict, List, Any
import numpy as np

class FleetBaselineEngine:
    """
    Computes dynamic rolling baselines (Mean, Standard Deviation, Median, MAD, and EWMA)
    from stored real laptop telemetry samples.
    """
    def __init__(self, window_size: int = 60, ewma_alpha: float = 0.2):
        self.window_size = window_size
        self.ewma_alpha = ewma_alpha
        self._history: Dict[str, List[float]] = {}
        self._ewma: Dict[str, float] = {}
        self._last_values: Dict[str, float] = {}

    def _key(self, tenant_id: str, source_id: str, metric: str) -> str:
        return f"{tenant_id}:{source_id}:{metric}"

    def record(self, tenant_id: str, source_id: str, metric: str, value: float) -> Dict[str, Any]:
        k = self._key(tenant_id, source_id, metric)
        if k not in self._history:
            self._history[k] = []
        buf = self._history[k]
        val = float(value)
        buf.append(val)
        if len(buf) > self.window_size:
            buf.pop(0)

        # Update EWMA
        if k not in self._ewma:
            self._ewma[k] = val
        else:
            self._ewma[k] = round((self.ewma_alpha * val) + ((1.0 - self.ewma_alpha) * self._ewma[k]), 2)

        last = self._last_values.get(k, val)
        rate = round(val - last, 2)
        self._last_values[k] = val

        arr = np.array(buf, dtype=float)
        mean_val = float(np.mean(arr))
        median_val = float(np.median(arr))
        std_val = float(np.std(arr)) if len(buf) > 1 else 1.0
        if std_val < 0.1:
            std_val = 1.0

        mad_val = float(np.median(np.abs(arr - median_val)))
        if mad_val < 0.1:
            mad_val = 1.0

        is_calibrating = len(buf) < 5

        return {
            "mean": round(mean_val, 2),
            "median": round(median_val, 2),
            "std": round(std_val, 2),
            "mad": round(mad_val, 2),
            "ewma": self._ewma[k],
            "rate_of_change": rate,
            "sample_count": len(buf),
            "is_calibrating": is_calibrating
        }

    def get_baseline(self, tenant_id: str, source_id: str, metric: str) -> Dict[str, Any]:
        k = self._key(tenant_id, source_id, metric)
        buf = self._history.get(k, [])
        if not buf or len(buf) < 5:
            arr = np.array(buf, dtype=float) if buf else np.array([0.0])
            med = float(np.median(arr))
            mad = float(np.median(np.abs(arr - med))) or 1.0
            return {
                "mean": round(float(np.mean(arr)), 2),
                "median": round(med, 2),
                "std": round(float(np.std(arr)), 2) or 1.0,
                "mad": round(mad, 2),
                "ewma": self._ewma.get(k, round(med, 2)),
                "rate_of_change": 0.0,
                "sample_count": len(buf),
                "is_calibrating": True
            }

        arr = np.array(buf, dtype=float)
        med = float(np.median(arr))
        mad = float(np.median(np.abs(arr - med))) or 1.0
        return {
            "mean": round(float(np.mean(arr)), 2),
            "median": round(med, 2),
            "std": round(float(np.std(arr)), 2) or 1.0,
            "mad": round(mad, 2),
            "ewma": self._ewma.get(k, round(med, 2)),
            "rate_of_change": 0.0,
            "sample_count": len(buf),
            "is_calibrating": len(buf) < 5
        }
