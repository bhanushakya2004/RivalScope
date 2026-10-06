"""Base provider abstractions and schemas for external ingestion and notifications."""

from abc import ABC, abstractmethod
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field


class IngestedItem(BaseModel):
    """Normalized ingested item returned by ingestion providers."""

    url: str
    title: str
    content: str
    provider: str
    published_at: datetime | None = Field(default_factory=lambda: datetime.now(UTC))
    raw_metadata: dict[str, Any] = Field(default_factory=dict)


class BaseSearchProvider(ABC):
    """Abstract base class for web and news search providers."""

    @abstractmethod
    async def search(self, query: str, max_results: int = 5) -> list[IngestedItem]:
        """Search the web or news feeds for items matching the query."""
        pass


class BaseCrawlProvider(ABC):
    """Abstract base class for webpage and changelog crawlers."""

    @abstractmethod
    async def crawl_url(self, url: str) -> IngestedItem | None:
        """Extract main content and metadata from a target webpage."""
        pass


class BaseFilingsProvider(ABC):
    """Abstract base class for financial and regulatory filing providers."""

    @abstractmethod
    async def get_recent_filings(
        self,
        identifier: str,
        form_types: list[str] | None = None,
        limit: int = 5,
    ) -> list[IngestedItem]:
        """Fetch regulatory filings for a given company ticker or CIK."""
        pass


class BaseSocialProvider(ABC):
    """Abstract base class for RSS and public social pulse feeds."""

    @abstractmethod
    async def fetch_feed(self, feed_url: str, limit: int = 10) -> list[IngestedItem]:
        """Parse syndicated RSS/Atom or public social feed."""
        pass


class BaseNotifier(ABC):
    """Abstract base class for delivery channels."""

    @abstractmethod
    async def send(
        self,
        target: str,
        title: str,
        message: str,
        metadata: dict[str, Any] | None = None,
    ) -> bool:
        """Deliver competitive intelligence notification to target recipient or channel."""
        pass
