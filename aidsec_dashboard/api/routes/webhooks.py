"""Webhook handlers for third-party integrations (e.g., Brevo Inbound Parse)."""
import os
from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
from datetime import datetime

from api.dependencies import get_db
from database.models import (
    Lead,
    CampaignLead,
    FollowUp,
    LeadStatus,
    StatusHistory
)
from services.telegram_service import process_telegram_update

router = APIRouter(tags=["webhooks"])


def _telegram_secret_ok(request: Request) -> bool:
    expected = os.getenv("TELEGRAM_WEBHOOK_SECRET", "").strip()
    if not expected:
        return True

    header_value = request.headers.get("x-telegram-bot-api-secret-token", "").strip()
    query_value = request.query_params.get("secret", "").strip()
    return header_value == expected or query_value == expected

@router.post("/webhooks/inbound-email")
async def handle_inbound_email(request: Request, db: Session = Depends(get_db)):
    """
    Handle inbound emails parsed by Brevo or SendGrid webhooks.
    Pauses active campaigns for the lead and creates a Follow-Up task.
    """
    payload = await request.json()

    # Extract sender email (formats vary between Brevo/SendGrid, handle basic patterns)
    sender_email = None
    if "From" in payload:
        sender_email = payload["From"]
    elif "items" in payload and len(payload["items"]) > 0:
        # Brevo structure
        sender_email = payload["items"][0].get("From", {}).get("Address")
    
    if not sender_email:
        # Try to parse string formats like "Name <email@domain.com>"
        sender_str = payload.get("from", "")
        if "<" in sender_str and ">" in sender_str:
            sender_email = sender_str.split("<")[1].split(">")[0]
        else:
            sender_email = sender_str

    if not sender_email:
        return {"status": "ignored", "reason": "No sender email found"}

    # Find lead
    lead = db.query(Lead).filter(Lead.email.ilike(f"%{sender_email}%")).first()
    if not lead:
        return {"status": "ignored", "reason": "Lead not found"}

    # Pause active campaigns
    active_campaigns = db.query(CampaignLead).filter(
        CampaignLead.lead_id == lead.id,
        CampaignLead.cl_status == "aktiv"
    ).all()
    
    for cl in active_campaigns:
        cl.cl_status = "pausiert"

    # Create FollowUp Task
    subject = payload.get("Subject", payload.get("subject", "Antwort auf Kampagne"))
    new_task = FollowUp(
        lead_id=lead.id,
        datum=datetime.utcnow(),
        notiz=f"Antwort erhalten: {subject}",
        erledigt=False
    )
    db.add(new_task)

    # Move Lead state to PENDING if OFFEN
    if lead.status == LeadStatus.OFFEN:
        old_status = lead.status
        lead.status = LeadStatus.PENDING
        db.add(StatusHistory(lead_id=lead.id, von_status=old_status, zu_status=LeadStatus.PENDING))

    db.commit()
    
    return {
        "status": "success",
        "action": f"Paused {len(active_campaigns)} campaigns and created a follow-up for lead {lead.id}"
    }


@router.post("/webhooks/telegram")
async def handle_telegram_webhook(request: Request, db: Session = Depends(get_db)):
    """Handle Telegram bot updates and map commands to task queue operations."""
    if not _telegram_secret_ok(request):
        return {"ok": False, "error": "invalid_secret"}

    payload = await request.json()
    return process_telegram_update(payload, db)


@router.get("/webhooks/telegram/health")
def telegram_webhook_health():
    return {
        "ok": True,
        "webhook_secret_configured": bool(os.getenv("TELEGRAM_WEBHOOK_SECRET", "").strip()),
        "allowed_chat_ids_configured": bool(os.getenv("TELEGRAM_ALLOWED_CHAT_IDS", "").strip()),
        "allowed_user_ids_configured": bool(os.getenv("TELEGRAM_ALLOWED_USER_IDS", "").strip()),
    }
