"""Email endpoints: send, history, templates, SMTP test."""
from __future__ import annotations

import time as _time
import uuid
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from api.dependencies import get_db, verify_api_key
from api.schemas.email import (
    SendEmailRequest,
    BulkSendRequest,
    BulkPreviewRequest,
    EmailHistoryOut,
    GenerateEmailRequest,
    SmtpTestResult,
    TemplateOut,
    CustomTemplateOut,
    CustomTemplateCreate,
    CustomTemplateUpdate,
    CustomTemplateDuplicate,
    TemplateWithVariablesOut,
    GlobalEmailHistoryOut,
    DraftUpdateRequest,
    BulkDraftApproveRequest,
    ABTestCreate,
    ABTestOut,
    ABTestStats,
    SequenceCreate,
    SequenceUpdate,
    SequenceOut,
    SequenceAssignLeads,
    SequenceStats,
    EmailAnalyticsOverview,
    TemplateAnalytics,
    EmailAnalyticsDashboard,
    EmailAnalyticsByTemplateItem,
    EmailAnalyticsTimelineItem,
    EmailPreviewRequest,
    EmailPreviewResponse,
)

from api.schemas.common import GenericResponse
from database.models import (
    Lead,
    LeadStatus,
    EmailHistory,
    EmailStatus,
    EmailTemplate,
    StatusHistory,
    Settings,
    EmailSequence,
    LeadSequenceAssignment,
    ABTest,
)
from services.email_service import get_email_service, DEFAULT_TEMPLATES
from services.llm_service import get_llm_service
from services.outlook_service import get_outlook_service
from services.outreach import detect_email_type, get_recommended_product, parse_llm_json

router = APIRouter(tags=["emails"], dependencies=[Depends(verify_api_key)])

_bulk_email_jobs: dict[str, dict] = {}


def _load_signature(db: Session) -> dict:
    sig_row = db.query(Settings).filter(Settings.key == "email_signature").first()
    logo_row = db.query(Settings).filter(Settings.key == "signature_logo").first()
    mime_row = db.query(Settings).filter(Settings.key == "signature_logo_mime").first()
    return {
        "text": sig_row.value if sig_row else "",
        "logo_b64": logo_row.value if logo_row else "",
        "logo_mime": mime_row.value if mime_row else "",
    }


@router.post("/emails/send")
def send_email(payload: SendEmailRequest, db: Session = Depends(get_db)):
    lead = db.query(Lead).filter(Lead.id == payload.lead_id).first()
    if not lead:
        raise HTTPException(404, "Lead not found")
    if not lead.email:
        raise HTTPException(400, "Lead has no email address")

    svc = get_email_service()
    if not svc.is_configured():
        raise HTTPException(503, "SMTP not configured")

    sig = _load_signature(db)
    body = payload.body
    if sig.get("text"):
        body = body.rstrip() + "\n\n-- \n" + sig["text"]

    result = svc.send_email(
        to_email=lead.email,
        subject=payload.subject,
        body=body,
        logo_b64=sig.get("logo_b64") or None,
        logo_mime=sig.get("logo_mime") or None,
    )

    status = EmailStatus.SENT if result.get("success") else EmailStatus.FAILED
    eh = EmailHistory(
        lead_id=lead.id,
        betreff=payload.subject,
        inhalt=payload.body,
        status=status,
        gesendet_at=datetime.utcnow() if status == EmailStatus.SENT else None,
        campaign_id=payload.campaign_id,
    )
    db.add(eh)

    if status == EmailStatus.SENT and lead.status == LeadStatus.OFFEN:
        old = lead.status
        lead.status = LeadStatus.PENDING
        db.add(StatusHistory(lead_id=lead.id, von_status=old, zu_status=LeadStatus.PENDING))

    db.commit()

    if not result.get("success"):
        raise HTTPException(502, result.get("error", "Send failed"))
    return {"success": True, "email_id": eh.id}


def _run_bulk_email(job_id: str, lead_ids: list[int], subject_tpl: str, body_tpl: str, delay_seconds: int, subject_variants: list[str] | None = None):
    """Background task: send emails to multiple leads with delay, supporting A/B subjects."""
    from database.database import get_session
    session = get_session()
    job = _bulk_email_jobs[job_id]
    svc = get_email_service()

    try:
        sig_row = session.query(Settings).filter(Settings.key == "email_signature").first()
        logo_row = session.query(Settings).filter(Settings.key == "signature_logo").first()
        mime_row = session.query(Settings).filter(Settings.key == "signature_logo_mime").first()
        sig = {
            "text": sig_row.value if sig_row else "",
            "logo_b64": logo_row.value if logo_row else "",
            "logo_mime": mime_row.value if mime_row else "",
        }

        leads = session.query(Lead).filter(Lead.id.in_(lead_ids)).all()
        lead_map = {l.id: l for l in leads}
        job["total"] = len(lead_ids)

        for i, lid in enumerate(lead_ids):
            if job.get("cancelled"):
                break
            lead = lead_map.get(lid)
            if not lead or not lead.email:
                job["errors"] += 1
                job["completed"] += 1
                continue

            body = body_tpl
            if subject_variants and len(subject_variants) > 0:
                base_subject = subject_variants[i % len(subject_variants)]
            else:
                base_subject = subject_tpl
            subject = base_subject
            variables = {
                "firma": lead.firma or "",
                "stadt": lead.stadt or "Schweiz",
                "website": lead.website or "",
                "ranking_grade": lead.ranking_grade or "?",
                "ranking_score": str(lead.ranking_score or "?"),
            }
            for k, v in variables.items():
                body = body.replace(f"{{{k}}}", v)
                subject = subject.replace(f"{{{k}}}", v)

            full_body = body
            if sig.get("text"):
                full_body = body.rstrip() + "\n\n-- \n" + sig["text"]

            try:
                result = svc.send_email(
                    to_email=lead.email,
                    subject=subject,
                    body=full_body,
                    logo_b64=sig.get("logo_b64") or None,
                    logo_mime=sig.get("logo_mime") or None,
                )
                status = EmailStatus.SENT if result.get("success") else EmailStatus.FAILED
                eh = EmailHistory(
                    lead_id=lead.id, betreff=subject, inhalt=body,
                    status=status,
                    gesendet_at=datetime.utcnow() if status == EmailStatus.SENT else None,
                )
                session.add(eh)

                if status == EmailStatus.SENT and lead.status == LeadStatus.OFFEN:
                    old = lead.status
                    lead.status = LeadStatus.PENDING
                    session.add(StatusHistory(lead_id=lead.id, von_status=old, zu_status=LeadStatus.PENDING))

                session.flush()
                if result.get("success"):
                    job["sent"] += 1
                else:
                    job["errors"] += 1
            except Exception:
                job["errors"] += 1

            job["completed"] += 1

            if i < len(lead_ids) - 1 and delay_seconds > 0:
                _time.sleep(delay_seconds)

        session.commit()
        job["status"] = "done"
    except Exception as e:
        job["status"] = "error"
        job["error"] = str(e)
    finally:
        session.close()


