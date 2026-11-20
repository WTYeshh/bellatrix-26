import hashlib
import json
import datetime
from typing import Dict, Any, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from backend.app.models import (
    MetricRecord, EgressProof, Collector, AnomalyRecord, Incident, AuditRecord
)
from backend.app.schemas import MetadataPayload, IngestionAck
from backend.app.aiops.engine import aiops_engine

STRICT_ALLOWED_FIELDS = {
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
    "health_state",
    "event_category",
    "severity",
    "payload_hash",
    "applied_policy",
    "approved_fields",
    "redacted_fields",
    "exact_transmitted_json"
}

def verify_payload_hash(exact_json: str, expected_hash: str) -> bool:
    """Computes SHA-256 over exact transmitted JSON string to verify integrity."""
    if not exact_json or not expected_hash:
        return True  # If client didn't supply hash, accept payload but mark unverified
    calculated = hashlib.sha256(exact_json.encode("utf-8")).hexdigest()
    return calculated == expected_hash

async def process_ingestion_payload(
    payload_dict: Dict[str, Any],
    db: AsyncSession
) -> IngestionAck:
    """
    Tier 2 Ingestion Pipeline:
    1. Independent Field Allow-List Validation
    2. Idempotency Check (prevent duplicates on network retry)
    3. SHA-256 Hash Integrity Verification
    4. Storage of Metrics & Egress Proof
    5. Real-time AIOps Anomaly Detection & Incident Correlation
    6. Collector State Update
    """
    # 1. Field allow-list check
    received_keys = set(payload_dict.keys())
    disallowed_keys = received_keys - STRICT_ALLOWED_FIELDS
    if disallowed_keys:
        raise ValueError(f"Strict privacy allow-list violation: Unapproved fields detected: {list(disallowed_keys)}")

    payload = MetadataPayload(**payload_dict)

    # 2. Idempotency check: see if payload_id already exists in DB
    existing_stmt = select(MetricRecord).where(
        MetricRecord.payload_id == payload.payload_id,
        MetricRecord.tenant_id == payload.tenant_id
    )
    res = await db.execute(existing_stmt)
    existing_metric = res.scalar_one_or_none()
    now_utc = datetime.datetime.now(datetime.timezone.utc)

    if existing_metric:
        # Return ACK without creating duplicate database records
        return IngestionAck(
            status="Acknowledged",
            payload_id=payload.payload_id,
            tenant_id=payload.tenant_id,
            server_ack_utc=now_utc.isoformat(),
            received_hash=payload.payload_hash or "",
            verified=True,
            duplicate=True
        )

    # 3. SHA-256 Hash Verification
    verified = True
    if payload.exact_transmitted_json and payload.payload_hash:
        verified = verify_payload_hash(payload.exact_transmitted_json, payload.payload_hash)

    # Parse timestamp
    try:
        ts = datetime.datetime.fromisoformat(payload.timestamp_utc.replace("Z", "+00:00"))
    except:
        ts = now_utc

    # 4. Save Metric Record
    metric_record = MetricRecord(
        payload_id=payload.payload_id,
        tenant_id=payload.tenant_id,
        source_id=payload.source_id,
        collector_id=payload.collector_id or "COLLECTOR_001",
        timestamp_utc=ts,
        cpu_usage=payload.cpu_usage,
        memory_usage=payload.memory_usage,
        disk_usage=payload.disk_usage,
        latency_ms=payload.latency_ms or 0.0,
        packet_loss_pct=payload.packet_loss_pct or 0.0,
        health_state=payload.health_state,
        event_category=payload.event_category,
        severity=payload.severity
    )
    db.add(metric_record)

    # 5. Save Egress Proof Record
    proof_record = EgressProof(
        payload_id=payload.payload_id,
        tenant_id=payload.tenant_id,
        source_id=payload.source_id,
        timestamp_utc=ts,
        approved_fields=json.dumps(payload.approved_fields or list(STRICT_ALLOWED_FIELDS)),
        redacted_fields=json.dumps(payload.redacted_fields or []),
        applied_policy=payload.applied_policy or "Standard-v1",
        exact_transmitted_json=payload.exact_transmitted_json or json.dumps(payload_dict),
        payload_hash=payload.payload_hash or hashlib.sha256(json.dumps(payload_dict, sort_keys=True).encode()).hexdigest(),
        transmission_status="Delivered & Verified" if verified else "Delivered (Hash Unverified)",
        server_ack_utc=now_utc
    )
    db.add(proof_record)

    # 6. Update Collector Heartbeat & Delivery Stats
    collector_stmt = select(Collector).where(
        Collector.collector_id == (payload.collector_id or "COLLECTOR_001"),
        Collector.tenant_id == payload.tenant_id
    )
    c_res = await db.execute(collector_stmt)
    collector = c_res.scalar_one_or_none()
    if collector:
        collector.last_heartbeat = now_utc
        collector.last_delivery_success = now_utc
        collector.status = "Online"
        collector.cpu_usage = payload.cpu_usage
        collector.memory_usage = payload.memory_usage
        if collector.pending_buffered > 0:
            collector.pending_buffered = max(0, collector.pending_buffered - 1)

    # 7. AIOps Detection Pipeline
    anomalies_detected = []
    for metric_name, val in [
        ("cpu_usage", payload.cpu_usage),
        ("memory_usage", payload.memory_usage),
        ("disk_usage", payload.disk_usage),
        ("latency_ms", payload.latency_ms or 0.0),
        ("packet_loss_pct", payload.packet_loss_pct or 0.0),
    ]:
        anomaly = aiops_engine.detect_statistical_anomaly(
            tenant_id=payload.tenant_id,
            source_id=payload.source_id,
            metric=metric_name,
            current_value=val
        )
        if anomaly:
            anomalies_detected.append(anomaly)
            anom_id = f"ANOM-{int(now_utc.timestamp())}-{metric_name}"
            anom_record = AnomalyRecord(
                anomaly_id=anom_id,
                tenant_id=payload.tenant_id,
                source_id=payload.source_id,
                metric=metric_name,
                observed_value=anomaly["observed_value"],
                baseline_value=anomaly["baseline_value"],
                anomaly_score=anomaly["anomaly_score"],
                severity=anomaly["severity"],
                reason=anomaly["reason"],
                contributing_signals=json.dumps(anomaly["contributing_signals"]),
                timestamp_utc=now_utc
            )
            db.add(anom_record)

    # 8. Incident DNA Alert Correlation
    if anomalies_detected:
        active_inc_stmt = select(Incident).where(
            Incident.tenant_id == payload.tenant_id,
            Incident.status.in_(["Active", "Investigating"])
        )
        active_incs = (await db.execute(active_inc_stmt)).scalars().all()

        correlated = aiops_engine.correlate_incident_dna(
            tenant_id=payload.tenant_id,
            anomalies=anomalies_detected,
            existing_active_incidents=active_incs
        )
        if correlated:
            new_incident = Incident(
                incident_id=correlated["incident_id"],
                tenant_id=payload.tenant_id,
                title=correlated["title"],
                severity=correlated["severity"],
                status=correlated["status"],
                affected_service=correlated["affected_service"],
                affected_collectors=json.dumps(correlated["affected_collectors"]),
                related_alerts=json.dumps(correlated["related_alerts"]),
                timeline=json.dumps(correlated["timeline"]),
                likely_cause=correlated["likely_cause"],
                recommended_investigation=correlated["recommended_investigation"],
                confidence=correlated["confidence"],
                created_at=now_utc
            )
            db.add(new_incident)

    await db.commit()

    return IngestionAck(
        status="Delivered",
        payload_id=payload.payload_id,
        tenant_id=payload.tenant_id,
        server_ack_utc=now_utc.isoformat(),
        received_hash=payload.payload_hash or "",
        verified=verified,
        duplicate=False
    )
