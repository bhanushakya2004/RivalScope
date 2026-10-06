"""Stage 4: Semantic Deduplication using Cosine Similarity."""

import hashlib
import math

from app.config import get_settings


def compute_deterministic_embedding(text: str, dimensions: int = 128) -> list[float]:
    """
    Generate deterministic, normalized dense vector for offline testing
    and fast local semantic clustering with zero API costs.
    """
    vec = [0.0] * dimensions
    words = text.lower().split()
    for word in words:
        digest = hashlib.sha256(word.encode("utf-8")).digest()
        for i in range(min(dimensions, len(digest))):
            vec[i] += (digest[i] - 128) / 128.0

    # L2 normalize
    norm = math.sqrt(sum(x * x for x in vec))
    if norm > 0:
        return [x / norm for x in vec]
    return vec


def cosine_similarity(v1: list[float], v2: list[float]) -> float:
    """Calculate cosine similarity between two normalized vectors."""
    if not v1 or not v2 or len(v1) != len(v2):
        return 0.0
    dot_product = sum(a * b for a, b in zip(v1, v2, strict=False))
    norm_a = math.sqrt(sum(a * a for a in v1))
    norm_b = math.sqrt(sum(b * b for b in v2))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot_product / (norm_a * norm_b)


class SemanticDeduplicator:
    """Evaluates semantic similarity between newly ingested items and existing clusters."""

    def __init__(self, threshold: float | None = None):
        settings = get_settings()
        self.threshold = threshold if threshold is not None else settings.semantic_cosine_threshold
        # In-memory vector store: tenant_id -> List of (doc_id, competitor_id, embedding)
        self._vectors: dict[str, list[tuple[str, str, list[float]]]] = {}

    def is_semantic_duplicate(
        self,
        tenant_id: str,
        embedding: list[float],
        competitor_id: str,
    ) -> tuple[bool, str | None, float]:
        """
        Check if vector similarity exceeds threshold for same competitor.
        Returns (is_dup, match_doc_id, similarity_score).
        """
        records = self._vectors.get(tenant_id, [])
        best_sim = 0.0
        best_match = None

        for doc_id, comp_id, existing_vec in records:
            if comp_id == competitor_id:
                sim = cosine_similarity(embedding, existing_vec)
                if sim > best_sim:
                    best_sim = sim
                    best_match = doc_id

        if best_sim >= self.threshold:
            return True, best_match, best_sim

        return False, best_match, best_sim

    def record(
        self, tenant_id: str, doc_id: str, competitor_id: str, embedding: list[float]
    ) -> None:
        """Store embedding in index."""
        if tenant_id not in self._vectors:
            self._vectors[tenant_id] = []
        self._vectors[tenant_id].append((doc_id, competitor_id, embedding))
