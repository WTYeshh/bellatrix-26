import time
import uuid
import datetime
import sys
import os
from typing import Dict, Any, Optional

from collector.config import collector_config
from collector.system_monitor import SystemMetricsSource
from collector.sources.security_events import SecurityEventsSource
from collector.host_inventory import WindowsHostInventory
from collector.heartbeat import HeartbeatManager
from collector.privacy.engine import PrivacyEngine
from collector.privacy.proof import EgressProofGenerator
from collector.storage.local_db import LocalCollectorStorage
from collector.transport.client import SaaSClient
from collector.aiops.local_analysis import LocalAIOpsCoordinator

class Tier1Collector:
    def __init__(self):
        self.config = collector_config
        self.host_inventory = WindowsHostInventory()
        self.metrics_source = SystemMetricsSource()
        self.security_source = SecurityEventsSource()
        self.privacy_engine = PrivacyEngine(policy_version="Standard-v1")
        self.proof_gen = EgressProofGenerator(policy_version="Standard-v1")
        self.storage = LocalCollectorStorage(db_path=self.config.LOCAL_DB_PATH)
        self.local_aiops = LocalAIOpsCoordinator()
        self.client = SaaSClient(
            base_url=self.config.SAAS_URL,
            tenant_id=self.config.TENANT_ID,
            collector_id=self.config.COLLECTOR_ID,
            auth_token=self.config.AUTH_TOKEN
        )
        self.heartbeat_mgr = HeartbeatManager(
            client=self.client,
            collector_id=self.config.COLLECTOR_ID,
            heartbeat_interval=self.config.HEARTBEAT_INTERVAL_SECONDS
        )
        self.last_heartbeat = 0.0
        self._cached_inventory = self.host_inventory.collect_full_inventory()

    def run_cycle(self) -> Dict[str, Any]:
        """
        Executes the mandatory Tier 1 processing sequence:
        COLLECT -> FILTER -> REDACT -> NORMALIZE -> AGGREGATE ->
        ANALYSE LOCALLY (Local AIOps) -> APPLY DATA POLICY -> GENERATE EGRESS PROOF -> TRANSMIT / BUFFER
        """
        now_utc = datetime.datetime.now(datetime.timezone.utc).isoformat()
        payload_id = str(uuid.uuid4())

        # 1. COLLECT: Gather real metrics from local host using psutil
        raw_telemetry = self.metrics_source.collect()

        # 2. STORE RAW LOCALLY (Raw data stays local by default)
        self.storage.save_raw_telemetry(payload_id, now_utc, raw_telemetry)

        # 3. ANALYSE LOCALLY: Run Tier 1 Local AIOps (MAD, Z-Score, Isolation Forest)
        local_anomalies = self.local_aiops.process_telemetry(self.config.SOURCE_ID, raw_telemetry)

        # 4. NORMALIZE & ENRICH
        raw_telemetry["payload_id"] = payload_id
        raw_telemetry["tenant_id"] = self.config.TENANT_ID
        raw_telemetry["collector_id"] = self.config.COLLECTOR_ID
        raw_telemetry["source_id"] = self.config.SOURCE_ID
        raw_telemetry["timestamp_utc"] = now_utc
        raw_telemetry["event_category"] = "Performance"
        raw_telemetry["local_anomalies"] = local_anomalies

        # 5. FILTER & REDACT (APPLY DATA POLICY)
        approved_payload, approved_fields, dropped_or_redacted_fields = (
            self.privacy_engine.apply_policy(raw_telemetry)
        )

        # 6. GENERATE EGRESS PROOF (Deterministic JSON + SHA-256)
        proof_bundle = self.proof_gen.generate_proof(
            approved_payload=approved_payload,
            approved_fields=approved_fields,
            redacted_fields=dropped_or_redacted_fields
        )
        payload_to_send = proof_bundle["payload_to_send"]
        proof_record = proof_bundle["proof_record"]

        # 6b. FAIL-CLOSED PRIVACY GATE: Block transmission if policy validation fails
        is_valid, priv_err = self.privacy_engine.validate_for_egress(payload_to_send)
        if not is_valid:
            proof_record["transmission_status"] = f"BLOCKED_BY_PRIVACY: {priv_err}"
            self.storage.record_proof(proof_record, "Blocked")
            return {
                "payload_id": payload_id,
                "success": False,
                "blocked_by_privacy": True,
                "error": priv_err,
                "approved_fields": approved_fields,
                "dropped_fields": dropped_or_redacted_fields,
                "local_anomalies": local_anomalies,
                "payload_hash": proof_record["payload_hash"],
                "exact_json": proof_record["exact_transmitted_json"],
                "pending_buffer_count": self.storage.count_pending()
            }

        # 7. TRANSMIT OR BUFFER LOCALLY (RESILIENCE)
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
            "local_anomalies": local_anomalies,
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
        buffered_cnt = self.storage.count_pending()
        raw_metrics = self.metrics_source.collect()
        inv = self._cached_inventory
        os_detail = f"{inv['windows_edition']} (Build {inv['windows_build']}) | {inv['cpu_model']}"
        self.client.send_heartbeat(
            status="Online",
            cpu_usage=round(raw_metrics.get("collector_cpu_pct", raw_metrics.get("cpu_usage", 0.0)), 1),
            memory_usage=round(raw_metrics.get("collector_mem_mb", raw_metrics.get("memory_usage", 0.0)), 1),
            pending_buffered=buffered_cnt,
            os_info=os_detail
        )
        self.last_heartbeat = time.time()

    def run_forever(self):
        inv = self._cached_inventory
        print(f"[AEGIS Collector] Starting Tier 1 Local Collector for Tenant={self.config.TENANT_ID}")
        print(f"[AEGIS Collector] Discovered Host: {inv['hostname']} ({inv['windows_edition']} Build {inv['windows_build']}, {inv['cpu_model']})")
        print(f"[AEGIS Collector] Hardware: {inv['cpu_physical_cores']} Cores / {inv['cpu_logical_cores']} Threads | {inv['ram_total_gb']} GB RAM")
        print(f"[AEGIS Collector] Local Storage: {self.config.LOCAL_DB_PATH}")
        print(f"[AEGIS Collector] Target SaaS URL: {self.config.SAAS_URL}")
        
        while True:
            try:
                cycle_result = self.run_cycle()
                status_str = "Delivered" if cycle_result["success"] else "Buffered"
                anom_count = len(cycle_result.get("local_anomalies", []))
                anom_flag = f" [! {anom_count} LOCAL ANOMALIES]" if anom_count > 0 else ""
                print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] Payload {cycle_result['payload_id'][:8]} -> {status_str}{anom_flag} (SHA-256: {cycle_result['payload_hash'][:12]}... Pending buffer: {cycle_result['pending_buffer_count']})")
                self.heartbeat_cycle()
            except Exception as e:
                print(f"[AEGIS Collector Error] {e}")
            time.sleep(self.config.COLLECTION_INTERVAL_SECONDS)

if __name__ == "__main__":
    collector = Tier1Collector()
    collector.run_forever()
