"""Pydantic schemas for Dashboard endpoints."""
from __future__ import annotations

from pydantic import BaseModel


class StatusCounts(BaseModel):
    total: int
    offen: int
    pending: int
    gewonnen: int
    verloren: int


class KategorieCounts(BaseModel):
    anwalt: int
    praxis: int
    wordpress: int


class WeeklyDelta(BaseModel):
    new_this_week: int
    won_this_week: int
    lost_this_week: int


class ConversionRates(BaseModel):
    kontaktiert_rate: float
    gewinn_rate: float
    verlust_rate: float


class GradeDistribution(BaseModel):
    A: int = 0
    B: int = 0
    C: int = 0
    D: int = 0
    F: int = 0


class EmailStats(BaseModel):
    total_sent: int
    leads_contacted: int
    avg_per_lead: float
    success_rate: float


class CampaignKPIs(BaseModel):
    total_campaigns: int
    active_campaigns: int
    leads_in_campaigns: int
    due_emails: int
    campaign_emails_sent: int


class MarketingKPIs(BaseModel):
    total: int
    planned: int
    active: int
    completed: int


class FollowUpCounts(BaseModel):
    overdue: int
    today: int
    upcoming: int


class DashboardKPIs(BaseModel):
    status: StatusCounts
    kategorie: KategorieCounts
    weekly: WeeklyDelta
    conversion: ConversionRates
    grades: GradeDistribution
    email_stats: EmailStats
    campaign: CampaignKPIs
    marketing: MarketingKPIs
    followups: FollowUpCounts
