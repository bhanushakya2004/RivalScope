"""InternalResearchAgent: Synthesizes internal uploaded documentation, tenant MCP tools, and external market signals."""

import asyncio
import json
from collections.abc import Callable
from typing import Any

from agno.agent import Agent
from agno.models.base import Model
from sqlalchemy import desc, or_
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.core.model_factory import resolve_model
from app.db.models import Company, InternalDocument, RawDocument, Signal
from app.db.session import SessionLocal
from app.mcp_gateway.client import get_tenant_mcp_tools
from app.providers.search import TavilySearchProvider

logger = get_logger("agents.internal_research")


def create_internal_research_agent(
    tenant_id: str = "default",
    model: Model | None = None,
    db: Session | None = None,
) -> Agent:
    """
    Construct Internal Research Agent equipped with:
    1. Uploaded document search (CSV/Excel/Word/MD tabular previews and chunks)
    2. Dynamic tenant MCP tools (financials, CRM, billing, roadmap)
    3. External web search (Tavily/Mock)
    4. Competitor market moves cross-referencing
    """
    model = model or resolve_model()
    session = db or SessionLocal()

    # --- Tool 1: Query Uploaded Internal Documents ---
    def query_internal_documents(query: str, limit: int = 5) -> str:
        """Search tenant uploaded documents (spreadsheets, contracts, word docs, markdown) for specific keywords or metrics."""
        try:
            q = (
                session.query(RawDocument)
                .filter(
                    RawDocument.tenant_id == tenant_id,
                    RawDocument.provider == "internal_document",
                )
            )
            words = [w.strip() for w in query.replace(",", " ").split() if len(w.strip()) > 2]
            if words:
                clauses = [RawDocument.content.ilike(f"%{w}%") for w in words]
                q = q.filter(or_(*clauses))
            else:
                q = q.filter(RawDocument.content.ilike(f"%{query}%"))

            results = q.order_by(desc(RawDocument.fetched_at)).limit(limit).all()
            if not results:
                # Return most recent chunks if specific words not matched
                results = (
                    session.query(RawDocument)
                    .filter(
                        RawDocument.tenant_id == tenant_id,
                        RawDocument.provider == "internal_document",
                    )
                    .order_by(desc(RawDocument.fetched_at))
                    .limit(limit)
                    .all()
                )

            if not results:
                return "No internal enterprise documents found matching the query."

            formatted = []
            for r in results:
                fn = (r.metadata_json or {}).get("filename", r.canonical_url or "Internal Document")
                formatted.append(f"### Source: `{fn}`\n{r.content}")
            return "\n\n---\n\n".join(formatted)
        except Exception as e:
            return f"Error querying internal documents: {e}"

    # --- Tool 2: List Internal Knowledge Catalog ---
    def list_internal_knowledge_catalog() -> str:
        """List all uploaded enterprise documents, their file types, row counts, and summary descriptions."""
        try:
            docs = (
                session.query(InternalDocument)
                .filter(InternalDocument.tenant_id == tenant_id)
                .order_by(desc(InternalDocument.created_at))
                .limit(20)
                .all()
            )
            if not docs:
                return "Knowledge catalog is currently empty. No documents have been uploaded yet."

            lines = ["| Document Name | Type | Rows / Paragraphs | Columns / Sheets | Ingested At |", "| --- | --- | --- | --- | --- |"]
            for d in docs:
                cols = ", ".join((d.column_names or [])[:4])
                if len(d.column_names or []) > 4:
                    cols += f" (+{len(d.column_names) - 4} more)"
                created_str = d.created_at.strftime("%Y-%m-%d %H:%M") if d.created_at else "N/A"
                lines.append(f"| `{d.filename}` | {d.file_type.upper()} | {d.row_count} | {cols or 'N/A'} | {created_str} |")
            return "\n".join(lines)
        except Exception as e:
            return f"Error retrieving knowledge catalog: {e}"

    # --- Tool 3: External Web Search via Tavily ---
    def web_search(query: str) -> str:
        """Search the public web for real-time announcements, news, or competitor details via Tavily."""
        try:
            provider = TavilySearchProvider()
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = None

            if loop and loop.is_running():
                # Already in async loop
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    items = executor.submit(lambda: asyncio.run(provider.search(query, max_results=3))).result()
            else:
                items = asyncio.run(provider.search(query, max_results=3))

            if not items:
                return f"No external search results found for query: '{query}'"

            results = []
            for item in items:
                results.append(f"- **[{item.title}]({item.url})**: {item.content[:280]}...")
            return "\n".join(results)
        except Exception as e:
            return f"Web search failed: {e}"

    # --- Tool 4: Competitor Market Signals Cross-Reference ---
    def get_competitor_market_moves(competitor_name: str | None = None) -> str:
        """Retrieve verified competitor intelligence signals and timeline moves from RivalScope database."""
        try:
            sig_query = session.query(Signal).filter(Signal.tenant_id == tenant_id)
            if competitor_name:
                comp = (
                    session.query(Company)
                    .filter(
                        Company.tenant_id == tenant_id,
                        Company.name.ilike(f"%{competitor_name}%"),
                    )
                    .first()
                )
                if comp:
                    sig_query = sig_query.filter(Signal.company_id == comp.id)

            signals = sig_query.order_by(desc(Signal.event_date)).limit(5).all()
            if not signals:
                return "No competitor signals recorded for the specified criteria."

            entries = []
            for s in signals:
                entries.append(
                    f"- **[{s.category.upper()}] {s.title}** (Importance: {s.importance_score}/100):\n  {s.summary}"
                )
            return "\n".join(entries)
        except Exception as e:
            return f"Error retrieving competitor moves: {e}"

    # --- Dynamic Tenant MCP Tools ---
    mcp_tools = get_tenant_mcp_tools(
        tenant_id=tenant_id,
        agent_name="internal_research",
        db=session,
    )

    all_tools: list[Callable] = [
        query_internal_documents,
        list_internal_knowledge_catalog,
        web_search,
        get_competitor_market_moves,
    ]
    all_tools.extend(mcp_tools)

    return Agent(
        name="InternalResearchAgent",
        model=model,
        tools=all_tools,
        description="Bridges internal documentation, connected ERP/CRM/finance MCP servers, and competitor intelligence.",
        instructions=[
            "You are the Principal Enterprise Research Agent for PayPulse.",
            "Your objective is to provide evidence-backed, comprehensive internal research by synthesizing:",
            "  1. Uploaded internal documentation (spreadsheets, docs, roadmaps, pricing models).",
            "  2. Active enterprise MCP servers (financial take-rates, CRM deals, billing tiers).",
            "  3. External web intelligence and verified competitor market moves (Stripe, Adyen, Revolut).",
            "Whenever asked a question, proactively determine whether internal metrics, competitor moves, or web data are required.",
            "Contrast competitor advantages or announcements directly against internal enterprise metrics.",
            "Format your answers with clean GitHub Markdown, including clear sections, bullet points, and data tables where helpful.",
            "Always cite internal document filenames and tool sources transparently.",
        ],
    )
