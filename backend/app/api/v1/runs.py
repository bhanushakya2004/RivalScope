"""Run tracking and Human-in-the-Loop (HITL) resumption router."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.api.deps import get_current_user_and_tenant
from app.db.models import Run
from app.db.session import get_db

router = APIRouter(prefix="/runs", tags=["Runs"])


class ResumeRunRequest(BaseModel):
    action: str = "approve"  # approve | reject
    comment: str | None = None


@router.get("")
def list_runs(
    status_filter: str | None = Query(None, alias="status"),
    limit: int = Query(25, ge=1, le=100),
    user_and_tenant=Depends(get_current_user_and_tenant),
    db: Session = Depends(get_db),
):
    _, tenant_id = user_and_tenant
    query = db.query(Run).filter(Run.tenant_id == tenant_id)
    if status_filter:
        query = query.filter(Run.status == status_filter)

    runs = query.order_by(desc(Run.created_at)).limit(limit).all()
    return [
        {
            "id": r.id,
            "schedule_id": r.schedule_id,
            "run_type": r.run_type,
            "status": r.status,
            "tokens": r.tokens,
            "duration_seconds": r.duration_seconds,
            "error_message": r.error_message,
            "created_at": r.created_at.isoformat(),
            "completed_at": r.completed_at.isoformat() if r.completed_at else None,
        }
        for r in runs
    ]


@router.get("/{run_id}")
def get_run(
    run_id: str,
    user_and_tenant=Depends(get_current_user_and_tenant),
    db: Session = Depends(get_db),
):
    _, tenant_id = user_and_tenant
    r = db.query(Run).filter(Run.id == run_id, Run.tenant_id == tenant_id).first()
    if not r:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found")

    return {
        "id": r.id,
        "schedule_id": r.schedule_id,
        "run_type": r.run_type,
        "status": r.status,
        "tokens": r.tokens,
        "duration_seconds": r.duration_seconds,
        "error_message": r.error_message,
        "created_at": r.created_at.isoformat(),
        "completed_at": r.completed_at.isoformat() if r.completed_at else None,
    }


@router.post("/{run_id}/resume")
def resume_hitl_run(
    run_id: str,
    payload: ResumeRunRequest,
    user_and_tenant=Depends(get_current_user_and_tenant),
    db: Session = Depends(get_db),
):
    """
    Human-in-the-Loop (HITL) approval endpoint.
    Approves or rejects a paused mutating tool run.
    """
    _, tenant_id = user_and_tenant
    run = db.query(Run).filter(Run.id == run_id, Run.tenant_id == tenant_id).first()
    if not run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found")

    if run.status != "paused":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Run is not in paused state (current status: {run.status})",
        )

    if payload.action == "approve":
        run.status = "completed"
        db.commit()
        return {"status": "approved", "run_id": run.id, "message": "Execution resumed"}
    else:
        run.status = "cancelled"
        run.error_message = f"Rejected by human operator: {payload.comment or 'No reason provided'}"
        db.commit()
        return {"status": "rejected", "run_id": run.id, "message": "Execution rejected"}
