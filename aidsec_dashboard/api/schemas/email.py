"""Pydantic schemas for Email endpoints."""
from __future__ import annotations

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict


class SendEmailRequest(BaseModel):
    lead_id: int
    subject: str
    body: str
    campaign_id: Optional[int] = None


class BulkSendRequest(BaseModel):
    lead_ids: list[int]
    subject: str = ""
    body: str = ""
    email_type: str = "erstkontakt"
    delay_seconds: int = 10
    campaign_id: Optional[int] = None


class EmailHistoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    lead_id: int
    betreff: str
    inhalt: str
    status: str
    gesendet_at: Optional[datetime] = None
    campaign_id: Optional[int] = None
    outlook_message_id: Optional[str] = None


class GenerateEmailRequest(BaseModel):
    lead_id: int
    email_type: str = "erstkontakt"


class SmtpTestResult(BaseModel):
    success: bool
    message: Optional[str] = None
    error: Optional[str] = None


class TemplateOut(BaseModel):
    key: str
    name: str
    betreff: str
    inhalt: str


class CustomTemplateOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    betreff: str
    inhalt: str


class CustomTemplateCreate(BaseModel):
    name: str
    betreff: str
    inhalt: str


class GlobalEmailHistoryOut(BaseModel):
    id: int
    lead_id: int
    lead_firma: Optional[str] = None
    betreff: str
    inhalt: str
    status: str
    gesendet_at: Optional[datetime] = None

class DraftUpdateRequest(BaseModel):
    subject: str
    body: str

class BulkDraftApproveRequest(BaseModel):
    draft_ids: list[int]
