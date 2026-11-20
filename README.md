# AEGIS — Privacy-First AIOps Observability Platform

> **Observe. Detect. Correlate. Recommend.**

AEGIS is an enterprise-grade, privacy-first AIOps observability SaaS platform that monitors distributed infrastructure while strictly retaining sensitive operational data inside customer environments.

---

## 🛡️ Architecture & Security Boundary

```
┌───────────────────────────────────────────┐     ┌───────────────────────────────────────────┐
│     TIER 1 — CUSTOMER ENVIRONMENT         │     │        TIER 2 — CENTRAL AEGIS SAAS        │
│                                           │     │                                           │
│  ┌────────────────┐  ┌─────────────────┐  │     │  ┌────────────────┐  ┌─────────────────┐  │
│  │ Real Telemetry │→ │ Privacy Engine  │  │     │  │ Fast Ingestion │→ │ AIOps Engine    │  │
│  │ (psutil + net) │  │ • Strict Allow  │  │     │  │ • Allow Verify │  │ • Robust Z-Score│  │
│  └────────────────┘  │ • Secret Scrub  │──┼────→│  │ • Hash Verify  │  │ • Isolation     │  │
│                      │ • Pseudonymize  │  │     │  │ • Idempotent   │  │   Forest (ML)   │  │
│  ┌────────────────┐  │ • Egress Proof  │  │     │  └────────────────┘  └─────────────────┘  │
│  │ Local SQLite   │  │   (SHA-256)     │  │     │           │                   │           │
│  │ • Raw Vault    │  └─────────────────┘  │     │           ▼                   ▼           │
│  │ • Outbox Queue │           │           │     │  ┌────────────────┐  ┌─────────────────┐  │
│  │   (Offline)    │───────────┘           │     │  │ Central DB     │  │ Incident DNA    │  │
│  └────────────────┘                       │     │  │ (PostgreSQL/   │  │ • Alert Group   │  │
│                                           │     │  │  SQLite Async) │  │ • Timeline      │  │
│  * Raw credentials and secrets stay HERE  │     │  │ • Tenant Isol. │  │ • Recommendation│  │
│    and NEVER cross the network boundary.  │     │  └────────────────┘  └─────────────────┘  │
└───────────────────────────────────────────┘     └───────────────────────────┬───────────────┘
                                                                              │
                                                                              ▼
                                                                 ┌────────────────────────────┐
                                                                 │ Frontend Dashboard (SPA)   │
                                                                 │ • Vanilla JS + Chart.js    │
                                                                 │ • Live Authenticated APIs  │
                                                                 │ • Egress Proof Inspector   │
                                                                 │ • Recovery Simulator       │
                                                                 └────────────────────────────┘
```

---

## 🚀 Running AEGIS

### Automated One-Click Windows Startup (Recommended)
You can launch the complete AEGIS ecosystem (FastAPI Backend, Tier 1 Windows psutil Collector, and Frontend) in order with full health validation using the included PowerShell script:
```powershell
# In PowerShell:
.\start_aegis.ps1
```
To stop all AEGIS services gracefully:
```powershell
.\stop_aegis.ps1
```

---

### Manual Step-by-Step Startup

#### 1. Start the Tier 2 Central SaaS Backend
```bash
# In project root:
python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
```
- API Documentation (Swagger): `http://localhost:8000/docs` or `http://127.0.0.1:8000/docs`
- Health check: `http://localhost:8000/health` (Performs genuine `SELECT 1` database verification)

#### 2. Start the Frontend Dashboard
```bash
# Serve frontend on port 3000:
python -m http.server 3000 --directory frontend
# Open http://localhost:3000 or http://127.0.0.1:3000 in your browser
```
Default credentials: `admin@aegis.io` / `aegis2026`

#### 3. Run the Tier 1 Local Collector (Real Windows Hardware Monitoring)
```bash
# Run continuous collector daemon (5s telemetry, 15s heartbeat):
python -u -m collector.main

# Or run a single manual collection & transmission cycle:
python collector/run_once.py
```

#### 4. Run the Full Automated Test Suite (38 Tests)
```bash
python -m pytest tests -v
```

---

## 🏆 Key Product Differentiators

1. **Privacy Passport**: Strict field allow-listing drops unknown fields by default. Sensitive logs, passwords, and private tokens are redacted before metadata generation.
2. **Exact Egress Proof**: SHA-256 cryptographic hash generated for every transmitted payload. Independent server verification guarantees complete data integrity.
3. **Incident DNA**: Correlates multi-metric anomalies (CPU spikes, latency surges, database errors) into unified incidents, reducing duplicate notification noise.
4. **Explainable AIOps**: Dual detection engine combining rolling robust Z-scores (Median Absolute Deviation) with Scikit-Learn Isolation Forest. Every alert shows baseline comparisons, deviation sigmas, and evidence trails.
5. **Recovery Simulator**: Human-approved remediation workflow with policy enforcement, safe sandbox simulation, audit logging, and automated rollback snapshots.
6. **Outage Resilience**: Tier 1 buffers approved metadata locally in SQLite during SaaS network outages, automatically draining the queue upon reconnection with zero duplicate records.

---

## 📋 Evaluation Checklist Status

All 8 mandatory evaluation scenarios and requirements have been implemented and verified with automated test assertions:
- `tests/test_privacy_and_egress.py`
- `tests/test_aiops_and_incidents.py`
- `tests/test_buffering_and_idempotency.py`
- `tests/test_live_scenarios.py`

*AEGIS — Monitor intelligently. Protect sensitive data. Resolve incidents faster.*
