"""Unit tests for MockModel and offline execution."""

from agno.agent import Agent
from app.core.mock_model import MockModel
from pydantic import BaseModel


class StrategicSignal(BaseModel):
    title: str
    confidence: float
    importance: int
    tags: list[str]


def test_mock_model_basic_invoke():
    model = MockModel(id="test-mock")
    agent = Agent(model=model, description="Test analyst")
    res = agent.run("Summarize Stripe's latest move")
    assert res is not None
    assert "Stripe" in res.content


def test_mock_model_structured_output():
    model = MockModel(id="test-mock-structured")
    agent = Agent(model=model, output_schema=StrategicSignal)
    res = agent.run("Extract signal for Stripe")
    assert isinstance(res.content, StrategicSignal)
    assert res.content.confidence == 0.95
    assert res.content.importance == 5


def test_mock_model_custom_responses():
    model = MockModel(
        id="test-custom",
        custom_responses={"revolut": "Revolut applied for UK banking license update."},
    )
    agent = Agent(model=model)
    res = agent.run("What happened with Revolut?")
    assert "Revolut applied for UK banking license" in res.content
