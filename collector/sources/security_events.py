import time
from typing import Dict, Any, List

class SecurityEventsSource:
    def __init__(self):
        self._local_failed_logins: List[Dict[str, Any]] = []

    def record_auth_event(self, username: str, success: bool, client_ip: str, raw_credentials_dump: str = ""):
        """
        Records a local authentication event.
        CRITICAL: Raw credentials dump must STAY LOCAL and NEVER leave customer environment!
        """
        event = {
            "timestamp": time.time(),
            "username": username,
            "success": success,
            "client_ip": client_ip,
            "raw_sensitive_log": raw_credentials_dump or f"USER={username} AUTH_ATTEMPT RESULT={'OK' if success else 'FAIL'}"
        }
        if not success:
            self._local_failed_logins.append(event)
        return event

    def get_security_summary(self) -> Dict[str, Any]:
        """
        Calculates a privacy-safe security summary:
        Only aggregate counts and threat levels are exported, NEVER individual credentials or raw logs!
        """
        now = time.time()
        # Look back over last 5 minutes
        recent_failures = [e for e in self._local_failed_logins if (now - e["timestamp"]) <= 300]
        count = len(recent_failures)

        if count >= 10:
            severity = "Critical"
            desc = f"Brute-force authentication anomaly: {count} failed logins within 5-minute window"
        elif count >= 3:
            severity = "High"
            desc = f"Repeated authentication failures detected: {count} failed attempts"
        elif count >= 1:
            severity = "Medium"
            desc = f"Suspicious login activity: {count} failed attempt"
        else:
            severity = "Low"
            desc = "Authentication activity within expected baseline"

        return {
            "failed_login_count": count,
            "severity": severity,
            "description": desc,
            "event_category": "Authentication Summary"
        }
