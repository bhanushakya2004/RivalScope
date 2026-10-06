"""Prometheus metrics and telemetry tracking for RivalScope."""

from typing import Any

from prometheus_client import Counter, Gauge, Histogram

from app.core.logging import get_logger

logger = get_logger("telemetry")

# HTTP request counters
HTTP_REQUESTS_TOTAL = Counter(
    "rivalscope_http_requests_total",
    "Total HTTP requests received",
    ["method", "endpoint", "status"],
)

# Agent & Run metrics
AGENT_RUNS_TOTAL = Counter(
    "rivalscope_agent_runs_total",
    "Total agent and workflow executions",
    ["agent_name", "status", "tenant_id"],
)

AGENT_RUN_DURATION_SECONDS = Histogram(
    "rivalscope_agent_run_duration_seconds",
    "Execution duration of agents and teams in seconds",
    ["agent_name"],
    buckets=[0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0, 120.0],
)

AGENT_TOKENS_TOTAL = Counter(
    "rivalscope_agent_tokens_total",
    "Total LLM tokens consumed",
    ["agent_name", "model", "token_type"],  # token_type: prompt | completion
)

AGENT_COST_USD_TOTAL = Counter(
    "rivalscope_agent_cost_usd_total",
    "Cumulative estimated cost in USD",
    ["tenant_id", "model"],
)

# Deduplication engine metrics
DEDUP_PROCESSED_TOTAL = Counter(
    "rivalscope_dedup_processed_total",
    "Total raw documents processed through deduplication",
    ["stage", "result"],  # result: passed | dropped
)

# MCP Gateway metrics
MCP_TOOL_CALLS_TOTAL = Counter(
    "rivalscope_mcp_tool_calls_total",
    "Total invocations of MCP gateway tools",
    ["server_name", "tool_name", "status"],
)

ACTIVE_COMPETITORS_GAUGE = Gauge(
    "rivalscope_active_competitors",
    "Number of actively monitored competitors",
    ["tenant_id"],
)


def track_tokens(
    agent_name: str,
    model: str,
    prompt_tokens: int,
    completion_tokens: int,
    tenant_id: str = "default",
) -> None:
    """Record token consumption and approximate costs."""
    AGENT_TOKENS_TOTAL.labels(agent_name=agent_name, model=model, token_type="prompt").inc(
        prompt_tokens
    )
    AGENT_TOKENS_TOTAL.labels(agent_name=agent_name, model=model, token_type="completion").inc(
        completion_tokens
    )

    # Approximate cost tracking ($0.15/1M prompt, $0.60/1M completion for mini; $2.50 / $10.00 for gpt-4o)
    rate_prompt = (
        2.50 / 1_000_000 if "gpt-4o" in model and "mini" not in model else 0.15 / 1_000_000
    )
    rate_comp = 10.00 / 1_000_000 if "gpt-4o" in model and "mini" not in model else 0.60 / 1_000_000
    est_cost = (prompt_tokens * rate_prompt) + (completion_tokens * rate_comp)
    AGENT_COST_USD_TOTAL.labels(tenant_id=tenant_id, model=model).inc(est_cost)


def init_telemetry(app: Any | None = None) -> None:
    """Initialize OpenTelemetry instrumentation and Prometheus exporters."""
    logger.info("Initialized telemetry metrics engine")
