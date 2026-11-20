import time
import uuid
import datetime
from typing import Dict, Any, Optional, Iterator

class SimulatedStreamAdapter:
    """
    Adapter for Organizer-Provided Simulated Telemetry Streams.
    Allows injecting synthetic or test bench streams into the Tier 1 pipeline
    without replacing or disturbing the primary Windows laptop monitoring.
    """
    def __init__(self, stream_source_id: str = "ORGANIZER_BENCH_01"):
        self.stream_source_id = stream_source_id
        self._step = 0

    def generate_simulated_payload(
        self,
        cpu_spike: bool = False,
        mem_spike: bool = False,
        latency_spike: bool = False
    ) -> Dict[str, Any]:
        """Generates a structured telemetry sample matching the official comparison schema."""
        self._step += 1
        now_utc = datetime.datetime.now(datetime.timezone.utc).isoformat()
        
        cpu = 88.5 if cpu_spike else (25.0 + (self._step % 15))
        mem = 92.4 if mem_spike else (55.0 + (self._step % 10))
        lat = 320.0 if latency_spike else (18.5 + (self._step % 5))
        
        health_state = "Excellent"
        if cpu > 85.0 or mem > 90.0:
            health_state = "Poor"
        elif cpu > 70.0 or mem > 80.0 or lat > 100.0:
            health_state = "Fair"
        elif cpu > 40.0:
            health_state = "Good"

        return {
            "source_id": self.stream_source_id,
            "timestamp_utc": now_utc,
            "cpu_usage": round(cpu, 1),
            "memory_usage": round(mem, 1),
            "disk_usage": 45.0,
            "latency_ms": round(lat, 1),
            "packet_loss_pct": 5.0 if latency_spike else 0.0,
            "upload_kbps": 128.0,
            "download_kbps": 1024.0,
            "health_state": health_state,
            "event_category": "Performance",
            "severity": "High" if health_state == "Poor" else ("Medium" if health_state == "Fair" else "Low"),
            "adapter_type": "organizer_simulated_stream"
        }
