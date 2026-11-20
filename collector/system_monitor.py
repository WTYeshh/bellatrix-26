import time
import os
import psutil
from typing import Dict, Any, List, Optional

from collector.cpu_monitor import CPUMonitor
from collector.memory_monitor import MemoryMonitor
from collector.disk_monitor import DiskMonitor
from collector.network_monitor import NetworkMonitor
from collector.process_monitor import ProcessMonitor
from collector.service_monitor import ServiceMonitor
from collector.security_monitor import SecurityMonitor

class SystemMetricsSource:
    """
    Tier 1 Unified System Monitor Source.
    Coordinates CPU, Memory, Disk, Network, Process, Service, and Security monitors.
    Provides standard telemetry payload dictionary for Tier 1 privacy evaluation and ingestion.
    """
    def __init__(self, probe_target: str = "8.8.8.8", probe_port: int = 53):
        self.cpu_monitor = CPUMonitor()
        self.memory_monitor = MemoryMonitor()
        self.disk_monitor = DiskMonitor()
        self.network_monitor = NetworkMonitor(probe_target=probe_target, probe_port=probe_port)
        self.process_monitor = ProcessMonitor()
        self.service_monitor = ServiceMonitor()
        self.security_monitor = SecurityMonitor()
        self._proc = psutil.Process(os.getpid())

    def measure_network_latency(self) -> float:
        probe = self.network_monitor.probe_latency_and_loss(samples=1)
        return probe["latency_ms"]

    def collect(self) -> Dict[str, Any]:
        """Gathers unified real system measurements across all subsystems."""
        cpu = self.cpu_monitor.collect()
        mem = self.memory_monitor.collect()
        disk = self.disk_monitor.collect()
        net = self.network_monitor.collect()
        procs = self.process_monitor.collect()
        services = self.service_monitor.collect()
        sec = self.security_monitor.collect_summary()

        # Collector self-footprint
        col_mem_mb = round(self._proc.memory_info().rss / (1024 * 1024), 1)
        try:
            col_cpu_pct = round(self._proc.cpu_percent(interval=None), 1)
        except Exception:
            col_cpu_pct = 0.0

        # Health state calculation based on 4-state product model
        health_state = "Excellent"
        if cpu["cpu_percent"] > 88.0 or mem["memory_percent"] > 92.0 or disk["primary_disk_percent"] > 95.0:
            health_state = "Poor"
        elif cpu["cpu_percent"] > 75.0 or mem["memory_percent"] > 82.0 or net["latency_ms"] > 150.0:
            health_state = "Fair"
        elif cpu["cpu_percent"] > 50.0 or mem["memory_percent"] > 70.0 or net["latency_ms"] > 80.0:
            health_state = "Good"

        return {
            "cpu_usage": cpu["cpu_percent"],
            "memory_usage": mem["memory_percent"],
            "disk_usage": disk["primary_disk_percent"],
            "latency_ms": net["latency_ms"],
            "packet_loss_pct": net["packet_loss_pct"],
            "upload_kbps": net["upload_kbps"],
            "download_kbps": net["download_kbps"],
            "health_state": health_state,
            "event_category": "Performance",
            "severity": "Low" if health_state in ["Excellent", "Good"] else ("High" if health_state == "Poor" else "Medium"),
            # Hardware details
            "per_core_cpu": cpu["per_core_percent"],
            "physical_cores": cpu["physical_cores"],
            "logical_cores": cpu["logical_cores"],
            "ram_total_gb": mem["total_gb"],
            "ram_available_gb": mem["available_gb"],
            "disk_partitions": disk["partitions"],
            "disk_read_kbps": disk["read_kbps"],
            "disk_write_kbps": disk["write_kbps"],
            "monitored_services": services["services"],
            "running_service_count": services["running_service_count"],
            "process_count": procs["total_process_count"],
            "top_processes": procs["top_processes"][:5],
            "security_failed_logins": sec["failed_login_count"],
            # Collector overhead
            "collector_cpu_pct": col_cpu_pct,
            "collector_mem_mb": col_mem_mb
        }
