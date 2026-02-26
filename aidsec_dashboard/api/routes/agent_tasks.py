"""Endpoints for external OpenClaw agents to pull tasks and report completions."""
import os
import uuid
from datetime import datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from api.dependencies import get_db, verify_api_key
from api.schemas.agent_task import (
    AgentTaskAcknowledgeResponse,
    AgentTaskCompletePayload,
    AgentTaskHeartbeatPayload,
    AgentTaskPullResponse,
)
from database.models import AgentTask, EmailHistory, EmailStatus

router = APIRouter(tags=["agents", "openclaw"], dependencies=[Depends(verify_api_key)])


def _parse_agent_api_keys() -> dict[str, str]:
    raw = os.getenv("AGENT_API_KEYS", "").strip()
    if not raw:
        return {}

    pairs = [item.strip() for item in raw.split(",") if item.strip()]
    parsed: dict[str, str] = {}
    for pair in pairs:
        if "=" in pair:
            agent_id, secret = pair.split("=", 1)
        elif ":" in pair:
            agent_id, secret = pair.split(":", 1)
        else:
            continue
        agent_id = agent_id.strip()
        secret = secret.strip()
        if agent_id and secret:
            parsed[agent_id] = secret
    return parsed


def _read_auth_token(request: Request) -> str:
    api_key = request.headers.get("x-api-key", "").strip()
    if api_key:
        return api_key

    auth = request.headers.get("authorization", "").strip()
    if auth.lower().startswith("bearer "):
        return auth[7:].strip()

    return ""


def _authorize_agent(request: Request, agent_id: str) -> None:
    keys = _parse_agent_api_keys()
    if not keys:
        return

    expected = keys.get(agent_id)
    if not expected:
        raise HTTPException(status_code=403, detail=f"Agent '{agent_id}' is not registered")

    token = _read_auth_token(request)
    if not token or token != expected:
        raise HTTPException(status_code=401, detail="Invalid credentials for agent")


def _calculate_retry_delay_seconds(attempts: int) -> int:
    base = 120
    capped_attempt = min(max(1, attempts), 8)
    return base * (2 ** (capped_attempt - 1))

@router.get("/agents/tasks/pull")
def pull_agent_task(
    request: Request,
    agent_id: str,
    lease_seconds: int = Query(300, ge=30, le=3600),
    db: Session = Depends(get_db),
) -> AgentTaskPullResponse:
    """
    Called by Agent 2 (SDR) to pull the next pending task from the queue.
    Locks the task by transitioning it to 'processing' and assigns it to the physical agent ID.
    """
    _authorize_agent(request, agent_id)

    now = datetime.utcnow()
    is_sqlite = (getattr(getattr(db, "bind", None), "dialect", None) is not None and db.bind.dialect.name == "sqlite")

    if is_sqlite:
        stale_filter = func.datetime(AgentTask.lease_until) < func.datetime(now)
        retry_ready_filter = func.datetime(AgentTask.next_retry_at) <= func.datetime(now)
    else:
        stale_filter = AgentTask.lease_until < now
        retry_ready_filter = AgentTask.next_retry_at <= now

    # Reclaim stale processing tasks (lease expired)
    stale_tasks = (
        db.query(AgentTask)
        .filter(
            AgentTask.status == "processing",
            AgentTask.lease_until.isnot(None),
            stale_filter,
        )
        .all()
    )

    for stale in stale_tasks:
        if (stale.attempts or 0) >= (stale.max_attempts or 5):
            stale.status = "dead_letter"
            stale.error_message = stale.error_message or "max_attempts_exceeded_after_lease_timeout"
            stale.completed_at = now
        else:
            stale.status = "pending"
            stale.assigned_to = None
            stale.lease_token = None
            stale.lease_until = None
            stale.last_heartbeat_at = None
            stale.next_retry_at = now

    db.flush()

    # Find oldest pending and retry-ready task
    task = (
        db.query(AgentTask)
        .filter(
            AgentTask.status == "pending",
            or_(
                AgentTask.next_retry_at.is_(None),
                retry_ready_filter,
            ),
        )
        .order_by(AgentTask.created_at.asc())
        .first()
    )
    
    if not task:
        db.commit()
        return AgentTaskPullResponse(success=True, message="Queue is empty", task=None)
        
    # Attempt to lock it (handling SQLite race conditions without skip_locked)
    lease_token = uuid.uuid4().hex
    lease_until = now + timedelta(seconds=lease_seconds)

    updated_rows = db.query(AgentTask).filter(
        AgentTask.id == task.id,
        AgentTask.status == "pending",
    ).update({
        "status": "processing",
        "assigned_to": agent_id,
        "lease_token": lease_token,
        "lease_until": lease_until,
        "last_heartbeat_at": now,
        "attempts": (task.attempts or 0) + 1,
        "error_message": None,
    })
    
    if updated_rows == 0:
        # Race condition: Another agent locked it before we could
        db.rollback()
        return AgentTaskPullResponse(success=True, message="Queue is empty", task=None)
        
    db.commit()
    db.refresh(task)
    
    return AgentTaskPullResponse(
        success=True,
        task={
            "id": task.id,
            "type": task.task_type,
            "lead_id": task.lead_id,
            "payload": task.payload,
            "lease_token": task.lease_token,
            "lease_until": task.lease_until,
        },
    )


