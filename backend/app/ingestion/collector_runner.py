"""Parallel execution runner for the 5 specialized ingestion collectors."""

import asyncio
import hashlib
import time

from app.config import get_settings
from app.core.logging import get_logger
from app.ingestion.normalizer import normalize_text, wrap_untrusted_content
from app.ingestion.schemas import IngestionBatchResult, IngestionItem
from app.ingestion.url_utils import canonicalize_url
from app.providers import (
    BaseCrawlProvider,
    BaseFilingsProvider,
    BaseSearchProvider,
    BaseSocialProvider,
    FirecrawlProvider,
    MockCrawlProvider,
    MockFilingsProvider,
    MockSearchProvider,
    MockSocialProvider,
    RssSocialProvider,
    SecEdgarFilingsProvider,
    TavilySearchProvider,
)

logger = get_logger("ingestion.collector_runner")


class CollectorRunner:
    """Orchestrates parallel data collection across fintech competitors."""

    def __init__(
        self,
        search_provider: BaseSearchProvider | None = None,
        crawl_provider: BaseCrawlProvider | None = None,
        filings_provider: BaseFilingsProvider | None = None,
        social_provider: BaseSocialProvider | None = None,
    ):
        settings = get_settings()

        if settings.mock_providers:
            self.search = search_provider or MockSearchProvider()
            self.crawl = crawl_provider or MockCrawlProvider()
            self.filings = filings_provider or MockFilingsProvider()
            self.social = social_provider or MockSocialProvider()
        else:
            self.search = search_provider or (
                TavilySearchProvider() if settings.tavily_api_key else MockSearchProvider()
            )
            self.crawl = crawl_provider or (
                FirecrawlProvider() if settings.firecrawl_api_key else MockCrawlProvider()
            )
            self.filings = filings_provider or SecEdgarFilingsProvider()
            self.social = social_provider or RssSocialProvider()

    async def run_for_competitor(
        self,
        tenant_id: str,
        company_id: str,
        company_name: str,
        domain: str,
        ticker: str | None = None,
        feeds: list[str] | None = None,
    ) -> IngestionBatchResult:
        """Execute all 5 collection vectors in parallel for a given competitor."""
        start_time = time.time()
        logger.info(f"Starting parallel collection for {company_name} ({domain})")

        # 1. Prepare parallel collection tasks
        search_query = f"{company_name} fintech payments product update 2026"
        changelog_url = f"https://{domain}/changelog"
        feed_url = feeds[0] if feeds else f"https://{domain}/blog/feed.xml"

        tasks = [
            self.search.search(query=search_query, max_results=3),
            self.crawl.crawl_url(url=changelog_url),
            self.social.fetch_feed(feed_url=feed_url, limit=2),
        ]

        if ticker:
            tasks.append(self.filings.get_recent_filings(identifier=ticker, limit=2))

        # Execute concurrently with exception suppression
        results = await asyncio.gather(*tasks, return_exceptions=True)

        raw_items = []
        errors = []

        # Unpack Search Results
        if isinstance(results[0], Exception):
            errors.append(f"Search failed: {results[0]}")
        elif isinstance(results[0], list):
            raw_items.extend(results[0])

        # Unpack Crawl Results
        if isinstance(results[1], Exception):
            errors.append(f"Crawl failed: {results[1]}")
        elif results[1] is not None:
            raw_items.append(results[1])

        # Unpack Social Results
        if isinstance(results[2], Exception):
            errors.append(f"Social failed: {results[2]}")
        elif isinstance(results[2], list):
            raw_items.extend(results[2])

        # Unpack Filings Results if ticker present
        if ticker and len(results) > 3:
            if isinstance(results[3], Exception):
                errors.append(f"Filings failed: {results[3]}")
            elif isinstance(results[3], list):
                raw_items.extend(results[3])

        # 2. Normalize and compute Stage 1 & 2 hashes
        ingested_items: list[IngestionItem] = []
        for raw in raw_items:
            # Stage 1: URL Canonicalization
            canonical = canonicalize_url(raw.url)
            norm_content = normalize_text(raw.content)

            # Stage 2: Exact SHA-256 Hash
            content_hash = hashlib.sha256(norm_content.encode("utf-8")).hexdigest()
            contained = wrap_untrusted_content(norm_content, canonical)

            ingested_items.append(
                IngestionItem(
                    url=raw.url,
                    canonical_url=canonical,
                    title=raw.title,
                    content=norm_content,
                    contained_content=contained,
                    content_hash=content_hash,
                    provider=raw.provider,
                    company_id=company_id,
                    company_name=company_name,
                    published_at=raw.published_at,
                    metadata_json=raw.raw_metadata,
                )
            )

        duration = time.time() - start_time
        logger.info(
            f"Completed collection for {company_name}: {len(ingested_items)} items discovered in {duration:.2f}s"
        )

        return IngestionBatchResult(
            tenant_id=tenant_id,
            total_discovered=len(ingested_items),
            items=ingested_items,
            errors=errors,
            duration_seconds=duration,
        )
