# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This repository contains:
1. **`aidsec_dashboard/`** - A lead management dashboard for AidSec (security company)
2. **`python_scripts/`** - Legacy scripts for processing and enriching lead data from Excel
3. **`praxen_leads_bereinigt.xlsx`** - Source data file with leads

## AidSec Dashboard Architecture

```
Streamlit Frontend (Port 8501) ←→ FastAPI Backend (Port 8000) ←→ SQLite (WAL mode)
```

- **Frontend**: Streamlit UI that communicates via REST API
- **Backend**: FastAPI with REST endpoints for all operations
- **Database**: SQLite with Write-Ahead Logging (WAL) for concurrent access
- **Authentication**: Shared password (APP_PASSWORD) + API key (API_KEY)

## Commands

### Setup
```bash
cd aidsec_dashboard
pip install -r requirements.txt
```

### Running the Application
```bash
# Option 1: Use startup scripts
start.bat          # Windows
./start.sh         # Linux/macOS

# Option 2: Manual startup
# Terminal 1: API
python -m uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
# Terminal 2: UI
python -m streamlit run app.py --server.address 0.0.0.0 --server.port 8501
```

### Access Points
- Dashboard: http://localhost:8501
- API Docs: http://localhost:8000/api/docs
- Health Check: http://localhost:8000/api/health

## Key Directories

| Directory | Purpose |
|-----------|---------|
| `aidsec_dashboard/api/` | FastAPI routes and schemas |
| `aidsec_dashboard/database/` | SQLAlchemy models and connection |
| `aidsec_dashboard/services/` | Business logic (email, ranking, LLM) |
| `aidsec_dashboard/views/` | Streamlit page components |
| `aidsec_dashboard/utils/` | Import/export utilities |
| `aidsec_dashboard/data/` | SQLite database (leads.db) |

## Lead Categories

| Category | Target | Product |
|----------|--------|---------|
| Anwalt | Law firms | Kanzlei-Härtung (CHF 950) |
| Praxis | Medical practices | Rapid Header Fix (CHF 490) |
| WordPress | WordPress users | Rapid Header Fix (CHF 490) |

## Email Outreach Sequence

1. **Stufe 1** (Day 1): Curiosity - short email with security issue, no price
2. **Stufe 2** (Day 3-4): Value - concrete tip, show expertise
3. **Stufe 3** (Day 7): Offer - introduce product + price
4. **Stufe 4** (Day 14): Final attempt - respectful follow-up

## Configuration

Environment variables in `aidsec_dashboard/.env`:
- `APP_PASSWORD` - Dashboard login password
- `API_KEY` - API authentication key
- `SMTP_*` - Email server settings (Brevo recommended)
- `DEFAULT_PROVIDER` - LLM provider (lm_studio or openai_compatible)
- `OPENAI_BASE_URL` / `OPENAI_API_KEY` - LLM endpoint and key
- `OPENAI_MODEL` - Model name (e.g., MiniMax-M2.5)

## Important Models

- **Lead**: Main entity with status (offen/pending/gewonnen/verloren), category, ranking data
- **Campaign**: Multi-step outreach sequences
- **FollowUp**: Scheduled tasks linked to leads
- **EmailHistory**: Track sent emails per lead
- **MarketingIdeaTracker**: Marketing ideas workflow

## Cursor Settings

The `.cursor/settings.json` enables the superpowers plugin.
