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
    tenant_id = Column(String(64), unique=True, index=True, nullable=False)
    name = Column(String(255), nullable=False)
    region = Column(String(64), default="us-east-1")
    timezone = Column(String(64), default="UTC")
    created_at = Column(DateTime(timezone=True), default=utcnow)

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String(64), ForeignKey("organizations.tenant_id"), index=True, nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=False)
    role = Column(String(64), default="IT Administrator")  # Organization Owner, IT Administrator, Security Engineer, DevOps Engineer, IT Manager
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)

class Collector(Base):
    __tablename__ = "collectors"

    id = Column(Integer, primary_key=True, index=True)
    collector_id = Column(String(64), unique=True, index=True, nullable=False)
    tenant_id = Column(String(64), ForeignKey("organizations.tenant_id"), index=True, nullable=False)
    host_identifier = Column(String(255), nullable=False)
    version = Column(String(32), default="1.0.0")
    status = Column(String(32), default="Online")  # Online, Offline, Degraded
    last_heartbeat = Column(DateTime(timezone=True), default=utcnow)
    pending_buffered = Column(Integer, default=0)
    cpu_usage = Column(Float, default=0.0)
    memory_usage = Column(Float, default=0.0)
    os_info = Column(String(255), default="Unknown")
    auth_token = Column(String(255), nullable=False)
    last_delivery_success = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)

class MetricRecord(Base):
    __tablename__ = "metrics"

    id = Column(Integer, primary_key=True, index=True)
    payload_id = Column(String(64), unique=True, index=True, nullable=False)
    tenant_id = Column(String(64), ForeignKey("organizations.tenant_id"), index=True, nullable=False)
    source_id = Column(String(64), index=True, nullable=False)
    collector_id = Column(String(64), index=True, nullable=False)
    timestamp_utc = Column(DateTime(timezone=True), index=True, nullable=False)
    cpu_usage = Column(Float, nullable=False)
    memory_usage = Column(Float, nullable=False)
    disk_usage = Column(Float, nullable=False)
    latency_ms = Column(Float, default=0.0)
    packet_loss_pct = Column(Float, default=0.0)
    health_state = Column(String(32), default="Good")  # Excellent, Good, Fair, Poor
    event_category = Column(String(64), default="Performance")
    severity = Column(String(32), default="Low")

    __table_args__ = (
        Index("ix_metrics_tenant_timestamp", "tenant_id", "timestamp_utc"),
        Index("ix_metrics_tenant_source", "tenant_id", "source_id"),
    )

class SecuritySummary(Base):
    __tablename__ = "security_summaries"

    id = Column(Integer, primary_key=True, index=True)
    payload_id = Column(String(64), unique=True, index=True, nullable=False)
    tenant_id = Column(String(64), ForeignKey("organizations.tenant_id"), index=True, nullable=False)
    source_id = Column(String(64), index=True, nullable=False)
    event_category = Column(String(64), default="Authentication")
    severity = Column(String(32), default="Medium")  # Low, Medium, High, Critical
    failed_login_count = Column(Integer, default=0)
    description = Column(String(512), nullable=False)
    timestamp_utc = Column(DateTime(timezone=True), index=True, nullable=False)

class EgressProof(Base):
    __tablename__ = "egress_proofs"

    id = Column(Integer, primary_key=True, index=True)
    payload_id = Column(String(64), unique=True, index=True, nullable=False)
    tenant_id = Column(String(64), ForeignKey("organizations.tenant_id"), index=True, nullable=False)
    source_id = Column(String(64), index=True, nullable=False)
    timestamp_utc = Column(DateTime(timezone=True), index=True, nullable=False)
    approved_fields = Column(Text, nullable=False)   # JSON array of approved strings
    redacted_fields = Column(Text, nullable=False)   # JSON array of redacted/dropped strings
    applied_policy = Column(String(64), default="Standard-v1")
    exact_transmitted_json = Column(Text, nullable=False)
    payload_hash = Column(String(64), nullable=False)  # SHA-256
    transmission_status = Column(String(32), default="Delivered")
    server_ack_utc = Column(DateTime(timezone=True), default=utcnow)

class AnomalyRecord(Base):
    __tablename__ = "anomalies"

    id = Column(Integer, primary_key=True, index=True)
    anomaly_id = Column(String(64), unique=True, index=True, nullable=False)
    tenant_id = Column(String(64), ForeignKey("organizations.tenant_id"), index=True, nullable=False)
    source_id = Column(String(64), index=True, nullable=False)
    metric = Column(String(64), nullable=False)
    observed_value = Column(Float, nullable=False)
    baseline_value = Column(Float, nullable=False)
    anomaly_score = Column(Float, nullable=False)
    severity = Column(String(32), default="Medium")  # Low, Medium, High, Critical
    reason = Column(Text, nullable=False)
    contributing_signals = Column(Text, nullable=False)  # JSON array
    timestamp_utc = Column(DateTime(timezone=True), index=True, default=utcnow)

class Incident(Base):
    __tablename__ = "incidents"

    id = Column(Integer, primary_key=True, index=True)
    incident_id = Column(String(64), unique=True, index=True, nullable=False)
    tenant_id = Column(String(64), ForeignKey("organizations.tenant_id"), index=True, nullable=False)
    title = Column(String(255), nullable=False)
    severity = Column(String(32), default="Medium")
    status = Column(String(32), default="Active")  # Active, Investigating, Mitigated, Resolved
    affected_service = Column(String(128), default="General Infrastructure")
    affected_collectors = Column(Text, nullable=False)  # JSON array
    related_alerts = Column(Text, nullable=False)       # JSON array of alerts
    timeline = Column(Text, nullable=False)             # JSON array of timeline steps
    likely_cause = Column(Text, nullable=False)
    recommended_investigation = Column(Text, nullable=False)
    confidence = Column(Float, default=0.85)
    created_at = Column(DateTime(timezone=True), default=utcnow)
    resolved_at = Column(DateTime(timezone=True), nullable=True)

class PrivacyPolicy(Base):
    __tablename__ = "privacy_policies"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String(64), ForeignKey("organizations.tenant_id"), index=True, nullable=False)
    version = Column(String(32), default="v1.0")
    name = Column(String(128), default="Default Strict Allow-List")
    allowed_fields = Column(Text, nullable=False)       # JSON array
    redaction_rules = Column(Text, nullable=False)      # JSON object regex rules
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)

class AuditRecord(Base):
    __tablename__ = "audit_records"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String(64), ForeignKey("organizations.tenant_id"), index=True, nullable=False)
    actor = Column(String(128), nullable=False)
    action = Column(String(128), nullable=False)
    target = Column(String(128), nullable=False)
    result = Column(String(64), default="Success")  # Success, Denied, Failed
    details = Column(Text, default="{}")
    timestamp_utc = Column(DateTime(timezone=True), default=utcnow)

class RecoverySimulation(Base):
    __tablename__ = "recovery_simulations"

    id = Column(Integer, primary_key=True, index=True)
    simulation_id = Column(String(64), unique=True, index=True, nullable=False)
    tenant_id = Column(String(64), ForeignKey("organizations.tenant_id"), index=True, nullable=False)
    incident_id = Column(String(64), nullable=False)
    recommendation_text = Column(Text, nullable=False)
    status = Column(String(32), default="Pending Approval")  # Pending Approval, Approved, Simulated, Rolled Back
    approver = Column(String(128), nullable=True)
    simulated_action = Column(String(255), nullable=False)
    policy_check = Column(String(64), default="Passed")
    simulation_result = Column(Text, nullable=True)
    rollback_info = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)
