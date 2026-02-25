# AidSec Lead Management Dashboard

Ein vollständiges Lead-Management-Dashboard für AidSec mit FastAPI-Backend und Streamlit-Frontend, optimiert für Team-Nutzung (2–5 Personen) und mobilen Zugriff.

## Architektur

```
┌──────────────────────────────────┐
│  Streamlit Frontend  (Port 8501) │
│  - Mobile-responsive UI          │
│  - Shared password auth          │
│  - Alle Daten via REST API       │
└──────────┬───────────────────────┘
           │ HTTP (REST)
┌──────────▼───────────────────────┐
│  FastAPI Backend   (Port 8000)   │
│  - REST-Endpoints + Swagger-Docs │
│  - Business Logic (Services)     │
│  - Background Tasks (Bulk Ops)   │
│  - API-Key Middleware            │
└──────────┬───────────────────────┘
           │ SQLAlchemy
┌──────────▼───────────────────────┐
│  SQLite (WAL mode)               │
│  - Write-Ahead Logging           │
│  - 30s Busy Timeout              │
│  - Indexierte Spalten            │
└──────────────────────────────────┘
```

## Features

- **Lead-Verwaltung**: Leads nach Status (Offen, Pending, Gewonnen, Verloren) verwalten mit Pagination, Sortierung und Bulk-Aktionen
- **360-Grad Lead-Ansicht**: Komplettes Lead-Profil mit Übersicht, Kontakt-Timeline, E-Mail-Tab und Ranking-Tab
- **Follow-Up System**: Follow-ups planen, Dashboard-Widget für anstehende Aufgaben, Sidebar-Badge
- **Kampagnen**: Multi-Step Outreach-Kampagnen mit Lead-Zuweisung und Fortschritts-Tracking
- **Excel/CSV Import**: Bestehende Leads aus Excel importieren mit Vorschau und Validierung
- **Ranking-Checks**: HTTP-Header-Prüfung (Einzel + Batch), Abbruch-Option, Fehlerberichte
- **LLM-Agenten**: Lead Search, Outreach Helper, Auto-Research Agent
- **E-Mail-Versand**: 4-Stufen-Outreach-Sequenz, KI-Generierung, Bulk-Versand, Custom Templates
- **Marketing-Ideen**: 140+ Ideen mit Tracking, KI-Empfehlungen
- **Dashboard**: KPIs, Wochen-Deltas, Conversion-Funnel, Ranking-Verteilung
- **Mobile-optimiert**: Responsive CSS für Smartphone- und Tablet-Zugriff
- **Team-Zugriff**: Shared Password Auth, API-Key-Schutz

## Schnellstart

### 1. Abhängigkeiten installieren

```bash
cd aidsec_dashboard
pip install -r requirements.txt
```

### 2. .env konfigurieren

Die `.env`-Datei enthält alle Einstellungen. Mindestens SMTP und LLM sollten konfiguriert werden:

```env
# ── Team Auth ─────────────────────────────────────────
# Team-Passwort (leer = kein Login erforderlich)
APP_PASSWORD=mein-sicheres-passwort
# API-Key (leer = kein API-Schutz)
API_KEY=

# ── SMTP (E-Mail) ────────────────────────────────────
SMTP_HOST=smtp-relay.brevo.com
SMTP_PORT=587
SMTP_USERNAME=your-login@email.com
SMTP_PASSWORD=your-smtp-key
SMTP_FROM_NAME=AidSec
SMTP_FROM_EMAIL=aid.destani@aidsec.ch

# ── LLM (KI-Agenten) ─────────────────────────────────
DEFAULT_PROVIDER=openai_compatible
OPENAI_BASE_URL=https://api.minimax.io/v1
OPENAI_API_KEY=sk-...
OPENAI_MODEL=MiniMax-M2.5
```

### 3. Starten

**Windows:**

```
start.bat
```

**Linux / macOS:**

```bash
chmod +x start.sh
./start.sh
```

**Manuell:**

