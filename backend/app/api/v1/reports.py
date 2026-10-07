"""Intelligence reports router."""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.api.deps import get_current_user_and_tenant
from app.core.model_factory import resolve_model
from app.db.models import Company, Report
from app.db.session import get_db
from app.memory.manager import RivalMemory
from app.teams.ci_team import create_ci_team

router = APIRouter(prefix="/reports", tags=["Reports"])


class GenerateReportRequest(BaseModel):
    title: str | None = "Weekly Competitive Landscape Brief"
    company_id: str | None = None
    report_type: str = "comprehensive"  # daily_brief, weekly_digest, deep_dive


class ReportResponse(BaseModel):
    id: str
    title: str
    period: str
    scope: dict[str, Any]
    markdown: str
    created_at: str
    report_type: str = "comprehensive"
    company_id: str | None = None
    summary: str = ""
    content: str = ""
    status: str = "completed"


@router.get("", response_model=list[ReportResponse])
def list_reports(
    limit: int = Query(20, ge=1, le=100),
    user_and_tenant=Depends(get_current_user_and_tenant),
    db: Session = Depends(get_db),
):
    _, tenant_id = user_and_tenant
    reports = (
        db.query(Report)
        .filter(Report.tenant_id == tenant_id)
        .order_by(desc(Report.created_at))
        .limit(limit)
        .all()
    )
    return [
        ReportResponse(
            id=r.id,
            title=r.title,
            period=r.period,
            scope=r.scope or {},
            markdown=r.markdown,
            created_at=r.created_at.isoformat(),
            report_type=r.period,
            company_id=(r.scope or {}).get("company_id"),
            summary=(r.structured_json or {}).get(
                "summary", r.markdown[:280] if r.markdown else ""
            ),
            content=r.markdown or "",
            status="completed",
        )
        for r in reports
    ]


@router.post("/generate", response_model=ReportResponse, status_code=status.HTTP_201_CREATED)
def generate_report(
    payload: GenerateReportRequest,
    user_and_tenant=Depends(get_current_user_and_tenant),
    db: Session = Depends(get_db),
):
    _, tenant_id = user_and_tenant

    comp_name = "Tracked Rivals"
    if payload.company_id:
        target_company = (
            db.query(Company)
            .filter(
                Company.id == payload.company_id,
                Company.tenant_id == tenant_id,
            )
            .first()
        )
        if target_company:
            comp_name = target_company.name

    # Synthesize intelligence via CI team
    model = resolve_model("report-gen-model")
    memory = RivalMemory(db=db)
    team = create_ci_team(model=model, memory=memory)

    prompt = (
        f"Generate executive competitive intelligence report for {comp_name}.\n"
        f"Format: {payload.report_type}.\n"
        "Synthesize strategic implications, market share threats, and recommended counter-moves."
    )
    team_output = team.run(prompt)
    report_content = str(team_output.content)

    rep = Report(
        tenant_id=tenant_id,
        title=payload.title or f"Competitive Brief: {comp_name}",
        period=payload.report_type,
        scope={"company_id": payload.company_id, "competitor_name": comp_name},
        markdown=report_content,
        structured_json={"summary": report_content[:280]},
        citations=[],
    )
    db.add(rep)
    db.commit()
    db.refresh(rep)

    return ReportResponse(
        id=rep.id,
        title=rep.title,
        period=rep.period,
        scope=rep.scope or {},
        markdown=rep.markdown,
        created_at=rep.created_at.isoformat(),
        report_type=rep.period,
        company_id=(rep.scope or {}).get("company_id"),
        summary=(rep.structured_json or {}).get(
            "summary", rep.markdown[:280] if rep.markdown else ""
        ),
        content=rep.markdown or "",
        status="completed",
    )


@router.get("/{report_id}", response_model=ReportResponse)
def get_report(
    report_id: str,
    user_and_tenant=Depends(get_current_user_and_tenant),
    db: Session = Depends(get_db),
):
    _, tenant_id = user_and_tenant
    rep = db.query(Report).filter(Report.id == report_id, Report.tenant_id == tenant_id).first()
    if not rep:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")

    return ReportResponse(
        id=rep.id,
        title=rep.title,
        period=rep.period,
        scope=rep.scope or {},
        markdown=rep.markdown,
        created_at=rep.created_at.isoformat(),
        report_type=rep.period,
        company_id=(rep.scope or {}).get("company_id"),
        summary=(rep.structured_json or {}).get(
            "summary", rep.markdown[:280] if rep.markdown else ""
        ),
        content=rep.markdown or "",
        status="completed",
    )
