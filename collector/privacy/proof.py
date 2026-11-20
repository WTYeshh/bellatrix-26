import json
import hashlib
from typing import Dict, Any, List

class EgressProofGenerator:
    def __init__(self, policy_version: str = "Standard-v1"):
        self.policy_version = policy_version

    def generate_proof(
        self,
        approved_payload: Dict[str, Any],
        approved_fields: List[str],
        redacted_fields: List[str]
    ) -> Dict[str, Any]:
        """
        Generates verifiable Egress Proof:
        1. Encodes payload to exact canonical JSON
        2. Computes SHA-256 hash
        3. Attaches proof metadata directly into the transmission object
        """
        # Canonical JSON string with sorted keys
        exact_json = json.dumps(approved_payload, sort_keys=True)
        payload_hash = hashlib.sha256(exact_json.encode("utf-8")).hexdigest()

        proof_record = {
            "payload_id": approved_payload.get("payload_id"),
            "tenant_id": approved_payload.get("tenant_id"),
            "source_id": approved_payload.get("source_id"),
            "timestamp_utc": approved_payload.get("timestamp_utc"),
            "approved_fields": approved_fields,
            "redacted_fields": redacted_fields,
            "applied_policy": self.policy_version,
            "exact_transmitted_json": exact_json,
            "payload_hash": payload_hash,
            "transmission_status": "Prepared"
        }

        # Embed proof attributes into payload so Tier 2 can independently verify
        transmittable_payload = approved_payload.copy()
        transmittable_payload["payload_hash"] = payload_hash
        transmittable_payload["applied_policy"] = self.policy_version
        transmittable_payload["approved_fields"] = approved_fields
        transmittable_payload["redacted_fields"] = redacted_fields
        transmittable_payload["exact_transmitted_json"] = exact_json

        return {
            "payload_to_send": transmittable_payload,
            "proof_record": proof_record
        }
