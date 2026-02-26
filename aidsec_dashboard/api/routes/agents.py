"""LLM Agent endpoints: lead search, outreach generation, auto-research."""
from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.orm import Session

from api.dependencies import get_db, verify_api_key
from api.schemas.common import AgentSearchRequest, AgentResearchRequest
from api.schemas.email import GenerateEmailRequest
from database.models import Lead, EmailHistory, EmailStatus
from services.llm_service import get_llm_service
from services.ranking_service import get_ranking_service
from services.outreach import parse_llm_json, detect_email_type

router = APIRouter(tags=["agents"], dependencies=[Depends(verify_api_key)])


def _fallback_outreach(lead: Lead, email_type: str) -> dict:
    category = lead.kategorie.value if getattr(lead, "kategorie", None) else "Unternehmen"
    firm = lead.firma or "Ihr Unternehmen"
    website = lead.website or "Ihre Website"

    if email_type == "angebot":
        subject = f"Sicherheits-Check für {firm}"
        body = (
            f"Guten Tag\n\n"
            f"bei einer kurzen Sichtung von {website} sind mir Sicherheitsaspekte aufgefallen, "
            f"die für {category} relevant sind.\n\n"
            f"Wenn Sie möchten, sende ich Ihnen eine kompakte Prioritätenliste mit den ersten "
            f"technischen Massnahmen.\n\n"
            f"Freundliche Grüsse\nAidSec"
        )
    elif email_type == "nachfassen":
        subject = f"Kurze Rückfrage zur Website-Sicherheit"
        body = (
            f"Guten Tag\n\n"
            f"ich wollte kurz nachfassen: Für {firm} wäre ein kurzer Header- und TLS-Check "
            f"ein pragmatischer erster Schritt, um Risiken zu reduzieren.\n\n"
            f"Passt Ihnen dazu ein 10-minütiger Austausch?\n\n"
            f"Freundliche Grüsse\nAidSec"
        )
    else:
        subject = f"Hinweis zur Website-Sicherheit"
        body = (
            f"Guten Tag\n\n"
            f"bei {website} habe ich Punkte gesehen, die für den Schutz sensibler Daten relevant "
            f"sein können.\n\n"
            f"Gerne zeige ich Ihnen in einem kurzen Austausch die wichtigsten Massnahmen für {firm}.\n\n"
            f"Freundliche Grüsse\nAidSec"
        )

    return {"success": True, "betreff": subject, "inhalt": body, "fallback": True}


@router.post("/agents/search")
def search_leads(payload: AgentSearchRequest):
    llm = get_llm_service()
    result = llm.search_leads(
        stadt=payload.stadt,
        kategorie=payload.kategorie,
        branche=payload.branche,
        groesse=payload.groesse,
        anzahl=payload.anzahl,
        extra_kriterien=payload.extra_kriterien,
    )
    if not result.get("success"):
        raise HTTPException(502, result.get("error", "LLM unavailable"))

    try:
        leads = parse_llm_json(result["content"], expect_array=True)
        return {"success": True, "leads": leads}
    except Exception:
        return {"success": True, "raw": result["content"]}


@router.post("/agents/outreach")
def generate_outreach(payload: GenerateEmailRequest, db: Session = Depends(get_db)):
    lead = db.query(Lead).filter(Lead.id == payload.lead_id).first()
    if not lead:
        raise HTTPException(404, "Lead not found")

    llm = get_llm_service()
    try:
        result = llm.generate_outreach_email(lead, db, email_type=payload.email_type)
    except Exception:
        return _fallback_outreach(lead, payload.email_type)

    if not result.get("success"):
        return _fallback_outreach(lead, payload.email_type)

    try:
        parsed = parse_llm_json(result["content"])
        return {"success": True, "betreff": parsed.get("betreff", ""), "inhalt": parsed.get("inhalt", "")}
    except Exception:
        return {"success": True, "raw": result["content"]}


@router.post("/agents/research/{lead_id}")
def research_lead(lead_id: int, db: Session = Depends(get_db)):
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(404, "Lead not found")

    ranking_svc = get_ranking_service()
    if lead.website:
        ranking_result = ranking_svc.check_url(lead.website)
        lead.ranking_score = ranking_result.get("score")
        lead.ranking_grade = ranking_result.get("grade")
        lead.ranking_details = ranking_result.get("headers")
        lead.ranking_checked_at = datetime.utcnow()
        db.flush()

    llm = get_llm_service()
    analysis = llm.analyze_lead(
        firma=lead.firma,
        url=lead.website or "",
        grade=lead.ranking_grade,
        score=lead.ranking_score,
        headers=lead.ranking_details if isinstance(lead.ranking_details, list) else [],
    )

    result = {"ranking": None, "analysis": None}
    if lead.ranking_grade:
        result["ranking"] = {
            "score": lead.ranking_score,
            "grade": lead.ranking_grade,
            "headers": lead.ranking_details,
        }

    if analysis.get("success"):
        try:
            parsed = parse_llm_json(analysis["content"])
            result["analysis"] = parsed
            existing_notes = lead.notes or ""
            summary = parsed.get("zusammenfassung", "")
            if summary and summary not in existing_notes:
                lead.notes = (existing_notes + "\n\n--- Auto-Research ---\n" + summary).strip()
        except Exception:
            result["analysis_raw"] = analysis["content"]

    db.commit()
    return result


@router.get("/agents/llm-status")
def llm_status():
    llm = get_llm_service()
    result = llm.test_connection()
    return result


@router.post("/agents/analyze")
def analyze_lead_direct(
    firma: str,
    url: str,
    grade: str = None,
    score: int = None,
):
    llm = get_llm_service()
    result = llm.analyze_lead(firma=firma, url=url, grade=grade, score=score)
    if not result.get("success"):
        raise HTTPException(502, result.get("error", "LLM unavailable"))
    try:
        parsed = parse_llm_json(result["content"])
        return {"success": True, "analysis": parsed}
    except Exception:
        return {"success": True, "raw": result["content"]}
