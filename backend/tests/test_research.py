import uuid
import pytest
from app.agents.internal_research_agent import create_internal_research_agent
from app.db.models import InternalDocument, RawDocument, Tenant
from app.db.session import SessionLocal
from app.ingestion.doc_parser import index_document_into_knowledge, parse_csv


def test_internal_research_agent_creation():
    db = SessionLocal()
    try:
        tenant = Tenant(name="Test Research Tenant", slug=f"test-res-{uuid.uuid4().hex[:8]}")
        db.add(tenant)
        db.commit()


        # Upload a test document
        csv_bytes = b"competitor,threat_vector,our_margin_bps\nStripe,Instant settlement,185\nAdyen,Unified terminals,210\n"
        parsed = parse_csv(csv_bytes, "margin_analysis.csv")
        doc_record = index_document_into_knowledge(
            parsed=parsed,
            tenant_id=tenant.id,
            db=db,
            upload_dir="data/test_uploads",
            file_bytes=csv_bytes,
        )

        agent = create_internal_research_agent(tenant_id=tenant.id, db=db)
        assert agent is not None
        assert agent.name == "InternalResearchAgent"
        assert len(agent.tools) >= 4  # internal docs query, catalog, web search, competitor signals

        # Test tool call directly
        tool_query_fn = next((t for t in agent.tools if getattr(t, "__name__", "") == "query_internal_documents"), None)
        assert tool_query_fn is not None
        result = tool_query_fn("margin")
        assert "margin_analysis.csv" in result or "Instant settlement" in result

        # Cleanup
        db.query(RawDocument).filter(RawDocument.tenant_id == tenant.id).delete()
        db.delete(doc_record)
        db.delete(tenant)
        db.commit()
    finally:
        db.close()
