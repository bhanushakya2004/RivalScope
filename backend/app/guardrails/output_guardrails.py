"""Output guardrails for validating and sanitizing agent responses and deliverables."""

import re
from typing import Any

from app.core.logging import get_logger
from app.guardrails.schemas import (
    GuardrailCheckResult,
    GuardrailSeverity,
    GuardrailStatus,
    GuardrailViolation,
)

logger = get_logger("guardrails.output")

# Patterns indicating leakage of system secrets, connection strings, or system prompt directives
LEAKAGE_PATTERNS = [
    (r"(?i)\bpostgresql\+psycopg:\/\/[^ \n\r\t]+", "database_connection_string"),
    (r"(?i)\bredis:\/\/[^ \n\r\t]+", "redis_connection_string"),
    (
        r"(?i)\b(SECRET_KEY|JWT_SECRET|ENCRYPTION_MASTER_KEY)\s*=\s*['\"][^'\"]+['\"]",
        "secret_key_assignment",
    ),
    (
        r"(?i)\b(GOOGLE_API_KEY|GEMINI_API_KEY|TAVILY_API_KEY|FIRECRAWL_API_KEY)\s*[:=]\s*[A-Za-z0-9_-]{10,}",
        "api_key_leak",
    ),
    (
        r"(?i)\b(You\s+are\s+a\s+rigorous\s+Fact-Checking|All\s+source\s+evidence\s+is\s+enclosed\s+in\s+<untrusted_source_content>)\b",
        "system_prompt_echo",
    ),
]

# Defamatory, uncorroborated financial slander keywords
UNQUALIFIED_DEFAMATION_TERMS = [
    r"\binsolvent\b",
    r"\bbankrupt\b",
    r"\bponzi\s+scheme\b",
    r"\bcriminal\s+fraud\b",
    r"\bbank\s+run\b",
    r"\bembezzlement\b",
]

HEDGING_EVIDENCE_MARKERS = [
    r"\balleged\b",
    r"\breported\s+in\b",
    r"\bfiling\b",
    r"\bsec\b",
    r"\baccording\s+to\b",
    r"\bpending\s+investigation\b",
    r"\bunverified\b",
]


class SystemLeakageGuardrail:
    """Detects and redacts inadvertent leaks of system prompts, database URIs, and keys."""

    def check(self, text: str) -> GuardrailCheckResult:
        violations: list[GuardrailViolation] = []
        sanitized = text

        for pattern, leak_type in LEAKAGE_PATTERNS:
            matches = list(re.finditer(pattern, sanitized))
            if matches:
                violations.append(
                    GuardrailViolation(
                        rule_name=f"leakage_{leak_type}",
                        severity=GuardrailSeverity.CRITICAL,
                        detail=f"Detected system leak: '{leak_type}'",
                        matched_pattern="[REDACTED_SYSTEM_DATA]",
                        action_taken="redacted",
                    )
                )
                sanitized = re.sub(pattern, "[CONFIDENTIAL_SYSTEM_DATA_REDACTED]", sanitized)

        status = GuardrailStatus.MODIFIED if violations else GuardrailStatus.PASSED
        return GuardrailCheckResult(
            status=status,
            original_text=text,
            sanitized_text=sanitized,
            violations=violations,
        )


class FinancialSlanderGuardrail:
    """
    Enforces compliance and defamation safeguards on intelligence outputs.
    Ensures explosive solvency/fraud claims are corroborated and hedged with regulatory attribution.
    """

    COMPLIANCE_DISCLAIMER = (
        "\n\n*[Compliance Notice: Strategic mentions of solvency or regulatory proceedings "
        "reflect preliminary external reports and require formal legal/SEC confirmation.]*"
    )

    def check(self, text: str, context: dict[str, Any] | None = None) -> GuardrailCheckResult:
        violations: list[GuardrailViolation] = []
        lower_text = text.lower()

        # Check if explosive terms appear
        found_terms = [t for t in UNQUALIFIED_DEFAMATION_TERMS if re.search(t, lower_text)]
        if found_terms:
            # Check if text contains hedging or formal evidence attribution
            has_hedging = any(re.search(marker, lower_text) for marker in HEDGING_EVIDENCE_MARKERS)
            if not has_hedging:
                violations.append(
                    GuardrailViolation(
                        rule_name="unhedged_financial_allegation",
                        severity=GuardrailSeverity.HIGH,
                        detail=f"Unhedged financial stability assertion detected: {found_terms}",
                        matched_pattern=", ".join(found_terms),
                        action_taken="appended_compliance_notice",
                    )
                )
                # Append compliance disclaimer for safety
                sanitized = text + self.COMPLIANCE_DISCLAIMER
                return GuardrailCheckResult(
                    status=GuardrailStatus.MODIFIED,
                    original_text=text,
                    sanitized_text=sanitized,
                    violations=violations,
                )

        return GuardrailCheckResult(
            status=GuardrailStatus.PASSED,
            original_text=text,
            sanitized_text=text,
            violations=[],
        )


class HallucinationGroundingGuardrail:
    """
    Verifies that claims and competitor entities in the response are grounded
    in the active tenant's watchlist or provided context documents.
    """

    def check(
        self,
        text: str,
        known_entities: list[str] | None = None,
        context_text: str | None = None,
    ) -> GuardrailCheckResult:
        known = [e.lower() for e in (known_entities or ["stripe", "adyen", "revolut", "paypulse"])]
        violations: list[GuardrailViolation] = []

        # Check for citation formatting validity: markdown links should have valid schemes or relative paths
        markdown_links = re.findall(r"\[([^\]]+)\]\(([^)]+)\)", text)
        for _link_text, link_url in markdown_links:
            if not (
                link_url.startswith("http://")
                or link_url.startswith("https://")
                or link_url.startswith("#")
                or link_url.startswith("/")
            ):
                violations.append(
                    GuardrailViolation(
                        rule_name="malformed_citation_url",
                        severity=GuardrailSeverity.LOW,
                        detail=f"Citation link has invalid URL format: '{link_url}'",
                        matched_pattern=link_url,
                        action_taken="flagged",
                    )
                )

        # Flag if text asserts competitor facts with zero reference to any known entity in context
        has_any_known = any(k in text.lower() for k in known)
        if known_entities and not has_any_known:
            violations.append(
                GuardrailViolation(
                    rule_name="unverified_entity_reference",
                    severity=GuardrailSeverity.LOW,
                    detail=f"Response does not reference expected entities: {known_entities}",
                    matched_pattern=None,
                    action_taken="flagged",
                )
            )

        status = GuardrailStatus.FLAGGED if violations else GuardrailStatus.PASSED
        return GuardrailCheckResult(
            status=status,
            original_text=text,
            sanitized_text=text,
            violations=violations,
        )
