"""Research API endpoints for automated lead data collection."""
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
import asyncio
import logging

from api.dependencies import get_db, verify_api_key
from database.models import Lead, LeadStatus
from services.research_service import get_research_service

logger = logging.getLogger(__name__)
router = APIRouter(tags=["research"], dependencies=[Depends(verify_api_key)])


@router.post("/leads/{lead_id}/research")
def research_lead(lead_id: int, db: Session = Depends(get_db)):
    """
    Manually trigger research for a specific lead.
    Scrapes the lead's website to collect contact information.
    """
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(404, "Lead not found")

    if not lead.website:
        raise HTTPException(400, "Lead has no website URL")

    # Update status to in_progress
    lead.research_status = "in_progress"
    db.commit()

    try:
        # Run research
        service = get_research_service()
        results = service.research_lead(lead.website, lead.firma)

        # Update lead with results
        if results.get("email"):
            lead.email = results["email"]
        if results.get("phone"):
            lead.telefon = results["phone"]
        if results.get("linkedin"):
            lead.linkedin = results["linkedin"]
        if results.get("xing"):
            lead.xing = results["xing"]

        # Store full results in JSON field
        lead.research_data = results
        lead.research_status = "completed" if not results.get("error") else "failed"
        lead.research_last = datetime.utcnow()

        db.commit()
        db.refresh(lead)

        return {
            "lead_id": lead_id,
            "status": lead.research_status,
            "data": results
        }

    except Exception as e:
        logger.error(f"Research failed for lead {lead_id}: {e}")
        lead.research_status = "failed"
        db.commit()
        raise HTTPException(500, f"Research failed: {str(e)}")


@router.get("/leads/{lead_id}/research-status")
def get_research_status(lead_id: int, db: Session = Depends(get_db)):
    """Get the current research status for a lead."""
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(404, "Lead not found")

    return {
        "lead_id": lead_id,
        "status": lead.research_status,
        "last_research": lead.research_last.isoformat() if lead.research_last else None,
        "has_website": bool(lead.website),
        "data": lead.research_data
    }


@router.post("/leads/research-missing")
def research_missing_leads(
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """
    Research all leads that have a website but are missing contact information.
    """
    # Find leads with website but missing email or phone
    leads = db.query(Lead).filter(
        Lead.website.isnot(None),
        Lead.website != "",
        Lead.research_status != "in_progress",
        (Lead.email.is_(None)) | (Lead.telefon.is_(None))
    ).limit(limit).all()

    if not leads:
        return {
            "message": "No leads need research",
            "processed": 0
        }

    service = get_research_service()
    processed = 0
    results = []

    for lead in leads:
        try:
            # Set status to in_progress
            lead.research_status = "in_progress"
            db.commit()

            # Run research
            research_results = service.research_lead(lead.website, lead.firma)

            # Update lead
            if research_results.get("email"):
                lead.email = research_results["email"]
            if research_results.get("phone"):
                lead.telefon = research_results["phone"]
            if research_results.get("linkedin"):
                lead.linkedin = research_results["linkedin"]
            if research_results.get("xing"):
                lead.xing = research_results["xing"]

            lead.research_data = research_results
            lead.research_status = "completed" if not research_results.get("error") else "failed"
            lead.research_last = datetime.utcnow()

            db.commit()

            results.append({
                "lead_id": lead.id,
                "firma": lead.firma,
                "status": lead.research_status,
                "found": {
                    "email": bool(research_results.get("email")),
                    "phone": bool(research_results.get("phone"))
                }
            })
            processed += 1

        except Exception as e:
            logger.error(f"Research failed for lead {lead.id}: {e}")
            lead.research_status = "failed"
            db.commit()
            results.append({
                "lead_id": lead.id,
                "firma": lead.firma,
                "status": "failed",
                "error": str(e)
            })

    return {
        "message": f"Research completed for {processed} leads",
        "processed": processed,
        "results": results
    }


@router.post("/leads/bulk-research")
def bulk_research_leads(
    lead_ids: list[int],
    db: Session = Depends(get_db)
):
    """Research multiple specific leads by their IDs."""
    results = []

    for lead_id in lead_ids:
        lead = db.query(Lead).filter(Lead.id == lead_id).first()
        if not lead:
            results.append({"lead_id": lead_id, "status": "not_found"})
            continue

        if not lead.website:
            results.append({"lead_id": lead_id, "status": "no_website"})
            continue

        try:
            lead.research_status = "in_progress"
            db.commit()

            service = get_research_service()
            research_results = service.research_lead(lead.website, lead.firma)

            if research_results.get("email"):
                lead.email = research_results["email"]
            if research_results.get("phone"):
                lead.telefon = research_results["phone"]
            if research_results.get("linkedin"):
                lead.linkedin = research_results["linkedin"]
            if research_results.get("xing"):
                lead.xing = research_results["xing"]

            lead.research_data = research_results
            lead.research_status = "completed" if not research_results.get("error") else "failed"
            lead.research_last = datetime.utcnow()

            db.commit()

            results.append({
                "lead_id": lead_id,
                "status": lead.research_status,
                "found": {
                    "email": bool(research_results.get("email")),
                    "phone": bool(research_results.get("phone"))
                }
            })

        except Exception as e:
            logger.error(f"Research failed for lead {lead_id}: {e}")
            lead.research_status = "failed"
            db.commit()
            results.append({
                "lead_id": lead_id,
                "status": "failed",
                "error": str(e)
            })

    return {
        "processed": len(results),
        "results": results
    }
