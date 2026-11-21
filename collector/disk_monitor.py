import time
import psutil
from typing import Dict, Any, List

class DiskMonitor:
    """
    Tier 1 Storage & Disk I/O Monitoring.
    Safely discovers all accessible Windows partitions, measures capacities,
    and calculates read/write throughput (KB/s) from differential counters.
    """
    def __init__(self):
        self._last_time = time.time()
        self._last_io = None
        self._partitions_cache = None
        self._partitions_cache_time = 0.0
        try:
            self._last_io = psutil.disk_io_counters()
        except Exception:
            pass

    def collect_partitions(self) -> List[Dict[str, Any]]:
        now = time.time()
        if self._partitions_cache and (now - self._partitions_cache_time) < 10.0:
            return self._partitions_cache

        partitions = []
        for p in psutil.disk_partitions(all=False):
            if 'cdrom' in p.opts or not p.fstype:
                continue
            try:
                u = psutil.disk_usage(p.mountpoint)
                partitions.append({
                    "mountpoint": p.mountpoint,
                    "fstype": p.fstype,
                    "total_gb": round(u.total / (1024**3), 2),
                    "used_gb": round(u.used / (1024**3), 2),
                    "free_gb": round(u.free / (1024**3), 2),
                    "percent": u.percent
                })
            except (PermissionError, OSError):
                continue
        self._partitions_cache = partitions
        self._partitions_cache_time = now
        return partitions

    def collect_throughput(self) -> Dict[str, Any]:
        now = time.time()
        dt = max(now - self._last_time, 0.001)
        read_kbps = 0.0
        write_kbps = 0.0
        read_count = 0
        write_count = 0
        total_iops = 0.0

        try:
            current_io = psutil.disk_io_counters()
            if current_io and self._last_io:
                read_bytes = max(0, current_io.read_bytes - self._last_io.read_bytes)
                write_bytes = max(0, current_io.write_bytes - self._last_io.write_bytes)
                read_kbps = round((read_bytes / dt) / 1024.0, 1)
                write_kbps = round((write_bytes / dt) / 1024.0, 1)
                read_count = current_io.read_count
                write_count = current_io.write_count
                r_diff = max(0, current_io.read_count - self._last_io.read_count)
                w_diff = max(0, current_io.write_count - self._last_io.write_count)
                total_iops = round((r_diff + w_diff) / dt, 1)
            self._last_io = current_io
        except Exception:
            pass
        self._last_time = now

        return {
            "read_kbps": read_kbps,
            "write_kbps": write_kbps,
            "read_count": read_count,
            "write_count": write_count,
            "total_iops": total_iops
        }

    def collect(self) -> Dict[str, Any]:
        partitions = self.collect_partitions()
        throughput = self.collect_throughput()
        primary_pct = partitions[0]["percent"] if partitions else 0.0

        return {
            "primary_disk_percent": primary_pct,
            "partitions": partitions,
            "read_kbps": throughput["read_kbps"],
            "write_kbps": throughput["write_kbps"],
            "read_count": throughput["read_count"],
            "write_count": throughput["write_count"],
            "total_iops": throughput["total_iops"]
        }
