import psutil
from typing import Dict, Any, List

class ProcessMonitor:
    """
    Tier 1 Safe Process Monitoring.
    Collects PID, process name, CPU%, memory RSS, and status.
    Strictly avoids reading command-line arguments, environment variables, or private files.
    """
    def __init__(self, top_limit: int = 10):
        self.top_limit = top_limit

    def collect(self) -> Dict[str, Any]:
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
                    "status": str(info.get('status')),
                    "memory_rss_mb": rss_mb
                })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        processes.sort(key=lambda x: x['memory_rss_mb'], reverse=True)

        return {
            "total_process_count": total_procs,
            "running_process_count": running_cnt,
            "top_processes": processes[:self.top_limit]
        }
