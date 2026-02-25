"""Sequence execution worker service for due email assignments."""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from sqlalchemy.orm import Session

from database.models import (
    EmailHistory,
    EmailSequence,
    EmailStatus,
    EmailTemplate,
    Lead,
    LeadSequenceAssignment,
    LeadStatus,
    SequenceStatus,
    Settings,
    StatusHistory,
)
from database.database import get_session
from services.email_service import get_email_service


def _extract_domain(website: str | None) -> str:
    if not website:
        return ""
    try:
        return website.replace("https://", "").replace("http://", "").split("/")[0]
    except Exception:
        return website


def _build_replacements(lead: Lead) -> dict[str, str]:
    full_name = (
        getattr(lead, "ansprechpartner", None)
        or getattr(lead, "name", None)
        or ""
    ).strip()
    name_parts = full_name.split()
    first_name = name_parts[0] if name_parts else ""
    last_name = " ".join(name_parts[1:]) if len(name_parts) > 1 else ""

    grade = lead.ranking_grade or "?"
    grade_note = f"Note {grade} (ungenügend)" if grade in ["F", "D"] else f"Note {grade}"

    greeting = f"Sehr geehrte/r {full_name}" if full_name else "Sehr geehrte Damen und Herren"

    return {
        "{{first_name}}": first_name,
        "{{last_name}}": last_name,
        "{{name}}": full_name or (lead.firma or ""),
        "{{company}}": lead.firma or "",
        "{{domain}}": _extract_domain(lead.website),
        "{{grade}}": grade,
        "{{grade_note}}": grade_note,
        "{{date}}": datetime.utcnow().strftime("%Y-%m-%d"),
        "{{personalized_greeting}}": greeting,
    }


def _apply_placeholders(text: str, replacements: dict[str, str]) -> str:
    output = text or ""
    for placeholder, value in replacements.items():
        output = output.replace(placeholder, value)
    return output


def _load_signature(db: Session) -> dict[str, str]:
    sig_row = db.query(Settings).filter(Settings.key == "email_signature").first()
    logo_row = db.query(Settings).filter(Settings.key == "signature_logo").first()
    mime_row = db.query(Settings).filter(Settings.key == "signature_logo_mime").first()
    return {
        "text": sig_row.value if sig_row else "",
        "logo_b64": logo_row.value if logo_row else "",
        "logo_mime": mime_row.value if mime_row else "",
    }


def _safe_step_offset(step: dict[str, Any] | None) -> int:
    if not step:
        return 0
    try:
        return max(0, int(step.get("day_offset", 0)))
    except Exception:
        return 0


