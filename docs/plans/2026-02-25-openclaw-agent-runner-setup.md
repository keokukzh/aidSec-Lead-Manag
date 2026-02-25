# OpenClaw Agent Runner Setup (Hetzner + Tailscale)

## Ziel

Remote-Agenten auf Hetzner sollen Tasks aus der lokalen AidSec Queue übernehmen:

- Local API Host (Tailscale): `100.100.97.120`
- Agent 1: `100.88.218.9`
- Agent 2: `100.87.63.92`

Implementierter Runner: `aidsec_dashboard/scripts/agent_runner.py`

---

## 1) Backend vorbereiten (lokal)

In `aidsec_dashboard/.env` setzen:

```env
API_KEY=<global_api_key>
AGENT_API_KEYS=agent1=<agent1_key>,agent2=<agent2_key>
```

API starten:

```bash
cd aidsec_dashboard
python -m uvicorn api.main:app --host 0.0.0.0 --port 8000
```

---

## 2) Agent-Server vorbereiten (beide Hetzner Nodes)

### Voraussetzungen

- Python 3.10+
- Tailscale verbunden
- Zugriff auf das Repo oder mindestens auf `scripts/agent_runner.py`

Verbindung testen:

```bash
tailscale ping 100.100.97.120
curl http://100.100.97.120:8000/api/health
```

---

## 3) Agent 1 starten

Environment:

```env
AIDSEC_API_BASE_URL=http://100.100.97.120:8000/api
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

---

## 4) Agent 2 starten

Environment:

```env
AIDSEC_API_BASE_URL=http://100.100.97.120:8000/api
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

## 5) Testlauf

### Einmaliger Pull-Zyklus (Dry Connectivity Test)

```bash
python scripts/agent_runner.py --once
```

Erwartung:

- Wenn Queue leer: sauberer Exit
- Wenn Task vorhanden: Pull → Verarbeitung → Complete

### Monitoring

- Queue-Liste: `/api/tasks`
- Worker Health: `/api/health/sequence-worker`

---

## 6) Betriebshinweise

- Heartbeat-Intervall muss kleiner sein als Lease (`heartbeat < lease`).
- Bei Agent-Absturz wird Task nach Lease-Ablauf reclaimt und erneut zugewiesen.
- Falsche Credentials führen zu 401/403.
- Unbekannte Task-Typen werden als failed abgeschlossen (mit Retry/Backoff auf Backend-Seite).

---

## 7) Optional: systemd Service (Linux)

Beispiel Unit-Datei (pro Agent anpassen):

```ini
[Unit]
Description=AidSec OpenClaw Agent Runner (agent1)
After=network-online.target

[Service]
Type=simple
WorkingDirectory=/opt/aidsec_dashboard
EnvironmentFile=/opt/aidsec_dashboard/agent1.env
ExecStart=/usr/bin/python3 scripts/agent_runner.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```
