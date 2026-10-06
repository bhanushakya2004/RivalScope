# RivalScope

[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python](https://img.shields.io/badge/Python-3.12-3776AB.svg?logo=python)](https://python.org)
[![Agno](https://img.shields.io/badge/Agno-3.1.1-purple.svg)](https://agno.com)
[![Next.js](https://img.shields.io/badge/Next.js-16.3.3-black.svg?logo=next.js)](https://nextjs.org)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16%20%2B%20pgvector-336791.svg?logo=postgresql)](https://github.com/pgvector/pgvector)

RivalScope is an open-source, self-hostable competitive-intelligence workspace for fintech teams. It turns public competitor activity into cited signals, reports, and actionable context, with a tenant-scoped MCP gateway for approved internal tools.

The repository runs in deterministic mock mode by default: no LLM, search, or crawl API key is needed for the local demo. Real provider integrations are opt-in through environment variables.

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
- **Offline Demo Mode**:
  - Deterministic mock providers and `MockModel` support local development and tests without external API keys.
- **Professional Web Experience**:
  - A public landing page explains the intelligence workflow, compliance posture, and MCP gateway.
  - The responsive workspace loads live companies and signals from `/api/v1` when the backend is reachable, then gracefully falls back to demo data.

---

## Quickstart

### 1. Run Offline Demo in 2 Minutes (No API Keys Needed)

```bash
# Clone repository
git clone https://github.com/rivalscope/rivalscope.git
cd rivalscope

# Copy environment template (PowerShell)
Copy-Item .env.example .env

# Start infrastructure (PostgreSQL with pgvector, Redis)
make up

# Run offline demo (seeds fintech rivals, executes agents, generates cited report)
make demo
```

Visit the product overview at `http://localhost:3000`, the workspace at `http://localhost:3000/dashboard`, or inspect the API at `http://localhost:7777/docs`.

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

## API Status

The backend currently mounts **20 versioned domain routes** under `/api/v1`. In development/mock mode, the API uses the seeded demo user when no bearer token is supplied. Production access must use authenticated JWT context; tenant IDs are never browser-supplied routing parameters.

| Area | Available routes |
| --- | --- |
| Auth | `POST /auth/login`, `GET /auth/me` |
| Companies | `GET/POST /companies`, `GET/DELETE /companies/{company_id}` |
| Signals | `GET /signals`, `GET /signals/{signal_id}` |
| Reports | `GET /reports`, `POST /reports/generate`, `GET /reports/{report_id}` |
| Schedules | `GET/POST /schedules`, `POST /schedules/{schedule_id}/run-now` |
| MCP gateway | `GET/POST /mcp-servers`, `PATCH /mcp-servers/{server_id}/policies` |
| Memory | `GET/POST /memory/preferences`, `GET /memory/timeline` |

The typed browser client lives in `frontend/lib/api.ts`. It supplies the dashboard and competitor screens with live API data when available.

---

## MCP Gateway

RivalScope can act as an MCP server and can connect tenant-approved external MCP servers. The gateway is deliberately restrictive:

- Streamable HTTP is the default transport; `stdio` is disabled by default.
- Credentials are encrypted at rest and hosted connectors use OAuth (`mcp_auth`).
- Per-tenant server registries and tool allowlists prevent accidental cross-tenant tool exposure.
- SSRF controls block local, private, metadata, CGNAT, and IPv6 local ranges; DNS is re-resolved at connect time and redirects are validated before following.
- Write-capable tools require human approval and are excluded from unattended schedules.

See [the MCP Gateway ADR](docs/adr/0004-mcp-gateway-security-and-isolation.md) for the security model.

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
1. Navigate to **MCP Gateway** in the Web UI or call `POST /api/v1/mcp-servers`.
2. Supply transport (`streamable-http`), URL, and authentication headers.
3. Test connectivity and selectively allowlist tools in the policy manager.

---

## Legal & Compliance Notes
See [Legal & Data Sources](docs/legal-data-sources.md) for full compliance guidelines. RivalScope operates strictly on public data, respects `robots.txt`, enforces rate limits, and rejects scrapers of forbidden sites (including LinkedIn).

## Current Status

This is an active implementation, not a claim that every item in the long-term architecture is complete. The core models, mock providers, ingestion/deduplication, memory facade, agent/workflow modules, API routers, MCP policy foundations, and frontend are present. Production provider setup, full API coverage, migrations, delivery verification, and end-to-end hardening remain ongoing work.

## License
Apache License 2.0. See [LICENSE](LICENSE).
