from typing import Any, Literal

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field

from app.api.deps import get_current_user_and_tenant
from app.evals.harness import (
    GOLDEN_SCENARIOS,
    AgentTestHarness,
    HarnessReport,
    HarnessScenario,
)
from app.evals.llm_judge import JudgeEvaluationResult, LLMJudge
from app.guardrails.runner import default_guardrail_harness
from app.guardrails.schemas import GuardrailCheckResult

router = APIRouter(prefix="/evals", tags=["evals"])


class JudgeEvaluationRequest(BaseModel):
    """Payload to trigger an LLM-as-a-judge evaluation."""

    query: str = Field(description="The input query or prompt presented to the agent")
    response: str = Field(description="The agent's response to be judged")
    context: list[str] | str | None = Field(
        default=None, description="Reference context documents or ground truth"
    )
    expected_entities: list[str] | None = Field(
        default=None, description="Expected entities (e.g. Stripe, Adyen)"
    )
    is_adversarial: bool = Field(
        default=False, description="Whether this is an adversarial red-teaming test case"
    )


class GuardrailCheckRequest(BaseModel):
    """Payload to run text through input or output guardrails."""

    text: str = Field(description="Input or output text to evaluate")
    direction: Literal["input", "output"] = Field(
        default="input", description="'input' or 'output'"
    )
    known_entities: list[str] | None = Field(
        default=None, description="Allowed or expected entities for output check"
    )


@router.get("/scenarios", response_model=list[HarnessScenario])
def list_scenarios(
    category: str | None = Query(None, description="Filter scenarios by category"),
    _auth: Any = Depends(get_current_user_and_tenant),
) -> list[HarnessScenario]:
    """List all available golden benchmark test scenarios."""
    if category:
        return [s for s in GOLDEN_SCENARIOS if s.category.lower() == category.lower()]
    return GOLDEN_SCENARIOS


@router.post("/judge", response_model=JudgeEvaluationResult)
def evaluate_with_judge(
    request: JudgeEvaluationRequest,
    _auth: Any = Depends(get_current_user_and_tenant),
) -> JudgeEvaluationResult:
    """
    Execute LLM-as-a-Judge scoring on a query and agent response.
    Evaluates groundedness, strategic relevance, guardrail safety, actionability, and citations.
    """
    judge = LLMJudge()
    return judge.evaluate(
        query=request.query,
        response=request.response,
        context=request.context,
        expected_entities=request.expected_entities,
        is_adversarial=request.is_adversarial,
    )


@router.post("/harness/run", response_model=HarnessReport)
def run_agent_harness(
    category: str | None = Query(
        None, description="Optionally run scenarios only in this category"
    ),
    _auth: Any = Depends(get_current_user_and_tenant),
) -> HarnessReport:
    """
    Execute full agent harness across golden benchmark scenarios,
    verifying input guardrails, team coordination, output guardrails, and LLM-as-a-judge scoring.
    """
    scenarios = GOLDEN_SCENARIOS
    if category:
        scenarios = [s for s in GOLDEN_SCENARIOS if s.category.lower() == category.lower()]

    harness = AgentTestHarness()
    return harness.run_all(scenarios=scenarios)


@router.post("/guardrails/check", response_model=GuardrailCheckResult)
def check_guardrails(
    request: GuardrailCheckRequest,
    _auth: Any = Depends(get_current_user_and_tenant),
) -> GuardrailCheckResult:
    """Run text through input or output guardrails."""
    if request.direction == "input":
        return default_guardrail_harness.guard_input(request.text)
    else:
        return default_guardrail_harness.guard_output(
            request.text, known_entities=request.known_entities
        )