# Predefined templates per feature request
BULK_TEMPLATES = {
    "praxis": {
        "subject": "Sicherheit Ihrer Praxis-Website {firma}",
        "body": "Guten Tag {firma},\n\nwir haben festgestellt, dass Ihre Praxis-Website ({website}) beim Security-Scan die Note {ranking_grade} erhalten hat.\n\nGerne unterstützen wir Sie bei der Behebung.\n\nViele Grüße"
    },
    "kanzlei": {
        "subject": "IT-Sicherheit für Kanzlei {firma}",
        "body": "Guten Tag {firma},\n\nals Kanzlei haben Sie besondere Anforderungen an den Datenschutz. Ihre Website ({website}) weist mit Note {ranking_grade} Mängel auf.\n\nWir beraten Sie gerne unverbindlich."
    },
    "kanzlei_spezial": {
        "subject": "Dringende Sicherheitslücken auf {website}",
        "body": "Sehr geehrte Damen und Herren von {firma},\n\nIhre professionelle Kanzlei-Website hat beim Security Scan lediglich ein {ranking_grade} erzielt. Um Reputationsschäden zu vermeiden, empfehlen wir ein zeitnahes Update.\n\nFreundliche Grüße"
    }
}


@router.post("/emails/bulk-preview")
def preview_bulk_send(payload: BulkPreviewRequest, db: Session = Depends(get_db)):
    """Generate previews for bulk sending."""
    from database.models import Lead
    template_data = BULK_TEMPLATES.get(payload.template)
    if not template_data:
        raise HTTPException(400, f"Template {payload.template} not found")

    leads = db.query(Lead).filter(Lead.id.in_(payload.lead_ids)).all()
    previews = []

    for lead in leads:
        variables = {
            "firma": lead.firma or "Damen und Herren",
            "stadt": lead.stadt or "Ihrer Region",
            "website": lead.website or "",
            "ranking_grade": lead.ranking_grade or "?",
            "ranking_score": str(lead.ranking_score or "?"),
        }
        
        body = template_data["body"]
        subject = template_data["subject"]
        
        for k, v in variables.items():
            body = body.replace(f"{{{k}}}", v)
            subject = subject.replace(f"{{{k}}}", v)

        previews.append({
            "lead_id": lead.id,
            "subject": subject,
            "body": body,
            "email": lead.email
        })

    return {"template": payload.template, "previews": previews}


