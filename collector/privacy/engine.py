import re
import socket
import os
import hashlib
import json
from typing import Dict, Any, Tuple, List, Set, Optional

class PrivacyEngine:
    """
    Tier 1 Privacy Engine with Literal Privacy Enforcement:
    - Never leaks the username 'Veeresh' or raw host machine name
    - Redacts user paths ('C:\\Users\\...') to '[USER_PATH]'
    - Enforces strict allow-list on metadata fields
    - Fails-closed if any sensitive pattern is detected in outgoing payload
    """
    ALLOWED_METADATA_FIELDS = {
        "payload_id",
        "tenant_id",
        "source_id",
        "collector_id",
        "timestamp_utc",
        "cpu_usage",
        "memory_usage",
        "disk_usage",
        "latency_ms",
        "packet_loss_pct",
        "upload_kbps",
        "download_kbps",
        "throughput_kbps",
        "bytes_sent",
        "bytes_recv",
        "disk_read_kbps",
        "disk_write_kbps",
        "disk_iops",
        "cpu_freq_mhz",
        "swap_percent",
        "battery_percent",
        "load_avg_1m",
        "top_processes",
        "local_anomalies",
        "health_state",
        "event_category",
        "severity"
    }

    # Secret & Privacy patterns
    SECRET_PATTERNS = [
        re.compile(r"(?i)(password|passwd|pwd)\s*[:=]\s*['\"]?([^'\"\s]+)"),
        re.compile(r"(?i)(api[_-]?key|secret|token)\s*[:=]\s*['\"]?([a-zA-Z0-9_\-]{16,})"),
        re.compile(r"(?i)bearer\s+[a-zA-Z0-9\-\._~\+\/]+=*"),
        re.compile(r"-----BEGIN (?:RSA )?PRIVATE KEY-----"),
        re.compile(r"(?i)Authorization:\s*Basic\s+[a-zA-Z0-9=]+"),
        # User path redaction
        re.compile(r"(?i)[a-zA-Z]:\\Users\\[^\s\\\"']+"),
        re.compile(r"(?i)/home/[^\s/\"']+"),
        # Username redaction
        re.compile(r"(?i)\bveeresh\b")
    ]

    def __init__(self, policy_version: str = "Standard-v1"):
        self.policy_version = policy_version
        self._raw_hostname = socket.gethostname().lower()

    def redact_secrets_in_string(self, text: str) -> Tuple[str, bool]:
        """Scans string for sensitive patterns, user paths, or usernames and redacts them."""
        redacted = False
        result = text
        for pat in self.SECRET_PATTERNS:
            if pat.search(result):
                redacted = True
                if "users" in pat.pattern.lower() or "home" in pat.pattern.lower():
                    result = pat.sub("[USER_PATH]", result)
                elif "veeresh" in pat.pattern.lower():
                    result = pat.sub("[USER]", result)
                else:
                    result = pat.sub("[REDACTED_SECRET]", result)

        if self._raw_hostname and self._raw_hostname != "server-01" and self._raw_hostname in result.lower():
            redacted = True
            result = re.sub(re.escape(self._raw_hostname), "server-01", result, flags=re.IGNORECASE)

        return result, redacted

    def scrub_text(self, text: str) -> str:
        scrubbed, _ = self.redact_secrets_in_string(text)
        return scrubbed

    def sanitize_processes(self, procs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Ensures process list only contains safe basenames and memory stats (no paths or cmdlines)."""
        clean = []
        for p in procs:
            raw_name = str(p.get("name", "unknown"))
            base_name = os.path.basename(raw_name)
            scrubbed_name, _ = self.redact_secrets_in_string(base_name)
            clean.append({
                "pid": p.get("pid", 0),
                "name": scrubbed_name,
                "memory_rss_mb": p.get("memory_rss_mb", 0.0)
            })
        return clean

    def apply_policy(self, raw_telemetry: Dict[str, Any]) -> Tuple[Dict[str, Any], List[str], List[str]]:
        approved_payload: Dict[str, Any] = {}
        approved_fields: List[str] = []
        dropped_or_redacted_fields: List[str] = []

        # Always enforce fixed single server identity
        raw_telemetry["source_id"] = "server-01"
        raw_telemetry["tenant_id"] = "default"
        raw_telemetry["collector_id"] = "COLLECTOR_SERVER_01"

        for key, value in raw_telemetry.items():
            if key in self.ALLOWED_METADATA_FIELDS:
                if key == "top_processes" and isinstance(value, list):
                    approved_payload[key] = self.sanitize_processes(value)
                    approved_fields.append(key)
                elif isinstance(value, str):
                    clean_val, was_redacted = self.redact_secrets_in_string(value)
                    approved_payload[key] = clean_val
                    approved_fields.append(key)
                    if was_redacted:
                        dropped_or_redacted_fields.append(f"{key}:[REDACTED]")
                else:
                    approved_payload[key] = value
                    approved_fields.append(key)
            else:
                dropped_or_redacted_fields.append(key)

        return approved_payload, approved_fields, dropped_or_redacted_fields

    EGRESS_PROOF_FIELDS = {
        "payload_hash",
        "applied_policy",
        "approved_fields",
        "redacted_fields",
        "exact_transmitted_json"
    }

    def validate_for_egress(self, payload: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """
        Fail-Closed Privacy Gate:
        Rejects payload if any disallowed field, unredacted username, or raw hostname is present.
        """
        keys = set(payload.keys())
        disallowed = keys - (self.ALLOWED_METADATA_FIELDS | self.EGRESS_PROOF_FIELDS)
        if disallowed:
            return False, f"Disallowed fields not on the approved allow-list: {list(disallowed)}"

        serialized = json.dumps(payload, default=str).lower()
        if "veeresh" in serialized:
            return False, "Privacy violation: unredacted username detected"

        if self._raw_hostname and self._raw_hostname != "server-01" and self._raw_hostname in serialized:
            return False, "Privacy violation: raw machine hostname detected"

        # Check for unredacted secrets in string values
        for val in payload.values():
            if isinstance(val, str):
                for pat in self.SECRET_PATTERNS:
                    if pat.search(val):
                        return False, f"Unredacted credential pattern detected matching {pat.pattern}"

        return True, None
