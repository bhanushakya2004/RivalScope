# ADR 0002: Four-Layer Memory Architecture and Unified MemoryManager Facade

## Status
Accepted

## Context
Competitive intelligence platforms require diverse memory temporalities:
1. Immediate conversational context (session state during an interactive investigation).
2. Durable organization preferences (our positioning, alert thresholds, competitor priorities).
3. Long-term semantic knowledge (historical articles, regulatory filings, reports).
4. Structured temporal facts (timeline of product launches, executive changes, funding rounds).

Without clean separation, LLM contexts suffer from token bloat, hallucinations, and stale data.

## Decision
We implement a **Four-Layer Memory Architecture** coordinated behind a single facade (`app.memory.manager.MemoryManager`):

1. **Layer 1: Working / Session Memory**
   - Agno session management backed by PostgreSQL (`PostgresDb`).
   - Run history tracking (`add_history_to_context=True`, `num_history_runs=3`).
   - Ephemeral scratchpad stored in `session_state` for intermediate workflow computations.

2. **Layer 2: User & Organization Memory**
   - Agno `MemoryManager` storing durable facts about the user's organization.
   - Includes company profile, target positioning, tracked competitors, alert sensitivity, and negative topic filters.
   - Exposed in the Web UI for manual editing and deletion with full audit provenance.

3. **Layer 3: Knowledge & Semantic Memory (Long-Term RAG)**
   - Backed by PostgreSQL `pgvector` via `agno.vectordb.pgvector.PgVector`.
   - Hybrid search (`SearchType.hybrid` combining dense vector embeddings with PostgreSQL tsvector full-text search).
   - Stores chunked `raw_documents` and generated reports with metadata filters (`tenant_id`, `competitor_id`, `category`, `published_at`).

4. **Layer 4: Entity & Event Timeline Memory**
   - Normalized relational tables in PostgreSQL (`signals`, `event_clusters`, `entity_timeline`).
   - Supports structured queries: "What features did Stripe launch in Q3?", "Show pricing changes for Adyen over the past 6 months".
   - Contradiction detection: compares newly extracted facts against existing records to flag updates, reversals, or false claims.

## Facade Interface
The `MemoryManager` facade exposes narrow, tenant-scoped methods to agents:
- `remember(tenant_id, text, category)`: Store durable org fact.
- `recall(tenant_id, query)`: Retrieve relevant org context.
- `search_knowledge(tenant_id, query, competitor_id, category, limit)`: Hybrid search over vector store.
- `timeline_query(tenant_id, competitor_id, start_date, end_date)`: Relational timeline slice.

## Consequences
- **Positive**: Strict tenant isolation across all layers, optimal token economics, fast hybrid retrieval, and clear provenance for every insight.
- **Negative**: Requires maintaining both relational and vector indexes in PostgreSQL.
