"""Schedules and monitoring jobs router."""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import get_current_user_and_tenant
from app.core.model_factory import resolve_model
from app.db.models import Schedule
from app.db.session import get_db
from app.scheduler.scheduler import SchedulerEngine

router = APIRouter(prefix="/schedules", tags=["Schedules"])


class ScheduleCreateRequest(BaseModel):
    name: str
    cron_expression: str | None = None
    interval_seconds: int | None = 3600
    scope: dict[str, Any] = Field(default_factory=dict)
    enabled: bool = True


class ScheduleResponse(BaseModel):
    id: str
    name: str
    cron_expression: str | None
    interval_seconds: int | None
    enabled: bool
    scope: dict[str, Any]
    next_run_at: str | None
    last_run_at: str | None


@router.get("", response_model=list[ScheduleResponse])
def list_schedules(
    user_and_tenant=Depends(get_current_user_and_tenant),
    db: Session = Depends(get_db),
):
    _, tenant_id = user_and_tenant
    schedules = db.query(Schedule).filter(Schedule.tenant_id == tenant_id).all()
    return [
        ScheduleResponse(
            id=s.id,
            name=s.name,
            cron_expression=s.cron_expression,
            interval_seconds=s.interval_seconds,
            enabled=s.enabled,
            scope=s.scope or {},
            next_run_at=s.next_run_at.isoformat() if s.next_run_at else None,
            last_run_at=s.last_run_at.isoformat() if s.last_run_at else None,
        )
        for s in schedules
    ]


@router.post("", response_model=ScheduleResponse, status_code=status.HTTP_201_CREATED)
def create_schedule(
    payload: ScheduleCreateRequest,
    user_and_tenant=Depends(get_current_user_and_tenant),
    db: Session = Depends(get_db),
):
    _, tenant_id = user_and_tenant
    sched = Schedule(
        tenant_id=tenant_id,
        name=payload.name,
        cron_expression=payload.cron_expression,
        interval_seconds=payload.interval_seconds,
        scope=payload.scope,
        enabled=payload.enabled,
    )
    db.add(sched)
    db.commit()
    db.refresh(sched)

    return ScheduleResponse(
        id=sched.id,
        name=sched.name,
        cron_expression=sched.cron_expression,
        interval_seconds=sched.interval_seconds,
        enabled=sched.enabled,
        scope=sched.scope or {},
        next_run_at=sched.next_run_at.isoformat() if sched.next_run_at else None,
        last_run_at=sched.last_run_at.isoformat() if sched.last_run_at else None,
    )


@router.post("/{schedule_id}/run-now")
async def trigger_schedule_now(
    schedule_id: str,
    user_and_tenant=Depends(get_current_user_and_tenant),
    db: Session = Depends(get_db),
):
    _, tenant_id = user_and_tenant
    sched = (
        db.query(Schedule)
        .filter(
            Schedule.id == schedule_id,
            Schedule.tenant_id == tenant_id,
        )
        .first()
    )
    if not sched:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Schedule not found")

    model = resolve_model("sched-runner")
    engine = SchedulerEngine(model=model)
    res = await engine.execute_schedule(schedule_id)
    return res
