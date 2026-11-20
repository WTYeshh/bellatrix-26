import time
import psutil
from typing import Dict, Any, List

class MemoryMonitor:
    """
    Tier 1 Physical and Virtual Memory Monitoring.
    Collects Total, Used, Available RAM, Utilization %, Swap metrics, and history.
    """
    def __init__(self, history_size: int = 60):
        self.history_size = history_size
        self._history: List[Dict[str, Any]] = []

    def collect(self) -> Dict[str, Any]:
        vm = psutil.virtual_memory()
        swap = psutil.swap_memory()
        now = time.time()

        record = {
            "timestamp": now,
            "total_bytes": vm.total,
            "available_bytes": vm.available,
            "used_bytes": vm.used,
            "total_gb": round(vm.total / (1024**3), 2),
            "used_gb": round(vm.used / (1024**3), 2),
            "available_gb": round(vm.available / (1024**3), 2),
            "memory_percent": vm.percent,
            "swap_total_gb": round(swap.total / (1024**3), 2),
            "swap_used_gb": round(swap.used / (1024**3), 2),
            "swap_percent": swap.percent
        }

        self._history.append({"timestamp": now, "memory_percent": record["memory_percent"]})
        if len(self._history) > self.history_size:
            self._history.pop(0)

        return record

    def get_history(self) -> List[Dict[str, Any]]:
        return list(self._history)
