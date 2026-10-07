"""Input guardrails for validating and sanitizing user inputs and external raw documents."""

import re

from app.core.logging import get_logger
from app.guardrails.schemas import (
    GuardrailCheckResult,
    GuardrailSeverity,
    GuardrailStatus,
    GuardrailViolation,
)

logger = get_logger("guardrails.input")

# Prompt injection heuristics & signature patterns
PROMPT_INJECTION_PATTERNS = [
    (
        r"(?i)\bignore\s+(all\s+)?(previous|prior|above)\s+(instructions|directives|rules|prompts)\b",
        "ignore_instructions",
    ),
    (
        r"(?i)\bdisregard\s+(all\s+)?(previous|prior|system)\s+(instructions|directives|prompts)\b",
        "disregard_instructions",
    ),
    (
        r"(?i)\b(system\s+prompt|system\s+instructions)\s*(reveal|show|print|leak|exfiltrate|dump|display)\b",
        "reveal_system_prompt",
    ),
    (
        r"(?i)\b(reveal|show|print|leak|exfiltrate|dump|output)\s+(your\s+)?(system\s+prompt|system\s+instructions|secret\s+key|api\s+key)\b",
        "extract_secrets",
    ),
    (
        r"(?i)\byou\s+are\s+now\s+in\s+(developer|unrestricted|jailbreak|god|dan)\s+mode\b",
        "jailbreak_mode",
    ),
    (r"(?i)\b(dan\s+mode|jailbreak|do\s+anything\s+now)\b", "dan_jailbreak"),
    (
        r"(?i)<\s*/?\s*(system|assistant|instruction|untrusted_source_content)\s*>",
        "tag_breakout_attempt",
    ),
    (
        r"(?i)\b(sudo\s+mode|system\s+override|admin\s+override|developer\s+override)\b",
        "admin_override",
    ),
]

# Sensitive PII and Secret patterns
PII_PATTERNS = [
    # Credit Card Numbers (13-19 digits with optional hyphens/spaces)
    (
        r"\b(?:\d{4}[ -]?){3}\d{4}\b|\b\d{4}[ -]?\d{6}[ -]?\d{5}\b",
        "credit_card",
        "[REDACTED_CREDIT_CARD]",
    ),
    # US Social Security Number
    (r"\b\d{3}-\d{2}-\d{4}\b", "ssn", "[REDACTED_SSN]"),
    # High-entropy API Keys / Tokens (Stripe sk_live/sk_test, Google AIza, OpenAI sk-, mock keys)
    (
        r"\b(?:sk_(?:live|test)_[0-9a-zA-Z]{24,}|AIza[0-9A-Za-z-_]{35}|ghp_[0-9a-zA-Z]{36}|mock_api_key_[0-9a-zA-Z]{16,})\b",
        "api_key",
        "[REDACTED_SECRET_KEY]",
    ),
]

# Dangerous scope patterns (code injection, destructive database commands)
DANGEROUS_SCOPE_PATTERNS = [
    (
        r"(?i)\b(drop\s+table|delete\s+from\s+users|truncate\s+table|rm\s+-rf\s+/)\b",
        "destructive_command",
    ),
    (r"(?i)\b(write\s+(malware|ransomware|keylogger|ddos\s+script))\b", "malicious_code_request"),
]


class PromptInjectionGuardrail:
    """Detects direct adversarial prompt injection and jailbreak payloads."""

    def __init__(self, block_on_injection: bool = True):
        self.block_on_injection = block_on_injection

    def check(self, text: str) -> GuardrailCheckResult:
        violations: list[GuardrailViolation] = []
        for pattern, rule_id in PROMPT_INJECTION_PATTERNS:
            match = re.search(pattern, text)
            if match:
                snippet = match.group(0)[:60]
                violations.append(
                    GuardrailViolation(
                        rule_name=f"prompt_injection_{rule_id}",
                        severity=GuardrailSeverity.CRITICAL,
                        detail=f"Prompt injection pattern detected: '{rule_id}'",
                        matched_pattern=snippet,
                        action_taken="blocked" if self.block_on_injection else "flagged",
                    )
                )

        if violations and self.block_on_injection:
            logger.warning(
                f"Blocked input due to prompt injection: {[v.rule_name for v in violations]}"
            )
            return GuardrailCheckResult(
                status=GuardrailStatus.BLOCKED,
                original_text=text,
                sanitized_text="[REQUEST_BLOCKED_SECURITY_VIOLATION]",
                violations=violations,
                metadata={"reason": "Prompt injection detected"},
            )

        return GuardrailCheckResult(
            status=GuardrailStatus.PASSED if not violations else GuardrailStatus.FLAGGED,
            original_text=text,
            sanitized_text=text,
            violations=violations,
        )


