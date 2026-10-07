"""MockModel implementation for fully deterministic, offline testing and demonstrations."""

import json
from collections.abc import AsyncIterator, Iterator
from datetime import UTC, datetime
from typing import Any, Union

from agno.models.base import Model
from agno.models.message import Message
from agno.models.response import ModelResponse
from pydantic import BaseModel


def _generate_mock_instance_dict(model_cls: type[BaseModel]) -> dict[str, Any]:
    """Dynamically generate valid mock values for any Pydantic model class."""
    data: dict[str, Any] = {}
    for name, field in model_cls.model_fields.items():
        annotation = field.annotation
        origin = getattr(annotation, "__origin__", None)
        args = getattr(annotation, "__args__", ())

        # Unpack Optional[T] / Union[T, None]
        if origin is Union and type(None) in args:
            actual_args = [a for a in args if a is not type(None)]
            if actual_args:
                annotation = actual_args[0]
                origin = getattr(annotation, "__origin__", None)

        if annotation is str:
            if "url" in name.lower():
                data[name] = "https://example.com/mock-intel-update"
            elif "id" in name.lower():
                data[name] = "mock-uuid-1234"
            elif "category" in name.lower():
                data[name] = "product"
            elif "summary" in name.lower() or "content" in name.lower() or "text" in name.lower():
                data[name] = (
                    "Stripe announced expanded support for agentic commerce and machine payments "
                    "via updated payment APIs, directly competing with Adyen's unified commerce."
                )
            else:
                data[name] = f"Mocked {name.replace('_', ' ').capitalize()}"
        elif annotation is float:
            data[name] = 0.95
        elif annotation is int:
            data[name] = 5
        elif annotation is bool:
            data[name] = True
        elif annotation is datetime:
            data[name] = datetime.now(UTC).isoformat()
        elif origin is list:
            if args and isinstance(args[0], type) and issubclass(args[0], BaseModel):
                data[name] = [_generate_mock_instance_dict(args[0])]
            elif args and args[0] is str:
                data[name] = [
                    "https://news.ycombinator.com/item?id=123",
                    "https://stripe.com/blog/agents",
                ]
            elif args and (args[0] is dict or getattr(args[0], "__origin__", None) is dict):
                data[name] = [{"type": "section", "text": "Mock block content"}]
            else:
                data[name] = ["mock_item_1"]
        elif origin is dict:
            data[name] = {"source": "mock_provider", "verified": True}
        elif isinstance(annotation, type) and issubclass(annotation, BaseModel):
            data[name] = _generate_mock_instance_dict(annotation)
        else:
            data[name] = "mock_value"
    return data


