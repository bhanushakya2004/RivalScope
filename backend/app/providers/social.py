"""Social and syndicated feed providers: RSS and Mock."""

import xml.etree.ElementTree as ET
from datetime import UTC, datetime

import httpx

from app.core.logging import get_logger
from app.providers.base import BaseSocialProvider, IngestedItem

logger = get_logger("providers.social")


class MockSocialProvider(BaseSocialProvider):
    """Deterministic offline social pulse provider."""

    async def fetch_feed(self, feed_url: str, limit: int = 10) -> list[IngestedItem]:
        logger.info(f"[MockSocial] Fetching offline pulse for: {feed_url}")
        now = datetime.now(UTC)

        return [
            IngestedItem(
                url="https://stripe.com/blog/infrastructure-scaling-cyber-week",
                title="Engineering at Scale: How Stripe Processed Peak Volume with 99.999% Reliability",
                content=(
                    "Stripe's core infrastructure engineering team shares architecture patterns for "
                    "multi-region ledger replication, zero-downtime card tokenization, and latency profiling."
                ),
                provider="mock_social",
                published_at=now,
                raw_metadata={"author": "Stripe Engineering", "channel": "blog"},
            ),
            IngestedItem(
                url="https://x.com/fintech_insider/status/1758291039",
                title="Industry chatter: Adyen testing biometric passkey payments in retail stores",
                content=(
                    "Fintech industry watchers report pilot trials of Adyen's palm and facial biometric authentication "
                    "terminals across major department stores in London and Paris."
                ),
                provider="mock_social",
                published_at=now,
                raw_metadata={"engagement_score": 1420, "channel": "social"},
            ),
        ][:limit]


class RssSocialProvider(BaseSocialProvider):
    """Syndicated RSS and Atom feed provider."""

    async def fetch_feed(self, feed_url: str, limit: int = 10) -> list[IngestedItem]:
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(feed_url, headers={"User-Agent": "RivalScope-RSS/1.0"})
                resp.raise_for_status()
                text = resp.text

            root = ET.fromstring(text)
            items: list[IngestedItem] = []

            # Check RSS 2.0 channel -> item
            for item in root.findall(".//item")[:limit]:
                title = item.findtext("title", "Untitled")
                link = item.findtext("link", "")
                description = item.findtext("description", "")
                pub_date_str = item.findtext("pubDate", "")

                items.append(
                    IngestedItem(
                        url=link,
                        title=title,
                        content=description,
                        provider="rss",
                        published_at=datetime.now(UTC),
                        raw_metadata={"raw_pub_date": pub_date_str, "feed_url": feed_url},
                    )
                )

            # Check Atom feed -> entry
            if not items:
                ns = {"atom": "http://www.w3.org/2005/Atom"}
                for entry in root.findall(".//atom:entry", ns)[:limit]:
                    title = entry.findtext("atom:title", "", ns)
                    link_el = entry.find("atom:link", ns)
                    link = link_el.get("href", "") if link_el is not None else ""
                    summary = entry.findtext("atom:summary", "", ns) or entry.findtext(
                        "atom:content", "", ns
                    )

                    items.append(
                        IngestedItem(
                            url=link,
                            title=title,
                            content=summary or "",
                            provider="atom",
                            published_at=datetime.now(UTC),
                            raw_metadata={"feed_url": feed_url},
                        )
                    )

            return items
        except Exception as e:
            logger.error(f"RSS fetch failed for {feed_url}: {e}. Falling back to mock provider.")
            return await MockSocialProvider().fetch_feed(feed_url, limit)
