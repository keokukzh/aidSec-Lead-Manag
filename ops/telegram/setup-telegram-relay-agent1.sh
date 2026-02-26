#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="/opt/aidSec-Lead-Manag"
INSTALL_DIR="/opt/aidSec-Lead-Manag/aidsec_dashboard"
SERVICE_NAME="aidsec-telegram-relay.service"

if [ -z "${TELEGRAM_BOT_TOKEN:-}" ]; then
  echo "TELEGRAM_BOT_TOKEN is required in environment"
  exit 1
fi

if [ -z "${AIDSEC_API_BASE_URL:-}" ]; then
  echo "AIDSEC_API_BASE_URL is required in environment"
  exit 1
fi

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

cat > .env.telegram-relay <<EOF
TELEGRAM_BOT_TOKEN=${TELEGRAM_BOT_TOKEN}
TELEGRAM_WEBHOOK_SECRET=${TELEGRAM_WEBHOOK_SECRET:-}
AIDSEC_API_BASE_URL=${AIDSEC_API_BASE_URL}
TELEGRAM_POLL_TIMEOUT_SECONDS=${TELEGRAM_POLL_TIMEOUT_SECONDS:-50}
TELEGRAM_IDLE_SLEEP_SECONDS=${TELEGRAM_IDLE_SLEEP_SECONDS:-2}
TELEGRAM_RELAY_LOG_LEVEL=${TELEGRAM_RELAY_LOG_LEVEL:-INFO}
EOF
chmod 600 .env.telegram-relay

cat > /etc/systemd/system/${SERVICE_NAME} <<EOF
[Unit]
Description=AidSec Telegram Relay
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
WorkingDirectory=${INSTALL_DIR}
EnvironmentFile=${INSTALL_DIR}/.env.telegram-relay
ExecStart=${INSTALL_DIR}/.venv/bin/python ${INSTALL_DIR}/scripts/telegram_relay.py
Restart=always
RestartSec=5
User=root

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable ${SERVICE_NAME}
systemctl restart ${SERVICE_NAME}

sleep 2
systemctl --no-pager --full status ${SERVICE_NAME} | sed -n '1,40p'
journalctl -u ${SERVICE_NAME} -n 30 --no-pager

echo "✅ Telegram relay setup complete on agent1"
