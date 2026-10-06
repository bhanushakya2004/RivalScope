"""Unit tests for the Benchmark and Evaluation Suite."""

from app.evals.benchmark import BENCHMARK_CASES, BenchmarkSuite


def test_benchmark_suite_cases():
    """Verify benchmark test cases are properly defined with fintech rivals."""
    assert len(BENCHMARK_CASES) >= 3
    competitors = [case["target_competitor"] for case in BENCHMARK_CASES]
    assert "Stripe" in competitors
    assert "Adyen" in competitors
    assert "Revolut" in competitors


def test_benchmark_retrieval_evaluation():
    """Verify retrieval precision evaluation against knowledge memory."""
    suite = BenchmarkSuite()
    retrieval_metrics = suite.run_retrieval_evaluation(tenant_id="t-paypulse-demo")
    assert "retrieval_precision_at_3" in retrieval_metrics
    assert retrieval_metrics["retrieval_precision_at_3"] >= 0.8
    assert retrieval_metrics["retrieval_cases_evaluated"] == len(BENCHMARK_CASES)


def test_benchmark_deduplication_evaluation():
    """Verify deduplication F1 score and stage verification."""
    suite = BenchmarkSuite()
    dedup_metrics = suite.run_deduplication_evaluation()
    assert "dedup_f1_score" in dedup_metrics
    assert dedup_metrics["dedup_f1_score"] >= 0.85
    assert dedup_metrics["pipeline_stages_verified"] == 6


def test_benchmark_full_suite():
    """Verify end-to-end benchmark execution and composite passing status."""
    suite = BenchmarkSuite()
    results = suite.run_full_suite(tenant_id="t-paypulse-demo")
    assert results["status"] == "passed"
    assert results["composite_score"] >= 0.85
    assert "metrics" in results
    assert results["metrics"]["pipeline_stages_verified"] == 6