@router.post("/agents/tasks/{task_id}/heartbeat", response_model=AgentTaskAcknowledgeResponse)
def heartbeat_agent_task(
    task_id: int,
    payload: AgentTaskHeartbeatPayload,
    request: Request,
    agent_id: str,
    lease_seconds: int = Query(300, ge=30, le=3600),
    db: Session = Depends(get_db),
):
    _authorize_agent(request, agent_id)

    task = db.query(AgentTask).filter(AgentTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    if task.status != "processing":
        raise HTTPException(status_code=409, detail=f"Task not in processing state ({task.status})")

    if task.assigned_to != agent_id:
        raise HTTPException(status_code=403, detail="Task is owned by a different agent")

    if not task.lease_token or task.lease_token != payload.lease_token:
        raise HTTPException(status_code=401, detail="Invalid lease token")

    now = datetime.utcnow()
    task.last_heartbeat_at = now
    task.lease_until = now + timedelta(seconds=lease_seconds)
    db.commit()

    return AgentTaskAcknowledgeResponse(success=True, message="Heartbeat accepted")


@router.post("/agents/tasks/{task_id}/complete")
def complete_agent_task(
    task_id: int,
    payload: AgentTaskCompletePayload,
    request: Request,
    agent_id: str,
    db: Session = Depends(get_db),
) -> AgentTaskAcknowledgeResponse:
    """
    Called by Agent 2 when a task finishes. 
    If it was a generation task, this endpoint will parse the result and drop the email draft.
    """
    _authorize_agent(request, agent_id)

    task = db.query(AgentTask).filter(AgentTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    if task.status == "completed":
        return AgentTaskAcknowledgeResponse(success=True, message="Task already completed")

    if task.status in {"failed", "dead_letter"}:
        raise HTTPException(status_code=409, detail=f"Task already finalized as {task.status}")

    if task.status != "processing":
        raise HTTPException(status_code=409, detail=f"Task not in processing state ({task.status})")

    if task.assigned_to != agent_id:
        raise HTTPException(status_code=403, detail="Task is owned by a different agent")

    if not task.lease_token or task.lease_token != payload.lease_token:
        raise HTTPException(status_code=401, detail="Invalid lease token")

    now = datetime.utcnow()
    task.result_payload = payload.result
        
    if not payload.success:
        attempts = task.attempts or 0
        max_attempts = task.max_attempts or 5
        if attempts >= max_attempts:
            task.status = "dead_letter"
            task.completed_at = now
            task.error_message = payload.error or "max_attempts_exceeded"
        else:
            retry_delay_seconds = _calculate_retry_delay_seconds(attempts)
            task.status = "pending"
            task.next_retry_at = now + timedelta(seconds=retry_delay_seconds)
            task.error_message = payload.error or "task_execution_failed"

        task.assigned_to = None
        task.lease_token = None
        task.lease_until = None
        task.last_heartbeat_at = None
        db.commit()
        return AgentTaskAcknowledgeResponse(success=True, message="Task failure processed")

    # Handle successful SDR Draft tasks
    if task.task_type == "GENERATE_DRAFT":
        result = payload.result or {}
        subject = result.get("betreff", "Automatisch generiert")
        body = result.get("inhalt", "")
        
        # Save straight to EmailHistory as a Draft ready for human review in the Outgoing Queue
        draft = EmailHistory(
            lead_id=task.lead_id,
            betreff=subject,
            inhalt=body,
            status=EmailStatus.DRAFT,
            campaign_id=task.payload.get("campaign_id") if task.payload else None
        )
        db.add(draft)
        
    # Close task
    task.status = "completed"
    task.completed_at = now
    task.next_retry_at = None
    task.error_message = None
    task.lease_until = None
    task.lease_token = None
    task.last_heartbeat_at = now
    db.commit()
    
    return AgentTaskAcknowledgeResponse(success=True, message="Task completed successfully")
