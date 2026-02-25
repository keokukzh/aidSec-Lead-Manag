# AidSec Dashboard — Scale & UX Redesign Plan

**Date:** 2026-02-20
**Goals:** Team deployment (2-5 users), mobile-friendly UI, clean API architecture
**Constraints:** Zero budget, self-hosted, keep SQLite, no Docker required

---

## Summary

Refactor the AidSec Lead Management Dashboard to support multi-user team access and mobile usage. The core change is extracting a FastAPI REST API from the existing services layer, adding mobile-responsive CSS, and creating a simple deployment workflow.

## Chosen Approach

**FastAPI Backend + Streamlit Frontend + SQLite (WAL mode)**

- FastAPI wraps existing services as a REST API (port 8000)
- Streamlit views call the API instead of the database directly
- SQLite stays, with WAL mode enabled for concurrent access (2-5 users)
- Mobile-responsive CSS via media queries
- Shared password authentication
- Startup script for single-command launch

## Architecture

```
┌─────────────────────────────────┐
│  Streamlit Frontend (UI only)   │  Port 8501
│  - Views call API via HTTP      │
│  - Mobile-responsive CSS        │
│  - Shared password auth         │
└──────────┬──────────────────────┘
           │ HTTP (REST)
┌──────────▼──────────────────────┐
│  FastAPI Backend                │  Port 8000
│  - REST endpoints               │
│  - Business logic (services)    │
│  - Background tasks (bulk ops)  │
│  - API key middleware           │
└──────────┬──────────────────────┘
           │ SQLAlchemy
┌──────────▼──────────────────────┐
│  SQLite (WAL mode)              │  data/leads.db
│  - Write-Ahead Logging          │
│  - 30s busy timeout             │
│  - Indexed columns              │
└─────────────────────────────────┘
```

## Components

### 1. FastAPI Backend (`api/`)

New directory structure:

```
api/
├── main.py              # FastAPI app, CORS, startup, API key middleware
├── routes/
│   ├── leads.py         # CRUD, search, filter, bulk status updates
│   ├── emails.py        # Send single/bulk, templates, history
│   ├── campaigns.py     # Campaign CRUD, step advancement
│   ├── ranking.py       # Single + batch ranking checks
│   ├── agents.py        # LLM agents (search, outreach, research)
│   ├── dashboard.py     # KPI aggregations, chart data
│   ├── followups.py     # Follow-up CRUD
│   ├── settings.py      # App settings, SMTP/LLM config
│   ├── import_export.py # Excel/CSV import, export
│   └── marketing.py     # Marketing ideas, tracker
├── schemas/
│   ├── lead.py          # Pydantic request/response models
│   ├── email.py
│   ├── campaign.py
│   └── ...
└── dependencies.py      # DB session dependency, API key validation
```

Key API endpoints:

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | /api/leads | List with filters, pagination, sorting |
| GET | /api/leads/{id} | Full detail with history |
| POST | /api/leads | Create lead |
| PATCH | /api/leads/{id} | Update fields/status |
| DELETE | /api/leads/{id} | Delete lead |
| POST | /api/leads/bulk-status | Bulk status update |
| POST | /api/emails/send | Send single email |
| POST | /api/emails/bulk | Start bulk send (background task) |
| GET | /api/emails/history/{lead_id} | Email history for lead |
| POST | /api/ranking/check | Check single URL |
| POST | /api/ranking/batch | Batch check (background task) |
| GET | /api/ranking/batch/{job_id} | Poll batch progress |
| POST | /api/agents/search | LLM lead search |
| POST | /api/agents/outreach | Generate outreach email |
| POST | /api/agents/research | Auto-research lead |
| GET | /api/dashboard/kpis | Dashboard metrics |
| GET | /api/dashboard/funnel | Conversion funnel data |
| GET | /api/campaigns | List campaigns |
| POST | /api/campaigns | Create campaign |
| GET | /api/followups | List follow-ups (with due filter) |
| POST | /api/followups | Create follow-up |
| GET | /api/settings/{key} | Get setting |
| PUT | /api/settings/{key} | Update setting |
| POST | /api/import/excel | Import from Excel |
| GET | /api/export/{format} | Export to CSV/Excel |
| GET | /api/marketing/ideas | List/filter marketing ideas |
| POST | /api/marketing/tracker | Add idea to tracker |

Background tasks (non-blocking):
- Bulk email sending → returns job ID, poll for progress
- Batch ranking checks → returns job ID, poll for progress
- Auto-research → runs in background, updates lead record

### 2. Database Changes (`database/`)

**database.py changes:**
- Enable WAL mode: `PRAGMA journal_mode=WAL`
- Set busy timeout: `PRAGMA busy_timeout=30000`
- Configure connection pooling for concurrent access

