# ADR 0003: Multi-Stage Deduplication and Event Clustering Pipeline

## Status
Accepted

## Context
Competitive monitoring feeds ingest hundreds of articles, press releases, blog reposts, and social updates daily. A major product launch or regulatory event may generate dozens of syndicated news articles covering the exact same factual event. Feeding all raw documents into downstream LLM reasoning stages leads to:
1. Massive redundant token expenditure.
2. Skewed importance weighting (a single syndicated press release looks like 50 distinct events).
3. Repetitive reports delivered to users in Slack, Telegram, and the dashboard.

## Decision
We implement a **6-stage pipeline** in `app/dedup/`:

1. **Stage 1: URL Canonicalization (`canonicalize.py`)**:
   - Strip tracking parameters (`utm_*`, `ref`, `fbclid`, `gclid`, etc.).
   - Standardize protocol (enforce https), lowercase hostname, strip default ports and trailing slashes.
   - Resolve URL redirects and follow canonical HTML `<link rel="canonical">` tags when available.

2. **Stage 2: Exact Content Hashing (`hashing.py`)**:
   - Normalize text (remove extraneous whitespace, standard unicode normal form NFKC).
   - Compute SHA-256 hash. If hash matches existing document for the tenant, immediately mark as duplicate.

3. **Stage 3: Near-Duplicate Detection via SimHash (`simhash.py`)**:
   - Generate 64-bit SimHash over token n-grams.
   - Calculate Hamming distance against recent documents (within 14 days for the same competitor).
   - If Hamming distance <= 3, mark as near-duplicate (e.g. syndicated wire releases, minor blog edits).

4. **Stage 4: Semantic Deduplication (`embedding.py`)**:
   - Generate vector embedding of title and leading summary paragraphs.
   - Compute cosine similarity against signals within the same competitor and 7-day window.
   - If cosine similarity > 0.88, merge evidence into the existing signal cluster.

5. **Stage 5: Event-Level Clustering (`event_cluster.py`)**:
   - Group related signals into `EventCluster` records.
   - Maintain a `corroboration_count` (how many distinct sources reported this event).
   - Aggregate all source URLs and timestamps as citations for the cluster.

6. **Stage 6: Delivery Idempotency & Novelty Scoring (`delivery_dedup.py`)**:
   - Track delivery idempotency keys `(signal_cluster_id, channel_id, delivery_date)`.
   - Compute a novelty score against Timeline Memory so digests only highlight newly discovered facts.

## Metrics & Observability
Expose deduplication performance metrics via Prometheus:
- `dedup_filtered_total{stage="canonical_url"}`
- `dedup_filtered_total{stage="exact_hash"}`
- `dedup_filtered_total{stage="simhash"}`
- `dedup_filtered_total{stage="semantic_cosine"}`
- `dedup_clusters_formed_total`

## Consequences
- **Positive**: 70-85% reduction in downstream LLM token usage, higher quality reports, no repetitive alerts.
- **Negative**: Adds processing overhead (hashing, SimHash, embedding comparison) before LLM analysis.
