"""Text content normalization, PII sanitization, and prompt-injection containment."""

import html
import re
import unicodedata
from urllib.parse import urlparse

# Basic regex for redacting email addresses and phone numbers
EMAIL_REGEX = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")
PHONE_REGEX = re.compile(r"\b(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b")
HTML_TAG_REGEX = re.compile(r"<[^>]+>")


def normalize_text(text: str) -> str:
    """Normalize text using Unicode NFKC, unescape HTML entities, and collapse whitespace."""
    if not text:
        return ""

    # Unescape HTML entities
    unescaped = html.unescape(text)

    # Strip HTML tags if present
    stripped = HTML_TAG_REGEX.sub(" ", unescaped)

    # Normalize unicode to NFKC
    normalized = unicodedata.normalize("NFKC", stripped)

    # Collapse multiple spaces and linebreaks
    collapsed = re.sub(r"[ \t]+", " ", normalized)
    collapsed = re.sub(r"\n\s*\n+", "\n\n", collapsed)
    return collapsed.strip()


def sanitize_pii(text: str) -> str:
    """Mask email addresses and phone numbers to respect privacy and PII minimization."""
    if not text:
        return ""
    masked = EMAIL_REGEX.sub("[EMAIL REDACTED]", text)
    masked = PHONE_REGEX.sub("[PHONE REDACTED]", masked)
    return masked


def wrap_untrusted_content(content: str, url: str) -> str:
    """
    Enclose untrusted external text in explicit XML containment tags
    to defend against indirect prompt injection.
    """
    domain = urlparse(url).netloc or "external-source"
    normalized = normalize_text(content)
    sanitized = sanitize_pii(normalized)

    return (
        f'<untrusted_source_content domain="{domain}" url="{url}">\n'
        f"{sanitized}\n"
        f"</untrusted_source_content>"
    )
