"""RivalScope Offline Demo Runner: End-to-End Multi-Agent CI Pipeline & Benchmark."""

import asyncio
import sys

from app.core.mock_model import MockModel
from app.db.seed import seed_database
from app.db.session import SessionLocal
from app.evals.benchmark import BenchmarkSuite
from app.memory.manager import RivalMemory
from app.workflows.monitor_pipeline import MonitorPipelineWorkflow, PipelineRunInput

BANNER = r"""
================================================================================
   ____  _            _ ____
  |  _ \(_)_   ____ _| / ___|  ___ ___  _ __   ___
  | |_) | \ \ / / _` | \___ \ / __/ _ \| '_ \ / _ \
  |  _ <| |\ V / (_| | |___) | (_| (_) | |_) |  __/
  |_| \_\_| \_/ \__,_|_|____/ \___\___/| .__/ \___|
                                       |_|
  Autonomous Multi-Agent Competitive Intelligence Platform (Fintech Edition)
================================================================================
"""


async def run_offline_demo() -> int:
    """Run full offline demo across fintech competitors and execute eval benchmarks."""
    print(BANNER)
    print(">> Initializing RivalScope Demonstration Environment...")

    # Step 1: Database verification and seeding
    print(">> [1/4] Verifying PostgreSQL + pgvector and seeding fintech rivals...")
    db = SessionLocal()
    try:
        seed_database(db)
        print("   [OK] Database verified: Tenant 'PayPulse Global' & rivals ready.")
    finally:
        db.close()

    # Step 2: Initialize Mock Model and Memory Facade
    print(
        "\n>> [2/4] Initializing MockModel (Deterministic LLM) and RivalMemory (4-layer facade)..."
    )
    mock_model = MockModel(id="mock-gemini-2.5")
    memory = RivalMemory()
    workflow = MonitorPipelineWorkflow(model=mock_model, memory=memory)
    print("   [OK] MockModel active: Zero external LLM token spend required.")
    print("   [OK] RivalMemory active: Session, Org Preferences, Vector L3, Timeline L4.")

    # Step 3: Run Competitive Intelligence Workflows
    competitors = [
        {"id": "c-comp-stripe", "name": "Stripe", "domain": "stripe.com"},
        {"id": "c-comp-adyen", "name": "Adyen", "domain": "adyen.com"},
        {"id": "c-comp-revolut", "name": "Revolut", "domain": "revolut.com"},
    ]

    print("\n>> [3/4] Executing Autonomous Multi-Agent Pipeline for Fintech Competitors...")
    total_discovered = 0
    total_clusters = 0
    total_verified = 0

    for idx, comp in enumerate(competitors, start=1):
        print("\n   ------------------------------------------------------------")
        print(
            f"   [{idx}/{len(competitors)}] Analyzing Competitor: {comp['name']} ({comp['domain']})"
        )
        print("   ------------------------------------------------------------")

        run_input = PipelineRunInput(
            tenant_id="t-paypulse-demo",
            company_id=comp["id"],
            company_name=comp["name"],
            domain=comp["domain"],
        )

        summary = await workflow.execute(run_input)
        total_discovered += summary.discovered_count
        total_clusters += summary.clusters_formed
        total_verified += summary.verified_signals

        print(
            f"   * Discovered Items : {summary.discovered_count} (Changelogs, News, Careers, Filings, Social)"
        )
        print("   * Dedup Pipeline   : Evaluated across 6 filtering stages")
        for dedup_res in summary.dedup_results:
            status = dedup_res.get("status")
            dropped = dedup_res.get("dropped_at")
            url = dedup_res.get("url", "")[:45]
            if status in ["unique_cluster", "corroborated"]:
                print(f"     -> [PASSED] {url}... => {status.upper()}")
            else:
                print(f"     -> [FILTERED] {url}... => {status} (Stage: {dropped})")

        print(f"   * Clusters Formed  : {summary.clusters_formed} actionable event clusters")
        print(f"   * Verified Signals : {summary.verified_signals} verified by VerifierAgent")
        print(
            f"   * Delivery Status  : {summary.delivery_status.upper()} (Mocked #competitive-intel channel)"
        )

        if summary.synthesized_report:
            preview = summary.synthesized_report.strip().split("\n")[0]
            print(f"   * Intelligence Brief Preview: {preview[:80]}...")

    # Step 4: Golden Fintech Benchmark Suite
    print("\n>> [4/4] Running Golden Fintech Benchmark Suite (Retrieval & Dedup Calibration)...")
    suite = BenchmarkSuite(memory=memory)
    eval_results = suite.run_full_suite(tenant_id="t-paypulse-demo")

    metrics = eval_results.get("metrics", {})
    precision = metrics.get("retrieval_precision_at_3", 0.0)
    dedup_f1 = metrics.get("dedup_f1_score", 0.0)
    composite = eval_results.get("composite_score", 0.0)
    status_str = eval_results.get("status", "unknown").upper()

    print("\n================================================================================")
    print("                     RIVALSCOPE DEMONSTRATION SCORECARD")
    print("================================================================================")
    print(f" Overall Status             : {status_str}")
    print(f" Composite Evaluation Score : {composite:.3f} / 1.000")
    print(f" Retrieval Precision @ 3    : {precision:.3f} (PgVector Hybrid Search)")
    print(f" Deduplication F1 Score     : {dedup_f1:.3f} (6-Stage Pipeline Calibrated)")
    print(f" Total Raw Items Ingested   : {total_discovered}")
    print(f" Actionable Clusters Formed : {total_clusters}")
    print(f" Verified Strategic Signals : {total_verified}")
    print("================================================================================")
    print("\n>> Demonstration complete!")
    print("   * Interactive API Docs : http://localhost:8000/docs")
    print("   * AgentOS Control Plane: http://localhost:8000/agentos")
    print("   * Health & Metrics     : http://localhost:8000/health | /metrics")
    print(
        "   * To use real providers: set GEMINI_API_KEY, TAVILY_API_KEY, FIRECRAWL_API_KEY in .env"
    )
    print("================================================================================\n")
    return 0


def main() -> None:
    """CLI entrypoint for demo runner."""
    exit_code = asyncio.run(run_offline_demo())
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
