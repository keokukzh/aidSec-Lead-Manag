"""Dashboard KPI aggregation endpoints."""
from __future__ import annotations

import time as _time
from datetime import datetime, timedelta, date

from fastapi import APIRouter, Depends
from sqlalchemy import func, case
from sqlalchemy.orm import Session

from api.dependencies import get_db, verify_api_key
from api.schemas.dashboard import (
    DashboardKPIs,
    StatusCounts,
    KategorieCounts,
    WeeklyDelta,
    ConversionRates,
    GradeDistribution,
    EmailStats,
    RevenueKPIs,
    CampaignKPIs,
    MarketingKPIs,
    FollowUpCounts,
)
from database.models import (
    Lead,
    LeadStatus,
    LeadKategorie,
    StatusHistory,
    EmailHistory,
    EmailStatus,
    FollowUp,
    Campaign,
    CampaignStatus,
    CampaignLead,
    MarketingIdeaTracker,
)

router = APIRouter(tags=["dashboard"], dependencies=[Depends(verify_api_key)])

_kpi_cache: dict = {"data": None, "ts": 0.0}
_KPI_CACHE_TTL = 30


def _compute_kpis(db: Session) -> DashboardKPIs:
    # --- Status + Kategorie counts in 2 queries instead of 7 ---
    status_rows = db.query(Lead.status, func.count()).group_by(Lead.status).all()
    status_map = {r[0].value if hasattr(r[0], "value") else str(r[0]): r[1] for r in status_rows}
    offen = status_map.get("offen", 0)
    pending = status_map.get("pending", 0)
    response_received = status_map.get("response_received", 0)
    offer_sent = status_map.get("offer_sent", 0)
    negotiation = status_map.get("negotiation", 0)
    gewonnen = status_map.get("gewonnen", 0)
    verloren = status_map.get("verloren", 0)
    
    total = sum(status_map.values())

    kat_rows = db.query(Lead.kategorie, func.count()).group_by(Lead.kategorie).all()
    kat_map = {r[0].value if hasattr(r[0], "value") else str(r[0]): r[1] for r in kat_rows}
    anwalt = kat_map.get("anwalt", 0)
    praxis = kat_map.get("praxis", 0)
    wordpress = kat_map.get("wordpress", 0)
    
    # --- Revenue / Pipeline Stats ---
    # Everything but OFFEN and VERLOREN is considered "pipeline" basically
    # Or more strictly, only offer_sent and negotiation? We'll sum all non-won/lost for total pipeline
    pipeline_amount = db.query(func.sum(Lead.deal_size)).filter(
        Lead.status.in_([LeadStatus.OFFER_SENT, LeadStatus.NEGOTIATION])
    ).scalar() or 0
    won_amount = db.query(func.sum(Lead.deal_size)).filter(Lead.status == LeadStatus.GEWONNEN).scalar() or 0
    
    # Calculate averages
    won_count = gewonnen
    avg_deal_size = int(won_amount / won_count) if won_count > 0 else 0

    # --- Weekly stats (3 queries -> stays 3, they have different tables/filters) ---
    week_ago = datetime.utcnow() - timedelta(days=7)
    new_this_week = db.query(Lead).filter(Lead.created_at >= week_ago).count()
    won_this_week = db.query(StatusHistory).filter(
        StatusHistory.zu_status == LeadStatus.GEWONNEN, StatusHistory.datum >= week_ago
    ).count()
    lost_this_week = db.query(StatusHistory).filter(
        StatusHistory.zu_status == LeadStatus.VERLOREN, StatusHistory.datum >= week_ago
    ).count()

    moved_past_offen = pending + gewonnen + verloren
    kontaktiert_rate = round(moved_past_offen / total * 100, 1) if total else 0
    gewinn_rate = round(gewonnen / max(1, gewonnen + verloren) * 100, 1)
    verlust_rate = round(verloren / max(1, total) * 100, 1)

    # --- Grade distribution in 1 query instead of 5 ---
    grade_rows = (
        db.query(Lead.ranking_grade, func.count())
        .filter(Lead.ranking_grade.isnot(None))
        .group_by(Lead.ranking_grade)
        .all()
    )
    grade_map = {r[0]: r[1] for r in grade_rows}
    grades = {g: grade_map.get(g, 0) for g in ["A", "B", "C", "D", "F"]}

    # --- Email stats (2 queries instead of 3) ---
    email_agg = db.query(
        func.count(EmailHistory.id),
        func.count(func.distinct(EmailHistory.lead_id)),
    ).filter(EmailHistory.status == EmailStatus.SENT).one()
    total_sent = email_agg[0] or 0
    contacted = email_agg[1] or 0
    avg_per_lead = round(total_sent / max(1, contacted), 1)
    won_and_contacted = (
        db.query(func.count(func.distinct(Lead.id)))
        .join(EmailHistory, EmailHistory.lead_id == Lead.id)
        .filter(EmailHistory.status == EmailStatus.SENT, Lead.status == LeadStatus.GEWONNEN)
        .scalar()
        or 0
    )
    success_rate = round(won_and_contacted / max(1, contacted) * 100, 1)
    
    # Extended Email Stats (Feature 5)
    # Estimate response rate and conversion rate 
    responded_leads = response_received + offer_sent + negotiation + gewonnen
    response_rate = round(responded_leads / max(1, total_sent) * 100, 1)
    conversion_rate = round(gewonnen / max(1, contacted) * 100, 1)
    
    avg_response_time = db.query(func.avg(Lead.response_time_hours)).filter(Lead.response_time_hours > 0).scalar() or 0

    # --- Campaign stats (combine into fewer queries) ---
    camp_agg = db.query(
        func.count(Campaign.id),
        func.sum(case((Campaign.status == CampaignStatus.AKTIV, 1), else_=0)),
    ).one()
    total_camp = camp_agg[0] or 0
    active_camp = int(camp_agg[1] or 0)
    leads_in_camp = db.query(CampaignLead).count()
    due_emails = (
        db.query(CampaignLead)
        .filter(CampaignLead.cl_status == "aktiv", CampaignLead.next_send_at <= datetime.utcnow())
        .count()
    )
    camp_emails = (
        db.query(func.count(EmailHistory.id))
        .filter(EmailHistory.campaign_id.isnot(None), EmailHistory.status == EmailStatus.SENT)
        .scalar()
        or 0
    )

    # --- Marketing tracker in 1 query with GROUP BY instead of loading all rows ---
    mkt_rows = (
        db.query(MarketingIdeaTracker.status, func.count())
        .group_by(MarketingIdeaTracker.status)
        .all()
    )
    mkt_map = {r[0]: r[1] for r in mkt_rows}
    m_total = sum(mkt_map.values())
    m_planned = mkt_map.get("geplant", 0)
    m_active = mkt_map.get("aktiv", 0)
    m_completed = mkt_map.get("abgeschlossen", 0)

    # --- Follow-ups (3 queries, different date ranges) ---
    today_start = datetime.combine(date.today(), datetime.min.time())
    today_end = datetime.combine(date.today(), datetime.max.time())
    fu_agg = db.query(
        func.sum(case((FollowUp.datum < today_start, 1), else_=0)),
        func.sum(case((FollowUp.datum >= today_start, case((FollowUp.datum <= today_end, 1), else_=0)), else_=0)),
        func.sum(case((FollowUp.datum > today_end, 1), else_=0)),
    ).filter(FollowUp.erledigt == False).one()
    overdue = int(fu_agg[0] or 0)
    today_fus = int(fu_agg[1] or 0)
    upcoming = int(fu_agg[2] or 0)

    return DashboardKPIs(
        status=StatusCounts(
            total=total, offen=offen, pending=pending,
            response_received=response_received, offer_sent=offer_sent,
            negotiation=negotiation, gewonnen=gewonnen, verloren=verloren
        ),
        kategorie=KategorieCounts(anwalt=anwalt, praxis=praxis, wordpress=wordpress),
        weekly=WeeklyDelta(new_this_week=new_this_week, won_this_week=won_this_week, lost_this_week=lost_this_week),
        conversion=ConversionRates(
            kontaktiert_rate=kontaktiert_rate, gewinn_rate=gewinn_rate, verlust_rate=verlust_rate
        ),
        grades=GradeDistribution(**grades),
        email_stats=EmailStats(
            total_sent=total_sent, leads_contacted=contacted,
            avg_per_lead=avg_per_lead, success_rate=success_rate,
            response_rate=response_rate, conversion_rate=conversion_rate,
            avg_response_time_hours=round(avg_response_time, 1)
        ),
        revenue=RevenueKPIs(
            total_pipeline=int(pipeline_amount),
            won_deals=int(won_amount),
            avg_deal_size=avg_deal_size
        ),
        campaign=CampaignKPIs(
            total_campaigns=total_camp, active_campaigns=active_camp,
            leads_in_campaigns=leads_in_camp, due_emails=due_emails,
            campaign_emails_sent=camp_emails,
        ),
        marketing=MarketingKPIs(total=m_total, planned=m_planned, active=m_active, completed=m_completed),
        followups=FollowUpCounts(overdue=overdue, today=today_fus, upcoming=upcoming),
    )


@router.get("/dashboard/kpis", response_model=DashboardKPIs)
def dashboard_kpis(db: Session = Depends(get_db)):
    now = _time.time()
    if _kpi_cache["data"] and (now - _kpi_cache["ts"]) < _KPI_CACHE_TTL:
        return _kpi_cache["data"]
    result = _compute_kpis(db)
    _kpi_cache["data"] = result
    _kpi_cache["ts"] = now
    return result
