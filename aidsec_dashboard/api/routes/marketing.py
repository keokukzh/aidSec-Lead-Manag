"""Marketing ideas endpoints: browse, filter, tracker CRUD, AI recommendations."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from api.dependencies import get_db, verify_api_key
from api.schemas.common import MarketingTrackerOut, MarketingTrackerCreate, MarketingTrackerUpdate, MarketingGenerateRequest, MarketingOptimizeRequest
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


@router.get("/marketing/tracker")
def list_tracker(db: Session = Depends(get_db)):
    from services.marketing_ideas import get_idea_by_nr
    rows = db.query(MarketingIdeaTracker).order_by(MarketingIdeaTracker.prioritaet.desc()).all()
    
    results = []
    for r in rows:
        data = MarketingTrackerOut.model_validate(r).model_dump()
        idea_details = get_idea_by_nr(r.idea_number) if r.idea_number else None
        if idea_details:
            data["title"] = idea_details.get("name")
            data["description"] = idea_details.get("desc")
            data["category"] = idea_details.get("cat")
        else:
            data["title"] = r.custom_title
            data["description"] = r.custom_description
            data["category"] = "KI Idee"
        results.append(data)
        
    return results


@router.post("/marketing/tracker", response_model=MarketingTrackerOut, status_code=201)
def add_to_tracker(payload: MarketingTrackerCreate, db: Session = Depends(get_db)):
    if payload.idea_number is not None:
        existing = db.query(MarketingIdeaTracker).filter(
            MarketingIdeaTracker.idea_number == payload.idea_number
        ).first()
        if existing:
            raise HTTPException(409, "Idea already tracked")
        idea_num = payload.idea_number
    else:
        import random
        while True:
            idea_num = -random.randint(1, 1000000)
            existing = db.query(MarketingIdeaTracker).filter(
                MarketingIdeaTracker.idea_number == idea_num
            ).first()
            if not existing:
                break

    tracker = MarketingIdeaTracker(
        idea_number=idea_num,

        custom_title=payload.custom_title,
        custom_description=payload.custom_description,
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


@router.post("/marketing/generate")
def generate_idea(payload: MarketingGenerateRequest, db: Session = Depends(get_db)):
    from services.llm_service import get_llm_service
    
    llm = get_llm_service()
    result = llm.generate_marketing_strategy(
        category=payload.category,
        intent=payload.intent
    )
    
    if not result.get("success"):
        raise HTTPException(502, result.get("error", "LLM unavailable"))
        
    return result


@router.post("/marketing/tracker/{tracker_id}/optimize", response_model=MarketingTrackerOut)
def optimize_tracker_idea(tracker_id: int, payload: MarketingOptimizeRequest, db: Session = Depends(get_db)):
    t = db.query(MarketingIdeaTracker).filter(MarketingIdeaTracker.id == tracker_id).first()
    if not t:
        raise HTTPException(404, "Tracker entry not found")
        
    from services.llm_service import get_llm_service
    llm = get_llm_service()
    
    result = llm.optimize_marketing_strategy(
        current_title=payload.current_title,
        current_description=payload.current_description,
        category=payload.category
    )
    
    if not result.get("success"):
        raise HTTPException(502, result.get("error", "LLM unavailable"))
        
    # Update the tracking record with the new description (which has actionable steps)
    if "description" in result:
        t.notizen = result["description"]
        db.commit()
        db.refresh(t)
        
    # We return the updated tracker record
    from api.schemas.common import MarketingTrackerOut
    
    data = MarketingTrackerOut.model_validate(t).model_dump()
    data["title"] = result.get("title", payload.current_title)
    data["description"] = result.get("description", payload.current_description)
    data["category"] = payload.category or ""
    
    return data
