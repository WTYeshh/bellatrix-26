import os
import json
import hashlib
import pytest
from collector.sources.system_metrics import SystemMetricsSource
from collector.privacy.engine import PrivacyEngine
from collector.privacy.proof import EgressProofGenerator

def test_collector_metrics_collection():
    """TEST: Real telemetry is gathered by psutil without simulation."""
    source = SystemMetricsSource()
    metrics = source.collect()

    assert "cpu_usage" in metrics
    assert "memory_usage" in metrics
    assert "disk_usage" in metrics
    assert "latency_ms" in metrics
    assert "health_state" in metrics
    assert 0.0 <= metrics["cpu_usage"] <= 100.0
    assert 0.0 <= metrics["memory_usage"] <= 100.0
    assert metrics["health_state"] in ["Excellent", "Good", "Fair", "Poor"]
    print("✅ Collector metric collection verified.")

def test_privacy_strict_allow_list_enforcement():
    """TEST: Disallowed raw fields (e.g. passwords, raw hostnames) are DROPPED."""
    engine = PrivacyEngine()
    raw_telemetry = {
        "payload_id": "TEST_001",
        "tenant_id": "default",
        "source_id": "NODE_1234",
        "cpu_usage": 45.0,
        "memory_usage": 60.0,
        "disk_usage": 50.0,
        # SENSITIVE / DISALLOWED FIELDS:
        "raw_hostname": "corp-payroll-db.internal",
        "raw_process_list": ["svchost.exe", "lsass.exe"],
        "database_password": "SuperSecretPassword123!",
        "aws_secret_key": "AKIAIOSFODNN7EXAMPLE"
    }

    approved, approved_fields, dropped_fields = engine.apply_policy(raw_telemetry)

    # Disallowed fields must NOT be in approved payload
    assert "raw_hostname" not in approved
    assert "raw_process_list" not in approved
    assert "database_password" not in approved
    assert "aws_secret_key" not in approved

    # Disallowed fields must be logged in dropped_fields for Egress Proof
    assert "database_password" in dropped_fields
    assert "raw_hostname" in dropped_fields
    assert "cpu_usage" in approved
    print("✅ Privacy strict allow-list enforcement verified.")

def test_secret_redaction_in_strings():
    """TEST 1 SCENARIO: Secret strings embedded in allowed fields are REDACTED."""
    engine = PrivacyEngine()
    sample_text = "Service alert: user failed login with password='AdminMasterSecret2026!' and Authorization: Basic dXNlcjpwYXNz"
    clean_text, was_redacted = engine.redact_secrets_in_string(sample_text)

    assert was_redacted is True
    assert "AdminMasterSecret2026!" not in clean_text
    assert "[REDACTED_SECRET]" in clean_text
    print("✅ Secret redaction verified.")

def test_egress_proof_sha256_verification():
    """TEST: Egress proof generates exact SHA-256 hash matching canonical JSON."""
    proof_gen = EgressProofGenerator()
    payload = {
        "payload_id": "PAYLOAD_ABC_123",
        "tenant_id": "default",
        "source_id": "NODE_99",
        "timestamp_utc": "2026-11-20T12:00:00Z",
        "cpu_usage": 88.5,
        "memory_usage": 72.0,
        "disk_usage": 60.0,
        "health_state": "Fair"
    }

    bundle = proof_gen.generate_proof(
        approved_payload=payload,
        approved_fields=list(payload.keys()),
        redacted_fields=["raw_pass"]
    )
    proof = bundle["proof_record"]

    # Re-verify SHA-256 hash independently
    exact_json = proof["exact_transmitted_json"]
    expected_hash = hashlib.sha256(exact_json.encode("utf-8")).hexdigest()

    assert proof["payload_hash"] == expected_hash
    assert bundle["payload_to_send"]["payload_hash"] == expected_hash
    print("✅ SHA-256 Egress Proof hash verification verified.")

def test_fail_closed_privacy_gate_blocks_transmission():
    """TEST: Privacy engine fail-closed gate blocks transmission if unapproved field or unredacted secret escapes."""
    engine = PrivacyEngine()
    
    # 1. Unapproved key escaping into payload
    corrupt_payload = {
        "payload_id": "TEST_LEAK",
        "tenant_id": "default",
        "source_id": "NODE_LEAK",
        "cpu_usage": 50.0,
        "raw_leaked_password": "PlaintextPassword123"
    }
    is_valid, err = engine.validate_for_egress(corrupt_payload)
    assert is_valid is False
    assert "not on the approved allow-list" in err

    # 2. Unredacted credential pattern escaping into string field
    unredacted_payload = {
        "payload_id": "TEST_LEAK_2",
        "tenant_id": "default",
        "source_id": "NODE_LEAK_2",
        "cpu_usage": 50.0,
        "event_category": "Failed login password=SecretPassword123"
    }
    is_valid_sec, err_sec = engine.validate_for_egress(unredacted_payload)
    assert is_valid_sec is False
    assert "Unredacted credential pattern detected" in err_sec
    print("✅ Fail-closed privacy gate blocking verified.")

if __name__ == "__main__":
    test_collector_metrics_collection()
    test_privacy_strict_allow_list_enforcement()
    test_secret_redaction_in_strings()
    test_egress_proof_sha256_verification()
    print("All Privacy & Egress tests passed!")
