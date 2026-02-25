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
    subject_variants: Optional[list[str]] = None
    body: str = ""
    email_type: str = "erstkontakt"
    delay_seconds: int = 10
    campaign_id: Optional[int] = None
    template: Optional[str] = None
    attach_screenshot: Optional[bool] = False
    schedule: Optional[str] = "now"


class BulkPreviewRequest(BaseModel):
    lead_ids: list[int]
    template: str
    attach_screenshot: Optional[bool] = False


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


# ============ Extended Schema for Email Optimization ============

class CustomTemplateUpdate(BaseModel):
    name: Optional[str] = None
    betreff: Optional[str] = None
    inhalt: Optional[str] = None
    kategorie: Optional[str] = None
    is_ab_test: Optional[bool] = None
    variables: Optional[dict] = None


class CustomTemplateDuplicate(BaseModel):
    new_name: str
    new_version: Optional[bool] = True  # Increment version if True


class TemplateWithVariablesOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    betreff: str
    inhalt: str
    kategorie: Optional[str] = None
    is_ab_test: bool = False
    version: int = 1
    variables: Optional[dict] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


# A/B Test Schemas
class ABTestCreate(BaseModel):
    name: str
    template_id: Optional[int] = None
    subject_a: str
    subject_b: str
    distribution_a: int = 50
    distribution_b: int = 50
    auto_winner_after: int = 20


class ABTestOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    template_id: Optional[int] = None
    subject_a: str
    subject_b: str
    distribution_a: int
    distribution_b: int
    status: str
    winner: Optional[str] = None
    auto_winner_after: int
    sent_a: int
    sent_b: int
    opens_a: int
    opens_b: int
    clicks_a: int
    clicks_b: int
    created_at: datetime
    completed_at: Optional[datetime] = None


class ABTestStats(BaseModel):
    test_id: int
    name: str
    status: str
    winner: Optional[str] = None
    variant_a: dict
    variant_b: dict
    significance: Optional[float] = None  # Statistical significance %


# Sequence Schemas
class SequenceStep(BaseModel):
    day_offset: int  # Days from start or previous step
    template_id: Optional[int] = None
    subject_override: Optional[str] = None
    body_override: Optional[str] = None


class SequenceCreate(BaseModel):
    name: str
    beschreibung: Optional[str] = None
    steps: list[SequenceStep]
    status: str = "entwurf"


class SequenceUpdate(BaseModel):
    name: Optional[str] = None
    beschreibung: Optional[str] = None
    steps: Optional[list[SequenceStep]] = None
    status: Optional[str] = None


class SequenceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    beschreibung: Optional[str] = None
    steps: list
    status: str
    created_at: datetime
    updated_at: Optional[datetime] = None


class SequenceAssignLeads(BaseModel):
    lead_ids: list[int]
    start_now: bool = True


class SequenceStats(BaseModel):
    sequence_id: int
    name: str
    total_assigned: int
    active: int
    completed: int
    paused: int
    unsubscribed: int


# Analytics Schemas
class EmailAnalyticsOverview(BaseModel):
    total_sent: int = 0
    delivered: int = 0
    opened: int = 0
    clicked: int = 0
    replied: int = 0
    bounced: int = 0
    open_rate: float = 0.0
    click_rate: float = 0.0
    response_rate: float = 0.0
    bounce_rate: float = 0.0


class TemplateAnalytics(BaseModel):
    template_id: int
    template_name: str
    sent: int
    opened: int
    clicked: int
    replied: int
    open_rate: float
    click_rate: float
    response_rate: float
