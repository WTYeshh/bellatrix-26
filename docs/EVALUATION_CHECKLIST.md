# AEGIS — Evaluation Checklist Tracker

> Updated: 2026-11-20T19:12:00Z

## Scoring Summary

| Phase | Description | Max Marks | Status |
|-------|-------------|-----------|--------|
| **Phase 1** | Problem Understanding & Ideation | 10 | IN PROGRESS |
| **Phase 2** | Architecture & Technical Design | 25 | IN PROGRESS |
| **Phase 3** | Implementation & Working Prototype | 35 | IN PROGRESS |
| **Phase 4** | Final Demo, Validation & Presentation | 30 | NOT STARTED |

---

## PHASE 1 — Problem Understanding & Ideation (10 marks)

| # | Requirement | Status | Evidence |
|---|------------|--------|----------|
| 1.1 | Clear problem statement — privacy-first observability | ✅ IMPLEMENTED | README.md, architecture diagram |
| 1.2 | Two-tier architecture identified | ✅ IMPLEMENTED | Tier 1 (Collector) + Tier 2 (SaaS) separated |
| 1.3 | Privacy as core differentiator | ✅ IMPLEMENTED | Privacy Passport & Egress Proof modules |
| 1.4 | AIOps value proposition | ✅ IMPLEMENTED | Observe → Detect → Correlate → Recommend pipeline |
| 1.5 | Target users and roles defined | ✅ IMPLEMENTED | 5 roles: Owner, IT Admin, Security Eng, DevOps, IT Mgr |

## PHASE 2 — Architecture & Technical Design (25 marks)

| # | Requirement | Status | Evidence |
|---|------------|--------|----------|
| 2.1 | Two-tier security boundary | ✅ IMPLEMENTED | Separate frontend/backend/collector directories |
| 2.2 | Technology stack compliance | ✅ IMPLEMENTED | HTML/CSS/JS, FastAPI, psutil, SQLite, PostgreSQL |
| 2.3 | Privacy pipeline design | IN PROGRESS | Collect→Filter→Redact→Normalize→Aggregate→Analyse→Policy→Proof→Transmit |
| 2.4 | Field allow-list strategy | IN PROGRESS | Defined in spec, implementation in Milestone 4 |
| 2.5 | Tenant isolation model | IN PROGRESS | Planned for Milestone 6 |
| 2.6 | Health state model (4 states) | ✅ IMPLEMENTED | Excellent/Good/Fair/Poor in UI |
| 2.7 | AIOps roadmap | IN PROGRESS | Observe/Detect/Correlate/Recommend/Act defined |
| 2.8 | Secure communication design | IN PROGRESS | Token auth, HTTPS notes, idempotency planned |
| 2.9 | Database model design | NOT STARTED | Milestone 6 |
| 2.10 | API architecture | NOT STARTED | Milestone 6 |

## PHASE 3 — Implementation & Working Prototype (35 marks)

### Frontend (Milestones 1-2)

| # | Requirement | Status | Evidence |
|---|------------|--------|----------|
| 3.1 | Login and authentication UI | ✅ IMPLEMENTED | Login form, demo auth, session management |
| 3.2 | Organization registration | ✅ IMPLEMENTED | Registration modal with form validation |
| 3.3 | Command Center dashboard | ✅ IMPLEMENTED | Health banner, stat cards, charts, activity lists |
| 3.4 | Infrastructure monitoring page | ✅ IMPLEMENTED | Server table layout, stat cards |
| 3.5 | Network monitoring page | ✅ IMPLEMENTED | Latency, packet loss, bandwidth cards |
| 3.6 | Security monitoring page | ✅ IMPLEMENTED | Security alerts table |
| 3.7 | Collector management page | ✅ IMPLEMENTED | Collector table with status fields |
| 3.8 | Incident DNA page | ✅ IMPLEMENTED | Incident list, correlation display |
| 3.9 | AI Insights page | ✅ IMPLEMENTED | AIOps pipeline status, anomaly list |
| 3.10 | Privacy Passport page | ✅ IMPLEMENTED | Policy management layout |
| 3.11 | Egress Proof page | ✅ IMPLEMENTED | Transmission log table |
| 3.12 | Audit Center page | ✅ IMPLEMENTED | Audit log table |
| 3.13 | Recovery Simulator page | ✅ IMPLEMENTED | Workflow steps display |
| 3.14 | Organization Settings page | ✅ IMPLEMENTED | Profile, data residency, user management |
| 3.15 | Responsive design | ✅ IMPLEMENTED | Mobile breakpoints in CSS |
| 3.16 | Design system consistency | ✅ IMPLEMENTED | CSS variables, component classes |
| 3.17 | Simulated data clearly labelled | ✅ IMPLEMENTED | Yellow sim-banner in UI |

