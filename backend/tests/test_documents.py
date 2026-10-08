"""Unit tests for document parsing (CSV, XLSX, DOCX, MD) and knowledge ingestion."""

import pytest
from app.db.models import InternalDocument, RawDocument, Tenant
from app.db.session import SessionLocal
from app.ingestion.doc_parser import (
    index_document_into_knowledge,
    parse_csv,
    parse_document,
    parse_text_or_markdown,
)


def test_parse_csv():
    csv_bytes = b"merchant_id,plan,volume_usd,take_rate_bps\nM001,Enterprise,15000000,185\nM002,Growth,450000,240\n"
    parsed = parse_csv(csv_bytes, "q3_pricing.csv")

    assert parsed.filename == "q3_pricing.csv"
    assert parsed.file_type == "csv"
    assert parsed.row_count == 2
    assert "merchant_id" in parsed.column_names
    assert "take_rate_bps" in parsed.column_names
    assert len(parsed.chunks) > 0
    assert "M001" in parsed.markdown_preview


def test_parse_markdown():
    md_bytes = b"# Q4 Engineering Roadmap\n\n- Sprint 44: Agentic Commerce Toolkit\n- Sprint 45: Instant Multi-Currency Settlement\n"
    parsed = parse_text_or_markdown(md_bytes, "roadmap.md", ext="md")

    assert parsed.filename == "roadmap.md"
    assert parsed.file_type == "md"
    assert "Sprint 44" in parsed.chunks[0]


def test_index_document_into_knowledge():
    db = SessionLocal()
    try:
        import uuid
        tenant = Tenant(name="Test Doc Tenant", slug=f"test-doc-{uuid.uuid4().hex[:8]}")
        db.add(tenant)
        db.commit()


        csv_bytes = b"metric,target,actual\nMRR,15M,14.2M\nGPV,800M,845M\n"
        parsed = parse_document(csv_bytes, "metrics.csv")

        doc_record = index_document_into_knowledge(
            parsed=parsed,
            tenant_id=tenant.id,
            db=db,
            upload_dir="data/test_uploads",
            file_bytes=csv_bytes,
        )

        assert doc_record.id is not None
        assert doc_record.status == "indexed"
        assert doc_record.row_count == 2

        # Check raw documents in pgvector
        raw_chunks = (
            db.query(RawDocument)
            .filter(
                RawDocument.tenant_id == tenant.id,
                RawDocument.provider == "internal_document",
            )
            .all()
        )
        assert len(raw_chunks) > 0
        assert "MRR" in raw_chunks[0].content

        # Cleanup
        db.query(RawDocument).filter(RawDocument.tenant_id == tenant.id).delete()
        db.delete(doc_record)
        db.delete(tenant)
        db.commit()
    finally:
        db.close()
