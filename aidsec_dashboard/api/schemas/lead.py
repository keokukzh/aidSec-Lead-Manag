"""Pydantic schemas for Lead endpoints."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Optional
from pydantic import BaseModel, ConfigDict


class LeadBase(BaseModel):
    firma: str
    website: Optional[str] = None
    email: Optional[str] = None
    telefon: Optional[str] = None
    stadt: Optional[str] = None
    kategorie: Optional[str] = "anwalt"
    status: Optional[str] = "offen"
    notes: Optional[str] = None
    quelle: Optional[str] = None
    wordpress_detected: Optional[str] = None
    linkedin: Optional[str] = None
    xing: Optional[str] = None


class LeadCreate(LeadBase):
    pass


class LeadUpdate(BaseModel):
    firma: Optional[str] = None
    website: Optional[str] = None
    email: Optional[str] = None
    telefon: Optional[str] = None
    stadt: Optional[str] = None
    kategorie: Optional[str] = None
    status: Optional[str] = None
    notes: Optional[str] = None
    quelle: Optional[str] = None
    wordpress_detected: Optional[str] = None
    linkedin: Optional[str] = None
    xing: Optional[str] = None
    ranking_score: Optional[int] = None
    ranking_grade: Optional[str] = None
    ranking_details: Optional[Any] = None
    research_status: Optional[str] = None
    research_data: Optional[Any] = None


class LeadOut(LeadBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ranking_score: Optional[int] = None
    ranking_grade: Optional[str] = None
    ranking_details: Optional[Any] = None
    ranking_checked_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    research_status: Optional[str] = None
    research_last: Optional[datetime] = None
    research_data: Optional[Any] = None
    lead_score: Optional[int] = 0


class LeadDetail(LeadOut):
    """Extended lead with history counts."""
    email_count: int = 0
    followup_count: int = 0


class PaginatedLeads(BaseModel):
    items: list[LeadOut]
    total: int
    page: int
    per_page: int
    pages: int


class BulkStatusUpdate(BaseModel):
    lead_ids: list[int]
    new_status: str


class BulkSecurityScanRequest(BaseModel):
    lead_ids: list[int]
    grade_filter: Optional[str] = None

