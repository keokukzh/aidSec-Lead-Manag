# Vercel Production Deploy + OpenClaw Agent Access

## Ziel

- Dashboard dauerhaft online und von überall erreichbar
- Frontend auf Vercel
- Backend als Cloud-Service (FastAPI)
- Hetzner-Agenten arbeiten zuverlässig gegen die Queue

---

## Architektur (empfohlen)

- Frontend: Vercel (Next.js)
- Backend: Railway/Render/Fly/VM (FastAPI)
- Datenbank: PostgreSQL (über `DATABASE_URL`)

Warum so:
- Vercel hostet das Next.js Frontend sehr gut
- Backend bleibt als persistenter API-Service mit Worker/Queue erreichbar
- PostgreSQL ist robust für 24/7 Cloud-Betrieb

---

## 1) Frontend (Vercel)

1. Repo in Vercel importieren
2. Root Directory: `frontend`
3. Env setzen:

```env
NEXT_PUBLIC_API_URL=https://<BACKEND-DOMAIN>/api
```

4. Deploy starten

---

## 2) Backend (Cloud)

Backend `.env` (Produktiv):

```env
APP_PASSWORD=<secure_password>
API_KEY=<global_api_key>
AGENT_API_KEYS=agent1=<agent1_key>,agent2=<agent2_key>

DATABASE_URL=postgresql+psycopg://<user>:<pass>@<host>:5432/<db>
CORS_ORIGINS=https://<your-vercel-domain>

SMTP_HOST=...
SMTP_PORT=587
SMTP_USERNAME=...
SMTP_PASSWORD=...
SMTP_FROM_NAME=AidSec
SMTP_FROM_EMAIL=...
```

Start command:

```bash
python -m uvicorn api.main:app --host 0.0.0.0 --port 8000
```

Health check:

```bash
GET /api/health
```

---

## 3) Agent-Zugriff einrichten (Hetzner)

### Agent 1 (`100.88.218.9`)

```env
AIDSEC_API_BASE_URL=https://<BACKEND-DOMAIN>/api
AIDSEC_GLOBAL_API_KEY=<global_api_key>
AIDSEC_AGENT_ID=agent1
AIDSEC_AGENT_API_KEY=<agent1_key>
AIDSEC_LEASE_SECONDS=300
AIDSEC_HEARTBEAT_INTERVAL_SECONDS=60
AIDSEC_POLL_INTERVAL_SECONDS=10
```

Start:

```bash
python scripts/agent_runner.py
```

### Agent 2 (`100.87.63.92`)

```env
AIDSEC_API_BASE_URL=https://<BACKEND-DOMAIN>/api
AIDSEC_GLOBAL_API_KEY=<global_api_key>
AIDSEC_AGENT_ID=agent2
AIDSEC_AGENT_API_KEY=<agent2_key>
AIDSEC_LEASE_SECONDS=300
AIDSEC_HEARTBEAT_INTERVAL_SECONDS=60
AIDSEC_POLL_INTERVAL_SECONDS=10
```

Start:

```bash
python scripts/agent_runner.py
```

---

## 4) Optional: weiterhin Tailscale nutzen

Wenn du Backend nicht öffentlich machen willst, kann Backend auf Tailscale bleiben.
Dann müssen Frontend-Zugriff und Agenten über deine Tailnet-Strategie gelöst werden (z. B. Exit/relay/proxy). Für "weltweit direkt erreichbar" ist öffentliches Backend-Domain-Setup normalerweise einfacher.

---

## 5) Go-Live Checklist

- [ ] `NEXT_PUBLIC_API_URL` korrekt gesetzt
- [ ] Backend `DATABASE_URL` auf PostgreSQL
- [ ] `CORS_ORIGINS` enthält Vercel-Domain
- [ ] `API_KEY` und `AGENT_API_KEYS` gesetzt
- [ ] `/api/health` = ok
- [ ] `/api/tasks` erreichbar mit Auth
- [ ] Beide Agenten laufen stabil (`agent_runner.py`)
