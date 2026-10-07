"""MonitorPipelineWorkflow: Autonomous Competitive Intelligence Ingestion and Synthesis Pipeline."""

import asyncio
from typing import Any

from agno.models.base import Model
from agno.workflow import Workflow
from agno.workflow.step import Step
from agno.workflow.types import StepInput, StepOutput
from pydantic import BaseModel, Field

from app.agents.analyst_agent import create_analyst_agent
from app.agents.reporter_agent import create_reporter_agent
from app.agents.verifier_agent import create_verifier_agent
from app.core.logging import get_logger
from app.core.model_factory import resolve_model
from app.dedup.pipeline import DeduplicationPipeline
from app.guardrails.runner import default_guardrail_harness
from app.ingestion.collector_runner import CollectorRunner
from app.memory.manager import RivalMemory
from app.providers.notify import MockNotifier

logger = get_logger("workflows.monitor_pipeline")


class PipelineRunInput(BaseModel):
    """Input payload for triggering a monitor cycle."""

    tenant_id: str = "t-paypulse-demo"
    company_id: str = "c-comp-stripe"
    company_name: str = "Stripe"
    domain: str = "stripe.com"
    ticker: str | None = None
    force_notify: bool = False


class PipelineExecutionSummary(BaseModel):
    """Execution summary returned by the workflow."""

    tenant_id: str
    company_name: str
    discovered_count: int
    dedup_results: list[dict[str, Any]] = Field(default_factory=list)
    clusters_formed: int = 0
    verified_signals: int = 0
    synthesized_report: str | None = None
    delivery_status: str = "completed"


class MonitorPipelineWorkflow:
    """Orchestrates ingestion, 6-stage dedup, verification, analysis, and reporting."""

    def __init__(self, model: Model | None = None, memory: RivalMemory | None = None):
        self.model = model or resolve_model()
        self.memory = memory or RivalMemory()
        self.collector_runner = CollectorRunner()
        self.dedup_pipeline = DeduplicationPipeline()
        self.verifier = create_verifier_agent(self.model)
        self.analyst = create_analyst_agent(self.model)
        self.reporter = create_reporter_agent(self.model)
        self.notifier = MockNotifier()

    async def execute(self, run_input: PipelineRunInput) -> PipelineExecutionSummary:
        """Run the end-to-end pipeline asynchronously."""
        tenant_id = run_input.tenant_id
        comp_id = run_input.company_id
        comp_name = run_input.company_name
        domain = run_input.domain

        logger.info(f"[Workflow] Starting monitor cycle for {comp_name} ({tenant_id})")

        # Step 1: Parallel Collection
        batch = await self.collector_runner.run_for_competitor(
            tenant_id=tenant_id,
            company_id=comp_id,
            company_name=comp_name,
            domain=domain,
            ticker=run_input.ticker,
        )

        # Step 2: 6-Stage Deduplication
        timeline_events = self.memory.get_timeline(tenant_id, company_id=comp_id, limit=20)
        historical_titles = [e["title"] for e in timeline_events]

        dedup_records = []
        actionable_clusters = []

        for item in batch.items:
            res = self.dedup_pipeline.process(
                tenant_id=tenant_id,
                item=item,
                historical_titles=historical_titles,
            )
            dedup_records.append(
                {
                    "url": res.item_url,
                    "status": res.status,
                    "dropped_at": res.dropped_at_stage,
                    "cluster_id": res.matched_cluster_id,
                }
            )
            if res.status in ["unique_cluster", "corroborated"] and res.cluster:
                actionable_clusters.append(res.cluster)

        # Step 3 & 4: Verification & Analysis
        verified_count = 0
        final_markdown_report = ""

        if actionable_clusters:
            top_cluster = actionable_clusters[0]

            # Evidence Verification with ADR 0005 untrusted source quarantine
            isolated_evidence = default_guardrail_harness.isolate_untrusted_document(
                raw_text=f"Summary: {top_cluster.summary}\nCitations: {[c.url for c in top_cluster.citations]}",
                source_id=getattr(top_cluster, "id", getattr(top_cluster, "cluster_id", "cluster-default")),
                domain=domain,
                title=top_cluster.title,
            )
            verify_prompt = (
                f"Verify the following event cluster: {top_cluster.title}\n{isolated_evidence}"
            )
            verifier_out = self.verifier.run(verify_prompt)
            verified_count += 1

            # Strategic Analysis
            analyst_prompt = (
                f"Analyze competitive move by {comp_name}: {top_cluster.title}\n"
                f"Verified details: {verifier_out.content}\n"
                f"Corroboration: {top_cluster.corroboration_count} sources."
            )
            analyst_out = self.analyst.run(analyst_prompt)

            # Executive Reporting
            reporter_prompt = (
                f"Format intelligence brief for {comp_name}.\n"
                f"Signal: {top_cluster.title}\n"
                f"Impact: {analyst_out.content}"
            )
            reporter_out = self.reporter.run(reporter_prompt)
            raw_report = str(reporter_out.content)

            # Output Guardrail Verification (leakage, financial slander, grounding)
            guarded_report = default_guardrail_harness.guard_output(
                text=raw_report,
                known_entities=[comp_name, "PayPulse"],
            )
            final_markdown_report = guarded_report.sanitized_text

            # Step 5: Multi-Channel Delivery
            await self.notifier.send(
                target="#competitive-intel",
                title=f"Competitive Signal: {top_cluster.title}",
                message=final_markdown_report[:400],
            )

            # Step 6: Memory Recording in Layer 4 Timeline
            self.memory.add_timeline_event(
                tenant_id=tenant_id,
                company_id=comp_id,
                category=top_cluster.category,
                title=top_cluster.title,
                details={"corroboration_count": top_cluster.corroboration_count},
            )

        logger.info(
            f"[Workflow] Finished monitor cycle for {comp_name}. "
            f"Discovered: {batch.total_discovered}, Actionable: {len(actionable_clusters)}"
        )

        return PipelineExecutionSummary(
            tenant_id=tenant_id,
            company_name=comp_name,
            discovered_count=batch.total_discovered,
            dedup_results=dedup_records,
            clusters_formed=len(actionable_clusters),
            verified_signals=verified_count,
            synthesized_report=final_markdown_report
            or "No new unique signals discovered this cycle.",
            delivery_status="delivered" if actionable_clusters else "no_deliverable_signals",
        )


def create_monitor_workflow(model: Model, memory: RivalMemory | None = None) -> Workflow:
    """Instantiate Agno Workflow wrapper around monitor pipeline."""
    pipeline_engine = MonitorPipelineWorkflow(model=model, memory=memory)

    def workflow_step_executor(step_input: StepInput) -> StepOutput:
        # Wrap async execution
        inp_data = step_input.input
        if isinstance(inp_data, dict):
            run_inp = PipelineRunInput(**inp_data)
        elif isinstance(inp_data, PipelineRunInput):
            run_inp = inp_data
        else:
            run_inp = PipelineRunInput()

        res = asyncio.run(pipeline_engine.execute(run_inp))
        return StepOutput(content=res.model_dump())

    pipeline_step = Step(
        name="CompetitiveMonitorStep",
        executor=workflow_step_executor,
        description="Executes parallel collection, 6-stage dedup, verification, and synthesis.",
    )

    return Workflow(
        name="MonitorPipelineWorkflow",
        description="Deterministic competitive intelligence pipeline workflow.",
        steps=[pipeline_step],
    )
