"""Ranking endpoints: single check, batch check with background tasks."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.orm import Session

from api.dependencies import get_db, verify_api_key
from api.schemas.common import RankingCheckRequest, RankingBatchRequest
from database.models import Lead
from services.ranking_service import get_ranking_service


def _normalized_grade(value: str | None) -> str | None:
    return get_ranking_service().normalize_grade(value)

router = APIRouter(tags=["ranking"], dependencies=[Depends(verify_api_key)])

_batch_jobs: dict[str, dict] = {}


@router.post("/ranking/check")
def check_single(payload: RankingCheckRequest):
    svc = get_ranking_service()
    result = svc.check_url(payload.url)
    return result


@router.post("/ranking/check-lead/{lead_id}")
def check_lead(lead_id: int, db: Session = Depends(get_db)):
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(404, "Lead not found")
    if not lead.website:
        raise HTTPException(400, "Lead has no website")

    svc = get_ranking_service()
    result = svc.check_url(lead.website)

    lead.ranking_score = result.get("score")
    lead.ranking_grade = _normalized_grade(result.get("grade"))
    lead.ranking_details = result.get("headers")
    lead.ranking_checked_at = datetime.utcnow()
    db.commit()

    return result


def _run_batch(job_id: str, lead_ids: list[int]):
    from database.database import get_session
    session = get_session()
    svc = get_ranking_service()
    job = _batch_jobs[job_id]
    try:
        leads = session.query(Lead).filter(Lead.id.in_(lead_ids)).all()
        job["total"] = len(leads)
        for i, lead in enumerate(leads):
            if job.get("cancelled"):
                break
            if not lead.website:
                job["errors"] += 1
                job["completed"] += 1
                continue
            try:
                result = svc.check_url(lead.website)
                lead.ranking_score = result.get("score")
                lead.ranking_grade = _normalized_grade(result.get("grade"))
                lead.ranking_details = result.get("headers")
                lead.ranking_checked_at = datetime.utcnow()
                session.flush()
                job["completed"] += 1
            except Exception:
                job["errors"] += 1
                job["completed"] += 1
        session.commit()
        job["status"] = "done"
    except Exception as e:
        job["status"] = "error"
        job["error"] = str(e)
    finally:
        session.close()


@router.post("/ranking/batch")
def start_batch(
    payload: RankingBatchRequest,
    background_tasks: BackgroundTasks,
):
    job_id = str(uuid.uuid4())[:8]
    _batch_jobs[job_id] = {
        "status": "running",
        "total": len(payload.lead_ids),
        "completed": 0,
        "errors": 0,
    }
    background_tasks.add_task(_run_batch, job_id, payload.lead_ids)
    return {"job_id": job_id}


@router.get("/ranking/batch/{job_id}")
def batch_status(job_id: str):
    job = _batch_jobs.get(job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    return job


@router.post("/ranking/batch/{job_id}/cancel")
def cancel_batch(job_id: str):
    job = _batch_jobs.get(job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    job["cancelled"] = True
    return {"cancelled": True}
