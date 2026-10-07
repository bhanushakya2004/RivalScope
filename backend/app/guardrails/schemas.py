"""Guardrail data structures and schemas for RivalScope agent runtime."""

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class GuardrailStatus(StrEnum):
    """Execution status resulting from a guardrail check."""

    PASSED = "passed"
    MODIFIED = "modified"  # Content was sanitized/redacted but allowed
    BLOCKED = "blocked"  # High-severity violation; execution halted
    FLAGGED = "flagged"  # Low/medium severity alert logged, execution continued


class GuardrailSeverity(StrEnum):
    """Severity level of a guardrail violation."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class GuardrailViolation(BaseModel):
    """Discrete security or quality violation identified by a guardrail."""

    rule_name: str = Field(
        description="Name of the triggered rule (e.g., prompt_injection, pii_leakage)"
    )
    severity: GuardrailSeverity = Field(description="Severity classification")
    detail: str = Field(description="Descriptive explanation of what was detected")
    matched_pattern: str | None = Field(
        default=None, description="Obfuscated or redacted snippet that triggered the rule"
    )
    action_taken: str = Field(description="Action taken (e.g., redacted, blocked, logged)")


class GuardrailCheckResult(BaseModel):
    """Aggregate result from executing one or more guardrails."""

    status: GuardrailStatus = Field(default=GuardrailStatus.PASSED)
    original_text: str = Field(description="Original input or output string")
    sanitized_text: str = Field(description="Sanitized, redacted, or transformed string")
    violations: list[GuardrailViolation] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @property
    def is_blocked(self) -> bool:
        """True if the content must not proceed."""
        return self.status == GuardrailStatus.BLOCKED

    @property
    def has_violations(self) -> bool:
        """True if any violation was recorded."""
        return len(self.violations) > 0
