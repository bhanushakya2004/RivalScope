"""Unified 6-Stage Deduplication and Event Corroboration Pipeline."""

import uuid

from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.core.telemetry import DEDUP_PROCESSED_TOTAL
from app.dedup.canonicalize import UrlCanonicalizer
from app.dedup.delivery_dedup import DeliveryDeduplicator
from app.dedup.embedding import SemanticDeduplicator, compute_deterministic_embedding
from app.dedup.event_cluster import ClusterCitation, CorroboratedCluster, EventClusterEngine
from app.dedup.hashing import ExactContentHasher
from app.dedup.simhash import SimHashFilter, compute_simhash
from app.ingestion.schemas import IngestionItem

logger = get_logger("dedup.pipeline")


class DedupPipelineResult(BaseModel):
    """Result of passing an ingested document through the 6-stage pipeline."""

    item_url: str
    status: str  # unique_cluster, corroborated, duplicate_url, duplicate_exact, duplicate_simhash, duplicate_semantic, filtered_novelty
    dropped_at_stage: str | None = None
    matched_cluster_id: str | None = None
    cluster: CorroboratedCluster | None = None
    simhash_val: int | None = None
    simhash_distance: int | None = None
    semantic_similarity: float | None = None
    novelty_score: float | None = None


class DeduplicationPipeline:
    """Orchestrates all six stages of deduplication sequentially."""

    def __init__(self, db: Session | None = None):
        self.canonicalizer = UrlCanonicalizer(db=db)
        self.exact_hasher = ExactContentHasher(db=db)
        self.simhash_filter = SimHashFilter()
        self.semantic_dedup = SemanticDeduplicator()
        self.cluster_engine = EventClusterEngine()
        self.delivery_dedup = DeliveryDeduplicator()

    def process(
        self,
        tenant_id: str,
        item: IngestionItem,
        historical_titles: list[str] | None = None,
    ) -> DedupPipelineResult:
        """Run a single item through the full 6-stage deduplication pipeline."""
        comp_id = item.company_id or "unknown-company"
        comp_name = item.company_name or "Competitor"

        # --- Stage 1: URL Canonicalization ---
        if self.canonicalizer.is_duplicate(tenant_id, item.canonical_url):
            DEDUP_PROCESSED_TOTAL.labels(stage="canonical_url", result="dropped").inc()
            logger.info(f"[Dedup Stage 1] Dropped duplicate canonical URL: {item.canonical_url}")
            return DedupPipelineResult(
                item_url=item.url,
                status="duplicate_url",
                dropped_at_stage="stage_1_canonical_url",
            )
        self.canonicalizer.record(tenant_id, item.canonical_url)
        DEDUP_PROCESSED_TOTAL.labels(stage="canonical_url", result="passed").inc()

        # --- Stage 2: Exact Content Hashing ---
        if self.exact_hasher.is_duplicate(tenant_id, item.content_hash):
            DEDUP_PROCESSED_TOTAL.labels(stage="exact_hash", result="dropped").inc()
            logger.info(f"[Dedup Stage 2] Dropped exact SHA-256 match for {item.canonical_url}")
            return DedupPipelineResult(
                item_url=item.url,
                status="duplicate_exact",
                dropped_at_stage="stage_2_exact_hash",
            )
        self.exact_hasher.record(tenant_id, item.content_hash)
        DEDUP_PROCESSED_TOTAL.labels(stage="exact_hash", result="passed").inc()

        # --- Stage 3: Near-Duplicate Detection via SimHash ---
        simhash_val = compute_simhash(item.content)
        is_near_dup, matched_doc_id, dist = self.simhash_filter.is_near_duplicate(
            tenant_id=tenant_id,
            simhash_val=simhash_val,
            competitor_id=comp_id,
        )
        if is_near_dup:
            DEDUP_PROCESSED_TOTAL.labels(stage="simhash", result="dropped").inc()
            logger.info(f"[Dedup Stage 3] Dropped SimHash near-duplicate (distance {dist})")
            return DedupPipelineResult(
                item_url=item.url,
                status="duplicate_simhash",
                dropped_at_stage="stage_3_simhash",
                simhash_val=simhash_val,
                simhash_distance=dist,
            )
        self.simhash_filter.record(
            tenant_id=tenant_id,
            simhash_val=simhash_val,
            doc_id=item.content_hash,
            competitor_id=comp_id,
        )
        DEDUP_PROCESSED_TOTAL.labels(stage="simhash", result="passed").inc()

        # --- Stage 4: Semantic Cosine Similarity ---
        embedding = compute_deterministic_embedding(item.content)
        is_sem_dup, matched_cluster_id, sim_score = self.semantic_dedup.is_semantic_duplicate(
            tenant_id=tenant_id,
            embedding=embedding,
            competitor_id=comp_id,
        )

        citation = ClusterCitation(
            url=item.canonical_url,
            title=item.title,
            provider=item.provider,
            published_at=item.published_at,
        )

        # --- Stage 5: Event-Level Clustering ---
        if is_sem_dup and matched_cluster_id:
            # Corroborate existing cluster
            DEDUP_PROCESSED_TOTAL.labels(stage="semantic_cosine", result="corroborated").inc()
            cluster = self.cluster_engine.add_to_cluster(matched_cluster_id, citation)
            logger.info(
                f"[Dedup Stage 5] Corroborated cluster {matched_cluster_id} (count: {cluster.corroboration_count})"
            )
            return DedupPipelineResult(
                item_url=item.url,
                status="corroborated",
                matched_cluster_id=matched_cluster_id,
                cluster=cluster,
                simhash_val=simhash_val,
                semantic_similarity=sim_score,
            )

        # Create new cluster for unique signal
        new_cluster_id = f"cluster-{uuid.uuid4().hex[:12]}"
        cluster = self.cluster_engine.create_cluster(
            cluster_id=new_cluster_id,
            tenant_id=tenant_id,
            company_id=comp_id,
            company_name=comp_name,
            title=item.title,
            summary=item.content[:280],
            category="product",
            citation=citation,
        )
        self.semantic_dedup.record(tenant_id, new_cluster_id, comp_id, embedding)
        DEDUP_PROCESSED_TOTAL.labels(stage="semantic_cosine", result="passed").inc()

        # --- Stage 6: Delivery Idempotency & Novelty Scoring ---
        novelty_score = self.delivery_dedup.calculate_novelty_score(
            cluster_title=cluster.title,
            cluster_summary=cluster.summary,
            historical_titles=historical_titles or [],
        )

        if not self.delivery_dedup.should_deliver(novelty_score):
            DEDUP_PROCESSED_TOTAL.labels(stage="novelty_check", result="dropped").inc()
            logger.info(
                f"[Dedup Stage 6] Dropped redundant recap below novelty threshold ({novelty_score:.2f})"
            )
            return DedupPipelineResult(
                item_url=item.url,
                status="filtered_novelty",
                dropped_at_stage="stage_6_novelty",
                matched_cluster_id=new_cluster_id,
                cluster=cluster,
                simhash_val=simhash_val,
                novelty_score=novelty_score,
            )

        DEDUP_PROCESSED_TOTAL.labels(stage="novelty_check", result="passed").inc()
        return DedupPipelineResult(
            item_url=item.url,
            status="unique_cluster",
            matched_cluster_id=new_cluster_id,
            cluster=cluster,
            simhash_val=simhash_val,
            novelty_score=novelty_score,
        )
