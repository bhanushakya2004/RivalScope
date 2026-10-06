"""Unit tests for offline and mock ingestion providers."""

import pytest
from app.providers.crawl import MockCrawlProvider
from app.providers.filings import MockFilingsProvider
from app.providers.notify import MockNotifier
from app.providers.search import MockSearchProvider
from app.providers.social import MockSocialProvider


@pytest.mark.asyncio
async def test_mock_search_provider():
    provider = MockSearchProvider()
    results = await provider.search("stripe payment agent", max_results=3)
    assert len(results) > 0
    assert "stripe" in results[0].url
    assert results[0].provider == "mock_search"


@pytest.mark.asyncio
async def test_mock_crawl_provider():
    provider = MockCrawlProvider()
    item = await provider.crawl_url("https://stripe.com/changelog")
    assert item is not None
    assert "Agentic" in item.content
    assert item.provider == "mock_crawl"


@pytest.mark.asyncio
async def test_mock_filings_provider():
    provider = MockFilingsProvider()
    filings = await provider.get_recent_filings("SQ", limit=2)
    assert len(filings) == 2
    assert "SQ" in filings[0].title
    assert filings[0].raw_metadata.get("form") in ["8-K", "10-Q"]


@pytest.mark.asyncio
async def test_mock_social_provider():
    provider = MockSocialProvider()
    items = await provider.fetch_feed("https://stripe.com/blog/feed.xml", limit=2)
    assert len(items) == 2
    assert items[0].provider == "mock_social"


@pytest.mark.asyncio
async def test_mock_notifier():
    notifier = MockNotifier()
    success = await notifier.send(
        target="#intel-alerts",
        title="Competitor Alert",
        message="Stripe launched machine payments suite",
    )
    assert success is True
    assert len(notifier.sent_messages) == 1
    assert notifier.sent_messages[0]["title"] == "Competitor Alert"
