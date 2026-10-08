"""Internal enterprise document model for uploaded knowledge files."""

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.models.tenant import gen_uuid, utcnow
from app.db.session import Base


class InternalDocument(Base):
    """Uploaded internal enterprise document (CSV, Excel, Word, Markdown, Text, JSON)."""

    __tablename__ = "internal_documents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    tenant_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("tenants.id", ondelete="CASCADE"), index=True, nullable=False
    )
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_type: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True
    )  # csv, xlsx, xls, docx, md, txt, json
    file_size_bytes: Mapped[int] = mapped_column(Integer, default=0)
    storage_path: Mapped[str] = mapped_column(String(500), nullable=False)
    row_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    column_names: Mapped[list[str]] = mapped_column(JSON, default=list)
    summary: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(
        String(50), default="indexed"
    )  # indexed, processing, error
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )
