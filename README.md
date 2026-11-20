# AEGIS — Privacy-First AIOps Observability Platform

> **Observe. Detect. Correlate. Recommend.**

AEGIS is an enterprise-grade, privacy-first AIOps observability SaaS platform that monitors distributed infrastructure while keeping sensitive data inside customer environments.

## Architecture Overview

```
┌─────────────────────────────────┐     ┌─────────────────────────────────┐
│   TIER 1 — Customer Env         │     │   TIER 2 — Central AEGIS SaaS   │
│                                 │     │                                 │
│  ┌─────────┐  ┌──────────────┐  │     │  ┌──────────┐  ┌────────────┐  │
│  │ Collect  │→ │ Privacy      │  │     │  │ Ingest   │→ │ AIOps      │  │
│  │ (psutil) │  │ Engine       │  │     │  │ Validate │  │ Engine     │  │
│  └─────────┘  │ • Redact     │──┼────→│  └──────────┘  │ • Detect   │  │
│               │ • Allow-list │  │     │                 │ • Correlate│  │
│  ┌─────────┐  │ • Pseudonym  │  │     │  ┌──────────┐  │ • Recommend│  │
│  │ SQLite   │  │ • Egress    │  │     │  │PostgreSQL│  └────────────┘  │
│  │ Local DB │  │   Proof     │  │     │  │ Tenant   │                  │
│  └─────────┘  └──────────────┘  │     │  │ Isolated │  ┌────────────┐  │
│                                 │     │  └──────────┘  │ Dashboard  │  │
│  Raw data stays HERE            │     │                │ Frontend   │  │
└─────────────────────────────────┘     └────────────────┴────────────┘
```

## Technology Stack

| Layer | Technology |
|-------|-----------|
| Frontend | HTML5, CSS3, Vanilla JS ES6+, Chart.js |
| Backend (Tier 2) | Python, FastAPI, PostgreSQL |
| Collector (Tier 1) | Python, psutil, SQLite |
| AIOps | Scikit-learn, Statistical Baselines |

## Quick Start

### Frontend (Milestone 1 — ✅ Complete)
```bash
cd frontend
# Open index.html in a browser, or use a local server:
python -m http.server 3000
# Visit http://localhost:3000
```

Demo credentials: `admin@aegis.io` / `aegis2026`

### Backend (Milestone 6 — Upcoming)
```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### Collector (Milestone 3 — Upcoming)
```bash
cd collector
pip install -r requirements.txt
python main.py
```

## Project Structure

```
AEGIS/
├── frontend/           # Tier 2 UI — HTML/CSS/JS SPA
│   ├── index.html      # Main entry point
│   ├── css/            # Design system, layout, page styles
│   ├── js/
│   │   ├── utils/      # API client, router, icons, toast
│   │   └── components/ # Auth, Command Center, page modules
│   └── assets/
├── backend/            # Tier 2 — FastAPI + PostgreSQL
│   └── app/
├── collector/          # Tier 1 — Local Python collector
├── database/           # Migrations and schemas
├── tests/              # Automated tests
├── docs/               # Architecture, checklists
└── README.md
```

## Milestone Tracker

| # | Milestone | Status |
|---|-----------|--------|
| 1 | Frontend foundation, login, design system | ✅ IMPLEMENTED |
| 2 | Complete navigation & Command Center | ✅ IMPLEMENTED |
| 3 | Tier 1 Python collector | 🔲 NOT STARTED |
| 4 | Privacy engine & egress proof | 🔲 NOT STARTED |
| 5 | Tier 1→Tier 2 secure transmission | 🔲 NOT STARTED |
| 6 | Tier 2 FastAPI backend + PostgreSQL | 🔲 NOT STARTED |
| 7 | Dashboard ↔ backend API integration | 🔲 NOT STARTED |
| 8 | AIOps detection & correlation | 🔲 NOT STARTED |
| 9 | Recovery simulation & audit | 🔲 NOT STARTED |
| 10 | Full validation & demo prep | 🔲 NOT STARTED |

## Health States

| State | Meaning |
|-------|---------|
| **EXCELLENT** | Healthy — all metrics within normal ranges |
| **GOOD** | Normal with minor deviations |
| **FAIR** | Needs attention — approaching thresholds |
| **POOR** | Critical degradation or collector offline |

## Security Boundaries

- **Tier 1 retains** all raw telemetry, secrets, and sensitive data locally
- **Tier 2 receives** only approved metadata via field allow-listing
- Egress proof records verify exactly what was transmitted
- Backend independently validates all incoming payloads
- Tenant isolation enforced on every query

## Team

Built for a 24-hour company-sponsored hackathon.

---
*AEGIS — Monitor intelligently. Protect sensitive data. Resolve incidents faster.*
