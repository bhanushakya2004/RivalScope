"""Stage 6: Delivery Idempotency and Novelty Scoring."""

from datetime import date

from app.config import get_settings


class DeliveryDeduplicator:
    """Enforces per-channel notification idempotency and novelty filtering."""

    def __init__(self, novelty_threshold: float | None = None):
        settings = get_settings()
        self.novelty_threshold = (
            novelty_threshold if novelty_threshold is not None else settings.novelty_score_threshold
        )
        self._sent_keys: set[str] = set()

    def generate_idempotency_key(
        self,
        tenant_id: str,
        cluster_id: str,
        channel_id: str,
        target_date: date | None = None,
    ) -> str:
        """Create unique key scoped to tenant, cluster, notification channel, and day."""
        d = target_date or date.today()
        return f"{tenant_id}:{cluster_id}:{channel_id}:{d.isoformat()}"

    def is_already_delivered(self, idempotency_key: str) -> bool:
        """Check if notification has already been dispatched for this channel/date."""
        return idempotency_key in self._sent_keys

    def record_delivery(self, idempotency_key: str) -> None:
        """Record successful delivery to prevent repeated alerts."""
        self._sent_keys.add(idempotency_key)

    def calculate_novelty_score(
        self,
        cluster_title: str,
        cluster_summary: str,
        historical_titles: list[str],
    ) -> float:
        """
        Calculate novelty score between 0.0 and 1.0 against historical timeline events.
        A score of 1.0 means completely unprecedented; < 0.65 indicates redundant recap.
        """
        if not historical_titles:
            return 1.0

        new_words = set(f"{cluster_title} {cluster_summary}".lower().split())
        if not new_words:
            return 0.0

        max_overlap_ratio = 0.0
        for past_title in historical_titles:
            past_words = set(past_title.lower().split())
            if not past_words:
                continue
            common = new_words.intersection(past_words)
            overlap = len(common) / min(len(new_words), len(past_words))
            if overlap > max_overlap_ratio:
                max_overlap_ratio = overlap

        # Novelty is inverse of maximum lexical overlap with existing timeline events
        novelty = max(0.0, 1.0 - max_overlap_ratio)
        return round(novelty, 3)

    def should_deliver(self, novelty_score: float) -> bool:
        """Determine whether signal exceeds minimum novelty threshold for user alert."""
        return novelty_score >= self.novelty_threshold
