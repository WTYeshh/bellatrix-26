import numpy as np
from typing import Dict, List, Any

class RollingBaselineTracker:
    """
    Tier 1 Local AIOps: Maintains rolling window statistics
    to calculate dynamic baselines without SaaS connectivity.
    """
    def __init__(self, window_size: int = 30):
        self.window_size = window_size
        self._buffers: Dict[str, List[float]] = {}
        self._last_values: Dict[str, float] = {}

    def update(self, metric: str, value: float) -> Dict[str, float]:
        """Records a new value and computes rolling baseline stats."""
        if metric not in self._buffers:
            self._buffers[metric] = []
        
        buf = self._buffers[metric]
        buf.append(float(value))
        if len(buf) > self.window_size:
            buf.pop(0)

        # Rate of change
        last = self._last_values.get(metric, value)
        rate_of_change = round(value - last, 2)
        self._last_values[metric] = value

        arr = np.array(buf, dtype=float)
        mean_val = float(np.mean(arr))
        median_val = float(np.median(arr))
        std_val = float(np.std(arr)) if len(buf) > 1 else 1.0
        if std_val < 0.1:
            std_val = 1.0  # Avoid zero-division

        # Median Absolute Deviation (MAD)
        mad_val = float(np.median(np.abs(arr - median_val)))
        if mad_val < 0.1:
            mad_val = 1.0

        return {
            "mean": round(mean_val, 2),
            "median": round(median_val, 2),
            "std": round(std_val, 2),
            "mad": round(mad_val, 2),
            "rate_of_change": rate_of_change,
            "sample_count": len(buf)
        }

    def get_baseline(self, metric: str) -> Dict[str, float]:
        buf = self._buffers.get(metric, [])
        if not buf:
            return {"mean": 0.0, "median": 0.0, "std": 1.0, "mad": 1.0, "rate_of_change": 0.0, "sample_count": 0}
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

    def is_ready(self, metric: str, min_samples: int = 5) -> bool:
        """Checks if enough samples exist for statistical significance."""
        return len(self._buffers.get(metric, [])) >= min_samples
