"""ReporterAgent: Formats intelligence into multi-channel deliveries (Markdown, Slack, Telegram)."""

from agno.agent import Agent
from agno.models.base import Model

from app.agents.schemas import FormattedReport


def create_reporter_agent(model: Model) -> Agent:
    """Create Reporter Agent formatting intelligence for diverse delivery channels."""
    return Agent(
        name="ReporterAgent",
        model=model,
        output_schema=FormattedReport,
        description="Formats verified intelligence and strategic implications for executive dashboards, Slack, and Telegram.",
        instructions=[
            "You are an Executive Communications and Intelligence Reporting specialist.",
            "Synthesize verified signals and analyst commentary into concise, high-impact briefs.",
            "Include verified source URLs as clickable markdown hyperlinks.",
            "Format output to satisfy all required communication channels: Executive Markdown, Slack Block Kit, and Telegram.",
            "Maintain a crisp, professional tone suitable for C-suite fintech leaders.",
        ],
    )
