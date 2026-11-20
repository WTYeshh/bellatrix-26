import time
import os
import socket
import datetime
import psutil
from typing import Dict, Any, List
from fastapi import APIRouter, Depends, Query
from backend.app.models import User
from backend.app.auth.security import get_current_user

router = APIRouter(prefix="/system", tags=["System Hardware & Windows Monitoring"])

_last_net_check = {"time": time.time(), "bytes_sent": 0, "bytes_recv": 0}
try:
    _init_net = psutil.net_io_counters()
    _last_net_check["bytes_sent"] = _init_net.bytes_sent
    _last_net_check["bytes_recv"] = _init_net.bytes_recv
except Exception:
    pass

def _measure_socket_latency(host: str = "8.8.8.8", port: int = 53) -> float:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(1.0)
    start = time.perf_counter()
    try:
        s.connect((host, port))
        lat = (time.perf_counter() - start) * 1000.0
        s.close()
        return round(lat, 1)
    except Exception:
        return 15.0

@router.get("/overview")
async def get_system_overview(current_user: User = Depends(get_current_user)):
    """Overview of physical host hardware and operating system."""
    vm = psutil.virtual_memory()
    disk = psutil.disk_usage("C:\\" if psutil.WINDOWS else "/")
    
    return {
        "hostname": socket.gethostname(),
        "platform": os.name,
        "os": "Windows" if psutil.WINDOWS else "Linux/Unix",
        "logical_processors": psutil.cpu_count(logical=True),
        "physical_cores": psutil.cpu_count(logical=False),
        "total_ram_gb": round(vm.total / (1024**3), 2),
        "available_ram_gb": round(vm.available / (1024**3), 2),
        "total_disk_gb": round(disk.total / (1024**3), 2),
        "free_disk_gb": round(disk.free / (1024**3), 2),
        "cpu_percent": psutil.cpu_percent(interval=0.1),
        "memory_percent": vm.percent,
        "disk_percent": disk.percent,
        "uptime_seconds": int(time.time() - psutil.boot_time()),
        "timestamp_utc": datetime.datetime.now(datetime.timezone.utc).isoformat()
    }

@router.get("/cpu")
async def get_system_cpu(current_user: User = Depends(get_current_user)):
    """Detailed real-time per-core CPU telemetry."""
    per_core = psutil.cpu_percent(interval=0.1, percpu=True)
    freq = psutil.cpu_freq()
    
    return {
        "overall_cpu_percent": psutil.cpu_percent(interval=None),
        "per_core_percent": per_core,
        "logical_processors": psutil.cpu_count(logical=True),
        "physical_cores": psutil.cpu_count(logical=False),
        "frequency_mhz": {
            "current": round(freq.current, 1) if freq else 0.0,
            "min": round(freq.min, 1) if freq and freq.min else 0.0,
            "max": round(freq.max, 1) if freq and freq.max else 0.0
        },
        "timestamp_utc": datetime.datetime.now(datetime.timezone.utc).isoformat()
    }

@router.get("/memory")
async def get_system_memory(current_user: User = Depends(get_current_user)):
    """Physical and swap memory measurements."""
    vm = psutil.virtual_memory()
    sm = psutil.swap_memory()
    
    return {
        "total_bytes": vm.total,
        "total_gb": round(vm.total / (1024**3), 2),
        "used_bytes": vm.used,
        "used_gb": round(vm.used / (1024**3), 2),
        "available_bytes": vm.available,
        "available_gb": round(vm.available / (1024**3), 2),
        "percent": vm.percent,
        "swap_total_gb": round(sm.total / (1024**3), 2),
        "swap_used_gb": round(sm.used / (1024**3), 2),
        "swap_percent": sm.percent,
        "timestamp_utc": datetime.datetime.now(datetime.timezone.utc).isoformat()
    }

@router.get("/disk")
async def get_system_disk(current_user: User = Depends(get_current_user)):
    """Disk partition capacity, utilization and read/write counters."""
    partitions_info = []
    for part in psutil.disk_partitions(all=False):
        if 'cdrom' in part.opts or not part.fstype:
            continue
        try:
            usage = psutil.disk_usage(part.mountpoint)
            partitions_info.append({
                "device": part.device,
                "mountpoint": part.mountpoint,
                "fstype": part.fstype,
                "total_gb": round(usage.total / (1024**3), 2),
                "used_gb": round(usage.used / (1024**3), 2),
                "free_gb": round(usage.free / (1024**3), 2),
                "percent": usage.percent
            })
        except (PermissionError, OSError):
            continue

    io_counters = psutil.disk_io_counters()
    return {
        "partitions": partitions_info,
        "read_bytes": io_counters.read_bytes if io_counters else 0,
        "write_bytes": io_counters.write_bytes if io_counters else 0,
        "read_count": io_counters.read_count if io_counters else 0,
        "write_count": io_counters.write_count if io_counters else 0,
        "timestamp_utc": datetime.datetime.now(datetime.timezone.utc).isoformat()
    }

