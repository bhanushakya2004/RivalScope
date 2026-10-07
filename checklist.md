# RivalScope Implementation Checklist & Status

**Platform**: RivalScope — Open-source, self-hostable, multi-agent Competitive Intelligence platform (Fintech Vertical).  
**Orchestration Engine**: Agno 3.1.1 + FastAPI + AgentOS.  
**Durability & State**: PostgreSQL 16 (`pgvector`) + Redis 7.  
**Execution Mode**: Autonomous development; local git commits only (manual push by operator).

---

## 1. Architectural Foundations & ADRs

- [x] **ADR 0001**: Micro-kernel & Agent Architecture using Agno 3.1.1
- [x] **ADR 0002**: Four-Layer Memory Architecture Facade (`RivalMemory`) with `SearchType.hybrid`
- [x] **ADR 0003**: 6-Stage Deduplication Pipeline with PostgreSQL `document_hashes` durability
- [x] **ADR 0004**: MCP Gateway Security, Extended SSRF Blocklist (IPv6 + CGNAT + 0.0.0.0/8), DNS Re-resolution & Policy Caching
- [x] **ADR 0005**: Prompt-Injection Defense, Untrusted Content Isolation & Schema-Validated HITL
- [x] **ADR 0006**: Deterministic `MockModel` for Zero-Token Offline Testing & CI
- [x] **ADR 0007**: Storage Durability Ownership (PostgreSQL primary, Redis ephemeral accelerator)
- [x] **Legal Data Ingestion**: SEC EDGAR User-Agent compliance & strict <=10 req/s rate limits (`docs/legal-data-sources.md`)

---

## 2. Core Backend Infrastructure

