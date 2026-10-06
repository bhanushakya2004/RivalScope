"""Scheduler engine polling and executing competitive monitoring schedules."""

import asyncio
import time
from datetime import UTC, datetime, timedelta
from typing import Any

from agno.models.base import Model
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.db.models import Company, Run, Schedule
from app.db.session import SessionLocal
from app.memory.manager import RivalMemory
from app.workflows.monitor_pipeline import MonitorPipelineWorkflow, PipelineRunInput

logger = get_logger("scheduler.engine")


class SchedulerEngine:
    """Manages periodic execution of competitive intelligence monitor cycles."""

    def __init__(self, model: Model, memory: RivalMemory | None = None):
        self.model = model
        self.memory = memory or RivalMemory()
        self.workflow = MonitorPipelineWorkflow(model=self.model, memory=self.memory)
        self._running = False

    def get_due_schedules(self, db: Session) -> list[Schedule]:
        """Find enabled schedules that are due for execution."""
        now = datetime.now(UTC)
        schedules = db.query(Schedule).filter(Schedule.enabled).all()
        due = []
        for s in schedules:
            if s.next_run_at is None or s.next_run_at <= now:
                due.append(s)
        return due

    async def execute_schedule(self, schedule_id: str) -> dict[str, Any]:
        """Execute a single schedule immediately."""
        db = SessionLocal()
        start_time = time.time()
        run_record = None

        try:
            schedule = db.query(Schedule).filter(Schedule.id == schedule_id).first()
            if not schedule:
                raise ValueError(f"Schedule {schedule_id} not found")

            # Create Run record
            run_record = Run(
                tenant_id=schedule.tenant_id,
                schedule_id=schedule.id,
                run_type="monitor",
                status="running",
            )
            db.add(run_record)
            db.commit()
            db.refresh(run_record)

            # Discover tracked competitors for this schedule
            comp_query = db.query(Company).filter(
                Company.tenant_id == schedule.tenant_id,
                Company.is_self.is_(False),
            )
            scope = schedule.scope or {}
            if scope.get("competitor_ids"):
                comp_query = comp_query.filter(Company.id.in_(scope["competitor_ids"]))

            competitors = comp_query.all()
            logger.info(f"Executing schedule '{schedule.name}' for {len(competitors)} competitors")

            results = []
            for comp in competitors:
                summary = await self.workflow.execute(
                    PipelineRunInput(
                        tenant_id=schedule.tenant_id,
                        company_id=comp.id,
                        company_name=comp.name,
                        domain=comp.domain,
                        ticker=comp.ticker,
                    )
                )
                results.append(summary.model_dump())

            # Update schedule run time
            now = datetime.now(UTC)
            schedule.last_run_at = now
            interval = schedule.interval_seconds or 3600
            schedule.next_run_at = now + timedelta(seconds=interval)

            duration = time.time() - start_time
            run_record.status = "completed"
            run_record.duration_seconds = duration
            run_record.completed_at = now
            db.commit()

            return {
                "schedule_id": schedule.id,
                "status": "completed",
                "competitors_monitored": len(competitors),
                "duration_seconds": duration,
                "results": results,
            }

        except Exception as e:
            logger.error(f"Schedule execution failed for {schedule_id}: {e}")
            if run_record:
                run_record.status = "failed"
                run_record.error_message = str(e)
                run_record.duration_seconds = time.time() - start_time
                db.commit()
            raise
        finally:
            db.close()

    async def run_poll_loop(self, poll_interval_seconds: int = 15) -> None:
        """Poll and trigger due schedules continuously."""
        self._running = True
        logger.info(f"Scheduler loop started (polling every {poll_interval_seconds}s)")

        while self._running:
            db = SessionLocal()
            try:
                due = self.get_due_schedules(db)
                for s in due:
                    logger.info(f"Schedule {s.name} ({s.id}) is due. Executing...")
                    asyncio.create_task(self.execute_schedule(s.id))
            except Exception as e:
                logger.error(f"Error checking due schedules: {e}")
            finally:
                db.close()

            await asyncio.sleep(poll_interval_seconds)

    def stop(self) -> None:
        """Halt the polling loop."""
        self._running = False
