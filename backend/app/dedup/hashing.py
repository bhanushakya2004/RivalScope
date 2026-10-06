"""Stage 2: Exact Content Hashing using SHA-256 and durable PostgreSQL table."""

import hashlib

from sqlalchemy.orm import Session

from app.db.models import DocumentHash


class ExactContentHasher:
    """Computes and evaluates exact content hashes."""

    def __init__(self, db: Session | None = None):
        self.db = db
        self._in_memory_seen: set[str] = set()

    def compute_hash(self, text: str) -> str:
        """Compute SHA-256 hex digest of normalized string."""
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    def is_duplicate(self, tenant_id: str, content_hash: str) -> bool:
        """Check if exact content hash exists for tenant."""
        lookup_key = f"{tenant_id}:{content_hash}"
        if lookup_key in self._in_memory_seen:
            return True

        if self.db is not None:
            existing = (
                self.db.query(DocumentHash)
                .filter(
                    DocumentHash.tenant_id == tenant_id,
                    DocumentHash.hash_type == "sha256",
                    DocumentHash.hash_value == content_hash,
                )
                .first()
            )
            if existing:
                self._in_memory_seen.add(lookup_key)
                return True

        return False

    def record(self, tenant_id: str, content_hash: str) -> None:
        """Record content hash into durable PostgreSQL storage."""
        lookup_key = f"{tenant_id}:{content_hash}"
        self._in_memory_seen.add(lookup_key)

        if self.db is not None:
            doc_hash = DocumentHash(
                tenant_id=tenant_id,
                hash_type="sha256",
                hash_value=content_hash,
            )
            self.db.add(doc_hash)
            self.db.flush()
