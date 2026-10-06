"""Pydantic schemas for Agent reasoning outputs."""

from typing import Any

from pydantic import BaseModel, Field


class VerifiedSignal(BaseModel):
    """Output schema for VerifierAgent."""

    title: str = Field(description="Normalized factual title")
    summary: str = Field(description="Synthesized factual summary grounded exclusively in evidence")
    category: str = Field(
        description="Signal category: product, pricing, financial, regulatory, hiring, social"
    )
    confidence: float = Field(
        default=0.90, description="Confidence score 0.0 - 1.0 based on citation grounding"
    )
    is_grounded: bool = Field(
        default=True, description="True if assertions are supported by provided sources"
    )
    grounded_facts: list[str] = Field(
        default_factory=list, description="List of discrete verified factual statements"
    )
    source_citations: list[str] = Field(
        default_factory=list, description="List of source URLs supporting the signal"
    )


class StrategicImpact(BaseModel):
    """Output schema for AnalystAgent."""

    competitor_name: str
    headline: str
    threat_level: str = Field(default="medium", description="high | medium | low | informational")
    fintech_vector: str = Field(
        description="Primary fintech battleground: payments, issuing, treasury, pos, lending"
    )
    strategic_so_what: str = Field(
        description="In-depth analysis of why this move matters to our company"
    )
    take_rate_impact: str = Field(
        default="neutral", description="compressed | expanding | neutral | unknown"
    )
    recommended_actions: list[str] = Field(
        default_factory=list, description="Concrete strategic counter-moves"
    )


class FormattedReport(BaseModel):
    """Output schema for ReporterAgent."""

    headline: str
    executive_summary: str
    markdown_report: str
    slack_blocks: list[dict[str, Any]] = Field(default_factory=list)
    telegram_text: str
