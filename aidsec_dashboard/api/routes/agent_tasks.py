"""Endpoints for external OpenClaw agents to pull tasks and report completions."""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from datetime import datetime
from pydantic import BaseModel
from typing import Optional, Dict, Any

from api.dependencies import get_db, verify_api_key
from database.models import AgentTask, EmailHistory, EmailStatus

router = APIRouter(tags=["agents", "openclaw"], dependencies=[Depends(verify_api_key)])

class TaskCompletePayload(BaseModel):
    success: bool
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

@router.get("/agents/tasks/pull")
def pull_agent_task(agent_id: str, db: Session = Depends(get_db)):
    """
    Called by Agent 2 (SDR) to pull the next pending task from the queue.
    Locks the task by transitioning it to 'processing' and assigns it to the physical agent ID.
    """
    # Find oldest pending task
    task = db.query(AgentTask).filter(AgentTask.status == "pending").order_by(AgentTask.created_at.asc()).first()
    
    if not task:
        return {"success": True, "message": "Queue is empty", "task": None}
        
    # Attempt to lock it (handling SQLite race conditions without skip_locked)
    updated_rows = db.query(AgentTask).filter(
        AgentTask.id == task.id,
        AgentTask.status == "pending"
    ).update({
        "status": "processing",
        "assigned_to": agent_id
    })
    
    if updated_rows == 0:
        # Race condition: Another agent locked it before we could
        db.rollback()
        return {"success": True, "message": "Queue is empty", "task": None}
        
    db.commit()
    db.refresh(task)
    
    return {
        "success": True, 
        "task": {
            "id": task.id,
            "type": task.task_type,
            "lead_id": task.lead_id,
            "payload": task.payload
        }
    }


@router.post("/agents/tasks/{task_id}/complete")
def complete_agent_task(task_id: int, payload: TaskCompletePayload, db: Session = Depends(get_db)):
    """
    Called by Agent 2 when a task finishes. 
    If it was a generation task, this endpoint will parse the result and drop the email draft.
    """
    task = db.query(AgentTask).filter(AgentTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
        
    if not payload.success:
        task.status = "failed"
        task.error_message = payload.error
        task.completed_at = datetime.utcnow()
        db.commit()
        return {"success": True, "message": "Marked as failed"}

    # Handle successful SDR Draft tasks
    if task.task_type == "GENERATE_DRAFT":
        result = payload.result or {}
        subject = result.get("betreff", "Automatisch generiert")
        body = result.get("inhalt", "")
        
        # Save straight to EmailHistory as a Draft ready for human review in the Outgoing Queue
        draft = EmailHistory(
            lead_id=task.lead_id,
            betreff=subject,
            inhalt=body,
            status=EmailStatus.DRAFT,
            campaign_id=task.payload.get("campaign_id") if task.payload else None
        )
        db.add(draft)
        
    # Close task
    task.status = "completed"
    task.completed_at = datetime.utcnow()
    db.commit()
    
    return {"success": True, "message": "Task completed successfully"}
