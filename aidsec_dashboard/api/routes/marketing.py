"""Marketing ideas endpoints: browse, filter, tracker CRUD, AI recommendations."""
from __future__ import annotations

from datetime import datetime
from typing import Optional
import random
import re

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from api.dependencies import get_db, verify_api_key
from api.schemas.common import MarketingTrackerOut, MarketingTrackerCreate, MarketingTrackerUpdate, MarketingGenerateRequest, MarketingOptimizeRequest
from database.models import MarketingIdeaTracker

router = APIRouter(tags=["marketing"], dependencies=[Depends(verify_api_key)])


MARKETING_CATEGORY_HOOKS = {
    "anwalt": {
        "pain": "Mandatsgeheimnis, Reputationsschutz und nDSG-konforme Aussenkommunikation",
        "cta": "15-Minuten Sicherheits-Sprechstunde für Kanzleileitung",
    },
    "praxis": {
        "pain": "Patientenvertrauen, Datenschutz bei Termin- und Kontaktformularen, nDSG-Risiken",
        "cta": "Kurz-Audit für Praxis-Website mit priorisierten Quick-Wins",
    },
    "wordpress": {
        "pain": "Plugin-Risiken, fehlende Hardening-Baselines und Sicherheits-Updates",
        "cta": "WordPress Security Baseline Check inklusive Header-Score",
    },
    "allgemein": {
        "pain": "sichtbare Sicherheitslücken auf öffentlichen Unternehmens-Websites",
        "cta": "kostenfreie Erstanalyse der Security-Header mit Handlungsplan",
    },
}


def _normalize_category(value: str | None) -> str:
    if not value:
        return "allgemein"
    normalized = value.strip().lower()
    if "anw" in normalized:
        return "anwalt"
    if "prax" in normalized or "arzt" in normalized or "medizin" in normalized:
        return "praxis"
    if "wp" in normalized or "word" in normalized:
        return "wordpress"
    return "allgemein"


def _detect_category_from_text(*parts: str | None) -> str:
    haystack = " ".join((p or "") for p in parts).lower()
    if re.search(r"anwalt|kanzlei|mandat", haystack):
        return "anwalt"
    if re.search(r"praxis|patient|arzt|medizin", haystack):
        return "praxis"
    if re.search(r"wordpress|plugin|cms", haystack):
        return "wordpress"
    return "allgemein"


def _build_marketing_fallback(category: str, intent: str | None = None) -> dict:
    from services.marketing_ideas import filter_ideas

    hooks = MARKETING_CATEGORY_HOOKS.get(category, MARKETING_CATEGORY_HOOKS["allgemein"])
    ideas = filter_ideas(search=(intent or "")) if intent else []
    if not ideas:
        ideas = filter_ideas(search=category)
    base_idea = random.choice(ideas) if ideas else None
    base_name = base_idea.get("name") if base_idea else "Swiss Security Trust Sprint"

    title = f"{base_name} – {category.capitalize()} Growth Playbook"
    description = (
        "### Ziel\n"
        f"Positionieren Sie AidSec als erste Sicherheitsadresse für {category if category != 'allgemein' else 'Schweizer KMU'}.\n\n"
        "### Strategischer Hook\n"
        f"Fokus auf: {hooks['pain']}.\n\n"
        "### Actionable Steps\n"
        "- Definieren Sie ein einheitliches Kernversprechen mit klarer Risikobotschaft.\n"
        "- Erstellen Sie eine kurze Landing-Page mit konkreten Vorher/Nachher-Beispielen (F → A).\n"
        "- Starten Sie eine 2-Wochen Outreach-Sequenz mit 3 Touchpoints und messbaren KPIs.\n"
        f"- Integrieren Sie als CTA: {hooks['cta']}.\n\n"
        "### KPI-Set\n"
        "- Antwortquote auf Erstkontakt\n"
        "- Anzahl qualifizierter Erstgespräche\n"
        "- Conversion von Audit zu Angebot"
    )
    return {"success": True, "title": title, "description": description, "fallback": True}


