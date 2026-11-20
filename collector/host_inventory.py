import os
import sys
import time
import socket
import platform
import datetime
from typing import Dict, Any, List, Optional
import psutil

try:
    import winreg
except ImportError:
    winreg = None

class WindowsHostInventory:
    """
    Tier 1 Real Windows Host Discovery and System Inventory.
    Collects 14 verified system attributes from the host machine:
    1. Windows hostname
    2. Windows edition and version
    3. Windows build number
    4. System architecture
    5. CPU model
    6. CPU physical and logical cores
    7. RAM capacity
    8. Storage devices and partitions
    9. Network interfaces
    10. System uptime
    11. Boot time
    12. Configured monitored services
    13. Running processes safe summary
    14. Collector version and resource usage
    """
    VERSION = "1.0.0"

    def __init__(self, monitored_services: Optional[List[str]] = None):
        self.monitored_services = monitored_services or [
            "EventLog", "LanmanServer", "wuauserv", "Spooler", "Themes", "PlugPlay", "RpcSs"
        ]
        self._proc = psutil.Process(os.getpid())

    def get_windows_edition_and_build(self) -> Dict[str, str]:
        """Discovers Windows product name, display version, and build number via Registry."""
        edition = "Windows"
        display_version = "Unknown"
        build_number = platform.version()

        if winreg and sys.platform == "win32":
            try:
                key = winreg.OpenKey(
                    winreg.HKEY_LOCAL_MACHINE,
                    r"SOFTWARE\Microsoft\Windows NT\CurrentVersion"
                )
                try:
                    edition = winreg.QueryValueEx(key, "ProductName")[0]
                except Exception:
                    pass
                try:
                    display_version = winreg.QueryValueEx(key, "DisplayVersion")[0]
                except Exception:
                    pass
                try:
                    build_number = winreg.QueryValueEx(key, "CurrentBuild")[0]
                except Exception:
                    pass
                winreg.CloseKey(key)
            except Exception:
                pass

        return {
            "edition": edition,
            "display_version": display_version,
            "build_number": str(build_number),
            "platform_release": platform.release(),
            "platform_version": platform.version()
        }

    def get_cpu_model(self) -> str:
        """Discovers CPU model name safely via Registry or platform processor."""
        if winreg and sys.platform == "win32":
            try:
                key = winreg.OpenKey(
                    winreg.HKEY_LOCAL_MACHINE,
                    r"HARDWARE\DESCRIPTION\System\CentralProcessor\0"
                )
                model_name = winreg.QueryValueEx(key, "ProcessorNameString")[0].strip()
                winreg.CloseKey(key)
                if model_name:
                    return model_name
            except Exception:
                pass
        return platform.processor() or "AMD/Intel x86_64 Processor"

    def get_storage_inventory(self) -> List[Dict[str, Any]]:
        """Discovers all mounted storage devices and accessible partitions."""
        storage = []
        for p in psutil.disk_partitions(all=False):
            if 'cdrom' in p.opts or not p.fstype:
                continue
            try:
                usage = psutil.disk_usage(p.mountpoint)
                storage.append({
                    "device": p.device,
                    "mountpoint": p.mountpoint,
                    "fstype": p.fstype,
                    "opts": p.opts,
                    "total_gb": round(usage.total / (1024**3), 2),
                    "used_gb": round(usage.used / (1024**3), 2),
                    "free_gb": round(usage.free / (1024**3), 2),
                    "percent": usage.percent
                })
            except (PermissionError, OSError):
                continue
        return storage

    def get_network_inventory(self) -> List[Dict[str, Any]]:
        """Discovers network adapters, MAC addresses, IPv4 configurations and link state."""
        interfaces = []
        addrs = psutil.net_if_addrs()
        stats = psutil.net_if_stats()

        for name, addr_list in addrs.items():
            ipv4 = None
            mac = None
            for a in addr_list:
                if getattr(a, 'family', None) == socket.AF_INET:
                    ipv4 = a.address
                elif getattr(a, 'family', None) == getattr(psutil, 'AF_LINK', -1):
                    mac = a.address

            st = stats.get(name)
            is_up = st.isup if st else False
            speed_mbps = st.speed if st else 0

            interfaces.append({
                "interface": name,
                "is_up": is_up,
                "speed_mbps": speed_mbps,
                "ipv4": ipv4 or "Unassigned",
                "mac": mac or "Unknown"
            })
        return interfaces

    def get_monitored_services(self) -> List[Dict[str, Any]]:
        """Checks configured Windows services and their current status."""
        services = []
        if sys.platform == "win32":
            for sname in self.monitored_services:
                try:
                    srv = psutil.win_service_get(sname)
                    info = srv.as_dict()
                    services.append({
                        "name": info.get("name", sname),
                        "display_name": info.get("display_name", sname),
                        "status": info.get("status", "unknown"),
                        "start_type": info.get("start_type", "unknown")
                    })
                except Exception:
                    services.append({
                        "name": sname,
                        "display_name": sname,
                        "status": "stopped",
                        "start_type": "manual"
                    })
        return services

    def get_process_summary(self) -> Dict[str, Any]:
        """Collects safe aggregate process counts and resource consumption without secrets."""
        total_procs = 0
        running_cnt = 0
        top_by_memory = []

        for p in psutil.process_iter(['pid', 'name', 'status', 'memory_info']):
            try:
                total_procs += 1
                info = p.info
                if info.get('status') == psutil.STATUS_RUNNING:
                    running_cnt += 1
                mem = info.get('memory_info')
                rss_mb = round(mem.rss / (1024 * 1024), 1) if mem else 0.0
                top_by_memory.append({
                    "pid": info['pid'],
                    "name": info['name'],
                    "rss_mb": rss_mb
                })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        top_by_memory.sort(key=lambda x: x['rss_mb'], reverse=True)
        return {
            "total_processes": total_procs,
            "running_processes": running_cnt,
            "top_processes_by_ram": top_by_memory[:5]
        }

    def collect_full_inventory(self) -> Dict[str, Any]:
        """Assembles the complete 14-point Windows Host Inventory."""
        win_info = self.get_windows_edition_and_build()
        cpu_model = self.get_cpu_model()
        vm = psutil.virtual_memory()
        boot_ts = psutil.boot_time()
        uptime_sec = int(time.time() - boot_ts)
        boot_dt = datetime.datetime.fromtimestamp(boot_ts, datetime.timezone.utc).isoformat()

        # Collector self-metrics
        col_mem_mb = round(self._proc.memory_info().rss / (1024 * 1024), 1)
        try:
            col_cpu_pct = round(self._proc.cpu_percent(interval=None), 1)
        except Exception:
            col_cpu_pct = 0.0

        return {
            "hostname": socket.gethostname(),
            "windows_edition": win_info["edition"],
            "windows_version": win_info["display_version"],
            "windows_build": win_info["build_number"],
            "architecture": platform.machine(),
            "cpu_model": cpu_model,
            "cpu_physical_cores": psutil.cpu_count(logical=False) or 1,
            "cpu_logical_cores": psutil.cpu_count(logical=True) or 1,
            "ram_total_gb": round(vm.total / (1024**3), 2),
            "ram_available_gb": round(vm.available / (1024**3), 2),
            "storage_partitions": self.get_storage_inventory(),
            "network_interfaces": self.get_network_inventory(),
            "system_uptime_seconds": uptime_sec,
            "boot_time_utc": boot_dt,
            "monitored_services": self.get_monitored_services(),
            "process_summary": self.get_process_summary(),
            "collector_info": {
                "version": self.VERSION,
                "memory_rss_mb": col_mem_mb,
                "cpu_percent": col_cpu_pct,
                "pid": os.getpid()
            },
            "timestamp_utc": datetime.datetime.now(datetime.timezone.utc).isoformat()
        }
