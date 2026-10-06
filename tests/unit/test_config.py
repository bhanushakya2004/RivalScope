"""Unit tests for RivalScope configuration."""

from app.config import Settings


def test_settings_defaults():
    settings = Settings()
    assert settings.app_name == "RivalScope"
    assert settings.port == 7777
    assert settings.mock_providers is True
    assert "team@rivalscope.org" in settings.sec_edgar_user_agent
    assert settings.sec_edgar_rate_limit_per_second <= 10.0
    assert settings.mcp_enable_stdio is False
    assert settings.simhash_hamming_threshold == 3
    assert settings.semantic_cosine_threshold == 0.88
    assert settings.novelty_score_threshold == 0.65