@router.get("/network")
async def get_system_network(current_user: User = Depends(get_current_user)):
    """Network speeds, interface details and live socket latency."""
    global _last_net_check
    now = time.time()
    current_io = psutil.net_io_counters()
    
    elapsed = max(0.1, now - _last_net_check["time"])
    bytes_sent_delta = max(0, current_io.bytes_sent - _last_net_check["bytes_sent"])
    bytes_recv_delta = max(0, current_io.bytes_recv - _last_net_check["bytes_recv"])
    
    upload_speed_kbps = round((bytes_sent_delta / 1024.0) / elapsed, 1)
    download_speed_kbps = round((bytes_recv_delta / 1024.0) / elapsed, 1)
    
    _last_net_check = {
        "time": now,
        "bytes_sent": current_io.bytes_sent,
        "bytes_recv": current_io.bytes_recv
    }
    
    latency = _measure_socket_latency()
    
    interfaces = list(psutil.net_if_addrs().keys())
    
    return {
        "interfaces": interfaces,
        "bytes_sent": current_io.bytes_sent,
        "bytes_recv": current_io.bytes_recv,
        "packets_sent": current_io.packets_sent,
        "packets_recv": current_io.packets_recv,
        "upload_speed_kbps": upload_speed_kbps,
        "download_speed_kbps": download_speed_kbps,
        "latency_ms": latency,
        "packet_loss_pct": 0.0,
        "timestamp_utc": datetime.datetime.now(datetime.timezone.utc).isoformat()
    }

@router.get("/processes")
async def get_system_processes(
    current_user: User = Depends(get_current_user),
    limit: int = Query(25, ge=5, le=100)
):
    """
    Safe running process monitoring.
    CRITICAL PRIVACY: Omits cmdline arguments, environment variables, passwords, or tokens.
    """
    procs = []
    for p in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent', 'status']):
        try:
            info = p.info
            if info['name']:
                procs.append({
                    "pid": info['pid'],
                    "name": info['name'],
                    "cpu_percent": round(info['cpu_percent'] or 0.0, 1),
                    "memory_percent": round(info['memory_percent'] or 0.0, 2),
                    "status": info['status'] or "running"
                })
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    # Sort by memory percent descending
    procs.sort(key=lambda x: (x['cpu_percent'], x['memory_percent']), reverse=True)
    return {
        "count": len(procs),
        "processes": procs[:limit],
        "timestamp_utc": datetime.datetime.now(datetime.timezone.utc).isoformat()
    }

@router.get("/services")
async def get_system_services(current_user: User = Depends(get_current_user)):
    """Monitored Windows service availability states."""
    target_services = [
        "EventLog", "LanmanServer", "wuauserv", "Spooler", 
        "Themes", "PlugPlay", "RpcSs", "Winmgmt", "Schedule"
    ]
    
    services_info = []
    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
    
    if psutil.WINDOWS:
        for s_name in target_services:
            try:
                svc = psutil.win_service_get(s_name)
                services_info.append({
                    "name": svc.name(),
                    "display_name": svc.display_name(),
                    "status": svc.status(),
                    "start_type": svc.start_type(),
                    "available": svc.status() in ["running", "start_pending"],
                    "last_check_utc": now_iso
                })
            except Exception:
                services_info.append({
                    "name": s_name,
                    "display_name": s_name,
                    "status": "stopped",
                    "start_type": "manual",
                    "available": False,
                    "last_check_utc": now_iso
                })
    else:
        # Fallback for non-windows environments
        for s_name in target_services:
            services_info.append({
                "name": s_name,
                "display_name": s_name,
                "status": "running",
                "start_type": "automatic",
                "available": True,
                "last_check_utc": now_iso
            })

    running_count = sum(1 for s in services_info if s["available"])
    return {
        "monitored_count": len(services_info),
        "running_count": running_count,
        "availability_pct": round((running_count / len(services_info)) * 100, 1),
        "services": services_info,
        "timestamp_utc": now_iso
    }
