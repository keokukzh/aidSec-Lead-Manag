from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import List, Dict, Any

from api.dependencies import get_db, verify_api_key
from database.models import AgentTask, Lead

router = APIRouter(tags=["tasks"], dependencies=[Depends(verify_api_key)])

@router.get("/tasks")
def list_tasks(limit: int = 50, db: Session = Depends(get_db)):
    """Fetch the list of agent tasks to display in the frontend queue viewer."""
    tasks = (
        db.query(AgentTask, Lead.firma)
        .outerjoin(Lead, AgentTask.lead_id == Lead.id)
        .order_by(desc(AgentTask.created_at))
        .limit(limit)
        .all()
    )
    
    result = []
    for task_obj, firma in tasks:
        result.append({
            "id": task_obj.id,
            "task_type": task_obj.task_type,
            "lead_id": task_obj.lead_id,
            "lead_firma": firma,
            "status": task_obj.status,
            "assigned_to": task_obj.assigned_to,
            "created_at": task_obj.created_at.isoformat() if task_obj.created_at else None,
            "completed_at": task_obj.completed_at.isoformat() if task_obj.completed_at else None,
            "error_message": task_obj.error_message
        })
        
    return result
