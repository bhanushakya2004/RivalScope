"""Database seed script populating demo fintech data and rivals."""

from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.db.models import (
    Company,
    EventCluster,
    McpPolicy,
    McpServer,
    NotificationChannel,
    RawDocument,
    Signal,
    Source,
    Tenant,
    TimelineEvent,
    User,
)
from app.db.session import Base, SessionLocal, engine


def seed_database(db: Session) -> None:
    """Populate database with rich fintech competitors and historical intelligence."""
    # Ensure vector extension and tables exist
    from sqlalchemy import text

    with engine.connect() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
        conn.commit()
    Base.metadata.create_all(bind=engine)

    # Check if already seeded
    existing = db.query(Tenant).filter(Tenant.slug == "paypulse").first()
    if existing:
        doc2 = db.query(RawDocument).filter(RawDocument.id == "doc-adyen-unified").first()
        if not doc2:
            now = datetime.now(UTC)
            adyen = db.query(Company).filter(Company.id == "c-comp-adyen").first()
            revolut = db.query(Company).filter(Company.id == "c-comp-revolut").first()
            if adyen:
                db.add(
                    RawDocument(
                        id="doc-adyen-unified",
                        tenant_id=existing.id,
                        company_id=adyen.id,
                        source_id="s-adyen-press",
                        url="https://www.adyen.com/press-and-media/q3-2026-financial-results",
                        canonical_url="https://www.adyen.com/press-and-media/q3-2026-financial-results",
                        content="Adyen unified commerce POS expansion drives 32% North America volume growth across enterprise acquiring.",
                        content_hash="hash-adyen-unified-sha256",
                        simhash=204928502948502,
                        provider="firecrawl",
                        fetched_at=now - timedelta(days=3),
                    )
                )
            if revolut:
                db.add(
                    RawDocument(
                        id="doc-revolut-charter",
                        tenant_id=existing.id,
                        company_id=revolut.id,
                        source_id="s-revolut-careers",
                        url="https://www.revolut.com/news/us-banking-license-application",
                        canonical_url="https://www.revolut.com/news/us-banking-license-application",
                        content="Revolut accelerates US banking license application and regulatory compliance recruitment.",
                        content_hash="hash-revolut-charter-sha256",
                        simhash=304928502948502,
                        provider="firecrawl",
                        fetched_at=now - timedelta(days=1),
                    )
                )
            db.commit()
            print("[seed] Populated missing benchmark documents for Adyen and Revolut.")
        print("[seed] Database already seeded. Skipping.")
        return

    print("[seed] Creating demo tenant and admin user...")
    tenant = Tenant(
        id="t-paypulse-demo",
        name="PayPulse Global",
        slug="paypulse",
    )
    db.add(tenant)
    db.flush()

    admin = User(
        id="u-admin-1",
        tenant_id=tenant.id,
        email="admin@paypulse.io",
        hashed_password=hash_password("Demo1234!"),
        role="admin",
        is_active=True,
    )
    db.add(admin)

    # Self Company
    print("[seed] Registering self company and rivals...")
    self_comp = Company(
        id="c-self-paypulse",
        tenant_id=tenant.id,
        name="PayPulse",
        is_self=True,
        domain="paypulse.io",
        region="US",
        tags=["payments", "treasury", "developer-api"],
    )
    db.add(self_comp)

    # Competitor 1: Stripe
    stripe = Company(
        id="c-comp-stripe",
        tenant_id=tenant.id,
        name="Stripe",
        is_self=False,
        domain="stripe.com",
        region="US",
        tags=["payments", "billing", "issuing", "enterprise"],
        feeds=["https://stripe.com/blog/feed.rss"],
    )
    db.add(stripe)

    # Competitor 2: Adyen
    adyen = Company(
        id="c-comp-adyen",
        tenant_id=tenant.id,
        name="Adyen",
        is_self=False,
        domain="adyen.com",
        ticker="ADYEN",
        region="EU",
        tags=["unified-commerce", "pos", "global-acquiring"],
    )
    db.add(adyen)

    # Competitor 3: Revolut
    revolut = Company(
        id="c-comp-revolut",
        tenant_id=tenant.id,
        name="Revolut",
        is_self=False,
        domain="revolut.com",
        region="UK",
        tags=["neobank", "business-accounts", "fx", "crypto"],
    )
    db.add(revolut)

    db.flush()

    # Sources
    sources = [
        Source(
            id="s-stripe-changelog",
            tenant_id=tenant.id,
            company_id=stripe.id,
            url="https://docs.stripe.com/changelog",
            source_type="changelog",
        ),
        Source(
            id="s-adyen-press",
            tenant_id=tenant.id,
            company_id=adyen.id,
            url="https://www.adyen.com/press-and-media",
            source_type="news",
        ),
        Source(
            id="s-revolut-careers",
            tenant_id=tenant.id,
            company_id=revolut.id,
            url="https://www.revolut.com/careers",
            source_type="careers",
        ),
    ]
    db.add_all(sources)
    db.flush()

    # Raw Documents & Signals
    now = datetime.now(UTC)
    raw_doc_1 = RawDocument(
        id="doc-stripe-agentic",
        tenant_id=tenant.id,
        company_id=stripe.id,
        source_id="s-stripe-changelog",
        url="https://docs.stripe.com/agentic-commerce-suite",
        canonical_url="https://docs.stripe.com/agentic-commerce-suite",
        content="Stripe announces Agentic Commerce Suite with automated purchasing agents and protocol-level settlement for AI transactions.",
        content_hash="hash-stripe-agentic-sha256",
        simhash=104928502948502,
        provider="firecrawl",
        fetched_at=now - timedelta(days=2),
    )
    db.add(raw_doc_1)
    db.flush()

    cluster_1 = EventCluster(
        id="cluster-stripe-agentic",
        tenant_id=tenant.id,
        company_id=stripe.id,
        title="Stripe Unveils Agentic Commerce Protocol",
        summary="Stripe officially announced toolkits and payments SDKs allowing autonomous AI agents to initiate checkouts and settle micro-transactions.",
        first_seen_at=now - timedelta(days=2),
        last_seen_at=now - timedelta(days=1),
        corroboration_count=3,
    )
    db.add(cluster_1)
    db.flush()

    signal_1 = Signal(
        id="sig-stripe-1",
        tenant_id=tenant.id,
        company_id=stripe.id,
        cluster_id=cluster_1.id,
        category="product",
        title="Agentic Commerce Protocol SDK Launch",
        summary="Direct threat to PayPulse autonomous checkout roadmaps. Stripe gives AI agents direct spending limits and one-click tokenized authorization.",
        event_date=now - timedelta(days=2),
        confidence=0.96,
        importance_score=9,
        evidence_ids=[raw_doc_1.id],
    )
    db.add(signal_1)

    raw_doc_2 = RawDocument(
        id="doc-adyen-unified",
        tenant_id=tenant.id,
        company_id=adyen.id,
        source_id="s-adyen-press",
        url="https://www.adyen.com/press-and-media/q3-2026-financial-results",
        canonical_url="https://www.adyen.com/press-and-media/q3-2026-financial-results",
        content="Adyen unified commerce POS expansion drives 32% North America volume growth across enterprise acquiring.",
        content_hash="hash-adyen-unified-sha256",
        simhash=204928502948502,
        provider="firecrawl",
        fetched_at=now - timedelta(days=3),
    )
    db.add(raw_doc_2)

    raw_doc_3 = RawDocument(
        id="doc-revolut-charter",
        tenant_id=tenant.id,
        company_id=revolut.id,
        source_id="s-revolut-careers",
        url="https://www.revolut.com/news/us-banking-license-application",
        canonical_url="https://www.revolut.com/news/us-banking-license-application",
        content="Revolut accelerates US banking license application and regulatory compliance recruitment.",
        content_hash="hash-revolut-charter-sha256",
        simhash=304928502948502,
        provider="firecrawl",
        fetched_at=now - timedelta(days=1),
    )
    db.add(raw_doc_3)
    db.flush()

    signal_2 = Signal(
        id="sig-adyen-1",
        tenant_id=tenant.id,
        company_id=adyen.id,
        category="financial",
        title="Adyen Q3 Volume Expands 32% in North America",
        summary="Adyen accelerates US merchant acquisition, taking wallet share among mid-market enterprise retailers through zero-cost interchange optimization.",
        event_date=now - timedelta(days=3),
        confidence=0.92,
        importance_score=7,
        evidence_ids=[raw_doc_2.id],
    )
    db.add(signal_2)

    signal_3 = Signal(
        id="sig-revolut-1",
        tenant_id=tenant.id,
        company_id=revolut.id,
        category="hiring",
        title="Revolut Aggressively Hires US Banking Compliance Leads",
        summary="35 new regulatory and compliance job postings published across NYC and SF, signalling renewed push for full US National Bank charter.",
        event_date=now - timedelta(days=1),
        confidence=0.88,
        importance_score=8,
        evidence_ids=[raw_doc_3.id],
    )
    db.add(signal_3)

    # Timeline Events
    timeline_events = [
        TimelineEvent(
            id="te-1",
            tenant_id=tenant.id,
            company_id=stripe.id,
            signal_id=signal_1.id,
            event_date=now - timedelta(days=2),
            category="product_launch",
            title="Launched Agentic Commerce Protocol SDK",
            details={"sdk_version": "v1.0.0", "target": "AI developers"},
        ),
        TimelineEvent(
            id="te-2",
            tenant_id=tenant.id,
            company_id=adyen.id,
            signal_id=signal_2.id,
            event_date=now - timedelta(days=3),
            category="financial",
            title="Reported Q3 Earnings with 32% US Volume Growth",
            details={"volume_growth": "32%", "geography": "North America"},
        ),
        TimelineEvent(
            id="te-3",
            tenant_id=tenant.id,
            company_id=revolut.id,
            signal_id=signal_3.id,
            event_date=now - timedelta(days=1),
            category="executive",
            title="Hired Head of US Regulatory Affairs",
            details={"role": "Chief Regulatory Counsel", "origin": "OCC"},
        ),
    ]
    db.add_all(timeline_events)

    # Demo Notification Channel
    mock_channel = NotificationChannel(
        id="chan-mock-slack",
        tenant_id=tenant.id,
        name="Fintech Intel Slack",
        channel_type="slack",
        encrypted_config="mock_slack_webhook_url",
        is_active=True,
    )
    db.add(mock_channel)

    # Demo MCP Server
    mcp_srv = McpServer(
        id="mcp-demo-crm",
        tenant_id=tenant.id,
        name="Internal CRM & Accounts MCP",
        transport="streamable-http",
        url="http://mock-crm.internal/mcp",
        auth_type="bearer",
        allowed_tools=["lookup_customer_pipeline", "get_churn_risk_accounts"],
        status="healthy",
    )
    db.add(mcp_srv)
    db.flush()

    policy = McpPolicy(
        id="pol-1",
        tenant_id=tenant.id,
        server_id=mcp_srv.id,
        tool_name="lookup_customer_pipeline",
        is_enabled=True,
        require_approval=False,
    )
    db.add(policy)

    db.commit()
    print("[seed] Finished seeding successfully!")


if __name__ == "__main__":
    db_session = SessionLocal()
    try:
        seed_database(db_session)
    finally:
        db_session.close()
