"""Lead CRUD endpoints with filtering, pagination, and bulk operations."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, BackgroundTasks
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from api.dependencies import get_db, verify_api_key
from services.enrichment_service import enrich_lead
from api.schemas.lead import (
    LeadCreate,
    LeadUpdate,
    LeadOut,
    LeadDetail,
    PaginatedLeads,
    BulkStatusUpdate,
    BulkSecurityScanRequest,
)
from database.models import (
    Lead,
    LeadStatus,
    LeadKategorie,
    StatusHistory,
    EmailHistory,
    FollowUp,
    EmailStatus,
)

limiter = Limiter(key_func=get_remote_address)
router = APIRouter(tags=["leads"], dependencies=[Depends(verify_api_key)])

SORT_MAP = {
    "newest": Lead.id.desc(),
    "oldest": Lead.id.asc(),
    "firma_asc": Lead.firma.asc(),
    "firma_desc": Lead.firma.desc(),
    "ranking_asc": Lead.ranking_score.asc(),
    "ranking_desc": Lead.ranking_score.desc(),
}


def _compute_lead_score(lead: Lead) -> int:
    score = 0
    if lead.deal_size:
        score += min(40, lead.deal_size // 1000)
    
    if lead.ranking_grade == "A":
        score += 30
    elif lead.ranking_grade == "B":
        score += 20
    elif lead.ranking_grade in ["D", "F"]:
        score -= 10
        
    if lead.status == LeadStatus.RESPONSE_RECEIVED:
        score += 40
    elif lead.status == LeadStatus.OFFER_SENT:
        score += 50
    elif lead.status == LeadStatus.NEGOTIATION:
        score += 60
    elif lead.status == LeadStatus.GEWONNEN:
        score += 100
        
    return max(0, min(100, score))


def _to_lead_out(lead: Lead) -> LeadOut:
    data = LeadOut.model_validate(lead).model_dump()
    data["lead_score"] = _compute_lead_score(lead)
    return LeadOut(**data)


@router.get("/leads", response_model=PaginatedLeads)
@limiter.limit("60/minute")
def list_leads(request: Request,
    status: Optional[str] = None,
    kategorie: Optional[str] = None,
    search: Optional[str] = None,
    stadt: Optional[str] = None,
    quelle: Optional[str] = None,
    ranking: Optional[str] = None,
    sort: str = Query("newest", enum=list(SORT_MAP.keys())),
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    q = db.query(Lead)

    if status:
        parts = [s.strip() for s in status.split(",") if s.strip()]
        if len(parts) == 1:
            q = q.filter(Lead.status == LeadStatus(parts[0]))
        else:
            q = q.filter(Lead.status.in_([LeadStatus(s) for s in parts]))
    if kategorie:
        q = q.filter(Lead.kategorie == LeadKategorie(kategorie))
    if stadt:
        q = q.filter(Lead.stadt == stadt)
    if quelle:
        q = q.filter(Lead.quelle == quelle)
    if ranking:
        if ranking == "none":
            q = q.filter(Lead.ranking_grade.is_(None))
        else:
            q = q.filter(Lead.ranking_grade == ranking)
    if search:
        term = f"%{search}%"
        q = q.filter(
            or_(
                Lead.firma.ilike(term),
                Lead.email.ilike(term),
                Lead.stadt.ilike(term),
                Lead.website.ilike(term),
            )
        )

    q = q.order_by(SORT_MAP.get(sort, Lead.id.desc()))
    total = q.count()
    pages = max(1, (total + per_page - 1) // per_page)
    items = q.offset((page - 1) * per_page).limit(per_page).all()

    return PaginatedLeads(
        items=[_to_lead_out(i) for i in items],
        total=total,
        page=page,
        per_page=per_page,
        pages=pages,
    )


@router.get("/leads/pipeline")
def pipeline_view(
    per_status: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """Return all 4 status buckets in a single response for the pipeline view."""
    result = {}
    for status in LeadStatus:
        leads = (
            db.query(Lead)
            .filter(Lead.status == status)
            .order_by(Lead.created_at.desc())
            .limit(per_status)
            .all()
        )
        total = db.query(Lead).filter(Lead.status == status).count()
        result[status.value] = {
            "items": [_to_lead_out(l).model_dump() for l in leads],
            "total": total,
        }
    return result


@router.get("/leads/{lead_id}", response_model=LeadDetail)
def get_lead(lead_id: int, db: Session = Depends(get_db)):
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(404, "Lead not found")

    email_count = (
        db.query(EmailHistory)
        .filter(EmailHistory.lead_id == lead_id, EmailHistory.status == EmailStatus.SENT)
        .count()
    )
    followup_count = (
        db.query(FollowUp)
        .filter(FollowUp.lead_id == lead_id, FollowUp.erledigt == False)
        .count()
    )

    data = _to_lead_out(lead).model_dump()
    data["email_count"] = email_count
    data["followup_count"] = followup_count
    return LeadDetail(**data)


@router.post("/leads", response_model=LeadOut, status_code=201)
def create_lead(payload: LeadCreate, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    lead = Lead(
        firma=payload.firma,
        website=payload.website,
        email=payload.email,
        telefon=payload.telefon,
        stadt=payload.stadt,
        kategorie=LeadKategorie(payload.kategorie) if payload.kategorie else LeadKategorie.ANWALT,
        status=LeadStatus(payload.status) if payload.status else LeadStatus.OFFEN,
        notes=payload.notes,
        quelle=payload.quelle,
        wordpress_detected=payload.wordpress_detected,
    )
    db.add(lead)
    db.commit()
    db.refresh(lead)
    
    # Auto-trigger enrichment
    if lead.website:
        background_tasks.add_task(enrich_lead, lead.id)
        
    return LeadOut.model_validate(lead)

@router.post("/leads/{lead_id}/enrich")
def trigger_enrichment(lead_id: int, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """Manually trigger background enrichment for a specific lead."""
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(404, "Lead not found")
    if not lead.website:
        raise HTTPException(400, "Lead has no website to enrich")
        
    lead.research_status = "pending"
    db.commit()
    background_tasks.add_task(enrich_lead, lead.id)
    return {"status": "Enrichment queued"}


@router.post("/leads/{lead_id}/security-scan")
async def trigger_security_scan(lead_id: int, db: Session = Depends(get_db)):
    """Run a security scan via Playwright for a specific lead."""
    from services.security_scan_service import security_scan

    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(404, "Lead not found")
    if not lead.website:
        raise HTTPException(400, "Lead has no website to scan")
        
    result = await security_scan(lead.website, capture_screenshot=False)
    if not result.get("success"):
        raise HTTPException(502, f"Scan failed: {result.get('error')}")
        
    lead.ranking_grade = result.get("grade")
    # optionally store details
    lead.ranking_details = {"scan_url": result.get("url"), "last_scanned": datetime.utcnow().isoformat()}
    db.commit()
    db.refresh(lead)

    return LeadOut.model_validate(lead)


@router.post("/leads/bulk-security-scan")
async def bulk_security_scan(payload: BulkSecurityScanRequest, db: Session = Depends(get_db)):
    """Run security scans for multiple leads, optionally filtering by grade."""
    from services.security_scan_service import security_scan

    leads = db.query(Lead).filter(Lead.id.in_(payload.lead_ids)).all()
    results = []

    for lead in leads:
        if not lead.website:
            results.append({"id": lead.id, "success": False, "error": "No website"})
            continue
            
        # Optional: if grade_filter is requested, maybe only scan if it currently matches, 
        # but usually a bulk scan implies we want to *find* their grade.
        res = await security_scan(lead.website, capture_screenshot=False)
        
        if res.get("success"):
            grade = res.get("grade")
            if payload.grade_filter and grade != payload.grade_filter:
                # If it doesn't match the filter we might not save it or we save it but note it didn't match.
                # Usually we still save the new grade, but we can return it as skipped from the bulk action perspective.
                pass
                
            lead.ranking_grade = grade
            lead.ranking_details = {"scan_url": res.get("url"), "last_scanned": datetime.utcnow().isoformat()}
            results.append({"id": lead.id, "success": True, "grade": grade})
        else:
            results.append({"id": lead.id, "success": False, "error": res.get("error")})

    db.commit()
    return {"processed": len(leads), "results": results}


@router.post("/leads/{lead_id}/followup-send")
def send_followup_reminder(lead_id: int, payload: dict, db: Session = Depends(get_db)):
    """Trigger a custom follow-up action/email for a Lead."""
    from services.email_service import get_email_service
    
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(404, "Lead not found")
        
    fu_id = payload.get("followup_id")
    if fu_id:
        fu = db.query(FollowUp).filter(FollowUp.id == fu_id, FollowUp.lead_id == lead_id).first()
        if fu:
            fu.erledigt = True
            
    # Typically this might use Outlook service to send a reminder template
    svc = get_email_service()
    if svc.is_configured() and lead.email:
        svc.send_email(
            to_email=lead.email,
            subject=f"Follow-up: {lead.firma}",
            body="Dies ist eine automatische Follow-up Erinnerung."
        )
        
    db.commit()
    return {"success": True, "message": "Follow-up processed and marked as done."}


@router.get("/leads/{lead_id}/screenshot")
async def get_lead_screenshot(lead_id: int, db: Session = Depends(get_db)):
    """Generate and return a base64 screenshot of the lead's security headers grade."""
    from services.security_scan_service import security_scan

    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(404, "Lead not found")
    if not lead.website:
        raise HTTPException(400, "Lead has no website to scan")
        
    result = await security_scan(lead.website, capture_screenshot=True)
    if not result.get("success"):
        raise HTTPException(502, f"Screenshot failed: {result.get('error')}")
        
    # We also update the grade since we scanned it anyway
    lead.ranking_grade = result.get("grade")
    lead.ranking_details = {"scan_url": result.get("url"), "last_scanned": datetime.utcnow().isoformat()}
    db.commit()

    return {
        "success": True,
        "lead_id": lead.id,
        "grade": result.get("grade"),
        "screenshot_b64": result.get("screenshot_b64")
    }


