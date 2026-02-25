"""Campaign endpoints: CRUD, lead assignment, step advancement."""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.orm import Session, joinedload
from api.dependencies import get_db, verify_api_key
from api.schemas.campaign import (
    CampaignOut,
    CampaignCreate,
    CampaignUpdate,
    CampaignLeadOut,
    AssignLeadsRequest,
)
from services.llm_service import get_llm_service
from database.models import (
    Campaign,
    CampaignLead,
    CampaignStatus,
    Lead,
    LeadStatus,
    AgentTask,
    EmailStatus,
    StatusHistory,
)

router = APIRouter(tags=["campaigns"], dependencies=[Depends(verify_api_key)])

DEFAULT_SEQUENZ = [
    {"typ": "erstkontakt", "delay_tage": 0, "template_id": None},
    {"typ": "nachfassen", "delay_tage": 3, "template_id": None},
    {"typ": "angebot", "delay_tage": 7, "template_id": None},
]


def _campaign_to_out(c: Campaign) -> CampaignOut:
    leads_count = len(c.campaign_leads) if c.campaign_leads else 0
    completed = sum(1 for cl in (c.campaign_leads or []) if cl.cl_status == "abgeschlossen")
    return CampaignOut(
        id=c.id,
        name=c.name,
        beschreibung=c.beschreibung,
        kategorie_filter=c.kategorie_filter.value if c.kategorie_filter else None,
        sequenz=c.sequenz,
        start_datum=c.start_datum,
        end_datum=c.end_datum,
        status=c.status.value if hasattr(c.status, "value") else str(c.status),
        created_at=c.created_at,
        leads_count=leads_count,
        completed_count=completed,
    )


@router.get("/campaigns", response_model=list[CampaignOut])
def list_campaigns(db: Session = Depends(get_db)):
    campaigns = (
        db.query(Campaign)
        .options(joinedload(Campaign.campaign_leads))
        .order_by(Campaign.created_at.desc())
        .all()
    )
    return [_campaign_to_out(c) for c in campaigns]


@router.get("/campaigns/{campaign_id}", response_model=CampaignOut)
def get_campaign(campaign_id: int, db: Session = Depends(get_db)):
    camp = db.query(Campaign).options(joinedload(Campaign.campaign_leads)).filter(Campaign.id == campaign_id).first()
    if not camp:
        raise HTTPException(404, "Campaign not found")
    return _campaign_to_out(camp)


@router.post("/campaigns", response_model=CampaignOut, status_code=201)
def create_campaign(payload: CampaignCreate, db: Session = Depends(get_db)):
    camp = Campaign(
        name=payload.name,
        beschreibung=payload.beschreibung,
        kategorie_filter=LeadKategorie(payload.kategorie_filter) if payload.kategorie_filter else None,
        sequenz=payload.sequenz or DEFAULT_SEQUENZ,
        status=CampaignStatus.ENTWURF,
    )
    db.add(camp)
    db.commit()
    db.refresh(camp)
    return _campaign_to_out(camp)


@router.patch("/campaigns/{campaign_id}", response_model=CampaignOut)
def update_campaign(campaign_id: int, payload: CampaignUpdate, db: Session = Depends(get_db)):
    camp = db.query(Campaign).options(joinedload(Campaign.campaign_leads)).filter(Campaign.id == campaign_id).first()
    if not camp:
        raise HTTPException(404, "Campaign not found")

    if payload.name is not None:
        camp.name = payload.name
    if payload.beschreibung is not None:
        camp.beschreibung = payload.beschreibung
    if payload.status is not None:
        new_status = CampaignStatus(payload.status)
        if new_status == CampaignStatus.AKTIV and camp.status == CampaignStatus.ENTWURF:
            camp.start_datum = datetime.utcnow()
            _init_next_send(db, camp)
        camp.status = new_status

    db.commit()
    db.refresh(camp)
    return _campaign_to_out(camp)


@router.delete("/campaigns/{campaign_id}", status_code=204)
def delete_campaign(campaign_id: int, db: Session = Depends(get_db)):
    camp = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    if not camp:
        raise HTTPException(404, "Campaign not found")
    db.delete(camp)
    db.commit()


@router.get("/campaigns/{campaign_id}/leads", response_model=list[CampaignLeadOut])
def campaign_leads(campaign_id: int, db: Session = Depends(get_db)):
    cls = (
        db.query(CampaignLead)
        .options(joinedload(CampaignLead.lead))
        .filter(CampaignLead.campaign_id == campaign_id)
        .all()
    )
    result = []
    for cl in cls:
        lead = cl.lead  # Already loaded via joinedload
        result.append(CampaignLeadOut(
            id=cl.id,
            campaign_id=cl.campaign_id,
            lead_id=cl.lead_id,
            current_step=cl.current_step,
            next_send_at=cl.next_send_at,
            cl_status=cl.cl_status,
            lead_firma=lead.firma if lead else None,
            lead_email=lead.email if lead else None,
            lead_stadt=lead.stadt if lead else None,
        ))
    return result


