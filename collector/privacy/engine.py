import re
import hashlib
from typing import Dict, Any, Tuple, List, Set

class PrivacyEngine:
    # Explicit field allow-list per specification
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
        "throughput_kbps",
        "bytes_sent",
        "bytes_recv",
        "local_anomalies",
        "health_state",
        "event_category",
        "severity"
    }

    # Secret detection regex patterns
    SECRET_PATTERNS = [
        re.compile(r"(?i)(password|passwd|pwd)\s*[:=]\s*['\"]?([^'\"\\s]+)"),
        re.compile(r"(?i)(api[_-]?key|secret|token)\s*[:=]\s*['\"]?([a-zA-Z0-9_\-]{16,})"),
        re.compile(r"(?i)bearer\s+[a-zA-Z0-9\-\._~\+\/]+=*"),
        re.compile(r"-----BEGIN (?:RSA )?PRIVATE KEY-----"),
        re.compile(r"(?i)Authorization:\s*Basic\s+[a-zA-Z0-9=]+"),
    ]

    def __init__(self, policy_version: str = "Standard-v1"):
        self.policy_version = policy_version

    def redact_secrets_in_string(self, text: str) -> Tuple[str, bool]:
        """Scans string for sensitive patterns and redacts them."""
        redacted = False
        result = text
        for pat in self.SECRET_PATTERNS:
            if pat.search(result):
                redacted = True
                result = pat.sub("[REDACTED_SECRET]", result)
        return result, redacted

    def pseudonymize_source(self, raw_identifier: str, salt: str = "aegis_salt_2026") -> str:
        """Generates deterministic pseudonymous identifier for customer host."""
        h = hashlib.sha256(f"{raw_identifier}:{salt}".encode("utf-8")).hexdigest()
        return f"NODE_{h[:8].upper()}"

    def apply_policy(self, raw_telemetry: Dict[str, Any]) -> Tuple[Dict[str, Any], List[str], List[str]]:
        """
        Executes Privacy Engine Pipeline:
        1. Identifies and isolates approved fields vs disallowed fields
        2. Drops all unapproved raw/sensitive fields (e.g. raw_sensitive_log, raw_hostname)
        3. Scans approved string values for any embedded secrets and redacts them
        4. Returns (approved_payload, list_of_approved_fields, list_of_dropped_or_redacted_fields)
        """
        approved_payload: Dict[str, Any] = {}
        approved_fields: List[str] = []
        dropped_or_redacted_fields: List[str] = []

        for key, value in raw_telemetry.items():
            if key in self.ALLOWED_METADATA_FIELDS:
                if isinstance(value, str):
                    clean_val, was_redacted = self.redact_secrets_in_string(value)
                    approved_payload[key] = clean_val
                    approved_fields.append(key)
                    if was_redacted:
                        dropped_or_redacted_fields.append(f"{key}:[secret_redacted]")
                elif isinstance(value, list) and key == "local_anomalies":
                    # Sanitize any string fields inside local anomalies
                    clean_anoms = []
                    for item in value:
                        if isinstance(item, dict):
                            clean_item = {}
                            for ik, iv in item.items():
                                if isinstance(iv, str):
                                    c_iv, _ = self.redact_secrets_in_string(iv)
                                    clean_item[ik] = c_iv
                                else:
                                    clean_item[ik] = iv
                            clean_anoms.append(clean_item)
                        else:
                            clean_anoms.append(item)
                    approved_payload[key] = clean_anoms
                    approved_fields.append(key)
                else:
                    approved_payload[key] = value
                    approved_fields.append(key)
            else:
                # Key is NOT on the strict allow-list: DROP IT!
                dropped_or_redacted_fields.append(key)

        return approved_payload, approved_fields, dropped_or_redacted_fields