class PIIScrubbingGuardrail:
    """Detects and redacts personally identifiable information (PII) and credentials."""

    def check(self, text: str) -> GuardrailCheckResult:
        violations: list[GuardrailViolation] = []
        sanitized = text

        for pattern, pii_type, replacement in PII_PATTERNS:
            matches = list(re.finditer(pattern, sanitized))
            if matches:
                violations.append(
                    GuardrailViolation(
                        rule_name=f"pii_{pii_type}",
                        severity=GuardrailSeverity.MEDIUM,
                        detail=f"Detected sensitive {pii_type} ({len(matches)} instance(s))",
                        matched_pattern=f"{pii_type}_detected",
                        action_taken="redacted",
                    )
                )
                sanitized = re.sub(pattern, replacement, sanitized)

        status = GuardrailStatus.MODIFIED if violations else GuardrailStatus.PASSED
        return GuardrailCheckResult(
            status=status,
            original_text=text,
            sanitized_text=sanitized,
            violations=violations,
        )


class ScopeGuardrail:
    """Verifies that the request aligns with competitive intelligence operations."""

    def check(self, text: str) -> GuardrailCheckResult:
        violations: list[GuardrailViolation] = []
        for pattern, rule_id in DANGEROUS_SCOPE_PATTERNS:
            match = re.search(pattern, text)
            if match:
                violations.append(
                    GuardrailViolation(
                        rule_name=f"scope_{rule_id}",
                        severity=GuardrailSeverity.CRITICAL,
                        detail=f"Forbidden operation requested: '{rule_id}'",
                        matched_pattern=match.group(0),
                        action_taken="blocked",
                    )
                )

        if violations:
            logger.warning(
                f"Blocked out-of-scope / destructive input: {[v.rule_name for v in violations]}"
            )
            return GuardrailCheckResult(
                status=GuardrailStatus.BLOCKED,
                original_text=text,
                sanitized_text="[REQUEST_BLOCKED_OUT_OF_SCOPE]",
                violations=violations,
                metadata={"reason": "Destructive or malicious operation requested"},
            )

        return GuardrailCheckResult(
            status=GuardrailStatus.PASSED,
            original_text=text,
            sanitized_text=text,
            violations=[],
        )


class UntrustedContentIsolationGuardrail:
    """
    Sanitizes external source text and ensures rigid tag boundary isolation
    in compliance with ADR 0005. Escapes embedded injection closing tags.
    """

    @staticmethod
    def isolate_source_document(
        raw_text: str,
        source_id: str,
        domain: str,
        title: str | None = None,
    ) -> str:
        """
        Escapes any rogue XML tags inside the untrusted content to prevent injection breakouts,
        and encapsulates the content cleanly inside <untrusted_source_content> tags.
        """
        # Neutralize attempts to close the untrusted container
        sanitized = raw_text.replace(
            "</untrusted_source_content>", "&lt;/untrusted_source_content&gt;"
        )
        sanitized = sanitized.replace("<untrusted_source_content", "&lt;untrusted_source_content")
        sanitized = sanitized.replace("</system>", "&lt;/system&gt;")

        header = f'<untrusted_source_content source_id="{source_id}" domain="{domain}"'
        if title:
            clean_title = title.replace('"', "&quot;")
            header += f' title="{clean_title}"'
        header += ">"

        return f"{header}\n{sanitized}\n</untrusted_source_content>"