def execute_due_sequence_assignments(db: Session, limit: int = 50, dry_run: bool = False) -> dict[str, Any]:
    now = datetime.utcnow()
    due_assignments = (
        db.query(LeadSequenceAssignment)
        .join(EmailSequence, EmailSequence.id == LeadSequenceAssignment.sequence_id)
        .filter(
            LeadSequenceAssignment.status == "aktiv",
            LeadSequenceAssignment.next_send_at.isnot(None),
            LeadSequenceAssignment.next_send_at <= now,
            EmailSequence.status == SequenceStatus.AKTIV,
        )
        .order_by(LeadSequenceAssignment.next_send_at.asc())
        .limit(max(1, limit))
        .all()
    )

    summary: dict[str, Any] = {
        "processed": 0,
        "sent": 0,
        "failed": 0,
        "completed": 0,
        "rescheduled": 0,
        "paused": 0,
        "skipped": 0,
        "dry_run": dry_run,
        "details": [],
    }

    if not due_assignments:
        return summary

    email_service = get_email_service()
    signature = _load_signature(db)

    for assignment in due_assignments:
        summary["processed"] += 1

        sequence = db.query(EmailSequence).filter(EmailSequence.id == assignment.sequence_id).first()
        lead = db.query(Lead).filter(Lead.id == assignment.lead_id).first()

        if not sequence or not lead:
            summary["skipped"] += 1
            summary["details"].append(
                {
                    "assignment_id": assignment.id,
                    "status": "skipped",
                    "reason": "missing_sequence_or_lead",
                }
            )
            continue

        if not lead.email:
            if not dry_run:
                assignment.status = "pausiert"
                assignment.next_send_at = None
            summary["paused"] += 1
            summary["details"].append(
                {
                    "assignment_id": assignment.id,
                    "lead_id": lead.id,
                    "status": "paused",
                    "reason": "missing_lead_email",
                }
            )
            continue

        steps = sequence.steps or []
        if assignment.current_step >= len(steps):
            if not dry_run:
                assignment.status = "abgeschlossen"
                assignment.completed_at = now
                assignment.next_send_at = None
            summary["completed"] += 1
            summary["details"].append(
                {
                    "assignment_id": assignment.id,
                    "lead_id": lead.id,
                    "status": "completed",
                    "reason": "no_remaining_steps",
                }
            )
            continue

        step = steps[assignment.current_step] if isinstance(steps[assignment.current_step], dict) else {}
        template_id = step.get("template_id")
        template = db.query(EmailTemplate).filter(EmailTemplate.id == template_id).first() if template_id else None

        subject_raw = (step.get("subject_override") or (template.betreff if template else "") or "").strip()
        body_raw = (step.get("body_override") or (template.inhalt if template else "") or "").strip()

        if not subject_raw or not body_raw:
            if not dry_run:
                assignment.next_send_at = now + timedelta(hours=24)
            summary["failed"] += 1
            summary["details"].append(
                {
                    "assignment_id": assignment.id,
                    "lead_id": lead.id,
                    "status": "failed",
                    "reason": "missing_subject_or_body",
                }
            )
            continue

        replacements = _build_replacements(lead)
        subject = _apply_placeholders(subject_raw, replacements)
        body = _apply_placeholders(body_raw, replacements)

        next_step_index = assignment.current_step + 1
        next_send_at = None
        if next_step_index < len(steps):
            offset_days = _safe_step_offset(steps[next_step_index] if isinstance(steps[next_step_index], dict) else None)
            next_send_at = now + timedelta(days=offset_days)

        if dry_run:
            summary["details"].append(
                {
                    "assignment_id": assignment.id,
                    "lead_id": lead.id,
                    "status": "would_send",
                    "step_index": assignment.current_step,
                    "subject": subject,
                    "next_send_at": next_send_at.isoformat() if next_send_at else None,
                    "will_complete": next_step_index >= len(steps),
                }
            )
            continue

        body_to_send = body
        if signature.get("text"):
            body_to_send = body_to_send.rstrip() + "\n\n-- \n" + signature["text"]

        result = email_service.send_email(
            to_email=lead.email,
            subject=subject,
            body=body_to_send,
            logo_b64=signature.get("logo_b64") or None,
            logo_mime=signature.get("logo_mime") or None,
        )

        send_status = EmailStatus.SENT if result.get("success") else EmailStatus.FAILED
        history_entry = EmailHistory(
            lead_id=lead.id,
            betreff=subject,
            inhalt=body,
            status=send_status,
            gesendet_at=now if send_status == EmailStatus.SENT else None,
        )
        db.add(history_entry)

        if result.get("success"):
            if lead.status == LeadStatus.OFFEN:
                previous_status = lead.status
                lead.status = LeadStatus.PENDING
                db.add(
                    StatusHistory(
                        lead_id=lead.id,
                        von_status=previous_status,
                        zu_status=LeadStatus.PENDING,
                    )
                )

            assignment.current_step = next_step_index
            if next_step_index >= len(steps):
                assignment.status = "abgeschlossen"
                assignment.completed_at = now
                assignment.next_send_at = None
                summary["completed"] += 1
            else:
                assignment.next_send_at = next_send_at
                summary["rescheduled"] += 1

            summary["sent"] += 1
            summary["details"].append(
                {
                    "assignment_id": assignment.id,
                    "lead_id": lead.id,
                    "status": "sent",
                    "step_index": next_step_index,
                    "next_send_at": assignment.next_send_at.isoformat() if assignment.next_send_at else None,
                }
            )
        else:
            assignment.next_send_at = now + timedelta(hours=6)
            summary["failed"] += 1
            summary["details"].append(
                {
                    "assignment_id": assignment.id,
                    "lead_id": lead.id,
                    "status": "failed",
                    "error": result.get("error", "send_failed"),
                }
            )

    if not dry_run:
        db.commit()

    return summary


def count_due_sequence_assignments(db: Session) -> int:
    now = datetime.utcnow()
    return (
        db.query(LeadSequenceAssignment)
        .join(EmailSequence, EmailSequence.id == LeadSequenceAssignment.sequence_id)
        .filter(
            LeadSequenceAssignment.status == "aktiv",
            LeadSequenceAssignment.next_send_at.isnot(None),
            LeadSequenceAssignment.next_send_at <= now,
            EmailSequence.status == SequenceStatus.AKTIV,
        )
        .count()
    )


def execute_due_sequence_assignments_with_session(limit: int = 50, dry_run: bool = False) -> dict[str, Any]:
    """Execute due assignments with a fresh database session."""
    db = get_session()
    try:
        return execute_due_sequence_assignments(db=db, limit=limit, dry_run=dry_run)
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
