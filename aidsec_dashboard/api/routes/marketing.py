"""Marketing ideas endpoints: browse, filter, tracker CRUD, AI recommendations."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from api.dependencies import get_db, verify_api_key
from api.schemas.common import MarketingTrackerOut, MarketingTrackerCreate, MarketingTrackerUpdate
from database.models import MarketingIdeaTracker

router = APIRouter(tags=["marketing"], dependencies=[Depends(verify_api_key)])


@router.get("/marketing/ideas")
def list_ideas(
    category: Optional[str] = None,
    budget: Optional[str] = None,
    stage: Optional[str] = None,
    search: Optional[str] = None,
):
    from services.marketing_ideas import MARKETING_IDEAS, filter_ideas
    ideas = filter_ideas(
        categories=[category] if category else None,
        budgets=[budget] if budget else None,
        stages=[stage] if stage else None,
        search=search or "",
    )
    return {"ideas": ideas, "total": len(ideas)}


@router.get("/marketing/ideas/{nr}")
def get_idea(nr: int):
    from services.marketing_ideas import get_idea_by_nr
    idea = get_idea_by_nr(nr)
    if not idea:
        raise HTTPException(404, "Idea not found")
    return idea


@router.get("/marketing/tracker", response_model=list[MarketingTrackerOut])
def list_tracker(db: Session = Depends(get_db)):
    rows = db.query(MarketingIdeaTracker).order_by(MarketingIdeaTracker.prioritaet.desc()).all()
    return [MarketingTrackerOut.model_validate(r) for r in rows]


@router.post("/marketing/tracker", response_model=MarketingTrackerOut, status_code=201)
def add_to_tracker(payload: MarketingTrackerCreate, db: Session = Depends(get_db)):
    existing = db.query(MarketingIdeaTracker).filter(
        MarketingIdeaTracker.idea_number == payload.idea_number
    ).first()
    if existing:
        raise HTTPException(409, "Idea already tracked")

    tracker = MarketingIdeaTracker(
        idea_number=payload.idea_number,
        status=payload.status,
        notizen=payload.notizen,
        prioritaet=payload.prioritaet,
    )
    db.add(tracker)
    db.commit()
    db.refresh(tracker)
    return MarketingTrackerOut.model_validate(tracker)


@router.patch("/marketing/tracker/{tracker_id}", response_model=MarketingTrackerOut)
def update_tracker(tracker_id: int, payload: MarketingTrackerUpdate, db: Session = Depends(get_db)):
    t = db.query(MarketingIdeaTracker).filter(MarketingIdeaTracker.id == tracker_id).first()
    if not t:
        raise HTTPException(404, "Tracker entry not found")

    if payload.status is not None:
        old_status = t.status
        t.status = payload.status
        if payload.status == "aktiv" and old_status != "aktiv":
            t.started_at = datetime.utcnow()
        elif payload.status == "abgeschlossen" and old_status != "abgeschlossen":
            t.completed_at = datetime.utcnow()
    if payload.notizen is not None:
        t.notizen = payload.notizen
    if payload.prioritaet is not None:
        t.prioritaet = payload.prioritaet
    if payload.campaign_id is not None:
        t.campaign_id = payload.campaign_id

    db.commit()
    db.refresh(t)
    return MarketingTrackerOut.model_validate(t)


@router.delete("/marketing/tracker/{tracker_id}", status_code=204)
def delete_tracker(tracker_id: int, db: Session = Depends(get_db)):
    t = db.query(MarketingIdeaTracker).filter(MarketingIdeaTracker.id == tracker_id).first()
    if not t:
        raise HTTPException(404, "Tracker entry not found")
    db.delete(t)
    db.commit()


@router.post("/marketing/recommend")
def recommend_ideas(db: Session = Depends(get_db)):
    from database.models import Lead, LeadStatus, LeadKategorie, EmailHistory, EmailStatus, Campaign, CampaignStatus
    from services.llm_service import get_llm_service
    from services.outreach import parse_llm_json
    from sqlalchemy import func

    pipeline_stats = {
        "total": db.query(Lead).count(),
        "offene": db.query(Lead).filter(Lead.status == LeadStatus.OFFEN).count(),
        "pending": db.query(Lead).filter(Lead.status == LeadStatus.PENDING).count(),
        "gewonnen": db.query(Lead).filter(Lead.status == LeadStatus.GEWONNEN).count(),
        "verloren": db.query(Lead).filter(Lead.status == LeadStatus.VERLOREN).count(),
        "praxis": db.query(Lead).filter(Lead.kategorie == LeadKategorie.PRAXIS).count(),
        "anwalt": db.query(Lead).filter(Lead.kategorie == LeadKategorie.ANWALT).count(),
        "wordpress": db.query(Lead).filter(Lead.kategorie == LeadKategorie.WORDPRESS).count(),
        "emails_sent": db.query(EmailHistory).filter(EmailHistory.status == EmailStatus.SENT).count(),
        "active_campaigns": db.query(Campaign).filter(Campaign.status == CampaignStatus.AKTIV).count(),
        "active_ideas": db.query(MarketingIdeaTracker).filter(MarketingIdeaTracker.status == "aktiv").count(),
    }

    llm = get_llm_service()
    result = llm.recommend_marketing_ideas(pipeline_stats)
    if not result.get("success"):
        raise HTTPException(502, result.get("error", "LLM unavailable"))

    try:
        recommendations = parse_llm_json(result["content"], expect_array=True)
        return {"success": True, "recommendations": recommendations}
    except Exception:
        return {"success": True, "raw": result["content"]}
