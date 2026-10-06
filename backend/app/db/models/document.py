"""Raw documents, Signals, Event Clusters, and Deduplication Hashes."""

from datetime import datetime
from typing import Any, Optional

from sqlalchemy import (
    JSON,
    BigInteger,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.models.tenant import gen_uuid, utcnow
from app.db.models.types import VectorType
from app.db.session import Base


class DocumentHash(Base):
    """PostgreSQL durable hash set for Stage 1 & Stage 2 deduplication."""

    __tablename__ = "document_hashes"
    __table_args__ = (
        UniqueConstraint("tenant_id", "hash_type", "hash_value", name="uq_tenant_hash_type_val"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    tenant_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("tenants.id", ondelete="CASCADE"), index=True, nullable=False
    )
    hash_type: Mapped[str] = mapped_column(
        String(32), nullable=False, index=True
    )  # sha256, canonical_url, simhash
    hash_value: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class RawDocument(Base):
    __tablename__ = "raw_documents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    tenant_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("tenants.id", ondelete="CASCADE"), index=True, nullable=False
    )
    company_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("companies.id", ondelete="SET NULL"), index=True, nullable=True
    )
    source_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("sources.id", ondelete="SET NULL"), index=True, nullable=True
    )
    url: Mapped[str] = mapped_column(Text, nullable=False)
    canonical_url: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)  # SHA-256
    simhash: Mapped[int | None] = mapped_column(
        BigInteger, nullable=True, index=True
    )  # 64-bit SimHash
    provider: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # tavily, websearch, firecrawl, edgar, rss
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, index=True
    )
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    embedding: Mapped[list[float] | None] = mapped_column(VectorType(1536), nullable=True)


class EventCluster(Base):
    __tablename__ = "event_clusters"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    tenant_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("tenants.id", ondelete="CASCADE"), index=True, nullable=False
    )
    company_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("companies.id", ondelete="SET NULL"), index=True, nullable=True
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    corroboration_count: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[str] = mapped_column(String(50), default="active")  # active, archived, noise

    # Relationships
    signals: Mapped[list["Signal"]] = relationship("Signal", back_populates="cluster")


class Signal(Base):
    __tablename__ = "signals"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    tenant_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("tenants.id", ondelete="CASCADE"), index=True, nullable=False
    )
    company_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("companies.id", ondelete="CASCADE"), index=True, nullable=False
    )
    cluster_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("event_clusters.id", ondelete="SET NULL"), index=True, nullable=True
    )
    category: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True
    )  # news, product, financial, hiring, social, pricing, regulatory
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    event_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, index=True
    )
    confidence: Mapped[float] = mapped_column(Float, default=1.0)  # 0.0 - 1.0 confidence score
    importance_score: Mapped[int] = mapped_column(
        Integer, default=5, index=True
    )  # 1 - 10 priority scale
    evidence_ids: Mapped[list[str]] = mapped_column(JSON, default=list)  # List of raw_document IDs
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    # Relationships
    cluster: Mapped[Optional["EventCluster"]] = relationship(
        "EventCluster", back_populates="signals"
    )
