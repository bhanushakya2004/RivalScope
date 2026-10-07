"""RivalScope application configuration using pydantic-settings."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # --- Server & Core ---
    env: str = "development"
    debug: bool = True
    port: int = 7777
    host: str = "0.0.0.0"
    app_name: str = "RivalScope"
    app_version: str = "0.1.0"
    agentos_url: str = "http://localhost:7777"

    # --- Security & Auth ---
    secret_key: str = "insecure-dev-secret-key-replace-in-production-min-32-chars"
    jwt_secret: str = "insecure-dev-jwt-secret-replace-in-production-min-32-chars"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 1440
    encryption_master_key: str = "dev-encryption-master-key-32b-exactly!!"

    # --- Database & Cache ---
    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/rivalscope"
    async_database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/rivalscope"
    redis_url: str = "redis://localhost:6379/0"

    # --- Offline / Mock Mode ---
    mock_providers: bool = True

    # --- LLM Models ---
    llm_provider: str = "gemini"
    openai_api_key: str | None = None
    anthropic_api_key: str | None = None
    gemini_api_key: str | None = None
    google_api_key: str | None = None
    collector_model: str = "gemini:gemini-3.8-flash"
    analyst_model: str = "gemini:gemini-3.8-flash"
    embedding_model: str = "text-embedding-3-small"

    @property
    def effective_gemini_api_key(self) -> str | None:
        return self.google_api_key or self.gemini_api_key

    # --- External Search & Crawl ---
    tavily_api_key: str | None = None
    firecrawl_api_key: str | None = None
    sec_edgar_user_agent: str = "RivalScope Research team@rivalscope.org"
    sec_edgar_rate_limit_per_second: float = 8.0

    # --- Deduplication Thresholds ---
    simhash_hamming_threshold: int = 3
    semantic_cosine_threshold: float = 0.88
    novelty_score_threshold: float = 0.65

    # --- MCP Layer ---
    mcp_server_enabled: bool = True
    mcp_connect_secret: str = "dev-mcp-connect-secret"
    mcp_server_card_url: str = "http://localhost:7777/mcp"
    mcp_allow_private_ips: bool = False
    mcp_enable_stdio: bool = False
    mcp_default_timeout_seconds: int = 15
    mcp_max_tool_output_chars: int = 50000

    # --- Scheduling & Delivery ---
    scheduler_enabled: bool = True
    scheduler_poll_interval_seconds: int = 15
    default_timezone: str = "UTC"

    # Notifications
    slack_bot_token: str | None = None
    slack_signing_secret: str | None = None
    slack_default_channel: str = "#competitive-intel"
    telegram_bot_token: str | None = None
    telegram_default_chat_id: str | None = None
    default_webhook_url: str | None = None

    # --- Telemetry ---
    telemetry_enabled: bool = True
    otel_exporter_otlp_endpoint: str | None = None
    prometheus_metrics_enabled: bool = True


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings singleton."""
    return Settings()


settings = get_settings()
