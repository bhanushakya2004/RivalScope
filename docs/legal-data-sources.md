# Legal & Data Sources Policy

RivalScope is engineered for ethical, compliant, and legally sound competitive intelligence gathering. This document outlines our data acquisition principles, accepted sources, prohibited practices, and compliance controls.

---

## 1. Core Principles

1. **Strict Terms of Service (ToS) Compliance**:
   - RivalScope **does not** scrape LinkedIn, password-protected portals, or platforms whose Terms of Service explicitly prohibit automated retrieval.
   - All external connectors require explicit user consent, key provisioning, and ToS acceptance in the administrative settings.

2. **Respect for Robots Exclusion Standard (`robots.txt`)**:
   - All automated web fetching strictly respects `robots.txt` rules per target domain.
   - Any path disallowed by `robots.txt` is bypassed.

3. **Per-Domain Rate Limiting & Responsible Crawling**:
   - Outbound requests adhere to exponential backoff and polite concurrency caps (default max 1 request per 2 seconds per target domain).
   - All general HTTP traffic identifies itself with a transparent, configurable User-Agent header:
     `User-Agent: RivalScope-Bot/1.0 (+https://github.com/rivalscope/rivalscope; bot@rivalscope.org)`

4. **SEC EDGAR Compliance Requirements**:
   - **Declared User-Agent**: The SEC strictly mandates that all automated queries declare a specific User-Agent containing the requesting entity's name and email contact (e.g., `User-Agent: RivalScope CI contact@example.com`). Failing to format the header properly results in HTTP 403 blocks.
   - **Strict Rate Limit (Max 10 req/s)**: The SEC limits automated requests to a hard maximum of **10 requests per second**. RivalScope enforces a dedicated token bucket rate limiter (`SecEdgarRateLimiter`) capping outbound SEC requests at 8 requests per second to ensure safety margins. Exceeding this threshold causes immediate IP bans by the SEC.

5. **Provenance & Citation Integrity**:
   - Every collected document stores `url`, `canonical_url`, `fetched_at` timestamp, and `provider`.
   - LLM agents are constrained by system prompts and output schemas to only report facts grounded in retrieved evidence. Hallucinations and unsupported assertions are rejected by the Verifier Agent.

---

## 2. Supported Data Sources & Providers

| Domain | Provider | Mechanism | Compliance Profile |
| :--- | :--- | :--- | :--- |
| **Financial & Filings** | SEC EDGAR API | Official SEC REST API / Submissions (`data.sec.gov`) | Declared User-Agent mandatory; hard token-bucket capped at <= 10 req/s. |
| **Financial & Filings** | Regional Filings (e.g. BSE/NSE, MCA, Companies House) | Pluggable regional adapter interfaces | Official open regulatory endpoints with structured rate limiting. |
| **News & Press** | Tavily Search API | Licensed search engine API (`topic=news,finance`) | Compliant programmatic API with licensed indexing. |
| **News & Fallback** | Agno WebSearchTools | DDGS meta-search (Google, Bing, Brave, Yahoo) | Meta-search fallback respecting source access guidelines. |
| **Product & Features** | Firecrawl CrawlProvider | Public changelog, blog, and release notes scraping | Public pages only; respects robots.txt and sitemap guidelines. |
| **Talent & Hiring** | Public Careers Pages via Firecrawl | Public careers / greenhouse / lever job board pages | No scraping of personal employee profiles or LinkedIn. Only public openings. |
| **Social & Community** | RSSProvider | Public RSS/Atom feeds (Substack, Medium, company blogs) | Standard syndicated protocol. |
| **Social & Community** | Optional Social Adapters (X API, YouTube API, Reddit API) | Official REST APIs requiring user-supplied API keys | Disabled by default. Enabled only when tenant provides developer keys and accepts platform ToS. |

---

## 3. Prohibited Practices

RivalScope strictly prohibits:
- Scraping personal professional profiles (e.g., LinkedIn, Xing).
- Bypassing paywalls, captchas, or authentication barriers.
- Masquerading as residential human browsers to deceive anti-bot security systems.
- Re-hosting or distributing copyrighted full-text articles (RivalScope retains only extracts and embeddings for synthesis and citation).

---

## 4. Privacy & PII Handling

- Personal Identifiable Information (PII) minimization: Collector agents strip email addresses, phone numbers, and home addresses before vector indexing.
- Executive personnel mentions are restricted to publicly announced executive officers and press release spokespersons.
- Tenants can trigger data retention purges or domain-level blocklists via `/api/v1/company` and `/api/v1/settings`.
