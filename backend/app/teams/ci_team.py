"""CompetitiveIntelligenceTeam coordinating Verifier, Analyst, and Reporter agents."""

from collections.abc import Callable
from typing import Any

from agno.models.base import Model
from agno.team import Team, TeamMode

from app.agents.analyst_agent import create_analyst_agent
from app.agents.reporter_agent import create_reporter_agent
from app.agents.verifier_agent import create_verifier_agent
from app.core.model_factory import resolve_model
from app.memory.manager import RivalMemory


def create_ci_team(
    model: Model | None = None,
    memory: RivalMemory | None = None,
    tools: list[Any] | Callable[[Any], list[Any]] | None = None,
    db: Any | None = None,
) -> Team:
    """
    Construct the Coordinated CI Team using Agno TeamMode.coordinate.
    The leader orchestrates specialized agents, accesses RivalMemory,
    and records sessions/runs in Agno's native PostgresDb storage.
    """
    from app.db.session import get_agno_db

    model = model or resolve_model()
    agno_db = db or get_agno_db()
    verifier = create_verifier_agent(model)
    analyst = create_analyst_agent(model)
    reporter = create_reporter_agent(model)

    # Provide memory lookup tools if memory facade provided
    team_tools = []
    if memory is not None:

        def search_knowledge_base(query: str, company_id: str | None = None) -> str:
            """Search long-term semantic knowledge base for articles and filings."""
            results = memory.search_knowledge("default", query, company_id=company_id, limit=3)
            if not results:
                return "No matching historical documents found in knowledge base."
            return "\n\n".join([f"[{r['url']}]: {r['content'][:300]}" for r in results])

        def get_competitor_timeline(company_id: str | None = None) -> str:
            """Query entity timeline for past milestone events and moves."""
            events = memory.get_timeline("default", company_id=company_id, limit=5)
            if not events:
                return "No timeline events recorded yet."
            return "\n".join(
                [f"- {e['event_date'][:10]} [{e['category']}]: {e['title']}" for e in events]
            )

        def query_internal_documents_and_metrics(query: str) -> str:
            """Query internal uploaded enterprise documents (spreadsheets, docs) and internal knowledge base."""
            results = memory.search_knowledge("default", query, limit=4)
            internal_docs = [r for r in results if "internal://" in (r.get("url") or "")]
            if internal_docs:
                return "\n\n".join([f"[{r['url']}]: {r['content'][:400]}" for r in internal_docs])
            return "No specific internal documents found; using general fintech context."

        team_tools.extend([search_knowledge_base, get_competitor_timeline, query_internal_documents_and_metrics])

    if tools:
        if callable(tools):
            team_tools = tools  # Callable factory for runtime dynamic MCP injection
        else:
            team_tools.extend(tools)

    return Team(
        name="CompetitiveIntelligenceTeam",
        mode=TeamMode.coordinate,
        model=model,
        members=[verifier, analyst, reporter],
        tools=team_tools,
        db=agno_db,
        description="Coordinates verification, fintech strategic impact analysis, and executive synthesis.",
        instructions=[
            "You are the Director of Competitive Intelligence leading a team of specialized agents.",
            "Coordinate tasks across your team members:",
            "1. Delegate evidence fact-checking and quotation extraction to `VerifierAgent`.",
            "2. Direct `AnalystAgent` to evaluate threat levels, take-rate impact, and strategic counter-moves.",
            "3. Instruct `ReporterAgent` to format the final synthesized deliverable with clickable source citations.",
            "Ground all conclusions in verified data.",
        ],
    )
