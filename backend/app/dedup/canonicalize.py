"""Stage 1: Pre-Fetch URL Canonicalization and Deduplication."""

import hashlib

from sqlalchemy.orm import Session

from app.db.models import DocumentHash
from app.ingestion.url_utils import canonicalize_url


class UrlCanonicalizer:
    """Canonicalizes URLs and verifies if URL was already ingested."""

    def __init__(self, db: Session | None = None):
        self.db = db
        self._in_memory_seen: set[str] = set()

    def canonicalize(self, raw_url: str) -> str:
        """Strip tracking parameters, lowercase domain, remove default ports and fragments."""
        return canonicalize_url(raw_url)

    def is_duplicate(self, tenant_id: str, canonical_url: str) -> bool:
        """Check if canonical URL has already been processed for the tenant."""
        url_hash = hashlib.sha256(canonical_url.encode("utf-8")).hexdigest()
        lookup_key = f"{tenant_id}:{url_hash}"

        if lookup_key in self._in_memory_seen:
            return True

        if self.db is not None:
            existing = (
                self.db.query(DocumentHash)
                .filter(
                    DocumentHash.tenant_id == tenant_id,
                    DocumentHash.hash_type == "canonical_url",
                    DocumentHash.hash_value == url_hash,
                )
                .first()
            )
            if existing:
                self._in_memory_seen.add(lookup_key)
                return True

        return False

    def record(self, tenant_id: str, canonical_url: str) -> None:
        """Persist canonical URL hash in durable PostgreSQL table."""
        url_hash = hashlib.sha256(canonical_url.encode("utf-8")).hexdigest()
        lookup_key = f"{tenant_id}:{url_hash}"
        self._in_memory_seen.add(lookup_key)

        if self.db is not None:
            doc_hash = DocumentHash(
                tenant_id=tenant_id,
                hash_type="canonical_url",
                hash_value=url_hash,
            )
            self.db.add(doc_hash)
            self.db.flush()
