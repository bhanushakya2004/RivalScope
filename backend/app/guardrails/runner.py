"""Unified Agent Guardrail Harness for multi-layer input and output enforcement."""

from typing import Any

from app.core.logging import get_logger
from app.guardrails.input_guardrails import (
    PIIScrubbingGuardrail,
    PromptInjectionGuardrail,
    ScopeGuardrail,
    UntrustedContentIsolationGuardrail,
)
from app.guardrails.output_guardrails import (
    FinancialSlanderGuardrail,
    HallucinationGroundingGuardrail,
    SystemLeakageGuardrail,
)
from app.guardrails.schemas import (
    GuardrailCheckResult,
    GuardrailStatus,
    GuardrailViolation,
)

logger = get_logger("guardrails.runner")


class AgentGuardrailHarness:
    """
    Central orchestration harness enforcing safety, prompt-injection defense,
    PII redaction, hallucination grounding, and leakage prevention on agents.
    """

    def __init__(
        self,
        block_on_injection: bool = True,
        scrub_pii: bool = True,
        check_leakage: bool = True,
        check_slander: bool = True,
    ):
        self.prompt_injection = PromptInjectionGuardrail(block_on_injection=block_on_injection)
        self.pii_scrubber = PIIScrubbingGuardrail()
        self.scope_checker = ScopeGuardrail()
        self.isolation_helper = UntrustedContentIsolationGuardrail()

        self.leakage_checker = SystemLeakageGuardrail()
        self.slander_checker = FinancialSlanderGuardrail()
        self.grounding_checker = HallucinationGroundingGuardrail()

        self.scrub_pii = scrub_pii
        self.check_leakage = check_leakage
        self.check_slander = check_slander

    def guard_input(self, text: str, context: dict[str, Any] | None = None) -> GuardrailCheckResult:
        """
        Execute full input pipeline: Scope -> Prompt Injection -> PII Scrubbing.
        Returns aggregate GuardrailCheckResult.
        """
        violations: list[GuardrailViolation] = []
        current_text = text

        # 1. Scope Check
        scope_res = self.scope_checker.check(current_text)
        if scope_res.is_blocked:
            return scope_res

        # 2. Prompt Injection Defense
        inj_res = self.prompt_injection.check(current_text)
        if inj_res.is_blocked:
            return inj_res
        if inj_res.violations:
            violations.extend(inj_res.violations)

        # 3. PII Scrubbing
        if self.scrub_pii:
            pii_res = self.pii_scrubber.check(current_text)
            current_text = pii_res.sanitized_text
            if pii_res.violations:
                violations.extend(pii_res.violations)

        status = (
            GuardrailStatus.MODIFIED
            if current_text != text
            else (GuardrailStatus.FLAGGED if violations else GuardrailStatus.PASSED)
        )

        return GuardrailCheckResult(
            status=status,
            original_text=text,
            sanitized_text=current_text,
            violations=violations,
            metadata={"stage": "input"},
        )

    def guard_output(
        self,
        text: str,
        context: dict[str, Any] | None = None,
        known_entities: list[str] | None = None,
    ) -> GuardrailCheckResult:
        """
        Execute full output pipeline: System Leakage -> Financial Slander -> Hallucination Grounding.
        """
        violations: list[GuardrailViolation] = []
        current_text = text

        # 1. Leakage Prevention
        if self.check_leakage:
            leak_res = self.leakage_checker.check(current_text)
            current_text = leak_res.sanitized_text
            if leak_res.violations:
                violations.extend(leak_res.violations)

        # 2. Financial Slander & Compliance Check
        if self.check_slander:
            slander_res = self.slander_checker.check(current_text, context=context)
            current_text = slander_res.sanitized_text
            if slander_res.violations:
                violations.extend(slander_res.violations)

        # 3. Hallucination Grounding & Link Format Check
        ground_res = self.grounding_checker.check(
            current_text,
            known_entities=known_entities,
            context_text=str(context) if context else None,
        )
        if ground_res.violations:
            violations.extend(ground_res.violations)

        status = (
            GuardrailStatus.MODIFIED
            if current_text != text
            else (GuardrailStatus.FLAGGED if violations else GuardrailStatus.PASSED)
        )

        return GuardrailCheckResult(
            status=status,
            original_text=text,
            sanitized_text=current_text,
            violations=violations,
            metadata={"stage": "output"},
        )

    def isolate_untrusted_document(
        self,
        raw_text: str,
        source_id: str,
        domain: str,
        title: str | None = None,
    ) -> str:
        """Convenience wrapper for untrusted source quarantine."""
        return self.isolation_helper.isolate_source_document(
            raw_text=raw_text,
            source_id=source_id,
            domain=domain,
            title=title,
        )


# Global default instance
default_guardrail_harness = AgentGuardrailHarness()
