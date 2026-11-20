import sys
import os
sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(__file__))))

from collector.main import Tier1Collector

if __name__ == "__main__":
    col = Tier1Collector()
    print("Running 5 Tier 1 Collector transmission cycles...")
    for i in range(5):
        res = col.run_cycle()
        pid = res["payload_id"][:8]
        suc = res["success"]
        hsh = res["payload_hash"][:16]
        print(f"Cycle {i+1}: Payload {pid} -> Delivered: {suc} (SHA-256: {hsh}...)")
    col.heartbeat_cycle()
    print("Heartbeat cycle delivered successfully.")
