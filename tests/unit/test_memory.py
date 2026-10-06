"""Unit tests for RivalMemory four-layer memory architecture facade."""

from datetime import UTC, datetime

import pytest
from app.db.session import SessionLocal
from app.memory import RivalMemory


@pytest.fixture
def memory_facade():
    session = SessionLocal()
    try:
        yield RivalMemory(db=session)
    finally:
        session.close()


def test_layer_2_remember_and_recall(memory_facade):
    tenant_id = "t-paypulse-demo"
    mem = memory_facade.remember(
        tenant_id=tenant_id,
        memory_text="PayPulse prioritizes mid-market enterprise payment acquirers.",
        category="positioning",
    )
    assert mem.id is not None

    recalled = memory_facade.recall(tenant_id=tenant_id, category="positioning")
    assert len(recalled) > 0
    assert any("PayPulse" in item["text"] for item in recalled)


def test_layer_3_knowledge_search(memory_facade):
    tenant_id = "t-paypulse-demo"
    results = memory_facade.search_knowledge(
        tenant_id=tenant_id,
        query="agentic",
        limit=5,
    )
    assert isinstance(results, list)


def test_layer_4_timeline_and_contradictions(memory_facade):
    tenant_id = "t-paypulse-demo"
    company_id = "c-comp-stripe"

    evt = memory_facade.add_timeline_event(
        tenant_id=tenant_id,
        company_id=company_id,
        category="pricing",
        title="Stripe increased interchange fee markup for standard accounts",
        event_date=datetime.now(UTC),
    )
    assert evt.id is not None

    timeline = memory_facade.get_timeline(tenant_id=tenant_id, company_id=company_id)
    assert len(timeline) > 0
    assert any("interchange" in e["title"] for e in timeline)

    # Check contradiction detection for opposite pricing change
    contradictions = memory_facade.detect_contradictions(
        tenant_id=tenant_id,
        company_id=company_id,
        proposed_title="Stripe announced pricing decrease across all transaction fees",
        proposed_summary="All fees waived for enterprise merchants.",
    )
    assert len(contradictions) > 0
    assert contradictions[0]["type"] == "pricing_reversal"
