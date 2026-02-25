"""Schemas for OpenClaw agent task queue operations."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel


class AgentTaskPullOut(BaseModel):
    id: int
    type: str
    lead_id: int | None = None
    payload: dict[str, Any] | None = None
    lease_token: str
    lease_until: datetime


class AgentTaskPullResponse(BaseModel):
    success: bool
    message: str | None = None
    task: AgentTaskPullOut | None = None


class AgentTaskCompletePayload(BaseModel):
    success: bool
    lease_token: str
    result: dict[str, Any] | None = None
    error: str | None = None


class AgentTaskHeartbeatPayload(BaseModel):
    lease_token: str


class AgentTaskAcknowledgeResponse(BaseModel):
    success: bool
    message: str
