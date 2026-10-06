"""Multi-stage deduplication package."""

from app.dedup.canonicalize import UrlCanonicalizer
from app.dedup.delivery_dedup import DeliveryDeduplicator
from app.dedup.embedding import (
    SemanticDeduplicator,
    compute_deterministic_embedding,
    cosine_similarity,
)
from app.dedup.event_cluster import ClusterCitation, CorroboratedCluster, EventClusterEngine
from app.dedup.hashing import ExactContentHasher
from app.dedup.pipeline import DeduplicationPipeline, DedupPipelineResult
from app.dedup.simhash import SimHashFilter, compute_simhash, hamming_distance

__all__ = [
    "UrlCanonicalizer",
    "ExactContentHasher",
    "SimHashFilter",
    "compute_simhash",
    "hamming_distance",
    "SemanticDeduplicator",
    "compute_deterministic_embedding",
    "cosine_similarity",
    "EventClusterEngine",
    "ClusterCitation",
    "CorroboratedCluster",
    "DeliveryDeduplicator",
    "DeduplicationPipeline",
    "DedupPipelineResult",
]