- [x] **Configuration**: Pydantic Settings with env parsing, dedup calibration, and rate limits ([backend/app/config.py](file:///C:/Users/bhanu/Desktop/Projects/RivalMoves/backend/app/config.py))
- [x] **Deterministic LLM**: Offline `MockModel` subclassing Agno `Model` ([backend/app/core/mock_model.py](file:///C:/Users/bhanu/Desktop/Projects/RivalMoves/backend/app/core/mock_model.py))
- [x] **Security Engine**: AES-256-GCM envelope encryption, Argon2/PBKDF2 password hashing, JWT tenant scoping ([backend/app/core/security.py](file:///C:/Users/bhanu/Desktop/Projects/RivalMoves/backend/app/core/security.py))
- [x] **Rate Limiter**: Token-bucket algorithm with Redis and in-memory fallback ([backend/app/core/ratelimit.py](file:///C:/Users/bhanu/Desktop/Projects/RivalMoves/backend/app/core/ratelimit.py))
- [x] **Observability**: Structured JSON logging and Prometheus metrics ([backend/app/core/logging.py](file:///C:/Users/bhanu/Desktop/Projects/RivalMoves/backend/app/core/logging.py), [backend/app/core/telemetry.py](file:///C:/Users/bhanu/Desktop/Projects/RivalMoves/backend/app/core/telemetry.py))
- [x] **Database Models**: SQLAlchemy 2.0 schemas for Tenants, Companies, Sources, RawDocuments, DocumentHashes, EventClusters, Signals, Reports, Schedules, Runs, McpServers, McpPolicies, TimelineEvents ([backend/app/db/models.py](file:///C:/Users/bhanu/Desktop/Projects/RivalMoves/backend/app/db/models.py))
- [x] **Fintech Seed Data**: Realistic PayPulse tenant with Stripe, Adyen, and Revolut benchmark documents ([backend/app/db/seed.py](file:///C:/Users/bhanu/Desktop/Projects/RivalMoves/backend/app/db/seed.py))

---

## 3. Ingestion & 6-Stage Deduplication Pipeline

- [x] **Stage 1 (Pre-fetch & Ingestion)**: URL normalization, UTM/tracking strip, canonical resolution ([backend/app/dedup/canonicalize.py](file:///C:/Users/bhanu/Desktop/Projects/RivalMoves/backend/app/dedup/canonicalize.py))
- [x] **Stage 2**: Exact SHA-256 content hashing with durable PostgreSQL `document_hashes` check ([backend/app/dedup/hashing.py](file:///C:/Users/bhanu/Desktop/Projects/RivalMoves/backend/app/dedup/hashing.py))
- [x] **Stage 3**: 64-bit unigram SimHash near-duplicate detection with calibrated Hamming distance <= 3 ([backend/app/dedup/simhash.py](file:///C:/Users/bhanu/Desktop/Projects/RivalMoves/backend/app/dedup/simhash.py))
- [x] **Stage 4**: Cosine semantic clustering via deterministic embeddings / pgvector ([backend/app/dedup/embedding.py](file:///C:/Users/bhanu/Desktop/Projects/RivalMoves/backend/app/dedup/embedding.py))
- [x] **Stage 5**: Multi-source corroboration cluster grouping ([backend/app/dedup/event_cluster.py](file:///C:/Users/bhanu/Desktop/Projects/RivalMoves/backend/app/dedup/event_cluster.py))
- [x] **Stage 6**: Multi-channel delivery novelty scoring (historical suppression & threshold gating) ([backend/app/dedup/delivery_dedup.py](file:///C:/Users/bhanu/Desktop/Projects/RivalMoves/backend/app/dedup/delivery_dedup.py))
- [x] **Collectors**: Parallel runner executing Search, Web Crawl, SEC EDGAR, Public Careers, and Syndicated Social feeds ([backend/app/ingestion/collector_runner.py](file:///C:/Users/bhanu/Desktop/Projects/RivalMoves/backend/app/ingestion/collector_runner.py))

---

## 4. Four-Layer Memory Facade (`RivalMemory`)

- [x] **Layer 1**: Session / Working context integration ([backend/app/memory/manager.py](file:///C:/Users/bhanu/Desktop/Projects/RivalMoves/backend/app/memory/manager.py))
- [x] **Layer 2**: Organizational & user preferences persistence
- [x] **Layer 3**: Knowledge base retrieval with hybrid keyword + vector search (`SearchType.hybrid`)
- [x] **Layer 4**: Chronological entity timeline and automated contradiction detection (pricing reversals, leadership shifts)

---

## 5. Multi-Agent Teams & Autonomous Workflows

- [x] **Specialized Agents**:
  - `VerifierAgent`: Source validation, fact checking, and citation attribution ([backend/app/agents/verifier_agent.py](file:///C:/Users/bhanu/Desktop/Projects/RivalMoves/backend/app/agents/verifier_agent.py))
  - `AnalystAgent`: Strategic impact, threat assessment, and counter-move recommendation ([backend/app/agents/analyst_agent.py](file:///C:/Users/bhanu/Desktop/Projects/RivalMoves/backend/app/agents/analyst_agent.py))
  - `ReporterAgent`: Executive brief synthesis with structured markdown ([backend/app/agents/reporter_agent.py](file:///C:/Users/bhanu/Desktop/Projects/RivalMoves/backend/app/agents/reporter_agent.py))
- [x] **Team Coordination**: Agno `Team` with `TeamMode.coordinate` and `RivalMemory` tool injection ([backend/app/teams/ci_team.py](file:///C:/Users/bhanu/Desktop/Projects/RivalMoves/backend/app/teams/ci_team.py))
- [x] **Autonomous Workflow**: `MonitorPipelineWorkflow` orchestrating ingestion, dedup, verification, analysis, report synthesis, timeline updates, and notification ([backend/app/workflows/monitor_pipeline.py](file:///C:/Users/bhanu/Desktop/Projects/RivalMoves/backend/app/workflows/monitor_pipeline.py))
- [x] **Delivery Dispatcher**: Multi-channel dispatching with channel idempotency ([backend/app/delivery/dispatcher.py](file:///C:/Users/bhanu/Desktop/Projects/RivalMoves/backend/app/delivery/dispatcher.py))
- [x] **Interactive Q&A Followup & Chatbot SSE**: Natural language conversational handler answering follow-up queries with citation memory and real-time Server-Sent Events (SSE) streaming ([backend/app/delivery/followup.py](file:///C:/Users/bhanu/Desktop/Projects/RivalMoves/backend/app/delivery/followup.py), [backend/app/api/v1/chat.py](file:///C:/Users/bhanu/Desktop/Projects/RivalMoves/backend/app/api/v1/chat.py))

---

## 6. Bidirectional MCP Server & Secure Gateway

- [x] **MCP Server**: FastMCP server exposing competitive intelligence tools (`search_knowledge_base`, `get_competitor_timeline`, `get_company_signals`)
- [x] **SSRF Firewall**: Comprehensive blocklist including IPv4 private/loopback, IPv6 unique-local/link-local/mapped, CGNAT (`100.64.0.0/10`), `0.0.0.0/8`, and AWS/GCP/Azure metadata endpoints ([backend/app/mcp_gateway/ssrf.py](file:///C:/Users/bhanu/Desktop/Projects/RivalMoves/backend/app/mcp_gateway/ssrf.py))
- [x] **DNS Re-Resolution & Redirect Protection**: Connect-time IP re-verification preventing DNS rebinding and blind redirects
- [x] **Policy Cache Invalidation**: Cache key structured as `f"{tenant_id}:{policy_version}"` ([backend/app/mcp_gateway/policy.py](file:///C:/Users/bhanu/Desktop/Projects/RivalMoves/backend/app/mcp_gateway/policy.py))
- [x] **HITL Write-Gating**: Mutation tools requiring operator approval via tokenized resume ([backend/app/mcp_gateway/client.py](file:///C:/Users/bhanu/Desktop/Projects/RivalMoves/backend/app/mcp_gateway/client.py))
- [x] **Isolation**: `stdio` transport disabled by default (admin-only)

---

## 7. API Layer & Scheduler

- [x] **FastAPI + AgentOS Integration**: Root application mounting AgentOS alongside versioned domain routes ([backend/app/main.py](file:///C:/Users/bhanu/Desktop/Projects/RivalMoves/backend/app/main.py))
- [x] **REST API v1**:
  - `/api/v1/auth`: Login, JWT issuance, profile retrieval
  - `/api/v1/companies`: Competitor registration, feed tracking, metadata
  - `/api/v1/signals`: Scored intelligence signals with confidence filters
  - `/api/v1/reports`: Intelligence brief query & on-demand synthesis
  - `/api/v1/schedules`: Autonomous recurring cycle definition & manual run triggers
  - `/api/v1/mcp-servers`: Dynamic MCP registry & tool policy patching
  - `/api/v1/memory`: Organizational preferences & entity timeline queries
  - `/api/v1/runs`: Execution tracking & HITL resume endpoint
- [x] **Autonomous Scheduler**: Background cron polling loop executing scheduled monitor cycles ([backend/app/scheduler/scheduler.py](file:///C:/Users/bhanu/Desktop/Projects/RivalMoves/backend/app/scheduler/scheduler.py))
- [x] **Worker Process**: Standalone background worker daemon ([backend/app/worker.py](file:///C:/Users/bhanu/Desktop/Projects/RivalMoves/backend/app/worker.py))

---

## 8. Evaluation, Golden Benchmarks & Demo Runner

- [x] **Golden Fintech Benchmark Suite**: Grounded evaluation across Stripe, Adyen, and Revolut test cases ([backend/app/evals/benchmark.py](file:///C:/Users/bhanu/Desktop/Projects/RivalMoves/backend/app/evals/benchmark.py))
  - Precision @ 3 = 1.000
  - Deduplication F1 Score = 0.980
  - Composite Score = 0.990 (Status: PASSED)
- [x] **Demo Runner Script**: Self-contained offline demonstration executable via `make demo` ([backend/app/scripts/demo_runner.py](file:///C:/Users/bhanu/Desktop/Projects/RivalMoves/backend/app/scripts/demo_runner.py))

---

## 9. Quality Gate & Testing

- [x] **Test Suite**: 64/64 unit and integration tests passing (`pytest tests/`)
- [x] **Linter**: 0 errors on `ruff check backend tests`
- [x] **Formatter**: Clean code formatting on `ruff format --check backend tests`
- [x] **OpenAPI Schema**: Successfully verified registered operations including interactive chat, guardrail check, judge scoring, and harness runs

---

## 10. Durable State, Chat Sessions & Dynamic UI

- [x] **PostgreSQL Chat Session & Message Persistence**: Added `ChatSession` and `ChatMessage` models (`backend/app/db/models/chat.py`) with PostgreSQL UUID primary keys, tenant isolation, and timestamps. Implemented `/api/v1/chat/sessions` (list, get transcript, delete) and wired chat endpoints to persist user queries and assistant responses.
- [x] **Agno Native Storage Integration**: Configured `agno.db.postgres.PostgresDb` in `app.db.session` (`agno_sessions`, `agno_runs`, `agno_memories`) and injected it directly into `create_ci_team()` to allow Agno itself to manage agent state, runs, and memories with zero greenlet warnings.
- [x] **Grounded Chat Prompting & Conversational Intelligence**: Enhanced `FollowUpHandler._build_grounded_prompt` to dynamically query live tenant companies, verified signals, and timeline events from PostgreSQL. Natural conversational greetings for "hi"/"hello", capabilities overview for capability queries, and grounded summaries for competitor queries.
- [x] **Comprehensive Dynamic UI Overhaul**: Audited and overhauled `frontend/components/rivalscope-app.tsx` and `frontend/lib/api.ts` to eliminate all hardcoded fallback data:
  - `SchedulesView`: Live schedule cards with cadence details and interactive "Run Now" trigger.
  - `MemoryView`: Layer 2 organizational preferences with inline creation form + Layer 4 entity timeline.
  - `CompareView`: Dynamic side-by-side competitor comparison derived from live signals.
  - `Mcp`: Full server registry with dynamic tool policy toggles and inline "Register Server" form.
  - `Competitors`: Live competitor watchlist with real signal counts and add competitor form.
  - `Chat Drawer`: Session switcher, "+ New Chat" button, transcript loading, and SSE token streaming.
- [x] **Docker Multi-Container Packaging**: Both frontend (`rivalmoves-web`) and backend (`rivalmoves-api`, `rivalmoves-worker`) Docker images built and validated. Full stack running healthy (`postgres`, `redis`, `api`, `worker`, `web`).
- [x] **Alembic Migration History**: Initial automated schema migration revision generated and stamped to head (`backend/alembic/versions/a0a73ffafa80_initial_schema.py`) with native pgvector extension support.
- [x] **Google AI Studio Gemini & Tavily Integration**: Centralized model factory (`app.core.model_factory.resolve_model`) using Agno's `Gemini` (`from agno.models.google import Gemini`) with Google AI Studio API key (`GOOGLE_API_KEY` / `GEMINI_API_KEY`) across all agents (`VerifierAgent`, `AnalystAgent`, `ReporterAgent`), teams (`ci_team`), workflows (`MonitorPipelineWorkflow`), and handlers (`FollowUpHandler`), alongside `TavilySearchProvider` activation via `TAVILY_API_KEY`.
- [x] **Real-Time Chatbot SSE Streaming**: Progressive Server-Sent Events (SSE) token-by-token streaming via `sse-starlette` (`POST /api/v1/chat/stream` and `GET /api/v1/chat/stream`), integrated with Agno team runner, Next.js reverse proxy (`/api/v1/:path*`), and interactive React chat drawer with immediate token streaming.
- [x] **Zero-ENV Resilient Architecture**: Graceful fallback handling when external API keys are omitted. System defaults to deterministic `MockModel`, `MockSearchProvider`, `MockCrawlProvider`, and optional `.env` loading in docker compose.
- [x] **CI/CD Pipeline**: GitHub Actions workflow (`.github/workflows/ci.yml`) running `ruff`, `mypy`, and `pytest` on push

---

## 11. Multi-Layer Agent Guardrails Subsystem

- [x] **Input Guardrails** (`backend/app/guardrails/input_guardrails.py`):
  - `PromptInjectionGuardrail`: Direct adversarial jailbreak detection ("ignore previous instructions", "DAN mode", "reveal system prompt") blocking attacks before agent execution.
  - `PIIScrubbingGuardrail`: Automated detection and redaction of credit card numbers (`[REDACTED_CREDIT_CARD]`), SSNs (`[REDACTED_SSN]`), and API secrets (`[REDACTED_SECRET_KEY]`).
  - `ScopeGuardrail`: Detection and blocking of destructive commands (SQL injections, drop table, malicious scripts).
  - `UntrustedContentIsolationGuardrail`: ADR 0005 quarantine for external crawled text with automated XML breakout sanitization and tag encapsulation (`<untrusted_source_content>`).
- [x] **Output Guardrails** (`backend/app/guardrails/output_guardrails.py`):
  - `SystemLeakageGuardrail`: Output scanning and redaction of database URIs (`postgresql+psycopg://`), Redis connection strings, and internal secrets.
  - `FinancialSlanderGuardrail`: Defamation and market manipulation safeguard flagging uncorroborated solvency/fraud claims and auto-appending formal legal compliance notices.
  - `HallucinationGroundingGuardrail`: Verifies competitor mentions against active tenant watchlists and validates markdown citation URLs.
- [x] **Unified Runner Harness** (`backend/app/guardrails/runner.py`): Centralized `AgentGuardrailHarness` integrating both input and output pipelines across `FollowUpHandler` and `MonitorPipelineWorkflow`.

---

## 12. LLM-as-a-Judge Evaluation & Agent Benchmarking Harness

- [x] **LLM-as-a-Judge Evaluation Engine** (`backend/app/evals/llm_judge.py`):
  - Evaluates agent outputs across 5 core dimensions:
    1. `groundedness` (0.0–1.0): Factual verification against context without hallucinations.
    2. `strategic_relevance` (0.0–1.0): Direct responsiveness and competitive intelligence depth.
    3. `guardrail_safety` (0.0–1.0): Resistance to adversarial attacks, secret leakage prevention, and safe refusals.
    4. `actionability` (0.0–1.0): Concrete tactical counter-moves and executive implications.
    5. `citation_quality` (0.0–1.0): Valid attribution and source URL citation integrity.
  - Dual-mode execution: Live evaluation using Google AI Studio Gemini (`gemini-3.8-flash`) or high-precision deterministic offline evaluation for zero-token CI testing.
- [x] **Agent Benchmarking Test Harness** (`backend/app/evals/harness.py`):
  - Predefined Golden Scenarios: `stripe_agentic_payments`, `adyen_unified_commerce`, `revolut_us_banking`, `adversarial_prompt_injection`, `pii_scrubbing_check`, and `conversational_capabilities`.
  - Automated end-to-end execution: Input guardrail verification -> Agent/Team coordination -> Output guardrails -> LLM-as-a-Judge scoring.
  - Formatted Markdown reporting and CLI executable (`python -m app.evals.harness`, `make evals`). Attained 100% pass rate (6/6 passed, composite score 0.965).
- [x] **Evaluation & Guardrail API Endpoints** (`backend/app/api/v1/evals.py`):
  - `GET /api/v1/evals/scenarios`: Enumerate benchmark test cases.
  - `POST /api/v1/evals/judge`: Run LLM-as-a-Judge scoring on arbitrary query/response pairs.
  - `POST /api/v1/evals/harness/run`: Trigger on-demand benchmark suite execution with category filtering.
  - `POST /api/v1/evals/guardrails/check`: Interactive guardrail testing endpoint for input/output verification.
- [x] **Live Provider Key Verification & Quota Fallback**: Live Google AI Studio Gemini (`gemini-3.8-flash`) key verified. Automatic mapping of deprecated model IDs to `gemini-3.8-flash`, with interception of Google AI Studio 429 quota exhaustion (`RESOURCE_EXHAUSTED`) to fall back gracefully to grounded PostgreSQL intelligence without raw JSON error leakage.
- [ ] **Helm & Kubernetes Manifests**: Optional cloud-native deployment manifests for self-hosted enterprise clusters