**models.py changes:**
- `wordpress_detected`: `String(10)` → `Boolean`
- Add indexes: `status`, `kategorie`, `email`, `website`, `created_at`
- No schema-breaking changes — existing data is preserved

### 3. Streamlit API Client (`api_client.py`)

Thin HTTP wrapper used by all views:

```python
API_BASE = os.getenv("API_URL", "http://localhost:8000")
API_KEY = os.getenv("API_KEY", "")

def api_get(endpoint, params=None):
    r = requests.get(f"{API_BASE}/api/{endpoint}",
                     params=params,
                     headers={"X-API-Key": API_KEY})
    r.raise_for_status()
    return r.json()

def api_post(endpoint, data=None, files=None):
    r = requests.post(f"{API_BASE}/api/{endpoint}",
                      json=data, files=files,
                      headers={"X-API-Key": API_KEY})
    r.raise_for_status()
    return r.json()
```

### 4. Streamlit View Refactoring

Each view removes direct database/service imports and calls the API client instead.

Pattern:
- `get_session()` → `api_get()` / `api_post()`
- `session.query(Lead)...` → `api_get("leads", params={...})`
- `service.send_email()` → `api_post("emails/send", {...})`

Views affected (all 8):
- dashboard.py, leads.py, lead_detail.py, email.py
- agenten.py, kampagnen.py, ranking.py, einstellungen.py
- import_leads.py, marketing_ideen.py

### 5. Authentication

**Streamlit level:**
- Shared password check on first load
- Password stored in `.env` as `APP_PASSWORD`
- Session state flag prevents re-auth

**API level:**
- API key middleware validates `X-API-Key` header
- Key stored in `.env` as `API_KEY`
- Auto-generated on first run if not set

### 6. Mobile Responsive CSS

Injected via `st.markdown()` in `app.py`:

**Breakpoints:**
- Desktop: > 768px (current layout)
- Mobile: ≤ 768px (stacked, simplified)

**Key mobile adaptations:**
- Sidebar: auto-collapsed, hamburger menu
- Columns: stack vertically via `flex-direction: column`
- Pipeline: single scrollable column
- Touch targets: minimum 44px height
- Tables: horizontal scroll with sticky first column
- Font: slightly larger base size

### 7. Deployment

**Startup script (`start.bat` / `start.sh`):**
```bash
# Start FastAPI in background
python -m uvicorn api.main:app --host 0.0.0.0 --port 8000 &

# Start Streamlit
python -m streamlit run app.py --server.address 0.0.0.0 --server.port 8501
```

**Team access:**
- Same network: `http://<server-ip>:8501`
- Remote: Tailscale (free VPN) or Cloudflare Tunnel

## Implementation Order

### Phase 1: Foundation (Days 1-2)
1. Database changes (WAL mode, indexes, wordpress_detected fix)
2. FastAPI app skeleton (`api/main.py`, dependencies, middleware)
3. Pydantic schemas for Lead, Email, Campaign
4. Core API routes: leads CRUD, dashboard KPIs

### Phase 2: API Routes (Days 3-5)
5. Email routes (send, bulk, history)
6. Ranking routes (single, batch with background tasks)
7. Agent routes (search, outreach, research)
8. Campaign routes (CRUD, step advancement)
9. Follow-up, settings, import/export, marketing routes

### Phase 3: Frontend Refactoring (Days 6-8) ✅ DONE
10. ✅ Created `api_client.py` — thin HTTP wrapper with convenience methods for all endpoints
11. ✅ Refactored dashboard.py + leads.py — all data via API
12. ✅ Refactored lead_detail.py + email.py — including new timeline, custom-templates, global-history API endpoints
13. ✅ Refactored remaining views (agenten, kampagnen, ranking, einstellungen, import, marketing)
    - kampagnen: campaign sending loop stays direct DB for progress-bar support; all reads use API
    - import: bulk import stays direct DB for performance; single lead creation via API
    - All other views fully API-driven

### Phase 4: Auth + Mobile + Deploy (Days 9-10) ✅ DONE
14. ✅ Shared password auth — `APP_PASSWORD` in `.env`, login gate in `app.py`, logout button in sidebar
15. ✅ API key middleware — already wired in Phase 1, `API_KEY` added to `.env`
16. ✅ Mobile responsive CSS — breakpoints at ≤768px (mobile) and 769–1024px (tablet), stacked columns, 44px touch targets, scrollable tabs/dataframes
17. ✅ Startup scripts — `start.bat` (Windows) and `start.sh` (Linux/macOS) with team-IP hints
18. ✅ README rewritten — architecture diagram, setup guide, team access, API endpoint table, project structure

## Open Questions

- Should we add WebSocket support for real-time progress updates (bulk ops)?
- Do you want email open/click tracking in a future phase?
- Should the marketing ideas catalog move to the database for easier updates?
- Is there a need for data backup automation?
