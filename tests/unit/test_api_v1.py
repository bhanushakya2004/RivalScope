"""Integration tests for REST API v1 endpoints."""

import pytest
from app.main import app
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    return TestClient(app)


def test_auth_me_endpoint(client):
    resp = client.get("/api/v1/auth/me")
    assert resp.status_code == 200
    data = resp.json()
    assert "email" in data
    assert "tenant_id" in data


def test_companies_endpoints(client):
    # List companies (seeded with Stripe, Adyen, Revolut)
    resp = client.get("/api/v1/companies")
    assert resp.status_code == 200
    companies = resp.json()
    assert len(companies) >= 3
    names = [c["name"] for c in companies]
    assert "Stripe" in names
    assert "Adyen" in names

    # Create new competitor
    create_resp = client.post(
        "/api/v1/companies",
        json={
            "name": "Plaid",
            "domain": "plaid.com",
            "region": "US",
            "tags": ["open-banking", "verification"],
        },
    )
    assert create_resp.status_code == 201
    assert create_resp.json()["name"] == "Plaid"


def test_signals_endpoints(client):
    resp = client.get("/api/v1/signals")
    assert resp.status_code == 200
    signals = resp.json()
    assert len(signals) > 0
    first_sig = signals[0]

    detail_resp = client.get(f"/api/v1/signals/{first_sig['id']}")
    assert detail_resp.status_code == 200
    assert detail_resp.json()["id"] == first_sig["id"]


def test_reports_endpoints(client):
    # List reports
    resp = client.get("/api/v1/reports")
    assert resp.status_code == 200

    # Generate on-demand report
    gen_resp = client.post(
        "/api/v1/reports/generate",
        json={
            "title": "On-Demand Test Brief",
            "report_type": "daily_brief",
        },
    )
    assert gen_resp.status_code == 201
    data = gen_resp.json()
    assert data["title"] == "On-Demand Test Brief"
    assert data["markdown"] != ""


def test_schedules_endpoints(client):
    resp = client.get("/api/v1/schedules")
    assert resp.status_code == 200

    create_resp = client.post(
        "/api/v1/schedules",
        json={
            "name": "Hourly Competitor Scan",
            "interval_seconds": 3600,
            "enabled": True,
        },
    )
    assert create_resp.status_code == 201
    assert create_resp.json()["name"] == "Hourly Competitor Scan"


def test_mcp_servers_endpoints(client):
    resp = client.get("/api/v1/mcp-servers")
    assert resp.status_code == 200
    servers = resp.json()
    assert isinstance(servers, list)


def test_memory_endpoints(client):
    resp = client.get("/api/v1/memory/preferences")
    assert resp.status_code == 200

    add_resp = client.post(
        "/api/v1/memory/preferences",
        json={
            "category": "positioning",
            "memory_text": "PayPulse is targeting mid-market SaaS platforms.",
        },
    )
    assert add_resp.status_code == 201


def test_runs_endpoints(client):
    resp = client.get("/api/v1/runs")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)

    # Test on-demand run trigger
    trigger_resp = client.post("/api/v1/runs/trigger", json={})
    assert trigger_resp.status_code == 201
    run_data = trigger_resp.json()
    assert run_data["status"] == "completed"
    assert run_data["company_name"] != ""


def test_chat_endpoint(client):
    resp = client.post(
        "/api/v1/chat",
        json={
            "question": "What is Stripe's current pricing strategy?",
            "competitor_name": "Stripe",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "answer" in data
    assert len(data["answer"]) > 0


def test_chat_stream_post_endpoint(client):
    resp = client.post(
        "/api/v1/chat/stream",
        json={
            "question": "What is Stripe's current pricing strategy?",
            "competitor_name": "Stripe",
        },
    )
    assert resp.status_code == 200
    assert "text/event-stream" in resp.headers.get("content-type", "")
    text = resp.text
    assert "event: start" in text or "start" in text
    assert "event: delta" in text or "delta" in text
    assert "event: done" in text or "done" in text


def test_chat_stream_get_endpoint(client):
    resp = client.get(
        "/api/v1/chat/stream?question=What+is+Adyen+doing&competitor_name=Adyen"
    )
    assert resp.status_code == 200
    assert "text/event-stream" in resp.headers.get("content-type", "")
    text = resp.text
    assert "event: start" in text or "start" in text
    assert "event: delta" in text or "delta" in text
    assert "event: done" in text or "done" in text


def test_reports_harmonized_fields(client):
    resp = client.get("/api/v1/reports")
    assert resp.status_code == 200
    reports = resp.json()
    if len(reports) > 0:
        first = reports[0]
        assert "content" in first
        assert "status" in first
        assert "report_type" in first
