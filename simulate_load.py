"""
AEGIS Physical Laptop Load Simulator
Generates real physical load on the host Windows machine:
- CPU Stress: Multiprocess/thread floating point & prime crunching
- Memory Stress: Real bytearray allocation and memory touch
- Disk Stress: Rapid file write/read bursts to temporary files
- Network Stress: Rapid HTTP socket probes
Usage:
    python simulate_load.py --cpu --duration 10
    python simulate_load.py --memory --duration 10
    python simulate_load.py --disk --duration 10
    python simulate_load.py --network --duration 10
    python simulate_load.py --all --duration 15
"""

import argparse
import os
import sys
import time
import math
import tempfile
import urllib.request
import threading
from concurrent.futures import ThreadPoolExecutor

def stress_cpu(duration: int):
    """Generates genuine CPU load across multiple CPU cores."""
    print(f"[LOAD-SIM] Starting CPU stress for {duration} seconds...")
    stop_event = threading.Event()

    def cpu_worker():
        while not stop_event.is_set():
            # Intense computation
            for _ in range(50000):
                math.sqrt(1234567.89) * math.sin(0.456)

    cores = os.cpu_count() or 4
    threads = []
    for _ in range(cores):
        t = threading.Thread(target=cpu_worker, daemon=True)
        t.start()
        threads.append(t)

    time.sleep(duration)
    stop_event.set()
    for t in threads:
        t.join(timeout=1.0)
    print(f"[LOAD-SIM] CPU stress complete.")

def stress_memory(duration: int, size_mb: int = 500):
    """Allocates and touches real physical RAM."""
    print(f"[LOAD-SIM] Allocating {size_mb} MB of real RAM for {duration} seconds...")
    try:
        # Allocate real chunks and write to them to prevent OS lazy paging
        chunk_size = 10 * 1024 * 1024  # 10 MB chunks
        chunks = []
        for _ in range(size_mb // 10):
            b = bytearray(chunk_size)
            # Touch pages
            for i in range(0, len(b), 4096):
                b[i] = 1
            chunks.append(b)
        print(f"[LOAD-SIM] Successfully locked {size_mb} MB in memory. Holding for {duration}s...")
        time.sleep(duration)
        del chunks
        print(f"[LOAD-SIM] Memory released.")
    except Exception as e:
        print(f"[LOAD-SIM] Memory stress encountered error: {e}")

def stress_disk(duration: int):
    """Generates real disk I/O read and write bursts."""
    print(f"[LOAD-SIM] Initiating disk I/O burst for {duration} seconds...")
    tmp_path = os.path.join(tempfile.gettempdir(), f"aegis_disk_stress_{int(time.time())}.tmp")
    data_chunk = os.urandom(1024 * 1024)  # 1 MB random data
    end_time = time.time() + duration
    total_written = 0

    try:
        with open(tmp_path, "wb") as f:
            while time.time() < end_time:
                for _ in range(20):
                    f.write(data_chunk)
                    f.flush()
                    total_written += 1
                time.sleep(0.05)
        print(f"[LOAD-SIM] Wrote {total_written} MB to disk. Reading back...")
        with open(tmp_path, "rb") as f:
            while f.read(1024 * 1024):
                pass
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
    print(f"[LOAD-SIM] Disk stress complete.")

def stress_network(duration: int):
    """Generates real network socket connect and download activity."""
    print(f"[LOAD-SIM] Initiating network socket activity for {duration} seconds...")
    end_time = time.time() + duration
    probes = 0

    while time.time() < end_time:
        try:
            # Query local Tier 1 or Tier 2 endpoints
            for port in [8000, 8001]:
                req = urllib.request.Request(f"http://127.0.0.1:{port}/health")
                with urllib.request.urlopen(req, timeout=1.0) as resp:
                    resp.read()
                    probes += 1
        except Exception:
            pass
        time.sleep(0.1)
    print(f"[LOAD-SIM] Network activity complete. Dispatched {probes} real socket probes.")

def main():
    parser = argparse.ArgumentParser(description="AEGIS Physical Laptop Real Load Simulator")
    parser.add_argument("--cpu", action="store_true", help="Generate real CPU load")
    parser.add_argument("--memory", action="store_true", help="Allocate real memory")
    parser.add_argument("--disk", action="store_true", help="Generate real disk I/O bursts")
    parser.add_argument("--network", action="store_true", help="Generate real network activity")
    parser.add_argument("--all", action="store_true", help="Stress all subsystems simultaneously")
    parser.add_argument("--duration", type=int, default=10, help="Duration in seconds (default: 10)")

    args = parser.parse_args()

    if not (args.cpu or args.memory or args.disk or args.network or args.all):
        print("Please specify at least one load flag: --cpu, --memory, --disk, --network, or --all")
        sys.exit(1)

    print(f"=== AEGIS HOST LOAD SIMULATOR (server-01) ===")
    print(f"Target node: server-01 (Physical Laptop)")
    print(f"Duration: {args.duration}s")

    if args.all:
        with ThreadPoolExecutor(max_workers=4) as executor:
            f1 = executor.submit(stress_cpu, args.duration)
            f2 = executor.submit(stress_memory, args.duration)
            f3 = executor.submit(stress_disk, args.duration)
            f4 = executor.submit(stress_network, args.duration)
            f1.result(); f2.result(); f3.result(); f4.result()
    else:
        if args.cpu:
            stress_cpu(args.duration)
        if args.memory:
            stress_memory(args.duration)
        if args.disk:
            stress_disk(args.duration)
        if args.network:
            stress_network(args.duration)

    print("=== All load generation complete. Telemetry will reflect anomalous deviations. ===")

if __name__ == "__main__":
    main()
