"""External ingestion and notification providers package."""

from app.providers.base import (
    BaseCrawlProvider,
    BaseFilingsProvider,
    BaseNotifier,
    BaseSearchProvider,
    BaseSocialProvider,
    IngestedItem,
)
from app.providers.crawl import FirecrawlProvider, MockCrawlProvider
from app.providers.filings import MockFilingsProvider, SecEdgarFilingsProvider
from app.providers.notify import MockNotifier, SlackNotifier, TelegramNotifier, WebhookNotifier
from app.providers.search import MockSearchProvider, TavilySearchProvider
from app.providers.social import MockSocialProvider, RssSocialProvider

__all__ = [
    "IngestedItem",
    "BaseSearchProvider",
    "BaseCrawlProvider",
    "BaseFilingsProvider",
    "BaseSocialProvider",
    "BaseNotifier",
    "MockSearchProvider",
    "TavilySearchProvider",
    "MockCrawlProvider",
    "FirecrawlProvider",
    "MockFilingsProvider",
    "SecEdgarFilingsProvider",
    "MockSocialProvider",
    "RssSocialProvider",
    "MockNotifier",
    "SlackNotifier",
    "TelegramNotifier",
    "WebhookNotifier",
]
