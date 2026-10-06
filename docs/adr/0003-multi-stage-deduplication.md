# ADR 0003: Multi-Stage Deduplication and Event Clustering Pipeline

## Status
Accepted

## Context
Competitive monitoring feeds ingest hundreds of articles, press releases, blog reposts, and social updates daily. A major product launch or regulatory event may generate dozens of syndicated news articles covering the exact same factual event. Feeding all raw documents into downstream LLM reasoning stages leads to:
1. Massive redundant token expenditure.
2. Skewed importance weighting (a single syndicated press release looks like 50 distinct events).
3. Repetitive reports delivered to users in Slack, Telegram, and the dashboard.

Additionally, assuming vanilla Redis includes Bloom filters is an operational hazard, as vanilla Redis lacks bloom filter commands unless the RedisBloom or Redis Stack module is installed.

## Decision
We implement a **6-stage pipeline** in `app/dedup/` with configurable thresholds, pre-fetch canonicalization, and a durable PostgreSQL persistence layer:

1. **Stage 1: Pre-Fetch URL Canonicalization (`canonicalize.py`)**:
   - Canonicalization runs **before fetching** wherever URLs are discovered (RSS feeds, search results, site links) to conserve network bandwidth and avoid duplicate scraping.
   - Strip tracking and referral query parameters (`utm_*`, `ref`, `fbclid`, `gclid`, `mc_eid`, etc.).
   - Standardize protocol (enforce https), lowercase hostname, strip default ports (80/443), and remove trailing slashes and hash fragments.
   - Resolve URL redirects and respect `<link rel="canonical">` metadata.

2. **Stage 2: Exact Content Hashing (`hashing.py`)**:
   - Normalize text (strip extraneous whitespace, apply Unicode NFKC normalization).
   - Compute SHA-256 hash.
   - Compare against a durable **PostgreSQL unique table/set (`document_hashes`)** which acts as the authoritative durability owner.
   - If Redis Stack with RedisBloom is enabled, check RedisBloom as a fast in-memory accelerator before checking PostgreSQL.

3. **Stage 3: Near-Duplicate Detection via SimHash (`simhash.py`)**:
   - Generate 64-bit SimHash over word 3-grams.
   - Calculate Hamming distance against recent documents (within a configurable time window, default 14 days, per competitor).
   - If Hamming distance <= `SIMHASH_HAMMING_THRESHOLD` (configurable, default 3), mark as near-duplicate.

4. **Stage 4: Semantic Deduplication (`embedding.py`)**:
   - Generate vector embedding of title and leading content chunks.
   - Compute cosine similarity against signals within the same competitor and 7-day window using PostgreSQL `pgvector`.
   - If cosine similarity > `SEMANTIC_COSINE_THRESHOLD` (configurable, default 0.88), merge evidence into the existing signal cluster.

5. **Stage 5: Event-Level Clustering (`event_cluster.py`)**:
   - Group related signals into `EventCluster` records.
   - Maintain a `corroboration_count` (number of distinct primary sources reporting this event).
   - Aggregate all source URLs, timestamps, and extracted entity mentions as citations for the cluster.

6. **Stage 6: Delivery Idempotency & Novelty Scoring (`delivery_dedup.py`)**:
   - Enforce delivery idempotency keys: `f"{tenant_id}:{cluster_id}:{channel}:{delivery_date}"`.
   - Compute a novelty score against Layer 4 Timeline Memory so scheduled alerts only push genuinely new or modified facts.

## Threshold Configuration & Calibration
All deduplication thresholds are configurable via environment variables and tenant settings:
- `SIMHASH_HAMMING_THRESHOLD` (default: 3)
- `SEMANTIC_COSINE_THRESHOLD` (default: 0.88)
- `NOVELTY_SCORE_THRESHOLD` (default: 0.65)

A dedicated calibration test suite (`tests/unit/test_dedup_calibration.py`) validates precision and recall on a curated fintech test corpus (e.g. syndicated wire releases, pricing updates, false positives).

## Durability & Storage Ownership
- **PostgreSQL 16 (`document_hashes`)** is the sole durability owner for dedup hashes and set membership.
- **Redis 7** is strictly an optional accelerator for ephemeral caching; data loss in Redis never compromises dedup integrity.

## Consequences
- **Positive**: 75-85% reduction in downstream LLM token usage, zero duplicate notifications, resilient persistence without requiring Redis Stack.
- **Negative**: Adds hashing, SimHash, and embedding computation overhead during ingestion.
