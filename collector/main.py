import time
import uuid
import datetime
import sys
from typing import Dict, Any, Optional

from collector.config import collector_config
from collector.sources.system_metrics import SystemMetricsSource
from collector.sources.security_events import SecurityEventsSource
from collector.privacy.engine import PrivacyEngine
from collector.privacy.proof import EgressProofGenerator
from collector.storage.local_db import LocalCollectorStorage
from collector.transport.client import SaaSClient

class Tier1Collector:
    def __init__(self):
        self.config = collector_config
        self.metrics_source = SystemMetricsSource()
        self.security_source = SecurityEventsSource()
        self.privacy_engine = PrivacyEngine(policy_version="Standard-v1")
        self.proof_gen = EgressProofGenerator(policy_version="Standard-v1")
        self.storage = LocalCollectorStorage(db_path=self.config.LOCAL_DB_PATH)
        self.client = SaaSClient(
            base_url=self.config.SAAS_URL,
            tenant_id=self.config.TENANT_ID,
            collector_id=self.config.COLLECTOR_ID,
            auth_token=self.config.AUTH_TOKEN
        )
        self.last_heartbeat = 0.0

    def run_cycle(self) -> Dict[str, Any]:
        """
        Executes the mandatory Tier 1 processing sequence:
        COLLECT -> FILTER -> REDACT -> NORMALIZE -> AGGREGATE ->
        ANALYSE LOCALLY -> APPLY DATA POLICY -> GENERATE EGRESS PROOF -> TRANSMIT / BUFFER
        """
        now_utc = datetime.datetime.now(datetime.timezone.utc).isoformat()
        payload_id = str(uuid.uuid4())

        # 1. COLLECT: Gather real metrics from local host using psutil
        raw_telemetry = self.metrics_source.collect()

        # 2. STORE RAW LOCALLY (Raw data stays local by default)
        self.storage.save_raw_telemetry(payload_id, now_utc, raw_telemetry)

        # 3. NORMALIZE & ENRICH
        raw_telemetry["payload_id"] = payload_id
        raw_telemetry["tenant_id"] = self.config.TENANT_ID
        raw_telemetry["collector_id"] = self.config.COLLECTOR_ID
        raw_telemetry["source_id"] = self.config.SOURCE_ID
        raw_telemetry["timestamp_utc"] = now_utc
        raw_telemetry["event_category"] = "Performance"

        # 4. FILTER & REDACT (APPLY DATA POLICY)
        approved_payload, approved_fields, dropped_or_redacted_fields = (
            self.privacy_engine.apply_policy(raw_telemetry)
        )

        # 5. GENERATE EGRESS PROOF (Deterministic JSON + SHA-256)
        proof_bundle = self.proof_gen.generate_proof(
            approved_payload=approved_payload,
            approved_fields=approved_fields,
            redacted_fields=dropped_or_redacted_fields
        )
        payload_to_send = proof_bundle["payload_to_send"]
        proof_record = proof_bundle["proof_record"]

        # 6. TRANSMIT OR BUFFER LOCALLY (RESILIENCE)
        success, response = self.client.send_metadata(payload_to_send)

        if success:
            proof_record["transmission_status"] = "Delivered & Acknowledged"
            self.storage.record_proof(proof_record, "Delivered")
            # Drain any previously buffered records from outbox!
            self.drain_outbox_backlog()
        else:
            # SaaS is offline / network outage: BUFFER APPROVED METADATA LOCALLY
            proof_record["transmission_status"] = "Buffered Locally (SaaS Offline)"
            self.storage.enqueue_outbox(payload_id, payload_to_send, now_utc)
            self.storage.record_proof(proof_record, "Buffered")

        return {
            "payload_id": payload_id,
            "success": success,
            "buffered": not success,
            "approved_fields": approved_fields,
            "dropped_fields": dropped_or_redacted_fields,
            "payload_hash": proof_record["payload_hash"],
            "exact_json": proof_record["exact_transmitted_json"],
            "pending_buffer_count": self.storage.count_pending()
        }

    def drain_outbox_backlog(self):
        """Replays buffered metadata payloads on reconnection without duplicates."""
        pending = self.storage.get_pending_outbox(limit=25)
        for item in pending:
            payload = item["payload"]
            payload_id = item["payload_id"]
            ok, resp = self.client.send_metadata(payload)
            if ok:
                self.storage.remove_from_outbox(payload_id)
            else:
                self.storage.increment_attempts(payload_id)
                break  # Stop if still unreachable

    def heartbeat_cycle(self):
        now = time.time()
        if now - self.last_heartbeat >= self.config.HEARTBEAT_INTERVAL_SECONDS:
            buffered_cnt = self.storage.count_pending()
            raw_metrics = self.metrics_source.collect()
            self.client.send_heartbeat(
                status="Online",
                cpu_usage=raw_metrics["cpu_usage"],
                memory_usage=raw_metrics["memory_usage"],
                pending_buffered=buffered_cnt,
                os_info=f"{sys.platform}"
            )
            self.last_heartbeat = now

    def run_forever(self):
        print(f"[AEGIS Collector] Starting Tier 1 Local Collector for Tenant={self.config.TENANT_ID}")
        print(f"[AEGIS Collector] Local Storage: {self.config.LOCAL_DB_PATH}")
        print(f"[AEGIS Collector] Target SaaS URL: {self.config.SAAS_URL}")
        
        while True:
            try:
                cycle_result = self.run_cycle()
                status_str = "Delivered" if cycle_result["success"] else "Buffered"
                print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] Payload {cycle_result['payload_id'][:8]} -> {status_str} (SHA-256: {cycle_result['payload_hash'][:12]}... Pending buffer: {cycle_result['pending_buffer_count']})")
                self.heartbeat_cycle()
            except Exception as e:
                print(f"[AEGIS Collector Error] {e}")
            time.sleep(self.config.COLLECTION_INTERVAL_SECONDS)

if __name__ == "__main__":
    collector = Tier1Collector()
    collector.run_forever()