```bash
# Terminal 1: API starten
python -m uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload

# Terminal 2: UI starten
python -m streamlit run app.py --server.address 0.0.0.0 --server.port 8501
```

### 4. Zugriff

| Was          | URL                              |
| ------------ | -------------------------------- |
| Dashboard    | http://localhost:8501            |
| API Docs     | http://localhost:8000/api/docs   |
| Health Check | http://localhost:8000/api/health |

## Team-Zugriff (2–5 Personen)

Alle Teammitglieder im selben Netzwerk können auf das Dashboard zugreifen:

1. **IP herausfinden** (auf dem Server-Rechner):
   - Windows: `ipconfig` → IPv4-Adresse
   - Linux/Mac: `hostname -I` oder `ifconfig`

2. **Im Browser öffnen**: `http://<SERVER-IP>:8501`

3. **Passwort eingeben** (wenn `APP_PASSWORD` gesetzt ist)

Für Remote-Zugriff (außerhalb des Netzwerks):

- **Tailscale** (kostenlos): Installieren auf Server + Client → Dashboard über Tailscale-IP erreichbar
- **Cloudflare Tunnel** (kostenlos): `cloudflared tunnel` einrichten → HTTPS-Zugriff weltweit

## API-Endpoints

| Methode  | Endpoint                      | Beschreibung                                     |
| -------- | ----------------------------- | ------------------------------------------------ |
| GET      | /api/leads                    | Leads auflisten (Filter, Pagination, Sortierung) |
| GET      | /api/leads/{id}               | Lead-Details                                     |
| GET      | /api/leads/{id}/timeline      | Lead-Timeline (Status, E-Mails, Follow-ups)      |
| POST     | /api/leads                    | Lead erstellen                                   |
| PATCH    | /api/leads/{id}               | Lead aktualisieren                               |
| DELETE   | /api/leads/{id}               | Lead löschen                                     |
| POST     | /api/leads/bulk-status        | Bulk-Statusänderung                              |
| POST     | /api/emails/send              | E-Mail senden                                    |
| GET      | /api/emails/history/{lead_id} | E-Mail-Verlauf pro Lead                          |
| GET      | /api/emails/history           | Globaler E-Mail-Verlauf                          |
| POST     | /api/emails/generate          | KI-generierte E-Mail                             |
| GET      | /api/emails/templates         | Default-Templates                                |
| GET/POST | /api/emails/custom-templates  | Custom Templates                                 |
| POST     | /api/ranking/check            | URL prüfen                                       |
| POST     | /api/ranking/batch            | Batch-Prüfung starten                            |
| POST     | /api/agents/search            | Lead-Suche per KI                                |
| POST     | /api/agents/outreach          | Outreach-E-Mail generieren                       |
| POST     | /api/agents/research/{id}     | Auto-Research                                    |
| GET      | /api/dashboard/kpis           | Dashboard-KPIs                                   |
| GET/POST | /api/campaigns                | Kampagnen verwalten                              |
| GET/POST | /api/followups                | Follow-ups verwalten                             |
| GET/PUT  | /api/settings/{key}           | Einstellungen                                    |
| POST     | /api/import/excel             | Excel-Import                                     |
| GET      | /api/export/csv               | CSV-Export                                       |
| GET      | /api/marketing/ideas          | Marketing-Ideen                                  |
| POST     | /api/marketing/recommend      | KI-Empfehlungen                                  |

Interaktive API-Dokumentation: http://localhost:8000/api/docs

## Projekt-Struktur

