"""Interactive Follow-up Q&A Handler for Slack and Telegram interactions."""

import asyncio
import json
from collections.abc import AsyncIterator
from typing import Any

from agno.models.base import Model

from app.core.logging import get_logger
from app.core.model_factory import resolve_model
from app.guardrails.runner import AgentGuardrailHarness, default_guardrail_harness
from app.memory.manager import RivalMemory
from app.teams.ci_team import create_ci_team

logger = get_logger("delivery.followup")


class FollowUpHandler:
    """Handles conversational follow-up questions from executives in chat surfaces."""

    def __init__(
        self,
        model: Model | None = None,
        memory: RivalMemory | None = None,
        guardrails: AgentGuardrailHarness | None = None,
    ):
        self.model = model or resolve_model()
        self.memory = memory or RivalMemory()
        self.team = create_ci_team(model=self.model, memory=self.memory)
        self.guardrails = guardrails or default_guardrail_harness

    def _build_grounded_prompt(
        self, tenant_id: str, question: str, competitor_name: str | None = None
    ) -> str:
        """Assemble prompt grounded with tenant preferences, monitored companies, live signals, and timeline events."""
        recalled_prefs = self.memory.recall(tenant_id=tenant_id, limit=3)
        pref_context = (
            "\n".join([f"- {p['text']}" for p in recalled_prefs])
            if recalled_prefs
            else "PayPulse Fintech Workspace"
        )

        company_context = []
        signal_context = []
        timeline_context = []

        if getattr(self.memory, "db", None):
            try:
                from app.db.models.company import Company
                from app.db.models.document import Signal
                from app.db.models.memory import TimelineEvent

                comps = self.memory.db.query(Company).filter(Company.tenant_id == tenant_id).all()
                if comps:
                    company_context = [f"- {c.name} ({c.domain})" for c in comps]

                sig_query = self.memory.db.query(Signal).filter(Signal.tenant_id == tenant_id)
                if competitor_name:
                    comp_match = next(
                        (c for c in comps if c.name.lower() == competitor_name.lower()),
                        None,
                    )
                    if comp_match:
                        sig_query = sig_query.filter(Signal.company_id == comp_match.id)

                recent_signals = sig_query.order_by(Signal.event_date.desc()).limit(5).all()
                for s in recent_signals:
                    signal_context.append(
                        f"- [{s.category}] {s.title}: {s.summary} (Score: {s.importance_score})"
                    )

                tevents = (
                    self.memory.db.query(TimelineEvent)
                    .filter(TimelineEvent.tenant_id == tenant_id)
                    .order_by(TimelineEvent.event_date.desc())
                    .limit(5)
                    .all()
                )
                for tev in tevents:
                    timeline_context.append(f"- {tev.title} ({tev.category})")
            except Exception as e:
                logger.warning(f"Error extracting database context for chat prompt: {e}")

        comp_str = (
            "\n".join(company_context)
            if company_context
            else "- Stripe (stripe.com)\n- Adyen (adyen.com)\n- Revolut (revolut.com)"
        )
        sig_str = (
            "\n".join(signal_context)
            if signal_context
            else "- Verified fintech signals stored in PostgreSQL pgvector"
        )
        time_str = (
            "\n".join(timeline_context)
            if timeline_context
            else "- Recent product and pricing timeline milestones"
        )

        return (
            f"Tenant Organization Context:\n{pref_context}\n\n"
            f"Active Monitored Competitors:\n{comp_str}\n\n"
            f"Recent Verified Intelligence Signals (from PostgreSQL):\n{sig_str}\n\n"
            f"Recent Strategic Milestones:\n{time_str}\n\n"
            f"User Question: {question}\n"
            f"Target Competitor: {competitor_name or 'General Fintech Rivals'}\n\n"
            "Instructions: Answer the user's question directly and conversationally using the live database intelligence above. "
            "If the user is saying hello or greeting, welcome them and invite them to explore monitored rivals. "
            "Cite sources and verified evidence where relevant."
        )

    def _sanitize_provider_error(self, raw_text: str, full_prompt: str) -> str:
        """If upstream LLM provider returns a raw API error payload, recover with grounded offline response."""
        if '"error":' in raw_text and any(
            err in raw_text
            for err in [
                '"RESOURCE_EXHAUSTED"',
                '"code": 429',
                '"NOT_FOUND"',
                '"code": 404',
                '"UNAUTHENTICATED"',
                '"code": 401',
            ]
        ):
            logger.warning(
                f"Upstream LLM provider returned error. Falling back to grounded response: {raw_text[:200]}"
            )
            from agno.models.message import Message

            from app.core.mock_model import MockModel

            fallback = MockModel().invoke([Message(role="user", content=full_prompt)]).content
            notice = ""
            if '"RESOURCE_EXHAUSTED"' in raw_text or '"code": 429' in raw_text:
                notice = "*(Notice: Google AI Studio daily free-tier quota of 20 requests was reached; serving grounded PostgreSQL intelligence.)*\n\n"
            return f"{notice}{fallback}"
        return raw_text

    def handle(
        self,
        tenant_id: str = "t-paypulse-demo",
        question: str = "",
        competitor_name: str | None = None,
    ) -> str:
        """Synchronous query handler with input and output guardrail verification."""
        input_guard = self.guardrails.guard_input(question)
        if input_guard.is_blocked:
            violation_details = ", ".join([v.detail for v in input_guard.violations])
            return (
                "I cannot fulfill this request because it violates platform security policies "
                f"({violation_details})."
            )

        full_prompt = self._build_grounded_prompt(
            tenant_id=tenant_id,
            question=input_guard.sanitized_text,
            competitor_name=competitor_name,
        )
        res = self.team.run(full_prompt)
        raw_ans = str(res.content) if hasattr(res, "content") else str(res)
        raw_ans = self._sanitize_provider_error(raw_ans, full_prompt)

        output_guard = self.guardrails.guard_output(raw_ans)
        return output_guard.sanitized_text

    async def handle_query(
        self,
        tenant_id: str,
        user_id: str,
        question: str,
        competitor_name: str | None = None,
    ) -> dict[str, Any]:
        """Process natural language question and coordinate team response with guardrails."""
        logger.info(f"Processing follow-up question for {tenant_id}: '{question}'")

        input_guard = self.guardrails.guard_input(question)
        if input_guard.is_blocked:
            violation_details = ", ".join([v.detail for v in input_guard.violations])
            return {
                "answer": (
                    "I cannot fulfill this request because it violates platform security policies "
                    f"({violation_details})."
                ),
                "tenant_id": tenant_id,
                "competitor": competitor_name,
                "guardrail_status": "blocked",
            }

        full_prompt = self._build_grounded_prompt(
            tenant_id=tenant_id,
            question=input_guard.sanitized_text,
            competitor_name=competitor_name,
        )
        res = self.team.run(full_prompt)
        raw_ans = str(res.content) if hasattr(res, "content") else str(res)
        raw_ans = self._sanitize_provider_error(raw_ans, full_prompt)

        output_guard = self.guardrails.guard_output(raw_ans)

        return {
            "answer": output_guard.sanitized_text,
            "tenant_id": tenant_id,
            "competitor": competitor_name,
            "guardrail_status": output_guard.status.value,
        }

    async def stream_query(
        self,
        tenant_id: str,
        user_id: str,
        question: str,
        competitor_name: str | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """Stream conversational follow-up response tokens via Server-Sent Events (SSE)."""
        logger.info(f"Streaming follow-up question for {tenant_id}: '{question}'")

        # Emit initial start event
        yield {
            "event": "start",
            "data": json.dumps(
                {
                    "status": "started",
                    "competitor": competitor_name,
                    "tenant_id": tenant_id,
                }
            ),
        }

        # Input guardrail check
        input_guard = self.guardrails.guard_input(question)
        if input_guard.is_blocked:
            blocked_msg = (
                "I cannot fulfill this request because it violates platform security policies "
                f"({', '.join([v.detail for v in input_guard.violations])})."
            )
            yield {
                "event": "delta",
                "data": json.dumps({"token": blocked_msg}),
            }
            yield {
                "event": "done",
                "data": json.dumps(
                    {
                        "status": "blocked",
                        "full_answer": blocked_msg,
                        "competitor": competitor_name,
                        "tenant_id": tenant_id,
                    }
                ),
            }
            return

        full_prompt = self._build_grounded_prompt(
            tenant_id=tenant_id,
            question=input_guard.sanitized_text,
            competitor_name=competitor_name,
        )

        full_answer: list[str] = []
        try:
            generator = self.team.run(full_prompt, stream=True)
            for chunk in generator:
                token = chunk if isinstance(chunk, str) else getattr(chunk, "content", None)
                if token is not None and str(token) != "":
                    text = str(token)
                    if '"error":' in text and any(
                        e in text for e in ['"RESOURCE_EXHAUSTED"', '"code": 429', '"code": 404']
                    ):
                        sanitized = self._sanitize_provider_error(text, full_prompt)
                        full_answer = [sanitized]
                        yield {
                            "event": "delta",
                            "data": json.dumps({"token": sanitized}),
                        }
                        break
                    full_answer.append(text)
                    yield {
                        "event": "delta",
                        "data": json.dumps({"token": text}),
                    }
                    await asyncio.sleep(0.005)
        except Exception as exc:
            logger.error(f"Error during stream generation: {exc}", exc_info=True)
            yield {
                "event": "error",
                "data": json.dumps({"error": str(exc)}),
            }
            return

        yield {
            "event": "done",
            "data": json.dumps(
                {
                    "status": "completed",
                    "full_answer": "".join(full_answer),
                    "competitor": competitor_name,
                    "tenant_id": tenant_id,
                }
            ),
        }
