"""Shared Pydantic schemas."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Optional
from pydantic import BaseModel, ConfigDict


class FollowUpCreate(BaseModel):
    lead_id: int
    datum: datetime
    notiz: str = ""


class FollowUpUpdate(BaseModel):
    datum: Optional[datetime] = None
    notiz: Optional[str] = None
    erledigt: Optional[bool] = None


class FollowUpOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    lead_id: int
    datum: datetime
    notiz: str
    erledigt: bool
    created_at: Optional[datetime] = None
    lead_firma: Optional[str] = None


class SettingOut(BaseModel):
    key: str
    value: Optional[str] = None


class SettingUpdate(BaseModel):
    value: str


class MarketingTrackerOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    status: str
    notizen: Optional[str] = None
    custom_title: Optional[str] = None
    custom_description: Optional[str] = None
    campaign_id: Optional[int] = None
    prioritaet: int
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: Optional[datetime] = None


class MarketingTrackerCreate(BaseModel):
    idea_number: Optional[int] = None
    custom_title: Optional[str] = None
    custom_description: Optional[str] = None
    status: str = "geplant"
    notizen: Optional[str] = None
    prioritaet: int = 0


class MarketingTrackerUpdate(BaseModel):
    status: Optional[str] = None
    notizen: Optional[str] = None
    prioritaet: Optional[int] = None
    campaign_id: Optional[int] = None


class MarketingGenerateRequest(BaseModel):
    category: Optional[str] = None
    intent: Optional[str] = "Taktik"


class MarketingOptimizeRequest(BaseModel):
    current_title: str
    current_description: str
    category: Optional[str] = None


class RankingCheckRequest(BaseModel):
    url: str


class RankingBatchRequest(BaseModel):
    lead_ids: list[int]


class AgentSearchRequest(BaseModel):
    stadt: Optional[str] = None
    kategorie: Optional[str] = None
    branche: Optional[str] = None
    groesse: Optional[str] = None
    anzahl: int = 10
    extra_kriterien: str = ""


class AgentResearchRequest(BaseModel):
    lead_id: int
