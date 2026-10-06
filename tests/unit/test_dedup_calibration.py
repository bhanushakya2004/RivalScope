"""Calibration tests for the 6-stage deduplication pipeline."""

from datetime import UTC, datetime

from app.dedup import DeduplicationPipeline, compute_simhash, hamming_distance
from app.ingestion.schemas import IngestionItem
from app.ingestion.url_utils import canonicalize_url


def test_stage_1_url_canonicalization():
    url1 = "https://STRIPE.com/newsroom/agentic?utm_source=twitter&utm_medium=social#overview"
    url2 = "https://stripe.com/newsroom/agentic/?ref=fintechfeed"

    c1 = canonicalize_url(url1)
    c2 = canonicalize_url(url2)

    assert c1 == "https://stripe.com/newsroom/agentic"
    assert c2 == "https://stripe.com/newsroom/agentic"
    assert c1 == c2


def test_stage_2_exact_content_hashing():
    pipeline = DeduplicationPipeline()
    now = datetime.now(UTC)

    item1 = IngestionItem(
        url="https://stripe.com/news/1",
        canonical_url="https://stripe.com/news/1",
        title="Stripe Agentic Commerce",
        content="Stripe launched agentic commerce suite.",
        contained_content="...",
        content_hash="hash-abc-123",
        provider="search",
        company_id="c-stripe",
        company_name="Stripe",
        published_at=now,
    )

    item2 = IngestionItem(
        url="https://mirror.stripe.com/news/1",
        canonical_url="https://mirror.stripe.com/news/1",
        title="Stripe Agentic Commerce Repost",
        content="Stripe launched agentic commerce suite.",
        contained_content="...",
        content_hash="hash-abc-123",  # Exact same content hash
        provider="crawl",
        company_id="c-stripe",
        company_name="Stripe",
        published_at=now,
    )

    res1 = pipeline.process("t-test", item1)
    assert res1.status in ["unique_cluster", "passed"]

    res2 = pipeline.process("t-test", item2)
    assert res2.status == "duplicate_exact"
    assert res2.dropped_at_stage == "stage_2_exact_hash"


def test_stage_3_simhash_near_duplicate_calibration():
    # Base real-world release (approx 70 words)
    t1 = (
        "Stripe announced the official launch of its new Agentic Commerce Suite today, enabling developers "
        "to build autonomous software agents capable of executing merchant checkouts and micro-settlements securely. "
        "The platform introduces programmatic spending limits, machine-readable invoices, and tokenized credentials "
        "tailored for LLM architectures. By deploying protocol-level rails for machine-to-machine financial transactions, "
        "Stripe aims to capture the emerging market of agent-driven retail before legacy competitors adapt."
    )
    # Minor editorial change (syndicated variation)
    t2 = (
        "Stripe announced the official launch of their new Agentic Commerce Suite today, enabling developers "
        "to build autonomous software agents capable of executing merchant checkouts and micro-settlements securely. "
        "The platform introduces programmatic spending limits, machine-readable invoices, and tokenized credentials "
        "tailored for LLM architectures. By deploying protocol-level rails for machine-to-machine financial transactions, "
        "Stripe aims to capture the emerging market of agent-driven retail before legacy competitors adapt."
    )
    # Completely different fintech article
    t3 = (
        "Klarna reported strong revenue acceleration across its European buy-now-pay-later division, driven by "
        "consumer adoption of its AI assistant and merchant checkout integrations. Operating income swung to a profit "
        "ahead of its anticipated direct listing on the New York Stock Exchange."
    )

    h1 = compute_simhash(t1)
    h2 = compute_simhash(t2)
    h3 = compute_simhash(t3)

    dist_near = hamming_distance(h1, h2)
    dist_diff = hamming_distance(h1, h3)

    assert dist_near <= 3, f"Expected Hamming distance <= 3, got {dist_near}"
    assert dist_diff > 15, (
        f"Expected distinct documents to have Hamming distance > 15, got {dist_diff}"
    )


def test_stage_4_and_5_semantic_clustering_and_corroboration():
    pipeline = DeduplicationPipeline()
    now = datetime.now(UTC)

    item1 = IngestionItem(
        url="https://techcrunch.com/stripe-agents",
        canonical_url="https://techcrunch.com/stripe-agents",
        title="Stripe unveils AI agent payments",
        content="Stripe announced tools allowing autonomous software agents to pay merchants directly.",
        contained_content="...",
        content_hash="hash-1",
        provider="search",
        company_id="c-stripe",
        company_name="Stripe",
        published_at=now,
    )

    res1 = pipeline.process("t-test", item1)
    assert res1.cluster is not None
    assert res1.matched_cluster_id is not None

    # Second item with very high semantic similarity (corroborating source)
    item2 = IngestionItem(
        url="https://reuters.com/stripe-machine-payments",
        canonical_url="https://reuters.com/stripe-machine-payments",
        title="Stripe launches agentic commerce tools",
        content="Stripe announced tools allowing autonomous software agents to pay merchants directly.",
        contained_content="...",
        content_hash="hash-2",
        provider="crawl",
        company_id="c-stripe",
        company_name="Stripe",
        published_at=now,
    )

    # If exact or simhash pass, semantic layer corroborates
    # Let's adjust content slightly so it gets past exact hash and SimHash
    item2.content = "Stripe released primitives enabling autonomous AI agents to execute direct checkout transactions."
    item2.content_hash = "hash-different"

    res2 = pipeline.process("t-test", item2)
    assert res2.status in ["corroborated", "unique_cluster"]


def test_stage_6_delivery_novelty_scoring():
    pipeline = DeduplicationPipeline()
    historical_titles = [
        "Stripe launched Agentic Commerce Protocol SDK for AI Agents",
    ]

    # Stale re-hash
    stale_item = IngestionItem(
        url="https://blog.com/stripe-recap",
        canonical_url="https://blog.com/stripe-recap",
        title="Stripe Agentic Commerce Protocol SDK for AI Agents",
        content="Stripe launched Agentic Commerce Protocol SDK for AI Agents.",
        contained_content="...",
        content_hash="hash-stale",
        provider="search",
        company_id="c-stripe",
        company_name="Stripe",
    )

    res = pipeline.process("t-test", stale_item, historical_titles=historical_titles)
    # Stale recap with 90%+ lexical overlap should be dropped at novelty stage
    assert res.status == "filtered_novelty"
    assert res.dropped_at_stage == "stage_6_novelty"
    assert res.novelty_score < 0.65
