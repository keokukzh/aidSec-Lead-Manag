#!/usr/bin/env bash
set -euo pipefail

AGENT_ID="agent2"
AGENT_KEY="agt2_5aea9e57cb08417b9e64888b1ef14a87"
GLOBAL_API_KEY="aidsec_api_a4da3c7956334a7b94d3c2e374e69961"
API_BASE_URL="https://aidsec-lead-manag-production-7292.up.railway.app/api"
INSTALL_DIR="/opt/aidSec-Lead-Manag/aidsec_dashboard"
REPO_DIR="/opt/aidSec-Lead-Manag"
SERVICE_NAME="aidsec-agent-${AGENT_ID}.service"

apt-get update -y
apt-get install -y git python3 python3-venv python3-pip curl ca-certificates

mkdir -p /opt
if [ ! -d "$REPO_DIR/.git" ]; then
  git clone https://github.com/keokukzh/aidSec-Lead-Manag.git "$REPO_DIR"
else
  git -C "$REPO_DIR" fetch --all --prune
  git -C "$REPO_DIR" reset --hard origin/main
fi

cd "$INSTALL_DIR"
python3 -m venv .venv
. .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

cat > .env.agent <<EOF
AIDSEC_API_BASE_URL=$API_BASE_URL
AIDSEC_GLOBAL_API_KEY=$GLOBAL_API_KEY
AIDSEC_AGENT_ID=$AGENT_ID
AIDSEC_AGENT_API_KEY=$AGENT_KEY
AIDSEC_LEASE_SECONDS=300
AIDSEC_HEARTBEAT_INTERVAL_SECONDS=60
AIDSEC_POLL_INTERVAL_SECONDS=10
AIDSEC_REQUEST_TIMEOUT_SECONDS=30
AIDSEC_AGENT_LOG_LEVEL=INFO
EOF
chmod 600 .env.agent

cat > /etc/systemd/system/aidsec-agent-${AGENT_ID}.service <<EOF
[Unit]
Description=AidSec OpenClaw Agent Runner (${AGENT_ID})
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
WorkingDirectory=$INSTALL_DIR
EnvironmentFile=$INSTALL_DIR/.env.agent
ExecStart=$INSTALL_DIR/.venv/bin/python $INSTALL_DIR/scripts/agent_runner.py --agent-id ${AGENT_ID}
Restart=always
RestartSec=5
User=root

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable "$SERVICE_NAME"
systemctl restart "$SERVICE_NAME"
sleep 2
systemctl --no-pager --full status "$SERVICE_NAME" | sed -n '1,40p'
journalctl -u "$SERVICE_NAME" -n 40 --no-pager

echo "=== API Health ==="
curl -sS "${API_BASE_URL%/api}/api/health" || true

echo "=== Agent Pull Check ==="
curl -sS -H "Authorization: Bearer ${GLOBAL_API_KEY}" -H "X-API-Key: ${AGENT_KEY}" "${API_BASE_URL}/agents/tasks/pull?agent_id=${AGENT_ID}&lease_seconds=120" || true

echo "✅ Agent ${AGENT_ID} setup complete"
