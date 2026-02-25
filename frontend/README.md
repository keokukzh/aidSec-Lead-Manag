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
