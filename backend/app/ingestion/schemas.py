"""Pydantic schemas for ingestion and normalization pipeline."""

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field


class IngestionItem(BaseModel):
    """Single ingested item from an external source."""

    url: str
    canonical_url: str
    title: str
    content: str
    contained_content: str
    content_hash: str
    provider: str
    company_id: str | None = None
    company_name: str | None = None
    published_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class IngestionBatchResult(BaseModel):
    """Result of an ingestion run across providers."""

    tenant_id: str
    total_discovered: int
    items: list[IngestionItem]
    errors: list[str] = Field(default_factory=list)
    duration_seconds: float = 0.0