def _build_optimized_fallback(current_title: str, current_description: str, category: str) -> dict:
    hooks = MARKETING_CATEGORY_HOOKS.get(category, MARKETING_CATEGORY_HOOKS["allgemein"])
    title = f"{current_title or 'Marketing-Idee'} – optimiert"
    description = (
        "### Positionierung\n"
        f"Schärfen Sie die Idee auf den Kernnutzen: {hooks['pain']}.\n\n"
        "### 7-Tage Umsetzungsplan\n"
        "- Tag 1: Zielsegment + Messaging finalisieren.\n"
        "- Tag 2-3: Kampagnen-Asset (Landingpage/LinkedIn-Post/E-Mail-Template) erstellen.\n"
        "- Tag 4-5: Outreach an Pilotzielgruppe starten (20-30 Kontakte).\n"
        "- Tag 6-7: Antworten auswerten und Copy iterativ verbessern.\n\n"
        "### Actionable Enhancements\n"
        f"- CTA standardisieren: {hooks['cta']}.\n"
        "- Jede Massnahme mit owner, deadline und KPI versehen.\n"
        "- Einwände in FAQ-Format vorbehandeln (Preis, Aufwand, Risiko).\n\n"
        "### Ausgangsnotiz\n"
        f"{(current_description or '').strip() or 'Keine Ausgangsbeschreibung vorhanden.'}"
    )
    return {"success": True, "title": title, "description": description, "fallback": True}


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
            data["description"] = r.custom_description or r.notizen or idea_details.get("desc")
            data["category"] = idea_details.get("cat")
        else:
            data["title"] = r.custom_title
            data["description"] = r.custom_description or r.notizen
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

    normalized_category = _normalize_category(payload.category)
    llm = get_llm_service()
    try:
        result = llm.generate_marketing_strategy(
            category=normalized_category,
            intent=payload.intent
        )
    except Exception:
        result = {"success": False, "error": "LLM exception"}

    if not result.get("success"):
        return _build_marketing_fallback(normalized_category, payload.intent)

    if not result.get("title") or not result.get("description"):
        return _build_marketing_fallback(normalized_category, payload.intent)

    return result


@router.post("/marketing/tracker/{tracker_id}/optimize", response_model=MarketingTrackerOut)
def optimize_tracker_idea(tracker_id: int, payload: MarketingOptimizeRequest, db: Session = Depends(get_db)):
    t = db.query(MarketingIdeaTracker).filter(MarketingIdeaTracker.id == tracker_id).first()
    if not t:
        raise HTTPException(404, "Tracker entry not found")
        
    from services.llm_service import get_llm_service
    llm = get_llm_service()
    detected_category = _normalize_category(payload.category) if payload.category else _detect_category_from_text(
        payload.current_title,
        payload.current_description,
        t.custom_title,
        t.custom_description,
    )

    try:
        result = llm.optimize_marketing_strategy(
            current_title=payload.current_title,
            current_description=payload.current_description,
            category=detected_category
        )
    except Exception:
        result = {"success": False, "error": "LLM exception"}

    if not result.get("success"):
        result = _build_optimized_fallback(payload.current_title, payload.current_description, detected_category)

    optimized_title = result.get("title") or payload.current_title
    optimized_description = result.get("description") or payload.current_description

    # Update the tracking record with the new description (which has actionable steps)
    t.custom_title = optimized_title
    t.custom_description = optimized_description
    t.notizen = optimized_description
    db.commit()
    db.refresh(t)

    # We return the updated tracker record
    from api.schemas.common import MarketingTrackerOut
    
    data = MarketingTrackerOut.model_validate(t).model_dump()
    data["title"] = optimized_title
    data["description"] = optimized_description
    data["category"] = detected_category
    data["fallback"] = bool(result.get("fallback"))
    
    return data
