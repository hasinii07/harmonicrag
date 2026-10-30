import sys
from pathlib import Path

# Add backend to sys.path
backend_dir = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(backend_dir))

from app.services.evaluation_service import evaluation_service

def main():
    print("=" * 80)
    print(" HarmonicsRAG — Automated Music Theory Evaluation Suite")
    print("=" * 80)
    print("Executing benchmark cases across all 6 required categories:\n"
          "  A. Direct in-corpus factual\n"
          "  B. Multi-passage synthesis\n"
          "  C. Uncovered or out-of-scope\n"
          "  D. Ambiguous musical questions\n"
          "  E. Incorrect musical assumptions\n"
          "  F. Strict citation requirements\n")

    report = evaluation_service.run_suite()

    print("\n" + "-" * 80)
    print("BENCHMARK EXECUTION RESULTS:")
    print("-" * 80)
    for c in report.cases:
        status_marker = "[ PASS ]" if c.status == "pass" else "[ FAIL ]"
        print(f"{status_marker} {c.test_id} ({c.category}): {c.question[:65]}...")
        if c.failure_reason:
            print(f"         Reason: {c.failure_reason}")
        if c.citations:
            print(f"         Citations: {', '.join(c.citations[:2])}")
        print(f"         Latency: {round(c.retrieval_latency_ms + c.generation_latency_ms, 1)}ms")

    print("\n" + "=" * 80)
    print("EVALUATION METRICS SUMMARY:")
    print("=" * 80)
    print(f"Total Tests Executed:       {report.total_tests}")
    print(f"Passed Tests:               {report.passed_tests}")
    print(f"Failed Tests:               {report.failed_tests}")
    print(f"Pass Rate:                  {report.pass_rate_pct}%")
    print(f"Retrieval Success Rate:     {report.retrieval_success_rate_pct}%")
    print(f"Citation Precision:         {report.citation_precision_pct}%")
    print(f"Citation Coverage:          {report.citation_coverage_pct}%")
    print(f"Unsupported Answer Rate:    {report.unsupported_answer_rate_pct}%")
    print(f"Abstention Performance:     {report.abstention_performance_pct}%")
    print(f"Average Total Latency:      {report.avg_latency_ms} ms")
    print("=" * 80)
    print(f"Results persisted to: data/metadata/evaluation_results.json\n")

if __name__ == "__main__":
    main()
