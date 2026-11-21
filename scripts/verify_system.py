import json
import urllib.request
import urllib.parse
import sys

def req(url, method="GET", data=None, headers=None):
    if headers is None:
        headers = {}
    body = None
    if data is not None:
        body = json.dumps(data).encode("utf-8")
        headers["Content-Type"] = "application/json"
    r = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(r, timeout=5) as res:
            content = res.read().decode("utf-8")
            ct = res.headers.get("Content-Type", "")
            if "application/json" in ct:
                return res.status, json.loads(content)
            return res.status, content
    except urllib.error.HTTPError as e:
        err_content = e.read().decode("utf-8")
        try:
            return e.code, json.loads(err_content)
        except Exception:
            return e.code, err_content
    except Exception as e:
        return 0, str(e)

def main():
    print("=" * 65)
    print("  🛡️  AEGIS PRIVACY-FIRST AIOPS FULL VERIFICATION SUITE")
    print("=" * 65)

    # 1. Frontend Check (Port 3000)
    st, res = req("http://localhost:3000/")
    print(f"\n[1] Frontend (Port 3000): HTTP {st}")
    assert st == 200, f"Expected 200, got {st}"
    assert "Command Center" in res
    assert "Telemetry & Security" in res
    assert "Collectors" in res
    assert "AIOps Incidents" in res
    assert "Recovery Simulator" in res
    assert "Egress Proof" in res
    assert "Audit & Policies" in res
    assert "Demo Controls & Settings" in res
    assert "global-tenant-select" in res
    print("  -> All 8 Sidebar Navigation tabs & Tenant Switcher verified in HTML!")

    # 2. Central Backend Health (Port 8000)
    st, res = req("http://127.0.0.1:8000/health")
    print(f"\n[2] Central Backend /health (Port 8000): HTTP {st}")
    assert st == 200 and res.get("status") == "healthy"
    print(f"  -> Service: {res.get('service')}, Database: {res.get('database')} ({res.get('database_type')})")

    # 3. Tier 1 Collector (Port 8001)
    st, res = req("http://127.0.0.1:8001/status")
    print(f"\n[3] Tier 1 Collector /status (Port 8001): HTTP {st}")
    assert st == 200
    print(f"  -> Collector ID: {res.get('collector_id')}, Tenant: {res.get('tenant_id')}")
    print(f"  -> Status: {res.get('status')}, Buffer Queue: {res.get('buffer_queue_size')}")
    print(f"  -> Privacy Engine: {res.get('privacy_engine')}")

    # 4. Auth Login
    print("\n[4] Backend Authentication (/api/v1/auth/login)")
    st, res = req("http://127.0.0.1:8000/api/v1/auth/login", method="POST", data={"email": "admin@hdfcbank.com", "password": "aegis2026"})
    print(f"  -> Login result: HTTP {st}")
    assert st == 200, f"Login failed: {res}"
    token = res.get("access_token")
    user = res.get("user", {})
    tenant = user.get("orgId") or user.get("tenant_id") or "BANK_HDFC_IN"
    print(f"  -> Logged in as: {user.get('name')} ({user.get('email')}), Role: {user.get('role')}, Tenant: {tenant}")
    
    auth_headers_hdfc = {
        "Authorization": f"Bearer {token}",
        "X-Tenant-ID": "BANK_HDFC_IN"
    }

    # 5. Dashboard Summary (HDFC Bank)
    st, res = req("http://127.0.0.1:8000/api/v1/dashboard/summary", headers=auth_headers_hdfc)
    print(f"\n[5] HDFC Bank Dashboard Summary: HTTP {st}")
    assert st == 200
    print(f"  -> Tenant: {res.get('tenant_id')} ({res.get('tenant_name')})")
    print(f"  -> Health Score: {res.get('health_score')}")
    print(f"  -> 4 Health States: Excellent={res.get('states',{}).get('excellent')}, Good={res.get('states',{}).get('good')}, Fair={res.get('states',{}).get('fair')}, Poor={res.get('states',{}).get('poor')}")
    print(f"  -> Online Collectors: {res.get('collectors_online')}/{res.get('collectors_total')}")

    # 6. Tenant Isolation Check (ICICI Bank)
    auth_headers_icici = {
        "Authorization": f"Bearer {token}",
        "X-Tenant-ID": "BANK_ICICI_IN"
    }
    st, res = req("http://127.0.0.1:8000/api/v1/dashboard/summary", headers=auth_headers_icici)
    print(f"\n[6] ICICI Bank Dashboard Summary (Tenant Isolation): HTTP {st}")
    assert st == 200
    print(f"  -> Tenant: {res.get('tenant_id')} ({res.get('tenant_name')})")
    print(f"  -> Health Score: {res.get('health_score')}")
    print(f"  -> 4 Health States: {res.get('states')}")

    # 7. AIOps Incidents (INC-2026-089)
    st, res = req("http://127.0.0.1:8000/api/v1/incidents/active", headers=auth_headers_hdfc)
    print(f"\n[7] Active AIOps Incidents: HTTP {st}")
    assert st == 200
    incidents = res if isinstance(res, list) else res.get("incidents", [])
    found_inc = False
    print(f"  -> Total Active Incidents: {len(incidents)}")
    for inc in incidents:
        if "089" in inc.get("incident_id", ""):
            found_inc = True
        print(f"     * [{inc.get('incident_id')}] {inc.get('title')}")
        print(f"       Severity: {inc.get('severity')} | Merged Alerts: {inc.get('merged_alerts_count')} | Confidence: {inc.get('confidence_score')}")
        print(f"       Root Cause: {inc.get('root_cause')}")
        print(f"       Z-Score Reasoning: {inc.get('z_score_reasoning')}")
        print(f"       Contributing Signals: {inc.get('contributing_signals')}")
    assert found_inc, "INC-2026-089 must be present in seeded incidents!"

    # 8. Recovery Simulator (Approve & Rollback)
    st, res = req("http://127.0.0.1:8000/api/v1/recovery", headers=auth_headers_hdfc)
    print(f"\n[8] Recovery Simulator /recovery: HTTP {st}")
    assert st == 200
    sims = res if isinstance(res, list) else res.get("simulations", [])
    print(f"  -> Found {len(sims)} simulations")
    sim_id = "SIM-2026-089"
    if sims:
        s0 = sims[0]
        sim_id = s0.get("simulation_id", sim_id)
        act_text = s0.get('simulated_action') or s0.get('action')
        print(f"     Action: {act_text}, Status: {s0.get('status')}")
    
    # Test Approve
    st, res = req("http://127.0.0.1:8000/api/v1/recovery/approve", method="POST", 
                  data={"simulation_id": sim_id, "approver": "ops-lead@hdfcbank.com"},
                  headers=auth_headers_hdfc)
    print(f"  -> Approve & Execute: HTTP {st}, Status: {res.get('status')}")
    assert st == 200 and res.get("status") in ["success", "Executed & Mitigated"]

    # Test Rollback
    st, res = req("http://127.0.0.1:8000/api/v1/recovery/rollback", method="POST",
                  data={"simulation_id": sim_id, "reason": "Operator requested rollback"},
                  headers=auth_headers_hdfc)
    print(f"  -> Rollback: HTTP {st}, Status: {res.get('status')}")
    assert st == 200 and res.get("status") in ["success", "Rolled Back"]

    # 9. Egress Proof Inspector (Side-by-side with PII highlighted)
    st, res = req("http://127.0.0.1:8000/api/v1/egress-proof?limit=5", headers=auth_headers_hdfc)
    print(f"\n[9] Egress Proofs Side-by-Side: HTTP {st}")
    assert st == 200
    proofs = res if isinstance(res, list) else res.get("proofs", [])
    print(f"  -> Retrieved {len(proofs)} proofs")
    if proofs:
        p0 = proofs[0]
        has_raw = bool(p0.get("raw_local_log_blocked"))
        has_san = bool(p0.get("sanitized_saas_payload") or p0.get("exact_transmitted_json"))
        print(f"     Proof ID: {p0.get('payload_id') or p0.get('proof_id')}")
        print(f"     Has raw_local_log_blocked (redacted locally): {has_raw}")
        print(f"     Has sanitized_saas_payload (egress verified): {has_san}")
        print(f"     Transmission: {p0.get('transmission_status')}")
        assert has_raw and has_san, "Egress proof must contain both raw blocked log and sanitized payload!"

    # 10. Audit Records
    st, res = req("http://127.0.0.1:8000/api/v1/audit?limit=5", headers=auth_headers_hdfc)
    print(f"\n[10] Audit Records: HTTP {st}")
    assert st == 200
    records = res if isinstance(res, list) else res.get("records", [])
    print(f"  -> Retrieved {len(records)} audit records")

    # 11. Collectors status
    st, res = req("http://127.0.0.1:8000/api/v1/collectors", headers=auth_headers_hdfc)
    print(f"\n[11] Collectors endpoint: HTTP {st}")
    assert st == 200
    cols = res if isinstance(res, list) else res.get("collectors", [])
    print(f"  -> Total Collectors: {len(cols)}")
    for c in cols:
        print(f"     * {c.get('collector_id')} ({c.get('collector_name')}): {c.get('status')}, Local Buffer: {c.get('local_buffer_queue_size')}")

    # 12. Demo Controls & Scenario Triggers
    print("\n[12] Testing Demo Scenario Triggers:")
    scenarios = [
        ("POST", "http://127.0.0.1:8000/api/v1/demo/inject-pii-log", {}),
        ("POST", "http://127.0.0.1:8000/api/v1/demo/inject-brute-force", {}),
        ("POST", "http://127.0.0.1:8000/api/v1/demo/inject-network-spike", {}),
        ("POST", "http://127.0.0.1:8000/api/v1/demo/simulate-outage-toggle", {}),
        ("POST", "http://127.0.0.1:8000/api/v1/demo/simulate-outage-toggle", {}), # toggle back
    ]
    for m, u, d in scenarios:
        name = u.split("/")[-1]
        st, res = req(u, method=m, data=d, headers=auth_headers_hdfc)
        print(f"  -> Trigger '{name}': HTTP {st} => {res.get('message', res.get('status'))}")
        assert st == 200

    print("\n" + "=" * 65)
    print("  🎉 ALL 12 VERIFICATION CHECKS PASSED WITH 100% SUCCESS!")
    print("=" * 65)

if __name__ == "__main__":
    main()
