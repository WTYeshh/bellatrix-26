import time
import psutil
from typing import Dict, Any, List

class CPUMonitor:
    """
    Tier 1 CPU Utilization and Hardware Monitoring.
    Measures overall CPU%, per-core CPU%, clock frequency, core counts, and rolling buffers.
    """
    def __init__(self, history_size: int = 60):
        self.history_size = history_size
        self._history: List[Dict[str, Any]] = []
        # Warmup CPU sampling
        psutil.cpu_percent(interval=None)
        psutil.cpu_percent(percpu=True)

    def collect(self) -> Dict[str, Any]:
        """Collects current timestamped CPU telemetry."""
        total_pct = psutil.cpu_percent(interval=None)
        per_core = psutil.cpu_percent(percpu=True)
        logical_cnt = psutil.cpu_count(logical=True) or len(per_core) or 1
        physical_cnt = psutil.cpu_count(logical=False) or max(1, logical_cnt // 2)

        freq = None
        try:
            f = psutil.cpu_freq()
            if f:
                freq = {
                    "current_mhz": round(f.current, 1),
                    "min_mhz": round(f.min, 1) if f.min else None,
                    "max_mhz": round(f.max, 1) if f.max else None
                }
        except Exception:
            pass

        now = time.time()
        record = {
            "timestamp": now,
            "cpu_percent": round(total_pct, 1),
            "per_core_percent": [round(c, 1) for c in per_core],
            "physical_cores": physical_cnt,
            "logical_cores": logical_cnt,
            "frequency": freq
        }

        self._history.append({"timestamp": now, "cpu_percent": record["cpu_percent"]})
        if len(self._history) > self.history_size:
            self._history.pop(0)

        return record

    def get_history(self) -> List[Dict[str, Any]]:
        return list(self._history)
