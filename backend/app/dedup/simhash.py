"""Stage 3: Near-Duplicate Detection using 64-bit SimHash."""

import hashlib
import re

from app.config import get_settings


def _hash_token(token: str) -> int:
    """Generate 64-bit unsigned hash integer from a string token."""
    digest = hashlib.md5(token.encode("utf-8")).digest()
    return int.from_bytes(digest[:8], byteorder="big", signed=False)


def compute_simhash(text: str) -> int:
    """
    Compute a 64-bit SimHash integer from input text using word unigrams.
    """
    tokens = re.findall(r"\w+", text.lower())
    if not tokens:
        return 0

    v = [0] * 64

    for tok in tokens:
        h = _hash_token(tok)
        for i in range(64):
            bit = (h >> i) & 1
            if bit == 1:
                v[i] += 1
            else:
                v[i] -= 1

    fingerprint = 0
    for i in range(64):
        if v[i] > 0:
            fingerprint |= 1 << i

    return fingerprint


def hamming_distance(h1: int, h2: int) -> int:
    """Compute the number of differing bits between two 64-bit integers."""
    x = (h1 ^ h2) & 0xFFFFFFFFFFFFFFFF
    return bin(x).count("1")


class SimHashFilter:
    """Evaluates near-duplicate content within a sliding temporal window."""

    def __init__(self, threshold: int | None = None):
        settings = get_settings()
        self.threshold = threshold if threshold is not None else settings.simhash_hamming_threshold
        # In-memory index: tenant_id -> List of (simhash, doc_id, competitor_id)
        self._index: dict[str, list[tuple[int, str, str]]] = {}

    def is_near_duplicate(
        self,
        tenant_id: str,
        simhash_val: int,
        competitor_id: str,
    ) -> tuple[bool, str | None, int]:
        """
        Check if simhash is within Hamming threshold of an existing document
        for the same competitor. Returns (is_dup, match_doc_id, distance).
        """
        records = self._index.get(tenant_id, [])
        for existing_hash, doc_id, comp_id in records:
            if comp_id == competitor_id:
                dist = hamming_distance(simhash_val, existing_hash)
                if dist <= self.threshold:
                    return True, doc_id, dist

        return False, None, 64

    def record(self, tenant_id: str, simhash_val: int, doc_id: str, competitor_id: str) -> None:
        """Add document SimHash to index."""
        if tenant_id not in self._index:
            self._index[tenant_id] = []
        self._index[tenant_id].append((simhash_val, doc_id, competitor_id))
