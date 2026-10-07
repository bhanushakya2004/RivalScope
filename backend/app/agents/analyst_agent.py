"""AnalystAgent: Generates fintech strategic implications and competitive counter-moves."""

from agno.agent import Agent
from agno.models.base import Model

from app.agents.schemas import StrategicImpact
from app.core.model_factory import resolve_model


def create_analyst_agent(model: Model | None = None) -> Agent:
    """Create Analyst Agent providing deep fintech strategic insights."""
    model = model or resolve_model()
    return Agent(
        name="AnalystAgent",
        model=model,
        output_schema=StrategicImpact,
        description="Analyzes verified signals to determine competitive threat, business implications, and tactical counter-moves.",
        instructions=[
            "You are a Principal Fintech Strategy Analyst advising the executive leadership of PayPulse.",
            "Analyze verified competitor moves across payments, issuing, unified commerce, treasury, and regulation.",
            "Always answer the fundamental question: 'So what does this mean for our business?'",
            "Assess realistic threat level: high, medium, low, or informational.",
            "Evaluate potential take-rate compression, merchant churn risks, and pricing margin impacts.",
            "Provide 2-3 concrete, actionable counter-moves (e.g. API roadmap accelerations, partner co-marketing).",
        ],
    )
