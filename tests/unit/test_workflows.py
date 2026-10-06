"""Unit tests for CI Team and MonitorPipelineWorkflow."""

import pytest
from app.core.mock_model import MockModel
from app.teams import create_ci_team
from app.workflows import MonitorPipelineWorkflow, PipelineRunInput


def test_ci_team_coordination():
    model = MockModel(id="test-team-model")
    team = create_ci_team(model=model)
    res = team.run("What are the fintech implications of Stripe agentic commerce?")
    assert res is not None
    assert res.content != ""


@pytest.mark.asyncio
async def test_monitor_pipeline_workflow_execution():
    model = MockModel(id="test-wf-model")
    wf = MonitorPipelineWorkflow(model=model)
    res = await wf.execute(
        PipelineRunInput(
            tenant_id="t-paypulse-demo",
            company_id="c-comp-stripe",
            company_name="Stripe",
            domain="stripe.com",
        )
    )
    assert res.company_name == "Stripe"
    assert res.discovered_count >= 3
    assert res.delivery_status in ["delivered", "no_deliverable_signals"]
