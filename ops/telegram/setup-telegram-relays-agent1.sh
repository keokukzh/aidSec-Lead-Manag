#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="/opt/aidSec-Lead-Manag"
INSTALL_DIR="/opt/aidSec-Lead-Manag/aidsec_dashboard"
API_BASE_URL="https://aidsec-lead-manag-production-7292.up.railway.app/api"
WEBHOOK_SECRET="aidsec-telegram-relay-2026"

BOT1_NAME="eddyscreatorbot"
BOT1_TOKEN="8025628083:AAFDjfPiIYG4Y0AFevgMW_LqZKwNP52FrIA"

BOT2_NAME="openbottlerbot"
BOT2_TOKEN="8454727084:AAEPvpPkcXf5wuEold5o97k37Sho7nQUKHA"

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

setup_bot_service() {
  local bot_name="$1"
  local bot_token="$2"
  local service_name="aidsec-telegram-relay-${bot_name}.service"
  local env_file="$INSTALL_DIR/.env.telegram-relay-${bot_name}"

  cat > "$env_file" <<EOF
TELEGRAM_BOT_TOKEN=${bot_token}
TELEGRAM_WEBHOOK_SECRET=${WEBHOOK_SECRET}
AIDSEC_API_BASE_URL=${API_BASE_URL}
TELEGRAM_POLL_TIMEOUT_SECONDS=50
TELEGRAM_IDLE_SLEEP_SECONDS=2
TELEGRAM_RELAY_LOG_LEVEL=INFO
EOF
  chmod 600 "$env_file"

  cat > "/etc/systemd/system/${service_name}" <<EOF
[Unit]
Description=AidSec Telegram Relay (${bot_name})
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
WorkingDirectory=${INSTALL_DIR}
EnvironmentFile=${env_file}
ExecStart=${INSTALL_DIR}/.venv/bin/python ${INSTALL_DIR}/scripts/telegram_relay.py
Restart=always
RestartSec=5
User=root

[Install]
WantedBy=multi-user.target
EOF

  systemctl enable "$service_name"
  systemctl restart "$service_name"
  sleep 1
  systemctl --no-pager --full status "$service_name" | sed -n '1,28p'
  journalctl -u "$service_name" -n 20 --no-pager
}

systemctl daemon-reload

setup_bot_service "$BOT1_NAME" "$BOT1_TOKEN"
setup_bot_service "$BOT2_NAME" "$BOT2_TOKEN"

echo "=== Bot reachability ==="
curl -sS "https://api.telegram.org/bot${BOT1_TOKEN}/getMe" || true
curl -sS "https://api.telegram.org/bot${BOT2_TOKEN}/getMe" || true

echo "✅ Both Telegram relay services are configured on agent1"
