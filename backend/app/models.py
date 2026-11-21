import datetime
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime, Text, ForeignKey, Index
)
from backend.app.database import Base

def utcnow():
    return datetime.datetime.now(datetime.timezone.utc)

class Organization(Base):
    __tablename__ = "organizations"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String(64), unique=True, index=True, default="default")
    name = Column(String(255), default="AEGIS Local Server")
    region = Column(String(64), default="local")
    timezone = Column(String(64), default="UTC")
    created_at = Column(DateTime(timezone=True), default=utcnow)

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String(64), default="default", index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=False)
    role = Column(String(64), default="System Administrator")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)

class Collector(Base):
    __tablename__ = "collectors"

    id = Column(Integer, primary_key=True, index=True)
    collector_id = Column(String(64), unique=True, index=True, default="COLLECTOR_SERVER_01")
    tenant_id = Column(String(64), default="default", index=True)
    host_identifier = Column(String(255), default="server-01")
    version = Column(String(32), default="1.0.0")
    status = Column(String(32), default="Online")  # Online, Offline, Degraded
    environment = Column(String(64), default="production", index=True)
    config_version = Column(String(32), default="v1.0")
    config_status = Column(String(64), default="Synchronized")
    last_heartbeat = Column(DateTime(timezone=True), default=utcnow)
    pending_buffered = Column(Integer, default=0)
    cpu_usage = Column(Float, default=0.0)
    memory_usage = Column(Float, default=0.0)
    os_info = Column(String(255), default="Windows Host")
    auth_token = Column(String(255), default="aegis-collector-token-server01")
    last_delivery_success = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)

class MetricRecord(Base):
    __tablename__ = "metrics"

    id = Column(Integer, primary_key=True, index=True)
    payload_id = Column(String(64), unique=True, index=True, nullable=False)
    tenant_id = Column(String(64), default="default", index=True)
    source_id = Column(String(64), index=True, default="server-01")
    collector_id = Column(String(64), index=True, default="COLLECTOR_SERVER_01")
    environment = Column(String(64), default="production", index=True)
    timestamp_utc = Column(DateTime(timezone=True), index=True, nullable=False)
    cpu_usage = Column(Float, nullable=False)
    memory_usage = Column(Float, nullable=False)
    disk_usage = Column(Float, nullable=False)
    latency_ms = Column(Float, default=0.0)
    packet_loss_pct = Column(Float, default=0.0)
    upload_kbps = Column(Float, default=0.0)
    download_kbps = Column(Float, default=0.0)
    disk_read_kbps = Column(Float, default=0.0)
    disk_write_kbps = Column(Float, default=0.0)
    disk_iops = Column(Float, default=0.0)
    cpu_freq_mhz = Column(Float, default=0.0)
    swap_percent = Column(Float, default=0.0)
    battery_percent = Column(Float, nullable=True)
    load_avg_1m = Column(Float, default=0.0)
    health_state = Column(String(32), default="Good")  # Excellent, Good, Fair, Poor
    event_category = Column(String(64), default="Performance")
    severity = Column(String(32), default="Low")
    top_processes_json = Column(Text, nullable=True)

    __table_args__ = (
        Index("ix_metrics_timestamp", "timestamp_utc"),
        Index("ix_metrics_source_timestamp", "source_id", "timestamp_utc"),
    )

class MetricRollup(Base):
    __tablename__ = "metric_rollups"

    id = Column(Integer, primary_key=True, index=True)
    source_id = Column(String(64), index=True, default="server-01")
    interval = Column(String(16), index=True, nullable=False)  # "1m", "5m", "1h"
    bucket_start_utc = Column(DateTime(timezone=True), index=True, nullable=False)
    cpu_avg = Column(Float, nullable=False)
    cpu_min = Column(Float, nullable=False)
    cpu_max = Column(Float, nullable=False)
    memory_avg = Column(Float, nullable=False)
    disk_avg = Column(Float, nullable=False)
    latency_avg = Column(Float, nullable=False)
    sample_count = Column(Integer, default=1)

    __table_args__ = (
        Index("ix_rollups_interval_bucket", "interval", "bucket_start_utc"),
    )

class SecuritySummary(Base):
    __tablename__ = "security_summaries"

    id = Column(Integer, primary_key=True, index=True)
    payload_id = Column(String(64), unique=True, index=True, nullable=False)
    tenant_id = Column(String(64), default="default", index=True)
    source_id = Column(String(64), index=True, default="server-01")
    pseudonymous_source_id = Column(String(64), default="server-01")
    event_category = Column(String(64), default="Authentication")
    severity = Column(String(32), default="Medium")
    failed_login_count = Column(Integer, default=0)
    time_window_sec = Column(Integer, default=300)
    adapter_type = Column(String(64), default="Local-Engine")
    description = Column(String(512), nullable=False)
    timestamp_utc = Column(DateTime(timezone=True), index=True, nullable=False)

