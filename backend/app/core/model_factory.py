"""Centralized model resolution factory supporting Google Gemini via Agno and deterministic MockModel fallback."""

import os

from agno.models.base import Model

from app.config import Settings, get_settings
from app.core.logging import get_logger
from app.core.mock_model import MockModel

logger = get_logger("core.model_factory")


def resolve_model(
    model_id: str | None = None,
    settings: Settings | None = None,
) -> Model:
    """
    Return appropriate model based on configuration.
    Uses Google AI Studio Gemini whenever GOOGLE_API_KEY or GEMINI_API_KEY is configured.
    Falls back gracefully to MockModel if no keys are provided or mock_providers is enabled.
    """
    settings = settings or get_settings()
    gemini_key = (
        settings.effective_gemini_api_key
        or os.getenv("GOOGLE_API_KEY")
        or os.getenv("GEMINI_API_KEY")
    )

    # 1. Google Gemini via Agno (Google AI Studio standard)
    if gemini_key:
        try:
            from agno.models.google import Gemini

            chosen_id = model_id or settings.analyst_model or "gemini-2.0-flash"
            if ":" in chosen_id:
                chosen_id = chosen_id.split(":", 1)[1]
            if chosen_id.startswith("mock-") or chosen_id.startswith("gpt-"):
                chosen_id = "gemini-2.0-flash"

            logger.info(f"Using Agno Gemini model '{chosen_id}' via Google AI Studio")
            return Gemini(id=chosen_id, api_key=gemini_key)
        except Exception as e:
            logger.warning(f"Failed to initialize Agno Gemini: {e}. Falling back to MockModel.")
            return MockModel(id=model_id or "mock-gemini-fallback")

    # If mock_providers is active and no live keys are configured, use deterministic MockModel
    if settings.mock_providers:
        return MockModel(id=model_id or "mock-default-model")

    # 2. OpenAI
    if settings.llm_provider == "openai" and settings.openai_api_key:
        try:
            from agno.models.openai import OpenAIChat

            chosen_id = model_id or settings.collector_model.replace("openai:", "")
            return OpenAIChat(id=chosen_id, api_key=settings.openai_api_key)
        except Exception as e:
            logger.warning(f"Failed to load OpenAIChat: {e}. Falling back to MockModel.")

    # 3. Anthropic
    if settings.llm_provider == "anthropic" and settings.anthropic_api_key:
        try:
            from agno.models.anthropic import Claude

            return Claude(id="claude-3-5-sonnet", api_key=settings.anthropic_api_key)
        except Exception as e:
            logger.warning(f"Failed to load Claude: {e}. Falling back to MockModel.")

    return MockModel(id=model_id or "mock-fallback-model")