@router.post("/campaigns/{campaign_id}/leads")
def assign_leads(campaign_id: int, payload: AssignLeadsRequest, db: Session = Depends(get_db)):
    camp = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    if not camp:
        raise HTTPException(404, "Campaign not found")

    existing_ids = {cl.lead_id for cl in db.query(CampaignLead).filter(CampaignLead.campaign_id == campaign_id).all()}
    added = 0
    for lid in payload.lead_ids:
        if lid not in existing_ids:
            db.add(CampaignLead(campaign_id=campaign_id, lead_id=lid, current_step=0, cl_status="aktiv"))
            added += 1
    db.commit()
    return {"added": added}


@router.patch("/campaigns/{campaign_id}/leads/{cl_id}")
def update_campaign_lead(campaign_id: int, cl_id: int, status: str, db: Session = Depends(get_db)):
    cl = db.query(CampaignLead).filter(CampaignLead.id == cl_id, CampaignLead.campaign_id == campaign_id).first()
    if not cl:
        raise HTTPException(404, "Campaign lead not found")
    cl.cl_status = status
    db.commit()
    return {"updated": True}


@router.delete("/campaigns/{campaign_id}/leads/{cl_id}", status_code=204)
def remove_campaign_lead(campaign_id: int, cl_id: int, db: Session = Depends(get_db)):
    cl = db.query(CampaignLead).filter(CampaignLead.id == cl_id, CampaignLead.campaign_id == campaign_id).first()
    if not cl:
        raise HTTPException(404, "Campaign lead not found")
    db.delete(cl)
    db.commit()


def _init_next_send(db: Session, campaign: Campaign):
    seq = campaign.sequenz or DEFAULT_SEQUENZ
    if not seq:
        return
    first_delay = seq[0].get("delay_tage", 0)
    target = datetime.utcnow() + timedelta(days=first_delay)
    for cl in campaign.campaign_leads:
        if cl.cl_status == "aktiv" and cl.current_step == 0 and not cl.next_send_at:
            cl.next_send_at = target
    db.flush()

@router.post("/campaigns/auto-followup")
def trigger_auto_followup(db: Session = Depends(get_db)):
    """Find leads contacted >7 days ago with no response, queue them for an automated follow-up via AgentTask."""
    seven_days_ago = datetime.utcnow() - timedelta(days=7)
    
    leads = db.query(Lead).filter(
        Lead.status == LeadStatus.PENDING,
        Lead.updated_at <= seven_days_ago
    ).all()
    
    queued = 0
    for lead in leads:
        existing = db.query(AgentTask).filter(
            AgentTask.target_id == lead.id, 
            AgentTask.task_type == "draft_followup", 
            AgentTask.status == "pending"
        ).first()
        
        if not existing:
            task = AgentTask(
                agent_type="outreach",
                task_type="draft_followup",
                target_id=lead.id,
                status="pending",
                context={"reason": "Auto-Follow-up 7 Days", "auto": True}
            )
            db.add(task)
            queued += 1
            
    db.commit()
    return {"success": True, "queued_followups": queued}

@router.post("/campaigns/process-due")
def process_due_campaigns(db: Session = Depends(get_db)):
    """
    Finds all active campaign leads that are due, and queues them as an 'AgentTask'
    for the external OpenClaw Agent 2 (SDR) to pull and process asynchronously over Tailscale.
    """
    now = datetime.utcnow()
    due_leads = (
        db.query(CampaignLead)
        .join(Campaign)
        .filter(
            CampaignLead.cl_status == "aktiv",
            Campaign.status == CampaignStatus.AKTIV,
            CampaignLead.next_send_at <= now,
        )
        .all()
    )

    tasks_queued = 0

    for cl in due_leads:
        seq = cl.campaign.sequenz or DEFAULT_SEQUENZ
        if cl.current_step >= len(seq):
            cl.cl_status = "abgeschlossen"
            continue

        step_config = seq[cl.current_step]
        email_type = step_config.get("typ", "erstkontakt")
        
        # Check if lead exists and is not won/lost or already replied
        lead = db.query(Lead).filter(Lead.id == cl.lead_id).first()
        if not lead or lead.status in [LeadStatus.GEWONNEN, LeadStatus.VERLOREN, LeadStatus.PENDING]:
            cl.cl_status = "pausiert"
            continue
            
        # Queue the task for Agent 2 instead of executing LLM directly
        agent_task = AgentTask(
            task_type="GENERATE_DRAFT",
            lead_id=lead.id,
            payload={
                "campaign_id": cl.campaign_id,
                "email_type": email_type
            },
            status="pending"
        )
        db.add(agent_task)
        tasks_queued += 1

        # Advance to next step
        cl.current_step += 1
        if cl.current_step < len(seq):
            next_delay = seq[cl.current_step].get("delay_tage", 7)
            cl.next_send_at = now + timedelta(days=next_delay)
        else:
            cl.cl_status = "abgeschlossen"

    db.commit()
    return {"processed": len(due_leads), "tasks_queued": tasks_queued}
