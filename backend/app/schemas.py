import datetime
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, EmailStr

# --- Ingestion Metadata Payload Schema (Strict Field Allow-Listing) ---
class MetadataPayload(BaseModel):
    class Config:
        extra = "forbid"

    payload_id: str = Field(..., description="Unique UUID for idempotency")
    tenant_id: str = Field(..., description="Organization tenant identifier")
    source_id: str = Field(..., description="Pseudonymous host or source identifier")
    collector_id: Optional[str] = "COLLECTOR_001"
    timestamp_utc: str = Field(..., description="ISO 8601 UTC timestamp")
    cpu_usage: float = Field(..., ge=0.0, le=100.0)
    memory_usage: float = Field(..., ge=0.0, le=100.0)
    disk_usage: float = Field(..., ge=0.0, le=100.0)
    latency_ms: Optional[float] = 0.0
    packet_loss_pct: Optional[float] = 0.0
    throughput_kbps: Optional[float] = 0.0
    bytes_sent: Optional[float] = 0.0
    bytes_recv: Optional[float] = 0.0
    upload_kbps: Optional[float] = 0.0
    download_kbps: Optional[float] = 0.0
    disk_read_kbps: Optional[float] = 0.0
    disk_write_kbps: Optional[float] = 0.0
    disk_iops: Optional[float] = 0.0
    cpu_freq_mhz: Optional[float] = 0.0
    swap_percent: Optional[float] = 0.0
    battery_percent: Optional[float] = None
    load_avg_1m: Optional[float] = 0.0
    top_processes: Optional[List[Dict[str, Any]]] = None
    local_anomalies: Optional[List[Dict[str, Any]]] = None
    health_state: str = Field("Good", pattern="^(Excellent|Good|Fair|Poor)$")
    event_category: str = "Performance"
    severity: str = "Low"
    
    # Egress Proof parameters attached by Tier 1 privacy engine
    payload_hash: Optional[str] = None
    applied_policy: Optional[str] = "Standard-v1"
    approved_fields: Optional[List[str]] = None
    redacted_fields: Optional[List[str]] = None
    exact_transmitted_json: Optional[str] = None

# Layer A1: Canonical AllowedPayload specification
AllowedPayload = MetadataPayload

class IngestionAck(BaseModel):
    status: str
    payload_id: str
    tenant_id: str
    server_ack_utc: str
    received_hash: str
    verified: bool
    duplicate: bool

# --- Authentication Schemas ---
class LoginRequest(BaseModel):
    email: str
    password: str

class RegisterRequest(BaseModel):
    org_name: str
    admin_name: str
    admin_email: str
    password: str
    region: Optional[str] = "us-east-1"
    timezone: Optional[str] = "UTC"

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: Dict[str, Any]

class UserOut(BaseModel):
    id: int
    tenant_id: str
    email: str
    full_name: str
    role: str
    is_active: bool

# --- Collector Schemas ---
class CollectorRegister(BaseModel):
    collector_id: str
    host_identifier: str
    version: str = "1.0.0"
    os_info: Optional[str] = "Unknown"

class CollectorHeartbeat(BaseModel):
    collector_id: str
    status: str = "Online"
    cpu_usage: float = 0.0
    memory_usage: float = 0.0
    pending_buffered: int = 0
    os_info: Optional[str] = None

class CollectorOut(BaseModel):
    collector_id: str
    tenant_id: str
    host_identifier: str
    collector_name: Optional[str] = None
    version: str
    status: str
    last_heartbeat: str
    pending_buffered: int
    local_buffer_queue_size: Optional[int] = None
    cpu_usage: float
    memory_usage: float
    os_info: str
    last_delivery_success: Optional[str]

# --- Anomaly & AIOps ---
class AnomalyOut(BaseModel):
    anomaly_id: str
    source_id: str
    metric: str
    observed_value: float
    baseline_value: float
    anomaly_score: float
    severity: str
    reason: str
    contributing_signals: List[str]
    timestamp_utc: str

# --- Incident Schemas ---
class IncidentOut(BaseModel):
    incident_id: str
    title: str
    severity: str
    status: str
    affected_service: str
    affected_collectors: List[str]
    related_alerts: List[Dict[str, Any]]
    timeline: List[Dict[str, Any]]
    likely_cause: str
    recommended_investigation: str
    confidence: float
    created_at: str
    resolved_at: Optional[str]
    root_cause: Optional[str] = None
    z_score_reasoning: Optional[str] = None
    contributing_signals: Optional[List[str]] = None
    confidence_score: Optional[float] = None
    merged_alerts_count: Optional[int] = None

# --- Recommendation Schemas ---
class RecommendationOut(BaseModel):
    recommendation_id: str
    incident_id: Optional[str]
    title: str
    reason: str
    severity: str
    confidence: float
    supporting_evidence: List[Dict[str, Any]]
    suggested_action: str

# --- Egress Proof Schemas ---
class EgressProofOut(BaseModel):
    payload_id: str
    tenant_id: str
    source_id: str
    timestamp_utc: str
    raw_local_log_blocked: Optional[str] = None
    sanitized_saas_payload: Optional[str] = None
    approved_fields: List[str]
    redacted_fields: List[str]
    applied_policy: str
    raw_local_log_blocked: Optional[str] = None
    exact_transmitted_json: str
    payload_hash: str
    transmission_status: str
    server_ack_utc: str
    hash_verified: bool

# --- Audit & Recovery Schemas ---
class AuditRecordOut(BaseModel):
    id: int
    actor: str
    action: str
    target: str
    result: str
    details: Dict[str, Any]
    timestamp_utc: str

class RecoveryActionRequest(BaseModel):
    incident_id: str
    recommendation_text: str
    approver: str

class RecoveryApproveRequest(BaseModel):
    simulation_id: str
    approver: Optional[str] = "Admin / SecOps Officer"

class RecoveryRollbackRequest(BaseModel):
    simulation_id: str
    reason: Optional[str] = "Operator requested rollback"

class RecoveryActionOut(BaseModel):
    simulation_id: str
    incident_id: str
    status: str
    approver: Optional[str]
    simulated_action: str
    policy_check: str
    simulation_result: str
    rollback_info: str
    created_at: str

# --- Dashboard Summary ---
class DashboardSummary(BaseModel):
    health_state: str
    health_score: int
    states: Dict[str, int]
    collectors_online: int
    collectors_offline: int
    collectors_total: Optional[int] = None
    tenant_id: Optional[str] = None
    tenant_name: Optional[str] = None
    active_incidents: int
    incidents_24h: int
    security_alerts: int
    security_severity: str
    privacy_status: str
    egress_count: int
    cpu_avg: float
    memory_avg: float
    disk_avg: float
    latency_avg: float
    incidents: List[Dict[str, Any]]
    recommendations: List[Dict[str, Any]]
    simulated: bool = False
    maturity_stage: str = "Stage 1: Ingest"
    host_status: str = "Configured Host"
    metrics_history: Optional[List[Dict[str, Any]]] = None
