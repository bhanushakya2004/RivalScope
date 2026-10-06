# ADR 0007: Storage Durability Ownership and Ephemeral Redis Role

## Status
Accepted

## Context
A common architectural pitfall is over-relying on Redis for core data persistence or assuming that a standard Redis deployment includes Bloom filter data structures. Standard upstream Redis 7 does not include bloom filters out of the box unless the RedisBloom module (or Redis Stack distribution) is installed.

Furthermore, stateful workflows, event logs, and deduplication records must survive process restarts and Redis cache flushes without corrupting competitive intelligence history or generating duplicate reports.

## Decision
We formally define the durability boundaries and storage roles across PostgreSQL and Redis:

1. **Durability Owner: PostgreSQL 16**:
   - PostgreSQL 16 is the single source of truth and authoritative durability owner for:
     - Workflow run states, steps, and checkpoints (`AgentOS` durable database).
     - Relational entities (tenants, companies, competitors, signals, reports, schedules, audit logs).
     - Layer 3 Vector and Keyword RAG indexes (`pgvector` tables).
     - Layer 4 Timeline facts and event clusters.
     - Ingestion Deduplication Set: An authoritative PostgreSQL table `document_hashes (tenant_id UUID, hash_type VARCHAR, hash_value VARCHAR, created_at TIMESTAMPTZ, PRIMARY KEY (tenant_id, hash_type, hash_value))` with unique B-tree indexes guarantees permanent deduplication.

2. **Ephemeral Acceleration Role: Redis 7**:
   - Redis is strictly used for transient, high-throughput operations where data loss on restart is tolerable:
     - Token bucket rate limiting (sliding window counters using `INCR` and `EXPIRE`).
     - Pub/Sub message distribution for Server-Sent Events (SSE) and live log streaming.
     - Ephemeral cache for recently computed competitor summaries.
   - **Optional RedisBloom**: If Redis Stack / RedisBloom module is detected, RivalScope can optionally mirror hashes into a Redis bloom filter for microsecond pre-filtering, but PostgreSQL remains the durability owner.

## Consequences
- **Positive**: Platform operates reliably on standard PostgreSQL and vanilla Redis; zero data loss if Redis restarts or is cleared; robust transactional integrity.
- **Negative**: Checking PostgreSQL B-tree index for exact deduplication is slightly higher latency than an in-memory bloom filter, but easily handles enterprise throughput (< 5ms per lookup).