### Tier 1 Collector (Milestones 3-5)

| # | Requirement | Status | Evidence |
|---|------------|--------|----------|
| 3.18 | psutil real metrics collection | NOT STARTED | Milestone 3 |
| 3.19 | Privacy engine — secret detection | NOT STARTED | Milestone 4 |
| 3.20 | Privacy engine — field allow-list | NOT STARTED | Milestone 4 |
| 3.21 | Privacy engine — redaction | NOT STARTED | Milestone 4 |
| 3.22 | Privacy engine — pseudonymization | NOT STARTED | Milestone 4 |
| 3.23 | Egress proof generation | NOT STARTED | Milestone 4 |
| 3.24 | SQLite local storage | NOT STARTED | Milestone 3 |
| 3.25 | Local buffering during outages | NOT STARTED | Milestone 5 |
| 3.26 | Retry with backoff | NOT STARTED | Milestone 5 |
| 3.27 | Idempotent delivery | NOT STARTED | Milestone 5 |
| 3.28 | Collector heartbeat | NOT STARTED | Milestone 5 |

### Tier 2 Backend (Milestones 6-8)

| # | Requirement | Status | Evidence |
|---|------------|--------|----------|
| 3.29 | FastAPI application | NOT STARTED | Milestone 6 |
| 3.30 | PostgreSQL database | NOT STARTED | Milestone 6 |
| 3.31 | Authentication API | NOT STARTED | Milestone 6 |
| 3.32 | Tenant isolation | NOT STARTED | Milestone 6 |
| 3.33 | Metadata ingestion API | NOT STARTED | Milestone 6 |
| 3.34 | Backend payload validation | NOT STARTED | Milestone 6 |
| 3.35 | AIOps anomaly detection | NOT STARTED | Milestone 8 |
| 3.36 | AIOps correlation engine | NOT STARTED | Milestone 8 |
| 3.37 | AIOps recommendations | NOT STARTED | Milestone 8 |
| 3.38 | Incident management | NOT STARTED | Milestone 8 |

## PHASE 4 — Final Demo, Validation & Presentation (30 marks)

### Live Validation Tests

| # | Test | Status | Evidence |
|---|------|--------|----------|
| 4.1 | TEST 1 — Raw log contains secret | NOT STARTED | Milestone 9 |
| 4.2 | TEST 2 — Collector loses connectivity | NOT STARTED | Milestone 9 |
| 4.3 | TEST 3 — Repeated failed logins | NOT STARTED | Milestone 9 |
| 4.4 | TEST 4 — Network latency spike | NOT STARTED | Milestone 9 |
| 4.5 | TEST 5 — CPU/Memory anomaly | NOT STARTED | Milestone 9 |
| 4.6 | TEST 6 — Multiple related alerts | NOT STARTED | Milestone 9 |
| 4.7 | TEST 7 — Duplicate/out-of-order events | NOT STARTED | Milestone 9 |
| 4.8 | TEST 8 — Remediation proposed | NOT STARTED | Milestone 9 |

### Performance Targets

| # | Target | Status | Measured |
|---|--------|--------|----------|
| 4.9 | Collection-to-dashboard ≤10s P95 | NOT STARTED | — |
| 4.10 | Breach-to-alert ≤15s | NOT STARTED | — |
| 4.11 | Offline detection ≤60s | NOT STARTED | — |
| 4.12 | Zero lost/duplicated records | NOT STARTED | — |

### Bonus Features

| # | Feature | Status |
|---|---------|--------|
| B.1 | Privacy pipeline | IN PROGRESS |
| B.2 | Local buffering | NOT STARTED |
| B.3 | Explainable AIOps | NOT STARTED |
| B.4 | Alert-noise reduction | NOT STARTED |
| B.5 | Global-ready delivery | IN PROGRESS |

---

## Notes

- Only mark TESTED after a successful test with evidence
- Only mark DEMONSTRATED LIVE after verifying in running application
- Simulated data is clearly labelled in the UI
- Backend auth replaces demo credentials when connected
