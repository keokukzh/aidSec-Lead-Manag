#!/usr/bin/env bash
set -euo pipefail

AGENT_ID="agent2"
AGENT_KEY="agt2_5aea9e57cb08417b9e64888b1ef14a87"
GLOBAL_API_KEY="aidsec_api_a4da3c7956334a7b94d3c2e374e69961"
API_BASE_URL="https://aidsec-lead-manag-production-7292.up.railway.app/api"
INSTALL_DIR="/opt/aidSec-Lead-Manag/aidsec_dashboard"

apt-get update -y
apt-get install -y git python3 python3-venv

mkdir -p /opt
if [ ! -d /opt/aidSec-Lead-Manag ]; then
  git clone https://github.com/keokukzh/aidSec-Lead-Manag.git /opt/aidSec-Lead-Manag
else
  git -C /opt/aidSec-Lead-Manag pull --ff-only
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
systemctl enable --now aidsec-agent-${AGENT_ID}.service
sleep 2
systemctl --no-pager --full status aidsec-agent-${AGENT_ID}.service | sed -n '1,40p'
journalctl -u aidsec-agent-${AGENT_ID}.service -n 40 --no-pager

echo "✅ Agent ${AGENT_ID} setup complete"
