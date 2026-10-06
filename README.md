# RivalScope: Autonomous Multi-Agent Competitive Intelligence for Fintech

[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python](https://img.shields.io/badge/Python-3.12-3776AB.svg?logo=python)](https://python.org)
[![Agno](https://img.shields.io/badge/Agno-3.1.1-purple.svg)](https://agno.com)
[![Next.js](https://img.shields.io/badge/Next.js-14-black.svg?logo=next.js)](https://nextjs.org)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16%20%2B%20pgvector-336791.svg?logo=postgresql)](https://github.com/pgvector/pgvector)

RivalScope is an open-source, self-hostable, multi-agent Competitive Intelligence platform tailored for the fintech vertical (payments, neobanks, lending, crypto, and wealthtech). It features plug-and-play architecture, a bidirectional Model Context Protocol (MCP) gateway, four-layer memory, and multi-stage deduplication.

---

## Architecture Diagram

```mermaid
flowchart TB
    subgraph Ingestion["1. Multi-Vector Ingestion"]
        SEC["SEC EDGAR (10-K, 10-Q, 8-K)"]
        TAV["Tavily Search (Fintech News & Earnings)"]
        FC["Firecrawl (Product Diffs, Pricing, Hiring)"]
        RSS["Compliant RSS & Feeds"]
    end

    subgraph DedupEngine["2. Multi-Stage Dedup & Clustering"]
        Canon["URL Canonicalization"]
        ExactHash["Exact SHA-256 Hashing"]
        SimHash["Near-Dup SimHash (Hamming < 3)"]
        SemDedup["Vector Cosine Clustering (> 0.88)"]
        Corroborate["Event Corroboration Count"]
    end

    subgraph Agents["3. Specialized Agent Orchestration"]
        Orch["Team Coordinator (TeamMode.coordinate)"]
        Verifier["Verifier Agent (Evidence Cross-Check)"]
        Analyst["Fintech Analyst (Impact & 'So What')"]
        Reporter["Reporter Agent (Slack / TG / Markdown)"]
    end

    subgraph Memory["4. Four-Layer Memory"]
        M1["Working / Session Memory"]
        M2["User & Org Memory (Preferences)"]
        M3["Knowledge Memory (pgvector Hybrid RAG)"]
        M4["Entity & Event Timeline (PostgreSQL)"]
    end

    subgraph MCP["5. MCP Layer (Bidirectional)"]
        Server["Platform MCP Server (/mcp)"]
        Gateway["Tenant MCP Gateway (CRM / Jira / Data Warehouse)"]
    end

    Ingestion --> DedupEngine
    DedupEngine --> Memory
    DedupEngine --> Agents
    Memory <--> Agents
    Agents --> MCP
```

---

## Key Features

- **Fintech Specialized Collectors**:
  - `NewsScout`: Real-time news discovery via Tavily and WebSearch fallback.
  - `ProductWatcher`: Crawls changelogs, API documentation, and pricing tables to compute diffs.
  - `FinanceAnalyst`: SEC EDGAR filings extractor (10-K, 10-Q, 8-K), funding rounds, and quarterly releases.
  - `TalentSignals`: Strategic hiring trends from public career portals (strictly ToS-compliant; no LinkedIn scraping).
  - `SocialPulse`: Official RSS/blog syndicated feeds and authorized social adapters.
- **Strict Compliance & Data Provenance**:
  - Respects `robots.txt` and domain rate limits.
  - Every extracted fact carries exact URL citation, fetch timestamp, and corroboration score.
  - Hallucination rejection: claims not backed by retrieved evidence are rejected by the Verifier.
- **Four-Layer Memory Architecture**:
  1. *Working/Session Memory*: Multi-turn dialogue state with run scratchpad.
  2. *User/Org Memory*: Durable company positioning and competitor watchlists.
  3. *Knowledge/Semantic Memory*: High-dimensional hybrid search (BM25 + pgvector).
  4. *Entity & Event Timeline*: Structured competitor timeline for trend charts and contradiction checks.
- **Multi-Stage Deduplication**:
  - Eliminates 70-85% of syndicated press release noise via URL canonicalization, SHA-256 hash, SimHash, semantic vector clustering, and delivery idempotency.
- **Bidirectional MCP**:
  - **MCP Server**: Exposes RivalScope capabilities at `/mcp` for Claude, Cursor, and ChatGPT.
  - **MCP Gateway**: Allows tenants to connect their own internal MCP servers (CRM, Snowflake, Jira) with strict SSRF defense, envelope encryption, and tool allowlisting.
- **100% Offline Demo Mode**:
  - Runs end-to-end with zero API keys required via deterministic mock providers.

---

## Quickstart

### 1. Run Offline Demo in 2 Minutes (No API Keys Needed)

```bash
# Clone repository
git clone https://github.com/rivalscope/rivalscope.git
cd rivalscope

# Copy environment template
cp .env.example .env

# Start infrastructure (PostgreSQL with pgvector, Redis)
make up

# Run offline demo (seeds fintech rivals, executes agents, generates cited report)
make demo
```

Visit the Web UI at `http://localhost:3000` or inspect the API at `http://localhost:7777/docs`.

### 2. Connect Real Providers

Edit `.env` to configure your API keys:
- `OPENAI_API_KEY` (or `ANTHROPIC_API_KEY` / `GEMINI_API_KEY`)
- `TAVILY_API_KEY`
- `FIRECRAWL_API_KEY`
- `SLACK_BOT_TOKEN` / `TELEGRAM_BOT_TOKEN`
- Set `MOCK_PROVIDERS=false`

---

## Environment Variables Table

| Variable | Description | Default |
| :--- | :--- | :--- |
| `MOCK_PROVIDERS` | Enable offline mock providers | `true` |
| `DATABASE_URL` | PostgreSQL 16 connection URL | `postgresql+psycopg://postgres:postgres@localhost:5432/rivalscope` |
| `REDIS_URL` | Redis 7 connection URL | `redis://localhost:6379/0` |
| `LLM_PROVIDER` | LLM model vendor (`openai`, `anthropic`, `gemini`) | `openai` |
| `COLLECTOR_MODEL`| Model for data extraction | `openai:gpt-4o-mini` |
| `ANALYST_MODEL` | High-reasoning model for reports | `openai:gpt-4o` |
| `TAVILY_API_KEY` | Tavily search API key | `None` |
| `FIRECRAWL_API_KEY`| Firecrawl scraping API key | `None` |
| `MCP_SERVER_ENABLED`| Serve MCP at `/mcp` | `true` |
| `MCP_ALLOW_PRIVATE_IPS`| Permit gateway to connect to private subnets | `false` |

---

## How to Extend

### Add a New Data Provider
1. Inherit from the base interface in `app/providers/<category>/base.py`.
2. Implement `fetch()` and `normalize()`.
3. Provide a corresponding mock implementation in `app/providers/<category>/mock.py`.
4. Register the provider in `app/providers/registry.py`.

### Add a New Agent
1. Define the agent role, prompt instructions, and Pydantic output schema in `app/agents/`.
2. Attach tools from `app/tools/` or provider interfaces.
3. Register the agent in `app/agents/orchestrator.py`.

### Register a Tenant MCP Server
1. Navigate to **MCP Gateway** in the Web UI or call `POST /api/v1/mcp/servers`.
2. Supply transport (`streamable-http`), URL, and authentication headers.
3. Test connectivity and selectively allowlist tools in the policy manager.

---

## Legal & Compliance Notes
See [Legal & Data Sources](docs/legal-data-sources.md) for full compliance guidelines. RivalScope operates strictly on public data, respects `robots.txt`, enforces rate limits, and rejects scrapers of forbidden sites (including LinkedIn).

## License
Apache License 2.0. See [LICENSE](LICENSE).
