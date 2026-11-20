import time
from typing import Dict, Any, Optional, Tuple
import requests

class SaaSClient:
    def __init__(
        self,
        base_url: str,
        tenant_id: str,
        collector_id: str,
        auth_token: str
    ):
        self.base_url = base_url.rstrip("/")
        self.tenant_id = tenant_id
        self.collector_id = collector_id
        self.auth_token = auth_token
        self.headers = {
            "Content-Type": "application/json",
            "X-Tenant-Id": self.tenant_id,
            "X-Collector-Id": self.collector_id,
            "X-Auth-Token": self.auth_token
        }

    def send_metadata(self, payload: Dict[str, Any]) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """Transmits metadata payload to Tier 2 SaaS."""
        url = f"{self.base_url}/ingestion/metadata"
        try:
            resp = requests.post(url, json=payload, headers=self.headers, timeout=4.0)
            if resp.status_code in [200, 201]:
                return True, resp.json()
            else:
                return False, {"status_code": resp.status_code, "error": resp.text}
        except Exception as e:
            return False, {"error": str(e)}

    def send_heartbeat(
        self,
        status: str = "Online",
        cpu_usage: float = 0.0,
        memory_usage: float = 0.0,
        pending_buffered: int = 0,
        os_info: str = "Windows / Linux"
    ) -> bool:
        """Sends periodic heartbeat to Tier 2 SaaS."""
        url = f"{self.base_url}/collectors/heartbeat"
        data = {
            "collector_id": self.collector_id,
            "status": status,
            "cpu_usage": cpu_usage,
            "memory_usage": memory_usage,
            "pending_buffered": pending_buffered,
            "os_info": os_info
        }
        try:
            resp = requests.post(url, json=data, headers=self.headers, timeout=3.0)
            return resp.status_code == 200
        except Exception:
            return False

    def send_security_summary(self, summary: Dict[str, Any]) -> bool:
        """Sends sanitized security summary."""
        url = f"{self.base_url}/security/event"
        try:
            resp = requests.post(url, json=summary, headers=self.headers, timeout=3.0)
            return resp.status_code == 200
        except Exception:
            return False
