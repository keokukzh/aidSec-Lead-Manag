"""Telegram command ingestion for OpenClaw task operations."""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

import requests
from sqlalchemy.orm import Session

from database.models import AgentTask, Settings


@dataclass
class TelegramContext:
    update_id: int
    chat_id: int
    user_id: int
    text: str


def _parse_int_set(raw: str | None) -> set[int]:
    if not raw:
        return set()
    values: set[int] = set()
    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue
        try:
            values.add(int(part))
        except ValueError:
            continue
    return values


def _get_setting(db: Session, key: str) -> str | None:
    entry = db.query(Settings).filter(Settings.key == key).first()
    return entry.value if entry else None


def _set_setting(db: Session, key: str, value: str) -> None:
    entry = db.query(Settings).filter(Settings.key == key).first()
    if entry:
        entry.value = value
    else:
        db.add(Settings(key=key, value=value))
    db.flush()


def _extract_context(update: dict[str, Any]) -> TelegramContext | None:
    update_id = update.get("update_id")
    message = update.get("message") or update.get("edited_message")
    if update_id is None or not isinstance(message, dict):
        return None

    chat = message.get("chat") or {}
    user = message.get("from") or {}
    text = (message.get("text") or "").strip()
    chat_id = chat.get("id")
    user_id = user.get("id")

    if chat_id is None or user_id is None:
        return None

    try:
        return TelegramContext(
            update_id=int(update_id),
            chat_id=int(chat_id),
            user_id=int(user_id),
            text=text,
        )
    except Exception:
        return None


def _is_duplicate_update(db: Session, update_id: int) -> bool:
    last = _get_setting(db, "telegram_last_update_id")
    if last is None:
        _set_setting(db, "telegram_last_update_id", str(update_id))
        db.commit()
        return False

    try:
        last_int = int(last)
    except ValueError:
        last_int = -1

    if update_id <= last_int:
        return True

    _set_setting(db, "telegram_last_update_id", str(update_id))
    db.commit()
    return False


def _allowed(ctx: TelegramContext) -> bool:
    allowed_chats = _parse_int_set(os.getenv("TELEGRAM_ALLOWED_CHAT_IDS"))
    allowed_users = _parse_int_set(os.getenv("TELEGRAM_ALLOWED_USER_IDS"))

    chat_ok = (not allowed_chats) or (ctx.chat_id in allowed_chats)
    user_ok = (not allowed_users) or (ctx.user_id in allowed_users)
    return chat_ok and user_ok


def _send_message(chat_id: int, text: str) -> None:
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    if not bot_token:
        return

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "disable_web_page_preview": True,
    }
    try:
        requests.post(url, json=payload, timeout=15)
    except Exception:
        return


def _cmd_help() -> str:
    return (
        "Commands:\n"
        "- task create <lead_id> [email_type] [agent1|agent2]\n"
        "- task status <task_id>\n"
        "- task list [limit]\n"
        "- run process-due\n"
        "- run auto-followup"
    )


def _handle_task_create(ctx: TelegramContext, db: Session, parts: list[str]) -> str:
    if len(parts) < 3:
        return "Usage: task create <lead_id> [email_type] [agent1|agent2]"

    try:
        lead_id = int(parts[2])
    except ValueError:
        return "lead_id must be numeric"

    email_type = "followup"
    if len(parts) >= 4:
        email_type = parts[3].strip().lower()

    agent_hint = None
    if len(parts) >= 5:
        candidate = parts[4].strip().lower()
        if candidate in {"agent1", "agent2"}:
            agent_hint = candidate

    payload: dict[str, Any] = {
        "source": "telegram",
        "email_type": email_type,
        "requested_by": {
            "chat_id": ctx.chat_id,
            "user_id": ctx.user_id,
        },
    }
    if agent_hint:
        payload["agent_hint"] = agent_hint

    task = AgentTask(
        task_type="GENERATE_DRAFT",
        lead_id=lead_id,
        payload=payload,
        status="pending",
    )
    db.add(task)
    db.commit()
    db.refresh(task)

    assigned_text = f", preferred={agent_hint}" if agent_hint else ""
    return f"Task #{task.id} created for lead {lead_id} (email_type={email_type}{assigned_text})"


def _handle_task_status(db: Session, parts: list[str]) -> str:
    if len(parts) < 3:
        return "Usage: task status <task_id>"

    try:
        task_id = int(parts[2])
    except ValueError:
        return "task_id must be numeric"

    task = db.query(AgentTask).filter(AgentTask.id == task_id).first()
    if not task:
        return f"Task #{task_id} not found"

    return (
        f"Task #{task.id}: status={task.status}, type={task.task_type}, "
        f"lead_id={task.lead_id}, assigned_to={task.assigned_to or '-'}, "
        f"attempts={task.attempts or 0}/{task.max_attempts or 5}"
    )


def _handle_task_list(db: Session, parts: list[str]) -> str:
    limit = 10
    if len(parts) >= 3:
        try:
            limit = max(1, min(30, int(parts[2])))
        except ValueError:
            pass

    tasks = (
        db.query(AgentTask)
        .order_by(AgentTask.created_at.desc())
        .limit(limit)
        .all()
    )
    if not tasks:
        return "No tasks available"

    lines = ["Latest tasks:"]
    for task in tasks:
        lines.append(
            f"#{task.id} {task.status} {task.task_type} lead={task.lead_id or '-'} assigned={task.assigned_to or '-'}"
        )
    return "\n".join(lines)


def _handle_run_command(db: Session, parts: list[str]) -> str:
    if len(parts) < 2:
        return "Usage: run process-due | run auto-followup"

    action = parts[1].strip().lower()
    if action == "process-due":
        from api.routes.campaigns import process_due_campaigns

        result = process_due_campaigns(db)
        return f"process-due done: processed={result.get('processed', 0)}, queued={result.get('tasks_queued', 0)}"

    if action == "auto-followup":
        from api.routes.campaigns import trigger_auto_followup

        result = trigger_auto_followup(db)
        return f"auto-followup done: queued={result.get('queued_followups', 0)}"

    return "Unknown run command. Use: run process-due | run auto-followup"


def process_telegram_update(update: dict[str, Any], db: Session, send_reply: bool = True) -> dict[str, Any]:
    ctx = _extract_context(update)
    if not ctx:
        return {"ok": True, "ignored": "unsupported_update"}

    if _is_duplicate_update(db, ctx.update_id):
        return {"ok": True, "ignored": "duplicate_update"}

    if not _allowed(ctx):
        return {"ok": True, "ignored": "not_allowlisted"}

    if not ctx.text:
        if send_reply:
            _send_message(ctx.chat_id, _cmd_help())
        return {"ok": True, "message": "empty_text"}

    normalized = ctx.text.strip().lower()
    normalized = normalized[1:] if normalized.startswith("/") else normalized
    parts = normalized.split()

    if not parts:
        if send_reply:
            _send_message(ctx.chat_id, _cmd_help())
        return {"ok": True, "message": "empty_command"}

    if parts[0] == "task":
        if len(parts) < 2:
            reply = _cmd_help()
        elif parts[1] == "create":
            reply = _handle_task_create(ctx, db, parts)
        elif parts[1] == "status":
            reply = _handle_task_status(db, parts)
        elif parts[1] == "list":
            reply = _handle_task_list(db, parts)
        else:
            reply = _cmd_help()
    elif parts[0] == "run":
        reply = _handle_run_command(db, parts)
    else:
        reply = _cmd_help()

    if send_reply:
        _send_message(ctx.chat_id, reply)
    return {"ok": True, "reply": reply}