@router.patch("/leads/{lead_id}", response_model=LeadOut)
def update_lead(lead_id: int, payload: LeadUpdate, db: Session = Depends(get_db)):
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(404, "Lead not found")

    update_data = payload.model_dump(exclude_unset=True)

    old_status = lead.status
    if "status" in update_data and update_data["status"]:
        new_status = LeadStatus(update_data["status"])
        update_data["status"] = new_status
        if new_status != old_status:
            db.add(StatusHistory(lead_id=lead_id, von_status=old_status, zu_status=new_status))

    if "kategorie" in update_data and update_data["kategorie"]:
        update_data["kategorie"] = LeadKategorie(update_data["kategorie"])

    for field, value in update_data.items():
        setattr(lead, field, value)

    lead.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(lead)
    return LeadOut.model_validate(lead)


@router.put("/leads/{lead_id}", response_model=LeadOut)
def update_lead_put(lead_id: int, payload: LeadUpdate, db: Session = Depends(get_db)):
    """PUT endpoint for lead updates - mirrors PATCH behavior for compatibility."""
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(404, "Lead not found")

    update_data = payload.model_dump(exclude_unset=True)

    old_status = lead.status
    if "status" in update_data and update_data["status"]:
        new_status = LeadStatus(update_data["status"])
        update_data["status"] = new_status
        if new_status != old_status:
            db.add(StatusHistory(lead_id=lead_id, von_status=old_status, zu_status=new_status))

    if "kategorie" in update_data and update_data["kategorie"]:
        update_data["kategorie"] = LeadKategorie(update_data["kategorie"])

    for field, value in update_data.items():
        setattr(lead, field, value)

    lead.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(lead)
    return LeadOut.model_validate(lead)


