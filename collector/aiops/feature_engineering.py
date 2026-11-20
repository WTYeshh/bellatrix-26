from typing import Dict, Any, List

class LocalFeatureEngineer:
    """
    Extracts multi-metric vectors and dynamic features
    for statistical and Isolation Forest evaluations.
    """
    def __init__(self):
        self._prev_metrics: Dict[str, float] = {}

    def extract_features(self, metrics: Dict[str, Any]) -> List[float]:
        """
        Builds feature vector:
        [cpu_usage, memory_usage, disk_usage, latency_ms, throughput_kbps, d_cpu, d_mem]
        """
        cpu = float(metrics.get("cpu_usage", 0.0))
        mem = float(metrics.get("memory_usage", 0.0))
        disk = float(metrics.get("disk_usage", 0.0))
        lat = float(metrics.get("latency_ms", 0.0))
        thr = float(metrics.get("throughput_kbps", 0.0))

        # First derivatives (delta from previous reading)
        d_cpu = round(cpu - self._prev_metrics.get("cpu_usage", cpu), 2)
        d_mem = round(mem - self._prev_metrics.get("memory_usage", mem), 2)

        self._prev_metrics = {
            "cpu_usage": cpu,
            "memory_usage": mem,
            "disk_usage": disk,
            "latency_ms": lat,
            "throughput_kbps": thr
        }

        return [cpu, mem, disk, lat, thr, d_cpu, d_mem]

FeatureEngineer = LocalFeatureEngineer