class EgressProof(Base):
    __tablename__ = "egress_proofs"

    id = Column(Integer, primary_key=True, index=True)
    payload_id = Column(String(64), unique=True, index=True, nullable=False)
    tenant_id = Column(String(64), default="default", index=True)
    source_id = Column(String(64), index=True, default="server-01")
    timestamp_utc = Column(DateTime(timezone=True), index=True, nullable=False)
    approved_fields = Column(Text, nullable=False)
    redacted_fields = Column(Text, nullable=False)
    applied_policy = Column(String(64), default="Standard-v1")
    raw_local_log_blocked = Column(Text, nullable=True)
    exact_transmitted_json = Column(Text, nullable=False)
    payload_hash = Column(String(64), nullable=False)
    transmission_status = Column(String(32), default="Delivered")
    server_ack_utc = Column(DateTime(timezone=True), default=utcnow)

class AnomalyRecord(Base):
    __tablename__ = "anomalies"

    id = Column(Integer, primary_key=True, index=True)
    anomaly_id = Column(String(64), unique=True, index=True, nullable=False)
    tenant_id = Column(String(64), default="default", index=True)
    source_id = Column(String(64), index=True, default="server-01")
    metric = Column(String(64), nullable=False)
    observed_value = Column(Float, nullable=False)
    baseline_value = Column(Float, nullable=False)
    anomaly_score = Column(Float, nullable=False)
    severity = Column(String(32), default="Medium")
    reason = Column(Text, nullable=False)
    contributing_signals = Column(Text, nullable=False)
    contributing_processes = Column(Text, nullable=True)
    timestamp_utc = Column(DateTime(timezone=True), index=True, default=utcnow)

class Incident(Base):
    __tablename__ = "incidents"

    id = Column(Integer, primary_key=True, index=True)
    incident_id = Column(String(64), unique=True, index=True, nullable=False)
    tenant_id = Column(String(64), default="default", index=True)
    title = Column(String(255), nullable=False)
    severity = Column(String(32), default="Medium")
    status = Column(String(32), default="Active")  # Active, Investigating, Mitigated, Resolved
    affected_service = Column(String(128), default="server-01")
    affected_collectors = Column(Text, default='["COLLECTOR_SERVER_01"]')
    metric_breached = Column(String(64), nullable=True)
    observed_value = Column(Float, nullable=True)
    expected_value = Column(Float, nullable=True)
    contributing_processes = Column(Text, nullable=True)
    related_alerts = Column(Text, default='[]')
    timeline = Column(Text, default='[]')
    likely_cause = Column(Text, nullable=False)
    recommended_investigation = Column(Text, nullable=False)
    confidence = Column(Float, default=0.88)
    created_at = Column(DateTime(timezone=True), default=utcnow)
    resolved_at = Column(DateTime(timezone=True), nullable=True)

class PrivacyPolicy(Base):
    __tablename__ = "privacy_policies"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String(64), default="default", index=True)
    version = Column(String(32), default="v1.0")
    name = Column(String(128), default="Strict Allow-List & Redaction")
    allowed_fields = Column(Text, nullable=False)
    redaction_rules = Column(Text, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)

class AuditRecord(Base):
    __tablename__ = "audit_records"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String(64), default="default", index=True)
    actor = Column(String(128), nullable=False)
    action = Column(String(128), nullable=False)
    target = Column(String(128), nullable=False)
    result = Column(String(64), default="Success")
    details = Column(Text, default="{}")
    timestamp_utc = Column(DateTime(timezone=True), default=utcnow)

class RecoverySimulation(Base):
    __tablename__ = "recovery_simulations"

    id = Column(Integer, primary_key=True, index=True)
    simulation_id = Column(String(64), unique=True, index=True, nullable=False)
    tenant_id = Column(String(64), default="default", index=True)
    incident_id = Column(String(64), nullable=False)
    recommendation_text = Column(Text, nullable=False)
    status = Column(String(32), default="Pending Approval")
    approver = Column(String(128), nullable=True)
    simulated_action = Column(String(255), nullable=False)
    policy_check = Column(String(64), default="Passed")
    simulation_result = Column(Text, nullable=True)
    rollback_info = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)

class HealthTransitionRecord(Base):
    __tablename__ = "health_transitions"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String(64), default="default", index=True)
    source_id = Column(String(64), index=True, default="server-01")
    previous_state = Column(String(32), nullable=False)
    current_state = Column(String(32), nullable=False)
    reason = Column(String(256), nullable=False)
    supporting_metrics = Column(Text, nullable=False)
    transition_time_utc = Column(DateTime(timezone=True), default=utcnow, nullable=False)
