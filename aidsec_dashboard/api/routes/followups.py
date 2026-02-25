"""Follow-up endpoints: CRUD with due date filtering."""
from __future__ import annotations

from datetime import datetime, date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload

from api.dependencies import get_db, verify_api_key
from api.schemas.common import FollowUpCreate, FollowUpUpdate, FollowUpOut
from database.models import FollowUp, Lead

router = APIRouter(tags=["followups"], dependencies=[Depends(verify_api_key)])


@router.get("/followups", response_model=list[FollowUpOut])
def list_followups(
    lead_id: int = None,
    due: str = Query(None, description="Filter: 'overdue', 'today', 'upcoming', 'pending'"),
    db: Session = Depends(get_db),
):
    q = db.query(FollowUp).options(joinedload(FollowUp.lead))

    if lead_id:
        q = q.filter(FollowUp.lead_id == lead_id)

    if due:
        today_start = datetime.combine(date.today(), datetime.min.time())
        today_end = datetime.combine(date.today(), datetime.max.time())
        if due == "overdue":
            q = q.filter(FollowUp.erledigt == False, FollowUp.datum < today_start)
        elif due == "today":
            q = q.filter(FollowUp.erledigt == False, FollowUp.datum >= today_start, FollowUp.datum <= today_end)
        elif due == "upcoming":
            q = q.filter(FollowUp.erledigt == False, FollowUp.datum > today_end)
        elif due == "pending":
            q = q.filter(FollowUp.erledigt == False)

    rows = q.order_by(FollowUp.datum.asc()).all()
    result = []
    for fu in rows:
        lead = fu.lead  # Already loaded via joinedload
        result.append(FollowUpOut(
            id=fu.id,
            lead_id=fu.lead_id,
            datum=fu.datum,
            notiz=fu.notiz or "",
            erledigt=fu.erledigt,
            created_at=fu.created_at,
            lead_firma=lead.firma if lead else None,
        ))
    return result


@router.post("/followups", response_model=FollowUpOut, status_code=201)
def create_followup(payload: FollowUpCreate, db: Session = Depends(get_db)):
    lead = db.query(Lead).filter(Lead.id == payload.lead_id).first()
    if not lead:
        raise HTTPException(404, "Lead not found")

    fu = FollowUp(lead_id=payload.lead_id, datum=payload.datum, notiz=payload.notiz)
    db.add(fu)
    db.commit()
    db.refresh(fu)
    return FollowUpOut(
        id=fu.id,
        lead_id=fu.lead_id,
        datum=fu.datum,
        notiz=fu.notiz or "",
        erledigt=fu.erledigt,
        created_at=fu.created_at,
        lead_firma=lead.firma,
    )


@router.patch("/followups/{fu_id}", response_model=FollowUpOut)
def update_followup(fu_id: int, payload: FollowUpUpdate, db: Session = Depends(get_db)):
    fu = db.query(FollowUp).filter(FollowUp.id == fu_id).first()
    if not fu:
        raise HTTPException(404, "Follow-up not found")

    if payload.datum is not None:
        fu.datum = payload.datum
    if payload.notiz is not None:
        fu.notiz = payload.notiz
    if payload.erledigt is not None:
        fu.erledigt = payload.erledigt

    db.commit()
    db.refresh(fu)
    lead = db.query(Lead).filter(Lead.id == fu.lead_id).first()
    return FollowUpOut(
        id=fu.id,
        lead_id=fu.lead_id,
        datum=fu.datum,
        notiz=fu.notiz or "",
        erledigt=fu.erledigt,
        created_at=fu.created_at,
        lead_firma=lead.firma if lead else None,
    )


@router.delete("/followups/{fu_id}", status_code=204)
def delete_followup(fu_id: int, db: Session = Depends(get_db)):
    fu = db.query(FollowUp).filter(FollowUp.id == fu_id).first()
    if not fu:
        raise HTTPException(404, "Follow-up not found")
    db.delete(fu)
    db.commit()
