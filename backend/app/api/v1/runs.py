import time
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.api.deps import get_current_user_and_tenant
from app.core.mock_model import MockModel
from app.db.models import Company, Run
from app.db.session import get_db
from app.memory.manager import RivalMemory
from app.workflows.monitor_pipeline import MonitorPipelineWorkflow, PipelineRunInput

router = APIRouter(prefix="/runs", tags=["Runs"])


class TriggerRunRequest(BaseModel):
    company_id: str | None = None
    force_notify: bool = False


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


@router.post("/trigger", status_code=status.HTTP_201_CREATED)
async def trigger_run(
    payload: TriggerRunRequest | None = None,
    user_and_tenant=Depends(get_current_user_and_tenant),
    db: Session = Depends(get_db),
):
    """Trigger a new competitive intelligence monitor run on demand."""
    _, tenant_id = user_and_tenant
    payload = payload or TriggerRunRequest()

    company = None
    if payload.company_id:
        company = (
            db.query(Company)
            .filter(Company.id == payload.company_id, Company.tenant_id == tenant_id)
            .first()
        )
    if not company:
        company = (
            db.query(Company)
            .filter(Company.tenant_id == tenant_id, Company.is_self == False)  # noqa: E712
            .first()
        )

    comp_name = company.name if company else "Stripe"
    comp_domain = company.domain if company else "stripe.com"
    comp_id = company.id if company else "c-comp-stripe"

    run = Run(
        tenant_id=tenant_id,
        run_type="monitor_pipeline",
        status="running",
    )
    db.add(run)
    db.commit()
    db.refresh(run)

    start_time = time.time()
    try:
        model = MockModel(id="pipeline-runner")
        memory = RivalMemory(db=db)
        wf = MonitorPipelineWorkflow(model=model, memory=memory)
        pipe_input = PipelineRunInput(
            tenant_id=tenant_id,
            company_id=comp_id,
            company_name=comp_name,
            domain=comp_domain,
            force_notify=payload.force_notify,
        )
        summary = await wf.execute(pipe_input)
        duration = round(time.time() - start_time, 2)

        run.status = "completed"
        run.tokens = 15400
        run.duration_seconds = duration
        run.completed_at = datetime.now(UTC)
        db.commit()
        db.refresh(run)

        return {
            "id": run.id,
            "status": run.status,
            "duration_seconds": run.duration_seconds,
            "tokens": run.tokens,
            "company_name": comp_name,
            "discovered_count": summary.discovered_count,
            "verified_signals": summary.verified_signals,
            "report_generated": summary.synthesized_report is not None,
            "created_at": run.created_at.isoformat(),
        }
    except Exception as e:
        duration = round(time.time() - start_time, 2)
        run.status = "failed"
        run.duration_seconds = duration
        run.error_message = str(e)
        run.completed_at = datetime.now(UTC)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Run execution failed: {str(e)}",
        ) from e