class MockModel(Model):
    """
    Deterministic offline model implementing Agno's Model interface.
    Supports freeform text responses, streaming token iteration, and
    Pydantic schema synthesis for structured output tests with zero remote calls.
    """

    def __init__(
        self,
        id: str = "mock-model",
        name: str = "MockModel",
        provider: str = "Mock",
        default_response: str | None = None,
        custom_responses: dict[str, str] | None = None,
        mock_tool_calls: list[dict[str, Any]] | None = None,
        **kwargs: Any,
    ):
        super().__init__(
            id=id,
            name=name,
            provider=provider,
            supports_native_structured_outputs=True,
            supports_json_schema_outputs=True,
            **kwargs,
        )
        self.default_response = default_response or (
            "Executive Competitive Intelligence Summary:\n"
            "- Signal: Stripe launched Agentic Commerce payment toolkits with instant settlement.\n"
            "- Strategic Impact: Direct pressure on Adyen and legacy merchant acquirers.\n"
            "- Evidence: Corroborated across 3 verified sources (Stripe Blog, PR Newswire, Hacker News).\n"
            "- Recommended Action: Evaluate our API latency and merchant onboarding timeline."
        )
        self.custom_responses = custom_responses or {}
        self.mock_tool_calls = mock_tool_calls

    def _resolve_content(self, **kwargs: Any) -> str:
        messages: list[Message] = kwargs.get("messages", [])
        response_format = kwargs.get("response_format")

        # 1. If structured output schema requested
        if (
            response_format is not None
            and isinstance(response_format, type)
            and issubclass(response_format, BaseModel)
        ):
            mock_dict = _generate_mock_instance_dict(response_format)
            return json.dumps(mock_dict)

        # 2. Check for explicit custom responses
        last_msg = ""
        if messages:
            last_msg = str(messages[-1].content or "")
            for query_fragment, custom_resp in self.custom_responses.items():
                if query_fragment.lower() in last_msg.lower():
                    return custom_resp

        # 3. Dynamic conversational detection from messages
        low_msg = last_msg.lower()

        # Check for user question line if embedded in structured prompt
        user_q = ""
        for line in last_msg.splitlines():
            if line.strip().lower().startswith("user question:"):
                user_q = line.split(":", 1)[1].strip().lower()
                break

        check_text = user_q or low_msg

        # Greetings & pleasantries
        if check_text in [
            "hi",
            "hello",
            "hey",
            "greetings",
            "good morning",
            "good afternoon",
            "good evening",
        ] or any(check_text.startswith(g) for g in ["hi ", "hello ", "hey "]):
            return (
                "Hello! I am your RivalScope competitive intelligence assistant. "
                "I am actively monitoring your fintech rivals, including Stripe, Adyen, and Revolut. "
                "You can ask me about recent product moves, pricing shifts, executive hiring, or regulatory filings."
            )

        # Well-being and casual conversation
        if any(
            w in check_text
            for w in [
                "how are you",
                "how're you",
                "how r u",
                "how do you do",
                "how is it going",
                "how's it going",
                "how are things",
                "how are you doing",
                "what's up",
                "whats up",
            ]
        ):
            return (
                "I am functioning smoothly! I am continuously monitoring your fintech rivals—including Stripe, "
                "Adyen, and Revolut—and tracking market moves across product, pricing, talent, and filings. "
                "What would you like to explore today?"
            )

        # Capabilities, features, and help
        if any(
            c in check_text
            for c in [
                "capabilit",
                "what can you do",
                "what do you do",
                "how can you help",
                "help",
                "features",
                "what are your tools",
                "what do you know",
                "instructions",
            ]
        ):
            return (
                "As your RivalScope competitive intelligence assistant, I can:\n\n"
                "1. **Continuous Competitor Tracking**: Monitor news, changelogs, SEC filings, and careers pages for rivals like Stripe, Adyen, and Revolut.\n"
                "2. **6-Stage Deduplication**: Filter duplicate reports and near-duplicate articles using SimHash and pgvector semantic clustering.\n"
                "3. **Evidence Citations**: Ground every strategic move against verified PostgreSQL evidence with confidence scoring.\n"
                "4. **Contradiction Detection**: Cross-reference Layer 4 historical timelines to flag strategic reversals (e.g. pricing fee changes, executive shifts).\n"
                "5. **On-Demand Intelligence Briefs**: Synthesize cited markdown reports and trigger autonomous monitor pipeline cycles.\n\n"
                "Try asking: 'Tell me about Adyen', 'What is Stripe's latest move?', or 'Compare Stripe and Adyen pricing'."
            )

        # Identity & platform overview
        if any(
            i in check_text
            for i in [
                "who are you",
                "what is rivalscope",
                "what is this",
                "about you",
                "about yourself",
                "introduce yourself",
            ]
        ):
            return (
                "I am RivalScope, an open-source, self-hostable multi-agent competitive intelligence platform for fintech teams. "
                "I orchestrate specialized collector, verifier, and analyst agents to deliver verifiable, evidence-backed strategic insights."
            )

        # Signals and recent updates
        if any(
            s in check_text
            for s in [
                "signal",
                "latest move",
                "recent move",
                "what's new",
                "whats new",
                "recent updates",
                "recent intelligence",
            ]
        ):
            return (
                "Latest Verified Competitive Signals:\n"
                "1. [Pricing] Stripe launched usage-based pricing for embedded finance (Score: 94 impact).\n"
                "2. [Product] Adyen expanded issuer processing across North America and India (Score: 88 impact).\n"
                "3. [Financial] Block reported 21% gross profit growth driven by Cash App (Score: 81 impact).\n"
                "4. [Talent] Plaid opened 34 platform engineering roles in enterprise identity (Score: 72 impact).\n"
                "All signals are verified with citations stored in PostgreSQL."
            )

        # Stripe queries
        if "stripe" in check_text and not ("adyen" in check_text and "revolut" in check_text):
            return (
                "Stripe Competitive Intelligence Summary:\n"
                "- Signal: Stripe launched Agentic Commerce payment toolkits with instant settlement.\n"
                "- Strategic Impact: Direct pressure on Adyen and legacy merchant acquirers.\n"
                "- Evidence: Corroborated across 3 verified sources (Stripe Blog, PR Newswire, Hacker News).\n"
                "- Recommended Action: Evaluate our API latency and merchant onboarding timeline."
            )

        # Adyen queries
        if "adyen" in check_text and not ("stripe" in check_text and "revolut" in check_text):
            return (
                "Adyen Competitive Intelligence Summary:\n"
                "- Unified Commerce: Adyen expanded its in-person POS issuer processing across North America and India with local rails.\n"
                "- Strategic Focus: Driving 32% volume growth in enterprise omnichannel retail and digital platform acquiring.\n"
                "- Evidence: Corroborated via Adyen press disclosures and regulatory filings in PostgreSQL storage.\n"
                "- Recommended Action: Assess PayPulse's localized acquiring settlement speed against Adyen's unified ledger."
            )

        # Revolut queries
        if "revolut" in check_text and not ("stripe" in check_text and "adyen" in check_text):
            return (
                "Revolut Competitive Intelligence Summary:\n"
                "- Banking & Licensing: Revolut secured progress on its UK banking license mobilization and expanded global business accounts.\n"
                "- Product Velocity: Rolled out automated treasury management and merchant acquiring tools for SME customers.\n"
                "- Evidence: Sourced from public changelogs, Reuters disclosures, and financial statements.\n"
                "- Recommended Action: Benchmark PayPulse's multi-currency exchange spreads against Revolut Business."
            )

        # Competitors overview
        if (
            "competitor" in check_text
            or "watchlist" in check_text
            or "rivals" in check_text
            or "who" in check_text
        ):
            return (
                "Monitored Competitors Overview:\n"
                "1. Stripe (stripe.com) — Leading developer infrastructure; recently rolled out agentic commerce toolkits and usage-based embedded finance billing.\n"
                "2. Adyen (adyen.com) — Enterprise unified commerce leader; expanding global acquiring rails and localized card issuing.\n"
                "3. Revolut (revolut.com) — High-velocity global neobank; scaling enterprise multi-currency payouts and treasury features.\n"
                "All intelligence is deduplicated across 6 stages and backed by citations in PostgreSQL."
            )

        # Pricing queries
        if "pricing" in check_text or "fee" in check_text:
            return (
                "Pricing Analysis Brief:\n"
                "- Stripe Move: Introduced modular usage-based pricing for embedded finance, lowering barrier to entry for marketplace platforms.\n"
                "- Adyen Response: Bundling acquiring fees with risk management tools to preserve net take-rate among Tier-1 merchants.\n"
                "- Impact: Competitive pressure on transaction take-rates for mid-market SaaS platforms."
            )

        # Dynamic fallback: Extract live database signals from the prompt if present
        extracted_signals = []
        for line in last_msg.splitlines():
            if line.strip().startswith("- [") and ":" in line:
                extracted_signals.append(line.strip())

        if extracted_signals:
            signals_summary = "\n".join(extracted_signals[:3])
            return (
                f"Here is the latest verified intelligence from our PostgreSQL database:\n\n"
                f"{signals_summary}\n\n"
                f"All signals have been verified across multiple sources and stored with pgvector citations. "
                f"Ask me about any specific competitor or move to dig deeper!"
            )

        return (
            "I am your RivalScope competitive intelligence assistant. I am actively tracking Stripe, Adyen, and Revolut.\n"
            "You can ask me about recent product moves, pricing changes, executive hiring, or compare specific competitors."
        )

    def invoke(self, *args: Any, **kwargs: Any) -> ModelResponse:
        content = self._resolve_content(**kwargs)
        return ModelResponse(
            role="assistant",
            content=content,
            tool_calls=self.mock_tool_calls,
        )

    async def ainvoke(self, *args: Any, **kwargs: Any) -> ModelResponse:
        return self.invoke(*args, **kwargs)

    def invoke_stream(self, *args: Any, **kwargs: Any) -> Iterator[ModelResponse]:
        content = self._resolve_content(**kwargs)
        # Yield words in chunks to simulate token streaming
        words = content.split(" ")
        for i, word in enumerate(words):
            chunk = word if i == len(words) - 1 else word + " "
            yield ModelResponse(role="assistant", content=chunk)

    async def ainvoke_stream(self, *args: Any, **kwargs: Any) -> AsyncIterator[ModelResponse]:
        for chunk in self.invoke_stream(*args, **kwargs):
            yield chunk

    def _parse_provider_response(self, response: Any, **kwargs: Any) -> ModelResponse:
        if isinstance(response, ModelResponse):
            return response
        return ModelResponse(role="assistant", content=str(response))

    def _parse_provider_response_delta(self, response: Any) -> ModelResponse:
        if isinstance(response, ModelResponse):
            return response
        return ModelResponse(role="assistant", content=str(response))
