"""Pytest configuration and common test fixtures."""

import os
import sys

# Disable external Agno telemetry during test execution and enforce deterministic test mode
os.environ["AGNO_TELEMETRY"] = "false"
os.environ["AGNO_MONITORING"] = "false"
os.environ["MOCK_PROVIDERS"] = "true"

# Ensure backend directory is in python path
sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend"))
)

import pytest
from app.config import Settings, get_settings

get_settings.cache_clear()


@pytest.fixture
def test_settings() -> Settings:
    """Return test settings with mock mode forced."""
    settings = get_settings()
    settings.mock_providers = True
    settings.env = "test"
    return settings
