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
        "allowed_chat_ids": _parse_int_set(os.getenv("TELEGRAM_ALLOWED_CHAT_IDS")),
        "allowed_user_ids": _parse_int_set(os.getenv("TELEGRAM_ALLOWED_USER_IDS")),
    }


def _parse_int_set(raw: str | None) -> set[int]:
    if not raw:
        return set()
    result: set[int] = set()
    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue
        try:
            result.add(int(part))
        except ValueError:
            continue
    return result


def _extract_ids(update: dict[str, Any]) -> tuple[int | None, int | None]:
    message = update.get("message") or update.get("edited_message") or {}
    chat = message.get("chat") or {}
    user = message.get("from") or {}

    chat_id = chat.get("id")
    user_id = user.get("id")

    try:
        chat_id = int(chat_id) if chat_id is not None else None
    except Exception:
        chat_id = None

    try:
        user_id = int(user_id) if user_id is not None else None
    except Exception:
        user_id = None

    return chat_id, user_id


def _is_allowed(update: dict[str, Any], allowed_chat_ids: set[int], allowed_user_ids: set[int]) -> bool:
    chat_id, user_id = _extract_ids(update)
    chat_ok = (not allowed_chat_ids) or (chat_id in allowed_chat_ids)
    user_ok = (not allowed_user_ids) or (user_id in allowed_user_ids)
    return chat_ok and user_ok


def _send_reply(session: requests.Session, telegram_url: str, chat_id: int, text: str) -> None:
    payload = {
        "chat_id": chat_id,
        "text": text,
        "disable_web_page_preview": True,
    }
    resp = session.post(f"{telegram_url}/sendMessage", json=payload, timeout=15)
    resp.raise_for_status()


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

                chat_id, _ = _extract_ids(update)
                if not _is_allowed(update, cfg["allowed_chat_ids"], cfg["allowed_user_ids"]):
                    logger.info("Skipping update %s because sender is not allowlisted", update_id)
                    continue

                headers = {"Content-Type": "application/json"}
                if cfg["webhook_secret"]:
                    headers["X-Telegram-Bot-Api-Secret-Token"] = cfg["webhook_secret"]
                headers["X-Aidsec-Telegram-Relay"] = "1"

                try:
                    forward = session.post(cfg["webhook_url"], json=update, headers=headers, timeout=20)
                    if forward.status_code >= 400:
                        logger.warning("Forward failed (status=%s): %s", forward.status_code, forward.text)
                    else:
                        try:
                            response_payload = forward.json()
                        except Exception:
                            response_payload = {}

                        reply = response_payload.get("reply") if isinstance(response_payload, dict) else None
                        if reply and chat_id is not None:
                            try:
                                _send_reply(session, cfg["telegram_url"], chat_id, str(reply))
                            except Exception as exc:
                                logger.warning("sendMessage failed for update %s: %s", update_id, exc)
                except Exception as exc:
                    logger.warning("Forward error for update %s: %s", update_id, exc)

        except Exception as exc:
            logger.warning("Polling error: %s", exc)
            time.sleep(cfg["idle_sleep"])

    logger.info("Relay stopped")
    return 0


if __name__ == "__main__":
    sys.exit(main())