@router.post("/emails/bulk-send")
def start_bulk_send(
    payload: BulkSendRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    job_id = str(uuid.uuid4())[:8]
    _bulk_email_jobs[job_id] = {
        "status": "running",
        "total": len(payload.lead_ids),
        "completed": 0,
        "sent": 0,
        "errors": 0,
    }
    
    subject = payload.subject
    subject_variants = payload.subject_variants
    body = payload.body
    
    if payload.template and payload.template in BULK_TEMPLATES:
        if not subject_variants and not subject:
            subject = BULK_TEMPLATES[payload.template]["subject"]
        body = BULK_TEMPLATES[payload.template]["body"]
        
    background_tasks.add_task(
        _run_bulk_email, job_id, payload.lead_ids,
        subject, body, payload.delay_seconds, subject_variants
    )
    return {"job_id": job_id, "status": "started"}

@router.get("/emails/bulk-send/{job_id}")
def bulk_send_status(job_id: str):
    job = _bulk_email_jobs.get(job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    return job


@router.post("/emails/bulk-send/{job_id}/cancel")
def cancel_bulk_send(job_id: str):
    job = _bulk_email_jobs.get(job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    job["cancelled"] = True
    return {"cancelled": True}


@router.get("/emails/history/{lead_id}", response_model=list[EmailHistoryOut])
def email_history(lead_id: int, db: Session = Depends(get_db)):
    rows = (
        db.query(EmailHistory)
        .filter(EmailHistory.lead_id == lead_id)
        .order_by(EmailHistory.gesendet_at.desc(), EmailHistory.created_at.desc())
        .all()
    )
    return rows

@router.get("/emails/ab-testing")
def ab_testing_stats(db: Session = Depends(get_db)):
    """Return metrics for each subject line used (A/B testing)."""
    from sqlalchemy import func, case
    from database.models import EmailHistory, Lead, LeadStatus, EmailStatus
    
    # Simple analytics: group by subject, count total sent, count leads who responded
    results = db.query(
        EmailHistory.betreff,
        func.count(EmailHistory.id).label("sent"),
        func.count(
            case((Lead.status.in_([
                LeadStatus.RESPONSE_RECEIVED, 
                LeadStatus.OFFER_SENT, 
                LeadStatus.NEGOTIATION, 
                LeadStatus.GEWONNEN
            ]), 1), else_=None)
        ).label("responded")
    ).join(Lead, Lead.id == EmailHistory.lead_id)\
     .filter(EmailHistory.status == EmailStatus.SENT)\
     .group_by(EmailHistory.betreff)\
     .order_by(func.count(EmailHistory.id).desc())\
     .all()
    
    out = []
    for row in results:
        subject = row[0]
        sent = row[1]
        responded = row[2]
        out.append({
            "subject": subject,
            "sent": sent,
            "responded": responded,
            "response_rate": round(responded / max(1, sent) * 100, 1)
        })
    return out


@router.post("/emails/generate")
def generate_email(payload: GenerateEmailRequest, db: Session = Depends(get_db)):
    lead = db.query(Lead).filter(Lead.id == payload.lead_id).first()
    if not lead:
        raise HTTPException(404, "Lead not found")

    llm = get_llm_service()
    result = llm.generate_outreach_email(lead, db, email_type=payload.email_type)
    if not result.get("success"):
        raise HTTPException(502, result.get("error", "LLM generation failed"))

    try:
        parsed = parse_llm_json(result["content"])
        subject = parsed.get("betreff", "")
        body = parsed.get("inhalt", "")
        return {
            "success": True,
            "betreff": subject,
            "inhalt": body,
            "subject": subject,
            "body": body,
        }
    except Exception:
        return {
            "success": True,
            "raw": result["content"],
            "subject": "",
            "body": result["content"],
        }


@router.post("/emails/preview", response_model=EmailPreviewResponse)
def preview_email(payload: EmailPreviewRequest, db: Session = Depends(get_db)):
    lead = db.query(Lead).filter(Lead.id == payload.lead_id).first()
    if not lead:
        raise HTTPException(404, "Lead not found")

    template = db.query(EmailTemplate).filter(EmailTemplate.id == payload.template_id).first()
    if not template:
        raise HTTPException(404, "Template not found")

    full_name = (
        getattr(lead, "ansprechpartner", None)
        or getattr(lead, "name", None)
        or ""
    ).strip()
    name_parts = full_name.split()
    first_name = name_parts[0] if name_parts else ""
    last_name = " ".join(name_parts[1:]) if len(name_parts) > 1 else ""
    domain = ""
    if lead.website:
        try:
            domain = lead.website.replace("https://", "").replace("http://", "").split("/")[0]
        except Exception:
            domain = lead.website

    greeting = f"Sehr geehrte/r {full_name}" if full_name else "Sehr geehrte Damen und Herren"
    grade = lead.ranking_grade or "?"
    grade_note = f"Note {grade} (ungenügend)" if grade in ["F", "D"] else f"Note {grade}"

    replacements = {
        "{{first_name}}": first_name,
        "{{last_name}}": last_name,
        "{{name}}": full_name or (lead.firma or ""),
        "{{company}}": lead.firma or "",
        "{{domain}}": domain,
        "{{grade}}": grade,
        "{{grade_note}}": grade_note,
        "{{date}}": datetime.utcnow().strftime("%Y-%m-%d"),
        "{{personalized_greeting}}": greeting,
    }

    subject = template.betreff or ""
    body = template.inhalt or ""
    for placeholder, value in replacements.items():
        subject = subject.replace(placeholder, value)
        body = body.replace(placeholder, value)

    if "<" in body and ">" in body:
        html = body
        plain = body.replace("<br>", "\n").replace("<br/>", "\n").replace("<p>", "").replace("</p>", "\n")
    else:
        plain = body
        html = "<p>" + body.replace("\n", "<br/>") + "</p>"

    return EmailPreviewResponse(
        lead_id=lead.id,
        template_id=template.id,
        preview_type=payload.preview_type,
        subject=subject,
        html=html,
        plain=plain,
    )


@router.get("/emails/templates", response_model=list[TemplateOut])
def list_templates():
    return [
        TemplateOut(key=k, name=v["name"], betreff=v["betreff"], inhalt=v["inhalt"])
        for k, v in DEFAULT_TEMPLATES.items()
    ]


@router.post("/emails/smtp-test", response_model=SmtpTestResult)
def smtp_test():
    svc = get_email_service()
    result = svc.test_connection()
    return SmtpTestResult(**result)


@router.get("/emails/daily-count")
def daily_email_count(db: Session = Depends(get_db)):
    from datetime import date
    today_start = datetime.combine(date.today(), datetime.min.time())
    count = (
        db.query(EmailHistory)
        .filter(EmailHistory.status == EmailStatus.SENT, EmailHistory.gesendet_at >= today_start)
        .count()
    )
    return {"count": count, "warning": count >= 10}


@router.get("/emails/history", response_model=list[GlobalEmailHistoryOut])
def global_email_history(
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(50, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db),
):
    from sqlalchemy.orm import joinedload

    # Get total count for pagination info
    total = db.query(EmailHistory).count()
    pages = max(1, (total + per_page - 1) // per_page)

    rows = (
        db.query(EmailHistory)
        .options(joinedload(EmailHistory.lead))
        .order_by(EmailHistory.gesendet_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )
    return [
        GlobalEmailHistoryOut(
            id=r.id,
            lead_id=r.lead_id,
            lead_firma=r.lead.firma if r.lead else None,
            betreff=r.betreff,
            inhalt=r.inhalt,
            status=r.status.value if hasattr(r.status, "value") else str(r.status),
            gesendet_at=r.gesendet_at,
        )
        for r in rows
    ]


@router.get("/emails/drafts", response_model=list[GlobalEmailHistoryOut])
def list_drafts(db: Session = Depends(get_db)):
    """Fetch all pending email drafts generated by AI."""
    from sqlalchemy.orm import joinedload
    rows = (
        db.query(EmailHistory)
        .options(joinedload(EmailHistory.lead))
        .filter(EmailHistory.status == EmailStatus.DRAFT)
        .order_by(EmailHistory.id.desc())
        .all()
    )
    return [
        GlobalEmailHistoryOut(
            id=r.id,
            lead_id=r.lead_id,
            lead_firma=r.lead.firma if r.lead else None,
            betreff=r.betreff,
            inhalt=r.inhalt,
            status=r.status.value if hasattr(r.status, "value") else str(r.status),
            gesendet_at=r.gesendet_at,
        )
        for r in rows
    ]

@router.put("/emails/drafts/{draft_id}")
def update_draft(draft_id: int, payload: DraftUpdateRequest, db: Session = Depends(get_db)):
    """Update a draft's subject and content."""
    draft = db.query(EmailHistory).filter(EmailHistory.id == draft_id, EmailHistory.status == EmailStatus.DRAFT).first()
    if not draft:
        raise HTTPException(404, "Draft not found")
        
    draft.betreff = payload.subject
    draft.inhalt = payload.body
    db.commit()
    return {"success": True}

@router.post("/emails/drafts/bulk-approve")
def bulk_approve_drafts(payload: BulkDraftApproveRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """Approve multiple drafts and submit them to be sent in background."""
    drafts = db.query(EmailHistory).filter(EmailHistory.id.in_(payload.draft_ids), EmailHistory.status == EmailStatus.DRAFT).all()
    
    approved_ids = []
    # Currently just sending synchronously inside loop or we can use background task
    # For simplicity, we just change their status to QUEUED or handle sending here:
    svc = get_email_service()
    
    if not svc.is_configured():
        raise HTTPException(503, "SMTP not configured")
        
    sig = _load_signature(db)
    
    for draft in drafts:
        lead = db.query(Lead).filter(Lead.id == draft.lead_id).first()
        if not lead or not lead.email:
            draft.status = EmailStatus.FAILED
            continue
            
        body = draft.inhalt
        if sig.get("text"):
            body = body.rstrip() + "\n\n-- \n" + sig["text"]
            
        # Send right away (or queue if using real async worker like Celery)
        # Note: If there are many drafts, it's better to background it.
        # But `_run_bulk_email` assumes template variables. We already have the concrete text.
        # Let's send directly for now, or assume this runs fast.
        try:
            res = svc.send_email(
                to_email=lead.email,
                subject=draft.betreff,
                body=body,
                logo_b64=sig.get("logo_b64") or None,
                logo_mime=sig.get("logo_mime") or None,
            )
            if res.get("success"):
                draft.status = EmailStatus.SENT
                draft.gesendet_at = datetime.utcnow()
                approved_ids.append(draft.id)
                
                if lead.status == LeadStatus.OFFEN:
                    old = lead.status
                    lead.status = LeadStatus.PENDING
                    db.add(StatusHistory(lead_id=lead.id, von_status=old, zu_status=LeadStatus.PENDING))
            else:
                draft.status = EmailStatus.FAILED
        except Exception:
            draft.status = EmailStatus.FAILED

    db.commit()
    return {"approved": len(approved_ids), "failed": len(drafts) - len(approved_ids)}


@router.get("/emails/custom-templates", response_model=list[CustomTemplateOut])
def list_custom_templates(db: Session = Depends(get_db)):
    rows = db.query(EmailTemplate).order_by(EmailTemplate.name).all()
    return [CustomTemplateOut.model_validate(r) for r in rows]


@router.post("/emails/custom-templates", response_model=CustomTemplateOut, status_code=201)
def create_custom_template(payload: CustomTemplateCreate, db: Session = Depends(get_db)):
    tpl = EmailTemplate(name=payload.name, betreff=payload.betreff, inhalt=payload.inhalt)
    db.add(tpl)
    db.commit()
    db.refresh(tpl)
    return CustomTemplateOut.model_validate(tpl)


@router.patch("/emails/custom-templates/{tpl_id}", response_model=CustomTemplateOut)
def update_custom_template(tpl_id: int, payload: CustomTemplateCreate, db: Session = Depends(get_db)):
    tpl = db.query(EmailTemplate).filter(EmailTemplate.id == tpl_id).first()
    if not tpl:
        raise HTTPException(404, "Template not found")
    tpl.name = payload.name
    tpl.betreff = payload.betreff
    tpl.inhalt = payload.inhalt
    db.commit()
    db.refresh(tpl)
    return CustomTemplateOut.model_validate(tpl)


@router.delete("/emails/custom-templates/{tpl_id}", status_code=204)
def delete_custom_template(tpl_id: int, db: Session = Depends(get_db)):
    tpl = db.query(EmailTemplate).filter(EmailTemplate.id == tpl_id).first()
    if not tpl:
        raise HTTPException(404, "Template not found")
    db.delete(tpl)
    db.commit()


@router.post("/emails/send-to-outlook")
def send_to_outlook_draft(payload: dict):
    """
    Create an email draft in Outlook.

    Request body:
    - subject: Email subject
    - body: Email body content (plain text)
    - html_body: Optional HTML content
    - to_email: Optional recipient email
    """
    subject = payload.get("subject", "")
    body = payload.get("body", "")
    html_body = payload.get("html_body")
    to_email = payload.get("to_email")

    if not subject:
        raise HTTPException(400, "Subject is required")

    outlook = get_outlook_service()

    if not outlook.is_configured():
        raise HTTPException(503, "Outlook nicht konfiguriert. Bitte in Einstellungen konfigurieren.")

    # Use HTML body if provided, otherwise use plain text
    if html_body:
        result = outlook.create_draft_with_html(
            subject=subject,
            html_body=html_body,
            to_email=to_email
        )
    else:
        result = outlook.create_draft(
            subject=subject,
            body=body,
            to_email=to_email
        )

    if not result.get("success"):
        raise HTTPException(502, result.get("error", "Fehler beim Erstellen des Entwurfs"))

    return {
        "success": True,
        "draft_id": result.get("draft_id"),
        "web_link": result.get("web_link"),
        "message": result.get("message")
    }


@router.get("/emails/outlook-configured")
def outlook_configured():
    """Check if Outlook is configured"""
    outlook = get_outlook_service()
    return {
        "configured": outlook.is_configured(),
        "user_email": outlook.user_email if outlook.is_configured() else None
    }


@router.post("/emails/outlook-draft")
def create_outlook_draft(payload: dict, db: Session = Depends(get_db)):
    """
    Create an Outlook email draft from a lead.

    Request body:
    - lead_id: Lead ID to get email address from
    - subject: Email subject
    - body: Email body content (plain text or HTML)
    """
    lead_id = payload.get("lead_id")
    subject = payload.get("subject", "")
    body = payload.get("body", "")

    if not lead_id:
        raise HTTPException(400, "lead_id is required")
    if not subject:
        raise HTTPException(400, "Subject is required")

    # Get lead
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(404, "Lead not found")

    outlook = get_outlook_service()

    if not outlook.is_configured():
        raise HTTPException(503, "Outlook nicht konfiguriert")

    result = outlook.create_draft_with_html(
        subject=subject,
        html_body=body,
        to_email=lead.email
    )

    if not result.get("success"):
        raise HTTPException(502, result.get("error", "Fehler beim Erstellen des Entwurfs"))

    return {
        "success": True,
        "draft_id": result.get("draft_id"),
        "web_link": result.get("web_link"),
        "message": result.get("message")
    }


# ============ OAuth Endpoints ============

import secrets


@router.get("/emails/outlook/connect")
def outlook_connect():
    """
    Get OAuth authorization URL for connecting Outlook account.
    User should be redirected to this URL to authorize access.
    """
    outlook = get_outlook_service()

    if not outlook.is_configured():
        raise HTTPException(503, "Outlook nicht konfiguriert")

    # Generate state for CSRF protection
    state = secrets.token_urlsafe(32)

    auth_url = outlook.get_authorization_url(state)

    return {
        "authorization_url": auth_url,
        "state": state,
        "message": "Öffnen Sie die URL und melden Sie sich bei Microsoft an"
    }


@router.get("/emails/debug-config")
def debug_config():
    """Diagnostic endpoint to check if keys are loaded (masked)."""
    client_id = os.getenv("OUTLOOK_CLIENT_ID", "")
    client_secret = os.getenv("OUTLOOK_CLIENT_SECRET", "")
    return {
        "client_id_present": bool(client_id),
        "client_id_starts_with": client_id[:4] if client_id else "",
        "client_secret_present": bool(client_secret),
        "client_secret_len": len(client_secret) if client_secret else 0,
        "env_path": os.path.abspath(".env"),
        "cwd": os.getcwd()
    }


@router.get("/emails/outlook/status")
def outlook_status():
    """Check if Outlook is connected and return status."""
    outlook = get_outlook_service()

    if not outlook.is_configured():
        return {"connected": False, "configured": False, "message": "Outlook nicht konfiguriert"}

    connected_user = outlook.get_connected_user()

    if connected_user:
        test_result = outlook.test_connection(connected_user)
        return {
            "connected": True,
            "configured": True,
            "user_email": connected_user,
            "message": test_result.get("detail", "Verbunden")
        }

    return {
        "connected": False,
        "configured": True,
        "message": "Nicht verbunden. Rufen Sie /emails/outlook/connect auf."
    }


@router.post("/emails/outlook/callback")
def outlook_callback(code: str, state: str = ""):
    """
    OAuth callback - exchange authorization code for tokens.
    This should be called after user authorizes the app.
    """
    print(f"DEBUG: Outlook callback received - code: {code[:10]}..., state: {state}")
    outlook = get_outlook_service()

    if not outlook.is_configured():
        print("DEBUG: Outlook not configured")
        raise HTTPException(503, "Outlook nicht konfiguriert (Client ID/Secret fehlen)")

    try:
        token_data = outlook.exchange_code_for_token(code)

        if not token_data:
            print("DEBUG: Token exchange failed - no data returned")
            raise HTTPException(400, "Token-Abruf fehlgeschlagen. Bitte prüfen Sie die Azure-Konfiguration (Redirect URI, Secret).")

        print(f"DEBUG: Successfully connected as {token_data.get('user_email')}")
        return {
            "success": True,
            "user_email": token_data.get("user_email"),
            "message": "Erfolgreich mit Outlook verbunden!"
        }
    except HTTPException as e:
        raise e
    except Exception as e:
        print(f"DEBUG: Critical error in outlook_callback: {str(e)}")
        raise HTTPException(500, f"Interner Fehler beim Outlook-Verbindungsaufbau: {str(e)}")


@router.post("/emails/outlook/disconnect")
def outlook_disconnect():
    """Disconnect Outlook account (clear tokens)."""
    outlook = get_outlook_service()
    outlook.disconnect()
    return {"success": True, "message": "Outlook getrennt"}


@router.post("/emails/outlook/send")
def outlook_send(
    lead_id: int,
    subject: str,
    body: str,
    db: Session = Depends(get_db)
):
    """Send email directly via Outlook (not as draft)."""
    outlook = get_outlook_service()

    if not outlook.is_configured():
        raise HTTPException(503, "Outlook nicht konfiguriert")

    # Get lead
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(404, "Lead nicht gefunden")

    if not lead.email:
        raise HTTPException(400, "Lead hat keine E-Mail-Adresse")

    # Send email
    result = outlook.send_email(
        subject=subject,
        body=body,
        to_email=lead.email
    )

    if not result.get("success"):
        raise HTTPException(502, result.get("error", "Fehler beim Senden"))

    # Save to email history
    email_history = EmailHistory(
        lead_id=lead_id,
        betreff=subject,
        inhalt=body[:500],
        status=EmailStatus.SENT,
        gesendet_at=datetime.utcnow()
    )
    db.add(email_history)
    db.commit()

    return {
        "success": True,
        "message": result.get("message")
    }


@router.get("/emails/outlook/sent")
def outlook_sent_emails(limit: int = 50):
    """Get sent emails from Outlook."""
    outlook = get_outlook_service()

    if not outlook.is_configured():
        raise HTTPException(503, "Outlook nicht konfiguriert")

    result = outlook.get_sent_emails(limit=limit)

    if not result.get("success"):
        raise HTTPException(502, result.get("error", "Fehler beim Abrufen"))

    return {
        "success": True,
        "emails": result.get("emails", []),
        "total": result.get("total", 0)
    }


@router.post("/emails/outlook/sync")
def sync_outlook_emails(limit: int = 50, db: Session = Depends(get_db)):
    """
    Sync sent emails from Outlook to the database.
    Matches emails to leads by email address.
    """
    from database.models import Lead, EmailHistory, EmailStatus
    from datetime import datetime

    outlook = get_outlook_service()

    if not outlook.is_configured():
        raise HTTPException(503, "Outlook nicht konfiguriert")

    # Get sent emails from Outlook
    result = outlook.get_sent_emails(limit=limit)

    if not result.get("success"):
        raise HTTPException(502, result.get("error", "Fehler beim Abrufen"))

    outlook_emails = result.get("emails", [])
    synced = 0
    matched = 0
    skipped = 0
    errors = []

    for email in outlook_emails:
        try:
            outlook_id = email.get("id")
            to_addresses = email.get("to", [])
            subject = email.get("subject", "")
            sent_at_str = email.get("sent_at")

            if not to_addresses:
                skipped += 1
                continue

            # Try to match recipient to a lead
            for to_email in to_addresses:
                lead = db.query(Lead).filter(Lead.email.ilike(to_email)).first()

                if lead:
                    # Check if already synced
                    existing = db.query(EmailHistory).filter(
                        EmailHistory.outlook_message_id == outlook_id
                    ).first()

                    if existing:
                        skipped += 1
                        break

                    # Parse sent_at datetime
                    gesendet_at = None
                    if sent_at_str:
                        try:
                            gesendet_at = datetime.fromisoformat(sent_at_str.replace("Z", "+00:00"))
                        except:
                            pass

                    # Create email history entry
                    email_history = EmailHistory(
                        lead_id=lead.id,
                        betreff=subject,
                        inhalt=email.get("preview", ""),
                        status=EmailStatus.SENT,
                        gesendet_at=gesendet_at,
                        outlook_message_id=outlook_id
                    )
                    db.add(email_history)
                    synced += 1
                    matched += 1
                    break
            else:
                # No matching lead found
                skipped += 1

        except Exception as e:
            errors.append(f"Error processing email {email.get('id')}: {str(e)}")

    db.commit()

    return {
        "success": True,
        "synced": synced,
        "matched": matched,
        "skipped": skipped,
        "errors": errors[:5] if errors else None
    }


@router.post("/emails/outlook/refresh", response_model=GenericResponse)
def refresh_outlook_token():
    """Manual trigger to refresh Outlook OAuth token"""
    svc = get_outlook_service()
    if not svc.is_configured():
        raise HTTPException(400, "Outlook is not configured.")
    
    connected_user = svc.get_connected_user()
    if not connected_user:
        raise HTTPException(400, "No connected Outlook user found.")
        
    new_token = svc.refresh_token(connected_user)
    if new_token:
        # We also trigger a test connection to ensure it was cached property
        conn = svc.test_connection(connected_user)
        if conn.get("success"):
            return GenericResponse(success=True, message="Token successfully refreshed.")
        else:
            return GenericResponse(success=False, message="Token refreshed but connection test failed.")
    
    raise HTTPException(401, "Failed to refresh token. Please re-authenticate.")


@router.get("/emails/synced")
def get_synced_emails(
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """Get all synced (sent) emails with lead information."""
    from database.models import Lead, EmailHistory

    emails = (
        db.query(EmailHistory, Lead)
        .join(Lead, EmailHistory.lead_id == Lead.id)
        .filter(EmailHistory.status == EmailStatus.SENT)
        .order_by(EmailHistory.gesendet_at.desc())
        .limit(limit)
        .all()
    )

    result = []
    for email_history, lead in emails:
        result.append({
            "id": email_history.id,
            "lead_id": lead.id,
            "firma": lead.firma,
            "lead_email": lead.email,
            "betreff": email_history.betreff,
            "inhalt": email_history.inhalt[:200] + "..." if len(email_history.inhalt) > 200 else email_history.inhalt,
            "status": email_history.status.value,
            "gesendet_at": email_history.gesendet_at.isoformat() if email_history.gesendet_at else None,
            "outlook_message_id": email_history.outlook_message_id,
            "campaign_id": email_history.campaign_id
        })

    return {
        "success": True,
        "emails": result,
        "total": len(result)
    }


# ============ Extended Template Endpoints ============

@router.get("/emails/custom-templates/with-variables", response_model=list[TemplateWithVariablesOut])
def list_templates_with_variables(db: Session = Depends(get_db)):
    """List all custom templates with their variable definitions."""
    rows = db.query(EmailTemplate).order_by(EmailTemplate.name, EmailTemplate.version.desc()).all()
    return [TemplateWithVariablesOut.model_validate(r) for r in rows]


@router.patch("/emails/custom-templates/{tpl_id}/extend", response_model=CustomTemplateOut)
def update_custom_template_extended(tpl_id: int, payload: CustomTemplateUpdate, db: Session = Depends(get_db)):
    """Update template with extended fields (category, version, variables)."""
    tpl = db.query(EmailTemplate).filter(EmailTemplate.id == tpl_id).first()
    if not tpl:
        raise HTTPException(404, "Template not found")

    if payload.name is not None:
        tpl.name = payload.name
    if payload.betreff is not None:
        tpl.betreff = payload.betreff
    if payload.inhalt is not None:
        tpl.inhalt = payload.inhalt
    if payload.kategorie is not None:
        from database.models import LeadKategorie
        try:
            tpl.kategorie = LeadKategorie(payload.kategorie)
        except ValueError:
            pass
    if payload.is_ab_test is not None:
        tpl.is_ab_test = payload.is_ab_test
    if payload.variables is not None:
        tpl.variables = payload.variables

    db.commit()
    db.refresh(tpl)
    return CustomTemplateOut.model_validate(tpl)


@router.post("/emails/custom-templates/{tpl_id}/duplicate", response_model=CustomTemplateOut)
def duplicate_template(tpl_id: int, payload: CustomTemplateDuplicate, db: Session = Depends(get_db)):
    """Duplicate a template, optionally as new version."""
    original = db.query(EmailTemplate).filter(EmailTemplate.id == tpl_id).first()
    if not original:
        raise HTTPException(404, "Template not found")

    new_version = 1
    if payload.new_version:
        # Find highest version number
        siblings = db.query(EmailTemplate).filter(
            EmailTemplate.parent_template_id == tpl_id
        ).all()
        if siblings:
            new_version = max(s.version for s in siblings) + 1
        else:
            new_version = original.version + 1

    new_tpl = EmailTemplate(
        name=payload.new_name,
        betreff=original.betreff,
        inhalt=original.inhalt,
        kategorie=original.kategorie,
        is_ab_test=original.is_ab_test,
        version=new_version,
        parent_template_id=tpl_id,
        variables=original.variables,
    )
    db.add(new_tpl)
    db.commit()
    db.refresh(new_tpl)
    return CustomTemplateOut.model_validate(new_tpl)


@router.get("/emails/templates/versions/{tpl_id}")
def get_template_versions(tpl_id: int, db: Session = Depends(get_db)):
    """Get all versions of a template."""
    # Get the root template
    root = db.query(EmailTemplate).filter(EmailTemplate.id == tpl_id).first()
    if not root:
        raise HTTPException(404, "Template not found")

    # Find all related versions
    versions = [root]
    # Check if it has children (newer versions)
    versions.extend(root.children)

    # If this is a child, find siblings and parent
    if root.parent_template_id:
        parent = db.query(EmailTemplate).filter(EmailTemplate.id == root.parent_template_id).first()
        if parent:
            versions.append(parent)
            versions.extend(parent.children)

    # Remove duplicates and sort by version
    seen = set()
    unique_versions = []
    for v in versions:
        if v.id not in seen:
            seen.add(v.id)
            unique_versions.append({
                "id": v.id,
                "version": v.version,
                "name": v.name,
                "betreff": v.betreff,
                "created_at": v.created_at.isoformat() if v.created_at else None,
            })

    return sorted(unique_versions, key=lambda x: x["version"], reverse=True)


# ============ A/B Testing Endpoints ============

@router.post("/emails/ab-tests", response_model=ABTestOut, status_code=201)
def create_ab_test(payload: ABTestCreate, db: Session = Depends(get_db)):
    """Create a new A/B test for subject lines."""
    test = ABTest(
        name=payload.name,
        template_id=payload.template_id,
        subject_a=payload.subject_a,
        subject_b=payload.subject_b,
        distribution_a=payload.distribution_a,
        distribution_b=payload.distribution_b,
        auto_winner_after=payload.auto_winner_after,
    )
    db.add(test)
    db.commit()
    db.refresh(test)
    return ABTestOut.model_validate(test)


@router.get("/emails/ab-tests", response_model=list[ABTestOut])
def list_ab_tests(db: Session = Depends(get_db)):
    """List all A/B tests."""
    tests = db.query(ABTest).order_by(ABTest.created_at.desc()).all()
    return [ABTestOut.model_validate(t) for t in tests]


@router.get("/emails/ab-tests/{test_id}", response_model=ABTestOut)
def get_ab_test(test_id: int, db: Session = Depends(get_db)):
    """Get a specific A/B test."""
    test = db.query(ABTest).filter(ABTest.id == test_id).first()
    if not test:
        raise HTTPException(404, "A/B Test not found")
    return ABTestOut.model_validate(test)


@router.get("/emails/ab-tests/{test_id}/stats", response_model=ABTestStats)
def get_ab_test_stats(test_id: int, db: Session = Depends(get_db)):
    """Get statistics for an A/B test."""
    test = db.query(ABTest).filter(ABTest.id == test_id).first()
    if not test:
        raise HTTPException(404, "A/B Test not found")

    # Calculate rates
    open_rate_a = (test.opens_a / max(1, test.sent_a)) * 100 if test.sent_a else 0
    open_rate_b = (test.opens_b / max(1, test.sent_b)) * 100 if test.sent_b else 0
    click_rate_a = (test.clicks_a / max(1, test.sent_a)) * 100 if test.sent_a else 0
    click_rate_b = (test.clicks_b / max(1, test.sent_b)) * 100 if test.sent_b else 0

    # Determine winner if test is complete
    winner = None
    if test.status == "completed" and test.winner:
        winner = test.winner

    return ABTestStats(
        test_id=test.id,
        name=test.name,
        status=test.status,
        winner=winner,
        variant_a={
            "subject": test.subject_a,
            "sent": test.sent_a,
            "opens": test.opens_a,
            "clicks": test.clicks_a,
            "open_rate": round(open_rate_a, 1),
            "click_rate": round(click_rate_a, 1),
        },
        variant_b={
            "subject": test.subject_b,
            "sent": test.sent_b,
            "opens": test.opens_b,
            "clicks": test.clicks_b,
            "open_rate": round(open_rate_b, 1),
            "click_rate": round(click_rate_b, 1),
        },
    )


@router.post("/emails/ab-tests/{test_id}/start")
def start_ab_test(test_id: int, db: Session = Depends(get_db)):
    """Start an A/B test."""
    test = db.query(ABTest).filter(ABTest.id == test_id).first()
    if not test:
        raise HTTPException(404, "A/B Test not found")

    test.status = "running"
    db.commit()
    return {"success": True, "message": f"A/B Test '{test.name}' started"}


@router.post("/emails/ab-tests/{test_id}/complete")
def complete_ab_test(test_id: int, winner: str = "A", db: Session = Depends(get_db)):
    """Manually complete an A/B test and declare a winner."""
    test = db.query(ABTest).filter(ABTest.id == test_id).first()
    if not test:
        raise HTTPException(404, "A/B Test not found")

    test.status = "completed"
    test.winner = winner
    test.completed_at = datetime.utcnow()
    db.commit()
    return {"success": True, "message": f"Winner: Variant {winner}", "winner": winner}


# ============ Sequence Endpoints ============

@router.post("/emails/sequences", response_model=SequenceOut, status_code=201)
def create_sequence(payload: SequenceCreate, db: Session = Depends(get_db)):
    """Create a new email sequence."""
    sequence = EmailSequence(
        name=payload.name,
        beschreibung=payload.beschreibung,
        steps=[s.model_dump() for s in payload.steps],
    )
    db.add(sequence)
    db.commit()
    db.refresh(sequence)
    return SequenceOut.model_validate(sequence)


@router.get("/emails/sequences", response_model=list[SequenceOut])
def list_sequences(db: Session = Depends(get_db)):
    """List all email sequences."""
    sequences = db.query(EmailSequence).order_by(EmailSequence.created_at.desc()).all()
    return [SequenceOut.model_validate(s) for s in sequences]


@router.get("/emails/sequences/{seq_id}", response_model=SequenceOut)
def get_sequence(seq_id: int, db: Session = Depends(get_db)):
    """Get a specific sequence."""
    sequence = db.query(EmailSequence).filter(EmailSequence.id == seq_id).first()
    if not sequence:
        raise HTTPException(404, "Sequence not found")
    return SequenceOut.model_validate(sequence)


@router.patch("/emails/sequences/{seq_id}", response_model=SequenceOut)
def update_sequence(seq_id: int, payload: SequenceUpdate, db: Session = Depends(get_db)):
    """Update a sequence."""
    sequence = db.query(EmailSequence).filter(EmailSequence.id == seq_id).first()
    if not sequence:
        raise HTTPException(404, "Sequence not found")

    if payload.name is not None:
        sequence.name = payload.name
    if payload.beschreibung is not None:
        sequence.beschreibung = payload.beschreibung
    if payload.steps is not None:
        sequence.steps = [s.model_dump() for s in payload.steps]
    if payload.status is not None:
        sequence.status = payload.status

    db.commit()
    db.refresh(sequence)
    return SequenceOut.model_validate(sequence)


@router.delete("/emails/sequences/{seq_id}", status_code=204)
def delete_sequence(seq_id: int, db: Session = Depends(get_db)):
    """Delete a sequence."""
    sequence = db.query(EmailSequence).filter(EmailSequence.id == seq_id).first()
    if not sequence:
        raise HTTPException(404, "Sequence not found")
    db.delete(sequence)
    db.commit()


@router.post("/emails/sequences/{seq_id}/assign", response_model=SequenceStats)
def assign_leads_to_sequence(seq_id: int, payload: SequenceAssignLeads, db: Session = Depends(get_db)):
    """Assign leads to a sequence."""
    sequence = db.query(EmailSequence).filter(EmailSequence.id == seq_id).first()
    if not sequence:
        raise HTTPException(404, "Sequence not found")

    assigned_count = 0
    for lead_id in payload.lead_ids:
        # Check if already assigned
        existing = db.query(LeadSequenceAssignment).filter(
            LeadSequenceAssignment.lead_id == lead_id,
            LeadSequenceAssignment.sequence_id == seq_id,
            LeadSequenceAssignment.status == "aktiv"
        ).first()

        if existing:
            continue

        lead = db.query(Lead).filter(Lead.id == lead_id).first()
        if not lead or not lead.email:
            continue

        assignment = LeadSequenceAssignment(
            lead_id=lead_id,
            sequence_id=seq_id,
            next_send_at=datetime.utcnow() if payload.start_now else None,
        )
        db.add(assignment)
        assigned_count += 1

    # Activate sequence if not already
    if sequence.status == "entwurf":
        sequence.status = "aktiv"

    db.commit()

    # Return stats
    stats = get_sequence_stats_internal(seq_id, db)
    return stats


def get_sequence_stats_internal(seq_id: int, db: Session) -> SequenceStats:
    """Internal helper to get sequence stats."""
    sequence = db.query(EmailSequence).filter(EmailSequence.id == seq_id).first()
    assignments = db.query(LeadSequenceAssignment).filter(
        LeadSequenceAssignment.sequence_id == seq_id
    ).all()

    return SequenceStats(
        sequence_id=seq_id,
        name=sequence.name if sequence else "Unknown",
        total_assigned=len(assignments),
        active=sum(1 for a in assignments if a.status == "aktiv"),
        completed=sum(1 for a in assignments if a.status == "abgeschlossen"),
        paused=sum(1 for a in assignments if a.status == "pausiert"),
        unsubscribed=sum(1 for a in assignments if a.status == "abgemeldet"),
    )


@router.get("/emails/sequences/{seq_id}/stats", response_model=SequenceStats)
def get_sequence_stats(seq_id: int, db: Session = Depends(get_db)):
    """Get statistics for a sequence."""
    return get_sequence_stats_internal(seq_id, db)


@router.get("/emails/sequences/{seq_id}/leads")
def get_sequence_leads(seq_id: int, db: Session = Depends(get_db)):
    """Get all leads assigned to a sequence."""
    assignments = db.query(LeadSequenceAssignment, Lead).join(
        Lead, Lead.id == LeadSequenceAssignment.lead_id
    ).filter(
        LeadSequenceAssignment.sequence_id == seq_id
    ).all()

    result = []
    for assignment, lead in assignments:
        result.append({
            "assignment_id": assignment.id,
            "lead_id": lead.id,
            "firma": lead.firma,
            "email": lead.email,
            "current_step": assignment.current_step,
            "next_send_at": assignment.next_send_at.isoformat() if assignment.next_send_at else None,
            "status": assignment.status,
        })

    return result


# ============ Analytics Endpoints ============

@router.get("/emails/analytics/overview", response_model=EmailAnalyticsOverview)
def get_email_analytics_overview(db: Session = Depends(get_db)):
    """Get overall email analytics."""
    # Get all sent emails
    total_sent = db.query(EmailHistory).filter(
        EmailHistory.status == EmailStatus.SENT
    ).count()

    delivered = total_sent  # Assume delivered (would need bounce tracking)
    bounced = 0

    opened = db.query(EmailHistory).filter(
        EmailHistory.status == EmailStatus.SENT,
        EmailHistory.opened_at.isnot(None)
    ).count()

    clicked = db.query(EmailHistory).filter(
        EmailHistory.status == EmailStatus.SENT,
        EmailHistory.clicked_at.isnot(None)
    ).count()

    replied = db.query(EmailHistory).filter(
        EmailHistory.status == EmailStatus.SENT,
        EmailHistory.replied_at.isnot(None)
    ).count()

    open_rate = (opened / max(1, delivered)) * 100
    click_rate = (clicked / max(1, delivered)) * 100
    response_rate = (replied / max(1, delivered)) * 100
    bounce_rate = (bounced / max(1, total_sent)) * 100

    return EmailAnalyticsOverview(
        total_sent=total_sent,
        delivered=delivered,
        opened=opened,
        clicked=clicked,
        replied=replied,
        bounced=bounced,
        open_rate=round(open_rate, 1),
        click_rate=round(click_rate, 1),
        response_rate=round(response_rate, 1),
        bounce_rate=round(bounce_rate, 1),
    )


@router.get("/emails/analytics/by-template", response_model=list[TemplateAnalytics])
def get_template_analytics(db: Session = Depends(get_db)):
    """Get analytics grouped by template."""
    templates = db.query(EmailTemplate).all()
    results = []

    for template in templates:
        # Get emails sent with this template (by matching subject pattern)
        emails = db.query(EmailHistory).filter(
            EmailHistory.status == EmailStatus.SENT,
            EmailHistory.campaign_id == None  # Template-based emails
        ).all()

        # Filter emails that match this template
        template_emails = [e for e in emails if template.betreff and template.betreff in e.betreff]

        sent = len(template_emails)
        opened = sum(1 for e in template_emails if e.opened_at)
        clicked = sum(1 for e in template_emails if e.clicked_at)
        replied = sum(1 for e in template_emails if e.replied_at)

        results.append(TemplateAnalytics(
            template_id=template.id,
            template_name=f"{template.name} (v{template.version})",
            sent=sent,
            opened=opened,
            clicked=clicked,
            replied=replied,
            open_rate=round((opened / max(1, sent)) * 100, 1),
            click_rate=round((clicked / max(1, sent)) * 100, 1),
            response_rate=round((replied / max(1, sent)) * 100, 1),
        ))

    return sorted(results, key=lambda x: x.sent, reverse=True)


@router.get("/emails/analytics/by-day")
def get_analytics_by_day(days: int = 30, db: Session = Depends(get_db)):
    """Get email analytics grouped by day."""
    from sqlalchemy import func

    start_date = datetime.utcnow() - timedelta(days=days)

    results = db.query(
        func.date(EmailHistory.gesendet_at).label("date"),
        func.count(EmailHistory.id).label("sent"),
    ).filter(
        EmailHistory.status == EmailStatus.SENT,
        EmailHistory.gesendet_at >= start_date
    ).group_by(
        func.date(EmailHistory.gesendet_at)
    ).order_by(
        func.date(EmailHistory.gesendet_at)
    ).all()

    return [{"date": r[0], "sent": r[1]} for r in results]


@router.get("/emails/analytics", response_model=EmailAnalyticsDashboard)
def get_email_analytics_dashboard(days: int = 14, db: Session = Depends(get_db)):
    """Unified analytics payload for email dashboard page."""
    total_sent = db.query(EmailHistory).filter(EmailHistory.status == EmailStatus.SENT).count()
    delivered = total_sent
    bounced = db.query(EmailHistory).filter(EmailHistory.status == EmailStatus.FAILED).count()

    opened = db.query(EmailHistory).filter(
        EmailHistory.status == EmailStatus.SENT,
        EmailHistory.opened_at.isnot(None),
    ).count()
    clicked = db.query(EmailHistory).filter(
        EmailHistory.status == EmailStatus.SENT,
        EmailHistory.clicked_at.isnot(None),
    ).count()
    replied = db.query(EmailHistory).filter(
        EmailHistory.status == EmailStatus.SENT,
        EmailHistory.replied_at.isnot(None),
    ).count()

    rates = {
        "open_rate": round((opened / max(1, delivered)) * 100, 1),
        "click_rate": round((clicked / max(1, delivered)) * 100, 1),
        "reply_rate": round((replied / max(1, delivered)) * 100, 1),
        "bounce_rate": round((bounced / max(1, total_sent)) * 100, 1),
    }

    by_template: dict[str, EmailAnalyticsByTemplateItem] = {}
    templates = db.query(EmailTemplate).all()
    sent_emails = db.query(EmailHistory).filter(EmailHistory.status == EmailStatus.SENT).all()
    for template in templates:
        matched = [e for e in sent_emails if template.betreff and template.betreff in (e.betreff or "")]
        sent = len(matched)
        opened_count = sum(1 for e in matched if e.opened_at)
        key = (template.kategorie.value if hasattr(template.kategorie, "value") else str(template.kategorie or "custom")).lower()
        by_template[key] = EmailAnalyticsByTemplateItem(
            sent=sent,
            opened=opened_count,
            rate=round((opened_count / max(1, sent)) * 100, 1),
        )

    day_rows = get_analytics_by_day(days=days, db=db)
    start_date = datetime.utcnow() - timedelta(days=days)
    open_rows = db.query(
        EmailHistory.gesendet_at,
        EmailHistory.opened_at,
    ).filter(
        EmailHistory.status == EmailStatus.SENT,
        EmailHistory.gesendet_at >= start_date,
    ).all()
    opened_by_day: dict[str, int] = {}
    for _sent_at, opened_at in open_rows:
        if opened_at:
            key = opened_at.date().isoformat()
            opened_by_day[key] = opened_by_day.get(key, 0) + 1

    timeline = [
        EmailAnalyticsTimelineItem(
            date=row["date"],
            sent=row["sent"],
            opened=opened_by_day.get(row["date"], 0),
        )
        for row in day_rows
    ]

    return EmailAnalyticsDashboard(
        overview={
            "total_sent": total_sent,
            "delivered": delivered,
            "opened": opened,
            "clicked": clicked,
            "replied": replied,
            "bounced": bounced,
        },
        rates=rates,
        by_template=by_template,
        timeline=timeline,
    )


# ============ Tracking Endpoints ============

@router.get("/track/open/{email_id}")
def track_email_open(email_id: int, db: Session = Depends(get_db)):
    """Tracking pixel endpoint for open tracking."""
    email = db.query(EmailHistory).filter(EmailHistory.id == email_id).first()
    if email:
        email.opened_at = datetime.utcnow()
        db.commit()

    # Return 1x1 transparent GIF
    import base64
    gif = base64.b64decode("R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7")
    from fastapi.responses import Response
    return Response(content=gif, media_type="image/gif")


@router.get("/track/click")
def track_click(email_id: int, url: str, db: Session = Depends(get_db)):
    """Track click and redirect to target URL."""
    email = db.query(EmailHistory).filter(EmailHistory.id == email_id).first()
    if email:
        email.clicked_at = datetime.utcnow()
        db.commit()

    from fastapi.responses import RedirectResponse
    return RedirectResponse(url=url)
