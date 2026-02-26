"""Telegram long-poll relay forwarding updates to backend webhook."""
from __future__ import annotations

import json
import logging
import os
import signal
import sys
import time
from typing import Any

import requests


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _build_config() -> dict[str, Any]:
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    if not token:
        raise ValueError("Missing TELEGRAM_BOT_TOKEN")

    api_base = os.getenv("AIDSEC_API_BASE_URL", "").strip().rstrip("/")
    if not api_base:
        raise ValueError("Missing AIDSEC_API_BASE_URL")

    secret = os.getenv("TELEGRAM_WEBHOOK_SECRET", "").strip()
    timeout_seconds = max(10, _env_int("TELEGRAM_POLL_TIMEOUT_SECONDS", 50))
    idle_sleep = max(1, _env_int("TELEGRAM_IDLE_SLEEP_SECONDS", 2))

    return {
        "token": token,
        "telegram_url": f"https://api.telegram.org/bot{token}",
        "webhook_url": f"{api_base}/webhooks/telegram",
        "webhook_secret": secret,
        "poll_timeout": timeout_seconds,
        "idle_sleep": idle_sleep,
    }


def main() -> int:
    logging.basicConfig(
        level=getattr(logging, os.getenv("TELEGRAM_RELAY_LOG_LEVEL", "INFO").upper(), logging.INFO),
        format="%(asctime)s %(levelname)s telegram_relay: %(message)s",
    )
    logger = logging.getLogger("telegram_relay")

    try:
        cfg = _build_config()
    except Exception as exc:
        logger.error("Config error: %s", exc)
        return 1

    stop = {"value": False}

    def _handle_signal(signum, frame):
        stop["value"] = True
        logger.info("Signal %s received, stopping", signum)

    signal.signal(signal.SIGINT, _handle_signal)
    signal.signal(signal.SIGTERM, _handle_signal)

    offset: int | None = None
    session = requests.Session()
    logger.info("Relay started (webhook=%s)", cfg["webhook_url"])

    while not stop["value"]:
        params = {
            "timeout": cfg["poll_timeout"],
            "allowed_updates": json.dumps(["message", "edited_message"]),
        }
        if offset is not None:
            params["offset"] = offset

        try:
            resp = session.get(f"{cfg['telegram_url']}/getUpdates", params=params, timeout=cfg["poll_timeout"] + 10)
            resp.raise_for_status()
            payload = resp.json()
            if not payload.get("ok"):
                logger.warning("Telegram returned non-ok response: %s", payload)
                time.sleep(cfg["idle_sleep"])
                continue

            updates = payload.get("result", [])
            if not updates:
                time.sleep(cfg["idle_sleep"])
                continue

            for update in updates:
                update_id = int(update.get("update_id", 0))
                offset = update_id + 1

                headers = {"Content-Type": "application/json"}
                if cfg["webhook_secret"]:
                    headers["X-Telegram-Bot-Api-Secret-Token"] = cfg["webhook_secret"]

                try:
                    forward = session.post(cfg["webhook_url"], json=update, headers=headers, timeout=20)
                    if forward.status_code >= 400:
                        logger.warning("Forward failed (status=%s): %s", forward.status_code, forward.text)
                except Exception as exc:
                    logger.warning("Forward error for update %s: %s", update_id, exc)

        except Exception as exc:
            logger.warning("Polling error: %s", exc)
            time.sleep(cfg["idle_sleep"])

    logger.info("Relay stopped")
    return 0


if __name__ == "__main__":
    sys.exit(main())