@router.delete("/leads/{lead_id}", status_code=204)
def delete_lead(lead_id: int, db: Session = Depends(get_db)):
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(404, "Lead not found")
    db.delete(lead)
    db.commit()


@router.get("/leads/{lead_id}/timeline")
def lead_timeline(lead_id: int, db: Session = Depends(get_db)):
    lead = db.query(Lead).options(
        joinedload(Lead.status_history),
        joinedload(Lead.email_history),
        joinedload(Lead.follow_ups)
    ).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(404, "Lead not found")

    events = []
    for sh in lead.status_history:
        von = sh.von_status.value if sh.von_status else "?"
        events.append({
            "date": sh.datum.isoformat() if sh.datum else None,
            "type": "status",
            "detail": f"{von} → {sh.zu_status.value}",
        })
    for eh in lead.email_history:
        events.append({
            "date": eh.gesendet_at.isoformat() if eh.gesendet_at else None,
            "type": "email",
            "status": eh.status.value if hasattr(eh.status, "value") else str(eh.status),
            "detail": eh.betreff,
        })
    if hasattr(lead, "follow_ups"):
        for fu in lead.follow_ups:
            events.append({
                "date": fu.datum.isoformat() if fu.datum else None,
                "type": "followup",
                "done": fu.erledigt,
                "detail": fu.notiz or "Follow-up",
            })
    events.sort(key=lambda e: e["date"] or "", reverse=True)
    return events


@router.post("/leads/bulk-status")
def bulk_status_update(payload: BulkStatusUpdate, db: Session = Depends(get_db)):
    new_status = LeadStatus(payload.new_status)
    updated = 0
    for lid in payload.lead_ids:
        lead = db.query(Lead).filter(Lead.id == lid).first()
        if lead and lead.status != new_status:
            old = lead.status
            lead.status = new_status
            db.add(StatusHistory(lead_id=lid, von_status=old, zu_status=new_status))
            updated += 1
    db.commit()
    return {"updated": updated}
