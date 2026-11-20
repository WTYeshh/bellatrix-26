import time
import hashlib
import datetime
import subprocess
import psutil
from typing import Dict, Any, List, Optional

class SecurityEventsSource:
    """
    Tier 1 Local Security Signal Processing Source.
    Processes authentication events locally inside customer environment:
    - Detects repeated failed logins within configurable time windows
    - Identifies unusual authentication frequency
    - Maps client endpoints to pseudonymous source IDs (SRC_AUTH_xxxx)
    - Integrates with Windows Security Event Log (EventID 4625: Failed Logon)
    - Zero export of usernames, passwords, tokens, or raw credentials
    """
    def __init__(self, window_seconds: int = 300):
        self.window_seconds = window_seconds
        self._local_failed_logins: List[Dict[str, Any]] = []
        self._last_win_event_check = time.time() - 300

    def record_auth_event(self, username: str, success: bool, client_ip: str, raw_credentials_dump: str = "") -> Dict[str, Any]:
        """
        Records a local authentication event.
        CRITICAL: Raw credentials dump must STAY LOCAL and NEVER leave customer environment!
        """
        now = time.time()
        pseudonymous_id = f"SRC_AUTH_{hashlib.sha256(client_ip.encode()).hexdigest()[:8].upper()}"
        
        event = {
            "timestamp": now,
            "pseudonymous_id": pseudonymous_id,
            "success": success,
            "client_ip_hash": pseudonymous_id,
            # Raw credentials kept strictly local
            "raw_sensitive_log": raw_credentials_dump or f"USER={username} ATTEMPT RESULT={'OK' if success else 'FAIL'}"
        }
        if not success:
            self._local_failed_logins.append(event)
        return event

    def query_windows_event_log_failed_logins(self) -> int:
        """
        Attempts to query Windows Event Log for Event ID 4625 (Failed Logon).
        Falls back safely without crashing if running without Administrator privileges.
        """
        if not psutil.WINDOWS:
            return 0
        try:
            # Query recent 4625 events from Security log via wevtutil
            cmd = ['wevtutil', 'qe', 'Security', '/q:*[System[(EventID=4625) and TimeCreated[timediff(@SystemTime) <= 300000]]]', '/c:20', '/f:text']
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=1.5)
            if res.returncode == 0:
                count = res.stdout.count("Event[")
                return count
        except Exception:
            pass
        return 0

    def get_security_summary(self) -> Dict[str, Any]:
        """
        Calculates a privacy-safe security summary:
        Only aggregate counts, severity, time window, and pseudonymous source are exported.
        Zero credentials, usernames, or raw logs leave Tier 1!
        """
        now = time.time()
        # Filter failures within configurable time window
        recent_failures = [e for e in self._local_failed_logins if (now - e["timestamp"]) <= self.window_seconds]
        local_count = len(recent_failures)
        win_count = self.query_windows_event_log_failed_logins()
        total_failed_count = max(local_count, win_count)

        # Determine primary pseudonymous source
        if recent_failures:
            primary_source = recent_failures[-1].get("pseudonymous_id", "SRC_AUTH_LOCAL")
        else:
            primary_source = "SRC_AUTH_LOCAL"

        # Rate and unusual frequency calculation
        rate_per_min = round((total_failed_count / (self.window_seconds / 60.0)), 1)
        unusual_frequency = rate_per_min >= 2.0

        if total_failed_count >= 10 or rate_per_min >= 5.0:
            severity = "Critical"
            desc = f"Brute-force authentication anomaly: {total_failed_count} failed logins ({rate_per_min}/min) within {self.window_seconds//60}-min window"
        elif total_failed_count >= 3:
            severity = "High"
            desc = f"Repeated authentication failures detected: {total_failed_count} attempts ({rate_per_min}/min)"
        elif total_failed_count >= 1:
            severity = "Medium"
            desc = f"Suspicious login activity: {total_failed_count} failed attempt in {self.window_seconds//60}-min window"
        else:
            severity = "Low"
            desc = "Authentication activity nominal within historical baseline"

        adapter = "Windows-EventLog" if win_count > 0 else "Local-Auth-Engine"
        now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()

        return {
            "event_category": "Authentication",
            "severity": severity,
            "failed_login_count": total_failed_count,
            "event_count": total_failed_count,
            "time_window_sec": self.window_seconds,
            "pseudonymous_source_id": primary_source,
            "adapter_type": adapter,
            "unusual_frequency": unusual_frequency,
            "description": desc,
            "detection_timestamp_utc": now_iso
        }
