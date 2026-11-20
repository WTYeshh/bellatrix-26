import time
import os
import sys
import psutil
from typing import Dict, Any, Optional
from collector.transport.client import SaaSClient

class HeartbeatManager:
    """
    Tier 1 Heartbeat Manager.
    Transmits regular heartbeats to Tier 2 SaaS, tracking collector ID, status,
    host info, self-resource consumption (CPU%, RAM MB), and pending buffer counts.
    """
    def __init__(
        self,
        client: SaaSClient,
        collector_id: str,
        heartbeat_interval: int = 15,
        version: str = "1.0.0"
    ):
        self.client = client
        self.collector_id = collector_id
        self.interval = heartbeat_interval
        self.version = version
        self.last_heartbeat_time = 0.0
        self._proc = psutil.Process(os.getpid())

    def send_if_due(self, pending_buffer_count: int = 0) -> Optional[bool]:
        now = time.time()
        if now - self.last_heartbeat_time >= self.interval:
            col_mem_mb = round(self._proc.memory_info().rss / (1024 * 1024), 1)
            try:
                col_cpu_pct = round(self._proc.cpu_percent(interval=None), 1)
            except Exception:
                col_cpu_pct = 0.0

            os_info = f"Windows ({sys.platform}) Python {sys.version.split()[0]}"
            success = self.client.send_heartbeat(
                status="Online",
                cpu_usage=col_cpu_pct,
                memory_usage=col_mem_mb,
                pending_buffered=pending_buffer_count,
                os_info=os_info
            )
            self.last_heartbeat_time = now
            return success
        return None
