import time
import hashlib
import subprocess
import sys
from typing import Dict, Any, List

class SecurityMonitor:
    """
    Tier 1 Local Security Monitoring.
    Tracks repeated failed logins, suspicious frequency bursts, and Windows Security Log events.
    Never exports credentials, passwords, or raw auth records.
    """
    def __init__(self, failure_window_seconds: int = 300, spike_threshold: int = 5):
        self.failure_window = failure_window_seconds
        self.spike_threshold = spike_threshold
        self._failed_attempts: List[Dict[str, Any]] = []
        self._wevt_cached_count = 0
        self._wevt_cached_time = 0.0

    def record_attempt(self, username: str, success: bool, client_ip: str, raw_credentials: str = "") -> Dict[str, Any]:
        now = time.time()
        pseudonymous_id = f"SRC_AUTH_{hashlib.sha256(client_ip.encode()).hexdigest()[:8].upper()}"

        event = {
            "timestamp": now,
            "pseudonymous_id": pseudonymous_id,
            "success": success,
            "raw_log_local_vault_only": raw_credentials or f"USER={username} RESULT={'OK' if success else 'FAIL'}"
        }
        if not success:
            self._failed_attempts.append(event)
        return event

    def query_windows_event_log_failed_logins(self) -> int:
        if sys.platform != "win32":
            return 0
        now = time.time()
        if (now - self._wevt_cached_time) < 10.0:
            return self._wevt_cached_count
        try:
            cmd = ['wevtutil', 'qe', 'Security', '/q:*[System[(EventID=4625) and TimeCreated[timediff(@SystemTime) <= 300000]]]', '/c:20', '/f:text']
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=1.5)
            if res.returncode == 0:
                self._wevt_cached_count = res.stdout.count("Event[")
        except Exception:
            pass
        self._wevt_cached_time = now
        return self._wevt_cached_count

    def collect_summary(self) -> Dict[str, Any]:
        now = time.time()
        # Clean expired attempts outside failure window
        self._failed_attempts = [e for e in self._failed_attempts if now - e["timestamp"] <= self.failure_window]

        local_fail_count = len(self._failed_attempts)
        wevt_fail_count = self.query_windows_event_log_failed_logins()
        total_failed = local_fail_count + wevt_fail_count

        severity = "Low"
        is_spike = total_failed >= self.spike_threshold
        if total_failed > 10:
            severity = "Critical"
        elif total_failed >= 5:
            severity = "High"
        elif total_failed > 0:
            severity = "Medium"

        return {
            "failed_login_count": total_failed,
            "local_failed_events": local_fail_count,
            "windows_event_4625_count": wevt_fail_count,
            "severity": severity,
            "is_anomaly_spike": is_spike,
            "window_seconds": self.failure_window
        }
