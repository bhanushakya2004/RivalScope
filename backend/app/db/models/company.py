"""Company and Source models."""

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.models.tenant import gen_uuid, utcnow
from app.db.session import Base


class Company(Base):
    __tablename__ = "companies"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    tenant_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("tenants.id", ondelete="CASCADE"), index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    is_self: Mapped[bool] = mapped_column(
        Boolean, default=False
    )  # True = User's own company, False = Competitor
    domain: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    ticker: Mapped[str | None] = mapped_column(
        String(20), nullable=True
    )  # Stock ticker (e.g. SQ, PYPL)
    region: Mapped[str] = mapped_column(
        String(50), default="US"
    )  # US, UK, EU, India (BSE/NSE), etc.
    social_handles: Mapped[dict[str, Any]] = mapped_column(
        JSON, default=dict
    )  # {"x": "@...", "github": "..."}
    feeds: Mapped[list[str]] = mapped_column(JSON, default=list)  # RSS/Atom feed URLs
    tags: Mapped[list[str]] = mapped_column(
        JSON, default=list
    )  # ["payments", "neobank", "checkout"]
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )

    # Relationships
    sources: Mapped[list["Source"]] = relationship(
        "Source", back_populates="company", cascade="all, delete-orphan"
    )


class Source(Base):
    __tablename__ = "sources"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    tenant_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("tenants.id", ondelete="CASCADE"), index=True, nullable=False
    )
    company_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("companies.id", ondelete="CASCADE"), index=True, nullable=False
    )
    url: Mapped[str] = mapped_column(Text, nullable=False)
    source_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # changelog, blog, filing, careers, news, rss
    crawl_policy: Mapped[dict[str, Any]] = mapped_column(
        JSON, default=dict
    )  # {"max_depth": 2, "check_interval_hours": 12}
    last_fetched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="active")  # active, paused, failed

    # Relationship
    company: Mapped["Company"] = relationship("Company", back_populates="sources")