```
aidsec_dashboard/
├── app.py                  # Main App (Auth + Routing + Sidebar + CSS)
├── api_client.py           # HTTP-Client für Streamlit → FastAPI
├── start.bat / start.sh    # Ein-Klick Start
├── .env                    # Konfiguration (SMTP, LLM, Auth)
├── api/                    # FastAPI Backend
│   ├── main.py             # FastAPI App, CORS, Startup
│   ├── dependencies.py     # DB Session, API-Key Validation
│   ├── routes/             # REST-Endpoints
│   │   ├── leads.py        # Lead CRUD + Bulk + Timeline
│   │   ├── dashboard.py    # KPI-Aggregation
│   │   ├── emails.py       # E-Mail Senden/History/Templates
│   │   ├── ranking.py      # Security Header Checks
│   │   ├── agents.py       # LLM Agents
│   │   ├── campaigns.py    # Kampagnen CRUD
│   │   ├── followups.py    # Follow-up CRUD
│   │   ├── settings.py     # App-Einstellungen
│   │   ├── import_export.py# Import/Export
│   │   └── marketing.py    # Marketing-Ideen
│   └── schemas/            # Pydantic Models
│       ├── lead.py
│       ├── email.py
│       ├── campaign.py
│       ├── dashboard.py
│       └── common.py
├── database/               # Datenbank
│   ├── database.py         # Engine, Session, WAL mode
│   └── models.py           # SQLAlchemy Models
├── services/               # Business Logic
│   ├── llm_service.py      # Multi-Provider LLM
│   ├── email_service.py    # SMTP + Templates
│   └── ranking_service.py  # Security Header Checks
├── views/                  # Streamlit Seiten
│   ├── dashboard.py        # KPIs, Charts
│   ├── leads.py            # Pipeline + Liste
│   ├── lead_detail.py      # 360-Grad Profil
│   ├── email.py            # E-Mail Management
│   ├── kampagnen.py        # Kampagnen
│   ├── ranking.py          # Ranking Checks
│   ├── agenten.py          # LLM Agents
│   ├── import_leads.py     # Import
│   ├── marketing_ideen.py  # Marketing-Ideen
│   └── einstellungen.py    # Einstellungen
├── utils/                  # Import/Export Utilities
├── data/                   # SQLite DB (leads.db)
└── .streamlit/             # Streamlit Theme
```

## Konfiguration

### SMTP (E-Mail)

Empfohlen: Brevo (ehemals Sendinblue) für zuverlässigen Versand.

```env
SMTP_HOST=smtp-relay.brevo.com
SMTP_PORT=587
SMTP_USERNAME=your-brevo-login@email.com
SMTP_PASSWORD=your-smtp-key
SMTP_FROM_NAME=AidSec
SMTP_FROM_EMAIL=aid.destani@aidsec.ch
```

### LLM (KI-Agenten)

**LM Studio (lokal)**:

```env
LM_STUDIO_URL=http://localhost:1234/v1
DEFAULT_PROVIDER=lm_studio
```

**OpenAI-kompatibel** (MiniMax, OpenRouter, Groq, DeepSeek, etc.):

```env
DEFAULT_PROVIDER=openai_compatible
OPENAI_BASE_URL=https://api.minimax.io/v1
OPENAI_API_KEY=sk-...
OPENAI_MODEL=MiniMax-M2.5
```

## Lead-Kategorien

| Kategorie | Zielgruppe       | Empfohlenes Produkt          |
| --------- | ---------------- | ---------------------------- |
| Anwalt    | Anwaltskanzleien | Kanzlei-Härtung (CHF 950.–)  |
| Praxis    | Arztpraxen       | Rapid Header Fix (CHF 490.–) |
| WordPress | WordPress-Nutzer | Rapid Header Fix (CHF 490.–) |

## E-Mail Outreach Workflow

1. **Stufe 1 — Neugier** (Tag 1): Kurz, kein Preis, konkretes Sicherheitsproblem
2. **Stufe 2 — Mehrwert** (Tag 3-4): Konkreter Tipp, Expertise zeigen
3. **Stufe 3 — Angebot** (Tag 7): Produkt + Preis vorstellen
4. **Stufe 4 — Letzter Versuch** (Tag 14): Respektvolle letzte Nachfrage

Die Stufe wird automatisch vorgeschlagen basierend auf bereits gesendeten E-Mails.

## Lizenz

MIT
