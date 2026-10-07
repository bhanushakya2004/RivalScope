"""Search providers: Tavily, Agno WebSearch, and deterministic Mock."""

from datetime import UTC, datetime

import httpx

from app.config import get_settings
from app.core.logging import get_logger
from app.providers.base import BaseSearchProvider, IngestedItem

logger = get_logger("providers.search")


class MockSearchProvider(BaseSearchProvider):
    """Deterministic offline search provider for CI pipelines, demos, and local tests."""

    async def search(self, query: str, max_results: int = 5) -> list[IngestedItem]:
        logger.info(f"[MockSearch] Searching offline for query: '{query}'")
        q = query.lower()

        items: list[IngestedItem] = []
        now = datetime.now(UTC)

        if "stripe" in q or "agent" in q or "payment" in q:
            items.append(
                IngestedItem(
                    url="https://stripe.com/newsroom/news/agentic-commerce-suite",
                    title="Stripe Unveils Agentic Commerce Platform for AI Agents and Autonomous Payments",
                    content=(
                        "Stripe announced its new Agentic Commerce Suite, allowing autonomous AI agents "
                        "to conduct machine-to-machine financial settlements using standardized tokenized credentials. "
                        "The suite features instant settlement, spend limit guardrails, and automated invoice verification."
                    ),
                    provider="mock_search",
                    published_at=now,
                    raw_metadata={"score": 0.98, "domain": "stripe.com"},
                )
            )
            items.append(
                IngestedItem(
                    url="https://techcrunch.com/2026/02/14/stripe-expands-machine-payments-apis/",
                    title="Stripe expands machine payments APIs to challenge Adyen unified commerce",
                    content=(
                        "Financial technology giant Stripe has introduced new machine payment primitives. "
                        "Industry analysts note the move intensifies competition against Adyen and PayPal, "
                        "targeting high-frequency agentic software transactions in enterprise commerce."
                    ),
                    provider="mock_search",
                    published_at=now,
                    raw_metadata={"score": 0.94, "domain": "techcrunch.com"},
                )
            )

        if "adyen" in q or "pricing" in q or "interchange" in q or not items:
            items.append(
                IngestedItem(
                    url="https://www.adyen.com/press-and-media/2026-q1-unified-commerce-expansion",
                    title="Adyen Expands Embedded Financial Products Across North American Enterprise Merchants",
                    content=(
                        "Adyen revealed a 24% year-over-year surge in unified commerce volume, expanding its embedded "
                        "card issuing and business bank account offerings to direct enterprise platforms in North America."
                    ),
                    provider="mock_search",
                    published_at=now,
                    raw_metadata={"score": 0.92, "domain": "adyen.com"},
                )
            )

        if "plaid" in q or "open banking" in q or len(items) < 2:
            items.append(
                IngestedItem(
                    url="https://plaid.com/blog/instant-account-verification-v2/",
                    title="Plaid Rolls Out Next-Gen Instant Account Verification with Real-Time Risk Scoring",
                    content=(
                        "Plaid announced the general availability of its upgraded account verification engine, "
                        "reducing fraud by 35% using real-time synthetic identity detection across credit unions."
                    ),
                    provider="mock_search",
                    published_at=now,
                    raw_metadata={"score": 0.89, "domain": "plaid.com"},
                )
            )

        return items[:max_results]


class TavilySearchProvider(BaseSearchProvider):
    """Live search provider backed by Tavily's AI search API."""

    def __init__(self, api_key: str | None = None):
        import os

        settings = get_settings()
        self.api_key = api_key or settings.tavily_api_key or os.getenv("TAVILY_API_KEY")

    async def search(self, query: str, max_results: int = 5) -> list[IngestedItem]:
        if not self.api_key:
            logger.warning("Tavily API key not configured; falling back to MockSearchProvider")
            return await MockSearchProvider().search(query, max_results)

        url = "https://api.tavily.com/search"
        payload = {
            "api_key": self.api_key,
            "query": query,
            "search_depth": "advanced",
            "topic": "news",
            "max_results": max_results,
            "include_raw_content": False,
        }

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(url, json=payload)
                resp.raise_for_status()
                data = resp.json()

            results: list[IngestedItem] = []
            now = datetime.now(UTC)
            for res in data.get("results", []):
                results.append(
                    IngestedItem(
                        url=res.get("url", ""),
                        title=res.get("title", ""),
                        content=res.get("content", ""),
                        provider="tavily",
                        published_at=now,
                        raw_metadata={"score": res.get("score", 0.0)},
                    )
                )
            return results
        except Exception as e:
            logger.error(f"Tavily search failed for query '{query}': {e}. Falling back to mock.")
            return await MockSearchProvider().search(query, max_results)
