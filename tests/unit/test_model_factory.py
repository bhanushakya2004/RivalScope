"""Tests for centralized model factory, Agno Gemini integration, and Tavily provider."""

from agno.models.google import Gemini
from app.agents.analyst_agent import create_analyst_agent
from app.agents.reporter_agent import create_reporter_agent
from app.agents.verifier_agent import create_verifier_agent
from app.config import Settings
from app.core.mock_model import MockModel
from app.core.model_factory import resolve_model
from app.providers.search import TavilySearchProvider
from app.teams.ci_team import create_ci_team


def test_resolve_model_fallback_mock():
    settings = Settings(mock_providers=True, google_api_key=None, gemini_api_key=None)
    model = resolve_model("test-model", settings=settings)
    assert isinstance(model, MockModel)


def test_resolve_model_with_google_api_key(monkeypatch):
    monkeypatch.setenv("GOOGLE_API_KEY", "test-google-ai-studio-key")
    settings = Settings(
        mock_providers=False, google_api_key="test-google-ai-studio-key"
    )
    model = resolve_model("gemini-2.0-flash", settings=settings)
    assert isinstance(model, Gemini)
    assert model.id == "gemini-2.0-flash"
    assert model.api_key == "test-google-ai-studio-key"


def test_resolve_model_with_gemini_api_key(monkeypatch):
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.setenv("GEMINI_API_KEY", "test-gemini-key")
    settings = Settings(mock_providers=False, gemini_api_key="test-gemini-key")
    model = resolve_model("gemini-2.5-flash", settings=settings)
    assert isinstance(model, Gemini)
    assert model.id == "gemini-2.5-flash"
    assert model.api_key == "test-gemini-key"


def test_agents_and_teams_accept_gemini():
    gemini_model = Gemini(id="gemini-2.0-flash", api_key="dummy-key-for-instantiation")
    verifier = create_verifier_agent(model=gemini_model)
    analyst = create_analyst_agent(model=gemini_model)
    reporter = create_reporter_agent(model=gemini_model)
    team = create_ci_team(model=gemini_model)

    assert verifier.model == gemini_model
    assert analyst.model == gemini_model
    assert reporter.model == gemini_model
    assert team.model == gemini_model
    assert len(team.members) == 3


def test_tavily_search_provider_api_key():
    provider = TavilySearchProvider(api_key="tvly-dummy-test-key")
    assert provider.api_key == "tvly-dummy-test-key"
