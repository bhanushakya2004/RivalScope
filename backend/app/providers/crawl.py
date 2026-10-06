"""Crawl providers: Firecrawl and deterministic Mock."""

from datetime import UTC, datetime

import httpx

from app.config import get_settings
from app.core.logging import get_logger
from app.providers.base import BaseCrawlProvider, IngestedItem

logger = get_logger("providers.crawl")


class MockCrawlProvider(BaseCrawlProvider):
    """Deterministic offline crawler for tests, changelogs, and product pages."""

    async def crawl_url(self, url: str) -> IngestedItem | None:
        logger.info(f"[MockCrawl] Crawling url offline: {url}")
        now = datetime.now(UTC)
        u = url.lower()

        if "stripe" in u:
            return IngestedItem(
                url=url,
                title="Stripe Changelog - Agentic Payments and Multi-Currency Instant Payouts",
                content=(
                    "February 2026 Release Notes:\n"
                    "- Launched Agentic Commerce API v2 with machine-readable payment descriptors.\n"
                    "- Added instant cross-border treasury settlements across 35 countries.\n"
                    "- Deprecated legacy v1 dispute webhooks in favor of streaming SSE dispute feeds."
                ),
                provider="mock_crawl",
                published_at=now,
                raw_metadata={"status_code": 200, "word_count": 48},
            )
        elif "adyen" in u:
            return IngestedItem(
                url=url,
                title="Adyen Product Updates - Next-Generation Unified Point of Sale Terminals",
                content=(
                    "Product Announcements:\n"
                    "- NYC1 and S1F2 terminal firmware upgraded with offline EMV PIN authentication.\n"
                    "- Embedded Capital financing pre-approvals now integrated into merchant dashboard.\n"
                    "- Interchange+ optimization algorithm updated for European merchants."
                ),
                provider="mock_crawl",
                published_at=now,
                raw_metadata={"status_code": 200, "word_count": 42},
            )
        else:
            return IngestedItem(
                url=url,
                title=f"Extracted content from {url}",
                content=f"Extracted verified page content for {url}. Includes recent product roadmap and hiring updates.",
                provider="mock_crawl",
                published_at=now,
                raw_metadata={"status_code": 200, "word_count": 25},
            )


class FirecrawlProvider(BaseCrawlProvider):
    """Live webpage scraper using Firecrawl API."""

    def __init__(self, api_key: str | None = None):
        settings = get_settings()
        self.api_key = api_key or settings.firecrawl_api_key

    async def crawl_url(self, url: str) -> IngestedItem | None:
        if not self.api_key:
            logger.warning("Firecrawl API key not configured; falling back to MockCrawlProvider")
            return await MockCrawlProvider().crawl_url(url)

        endpoint = "https://api.firecrawl.dev/v0/scrape"
        headers = {"Authorization": f"Bearer {self.api_key}"}
        payload = {"url": url, "pageOptions": {"onlyMainContent": True}}

        try:
            async with httpx.AsyncClient(timeout=25.0) as client:
                resp = await client.post(endpoint, json=payload, headers=headers)
                resp.raise_for_status()
                data = resp.json().get("data", {})

            return IngestedItem(
                url=url,
                title=data.get("metadata", {}).get("title", f"Scraped from {url}"),
                content=data.get("markdown") or data.get("content", ""),
                provider="firecrawl",
                published_at=datetime.now(UTC),
                raw_metadata=data.get("metadata", {}),
            )
        except Exception as e:
            logger.error(f"Firecrawl failed for {url}: {e}. Falling back to mock crawler.")
            return await MockCrawlProvider().crawl_url(url)
