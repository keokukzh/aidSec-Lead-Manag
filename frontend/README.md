# AidSec Dashboard - Next.js Version

Modernes Lead Management Dashboard mit Next.js + React Frontend.

## Quick Start

### 1. Backend starten
```bash
cd aidsec_dashboard
python -m uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```

### 2. Frontend starten
```bash
cd frontend
npm run dev
```

### 3. Öffnen
- **Dashboard:** http://localhost:3000
- **API Docs:** http://localhost:8000/api/docs

## Features

- Dashboard mit KPIs
- Lead-Verwaltung (CRUD)
- Kampagnen
- Ranking
- E-Mail-Generator
- Import/Export
- Outlook-Integration
- Marketing Ideen
- Einstellungen

## Architektur

```
Frontend (Next.js)  -->  Backend (FastAPI)  -->  SQLite
     Port 3000              Port 8000            leads.db
```

## Passwort

Das Dashboard ist mit einem Passwort geschützt. Das Passwort wird in der `.env` Datei unter `APP_PASSWORD` konfiguriert.

## Entwicklung

```bash
# Frontend Development
cd frontend
npm run dev    # Development Server
npm run build  # Production Build
npm run start  # Production Server

# Backend Development
cd aidsec_dashboard
python -m uvicorn api.main:app --reload
```

## Technologien

- **Frontend:** Next.js 14, React, TypeScript, Tailwind CSS, Zustand, TanStack Query
- **Backend:** FastAPI, SQLAlchemy, SQLite
- **Auth:** Session-basiert mit Passwort

## Deployment (Vercel)

### 1) Frontend auf Vercel deployen

1. Repository in Vercel importieren
2. Root Directory auf `frontend` setzen
3. Build-Settings automatisch übernehmen (`vercel.json`)
4. Environment Variable in Vercel setzen:

```env
NEXT_PUBLIC_API_URL=https://<YOUR-BACKEND-DOMAIN>/api
```

### 2) Backend separat deployen

Das FastAPI Backend muss als eigener Service laufen (z. B. Railway/Render/Fly/VM), weil Vercel hier nur das Next.js Frontend hostet.

Backend-Umgebungsvariablen mindestens:

```env
API_KEY=<global_api_key>
APP_PASSWORD=<dashboard_password>
DATABASE_URL=postgresql+psycopg://<user>:<pass>@<host>:5432/<db>
CORS_ORIGINS=https://<YOUR-VERCEL-DOMAIN>
AGENT_API_KEYS=agent1=<secret1>,agent2=<secret2>
```

### 3) Zugriff von unterwegs

Sobald Frontend (Vercel) und Backend (Cloud-Service) online sind, ist das Dashboard weltweit unter deiner Vercel-Domain erreichbar.
