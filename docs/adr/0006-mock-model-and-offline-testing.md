# ADR 0006: MockModel Architecture for Deterministic Offline Testing and Demos

## Status
Accepted

## Context
Running integration tests, local development cycles, CI pipelines, and live offline demonstrations should not require live LLM API keys (OpenAI, Anthropic, Gemini, Groq), incur cloud provider costs, or fail due to remote network latency, rate limits, or outages.

At the same time, earlier references in documentation claiming "air-gapped" deployment or "100% test coverage" were imprecise and overstated. A real-world competitive intelligence platform typically fetches public internet data, while test suites require realistic mocked execution rather than claiming theoretical absolute coverage.

## Decision
We introduce a first-class `MockModel` implementing Agno's `Model` interface (`backend/app/core/mock_model.py`):

1. **Subclassing `agno.models.base.Model`**:
   - Implements required abstract methods: `invoke`, `ainvoke`, `invoke_stream`, `ainvoke_stream`, `_parse_provider_response`, and `_parse_provider_response_delta`.
   - Supports:
     - Free-form text responses.
     - Structured JSON responses matching Pydantic `output_schema` definitions.
     - Optional mock tool call generation to exercise tool-calling loops.
     - Streaming response token iteration.
     - Async and synchronous execution.

2. **Full Offline Demo & Test Execution (`make demo`, `pytest`)**:
   - When `MOCK_PROVIDERS=true` or when no LLM API key is detected in the environment, RivalScope automatically configures agents to use `MockModel`.
   - Paired with deterministic mock ingestion providers (`MockSearchProvider`, `MockCrawlProvider`, `MockFilingsProvider`, `MockSocialProvider`, `MockNotifier`), the entire end-to-end pipeline (collection, 6-stage dedup, memory storage, agent coordination, report synthesis, and delivery) runs locally in seconds with zero network calls and zero API cost.

3. **Documentation Cleanup**:
   - Remove "air-gapped" terminology. The platform is designed for self-hostable environments with offline demo and testing capabilities.
   - Remove claims of "100% test coverage". Establish comprehensive unit, calibration, and integration test suites focused on critical paths.

## Consequences
- **Positive**: Immediate developer onboarding with `make demo` requiring zero API keys, fast deterministic CI test runs, predictable evaluation suites.
- **Negative**: Mocked responses do not test LLM reasoning edge cases, which must be validated separately with live eval suites.
