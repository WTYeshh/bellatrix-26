import time
import psutil
from typing import Dict, Any, List, Optional

class ProcessMonitor:
    """
    Tier 1 Safe Process Monitoring.
    Collects PID, process name, memory RSS, and status with lightweight TTL caching.
    Strictly avoids reading command-line arguments, environment variables, or private files.
    """
    def __init__(self, top_limit: int = 10, cache_ttl_sec: float = 10.0):
        self.top_limit = top_limit
        self.cache_ttl_sec = cache_ttl_sec
        self._cached_data = None
        self._last_time = 0.0

    def collect(self, limit: Optional[int] = None) -> Dict[str, Any]:
        now = time.time()
        top_n = limit or self.top_limit
        if self._cached_data and (now - self._last_time < self.cache_ttl_sec):
            return {
                "total_process_count": self._cached_data["total_process_count"],
                "running_process_count": self._cached_data["running_process_count"],
                "top_processes": self._cached_data["top_processes"][:top_n]
            }

        processes = []
        total_procs = 0
        running_cnt = 0

        for p in psutil.process_iter(['pid', 'name', 'status', 'memory_info']):
            try:
                total_procs += 1
                info = p.info
                if info.get('status') == psutil.STATUS_RUNNING:
                    running_cnt += 1
                mem = info.get('memory_info')
                rss_mb = round(mem.rss / (1024 * 1024), 1) if mem else 0.0

                processes.append({
                    "pid": info['pid'],
                    "name": info.get('name') or "unknown",
                    "status": str(info.get('status') or "running"),
                    "memory_rss_mb": rss_mb
                })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        processes.sort(key=lambda x: x['memory_rss_mb'], reverse=True)
        self._cached_data = {
            "total_process_count": total_procs,
            "running_process_count": running_cnt,
            "top_processes": processes
        }
        self._last_time = now

        return {
            "total_process_count": total_procs,
            "running_process_count": running_cnt,
            "top_processes": processes[:top_n]
        }
