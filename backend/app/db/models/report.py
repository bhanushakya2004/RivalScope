"""Report model for synthesized intelligence summaries."""

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.models.tenant import gen_uuid, utcnow
from app.db.session import Base


class Report(Base):
    __tablename__ = "reports"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    tenant_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("tenants.id", ondelete="CASCADE"), index=True, nullable=False
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    period: Mapped[str] = mapped_column(String(50), default="daily")  # daily, weekly, on_demand
    scope: Mapped[dict[str, Any]] = mapped_column(
        JSON, default=dict
    )  # {"competitor_ids": [...], "categories": [...]}
    markdown: Mapped[str] = mapped_column(Text, nullable=False)
    structured_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    citations: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON, default=list
    )  # [{"title": "...", "url": "...", "provider": "..."}]
    cost: Mapped[float] = mapped_column(Float, default=0.0)
    model: Mapped[str] = mapped_column(String(100), default="openai:gpt-4o")
    tokens_used: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, index=True
    )
