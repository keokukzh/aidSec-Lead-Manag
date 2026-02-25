"""Pydantic schemas for Campaign endpoints."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Optional
from pydantic import BaseModel, ConfigDict


class CampaignCreate(BaseModel):
    name: str
    beschreibung: Optional[str] = None
    kategorie_filter: Optional[str] = None
    sequenz: Optional[list[dict]] = None


class CampaignUpdate(BaseModel):
    name: Optional[str] = None
    beschreibung: Optional[str] = None
    status: Optional[str] = None


class CampaignLeadOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    campaign_id: int
    lead_id: int
    current_step: int
    next_send_at: Optional[datetime] = None
    cl_status: str
    lead_firma: Optional[str] = None
    lead_email: Optional[str] = None
    lead_stadt: Optional[str] = None


class CampaignOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    beschreibung: Optional[str] = None
    kategorie_filter: Optional[str] = None
    sequenz: Optional[Any] = None
    start_datum: Optional[datetime] = None
    end_datum: Optional[datetime] = None
    status: str
    created_at: Optional[datetime] = None
    leads_count: int = 0
    completed_count: int = 0


class AssignLeadsRequest(BaseModel):
    lead_ids: list[int]
