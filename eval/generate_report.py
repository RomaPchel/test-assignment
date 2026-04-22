#!/usr/bin/env python3
"""
Generate a markdown evaluation report from results.json.

Usage:
    python eval/generate_report.py
"""
import json
from pathlib import Path
from datetime import datetime

def generate_report(results_path: Path, output_path: Path):
    """Generate markdown report from evaluation results."""

    with open(results_path) as f:
        data = json.load(f)

    accuracy = data["accuracy"]
    total = data["total_claims"]
    correct = data["correct"]
    metrics = data["metrics"]
    results = data["results"]

    md = []
    md.append("# Evaluation Results - Insurance Claim Pipeline")
    md.append("")
    md.append(f"**Generated**: {data.get('timestamp', 'N/A')}")
    md.append("")

    # Overall metrics
    md.append("## Overall Performance")
    md.append("")
    md.append(f"- **Accuracy**: {accuracy:.1%} ({correct}/{total} correct)")

    avg_latency = sum(r.get("latency_ms", 0) for r in results) / len(results)
    md.append(f"- **Average Latency**: {avg_latency:.0f}ms per claim")

    errors = [r for r in results if "error" in r]
    if errors:
        md.append(f"- **Errors**: {len(errors)} claims failed to process")

    md.append("")

    # Per-decision metrics
    md.append("## Per-Decision Performance")
    md.append("")
    md.append("| Decision | Precision | Recall | F1 Score | Support |")
    md.append("|----------|-----------|--------|----------|---------|")

    for decision in ["APPROVE", "DENY", "UNCERTAIN"]:
        m = metrics["per_class"][decision]
        support = m["tp"] + m["fn"]
        md.append(
            f"| {decision} | {m['precision']:.2%} | {m['recall']:.2%} | "
            f"{m['f1']:.2%} | {support} |"
        )

    md.append("")

    # Confusion matrix
    md.append("## Confusion Matrix")
    md.append("")
    md.append("| Expected ↓ / Actual → | APPROVE | DENY | UNCERTAIN |")
    md.append("|------------------------|---------|------|-----------|")

    cm = metrics["confusion_matrix"]
    for expected in ["APPROVE", "DENY", "UNCERTAIN"]:
        counts = [
            cm.get((expected, actual), 0)
            for actual in ["APPROVE", "DENY", "UNCERTAIN"]
        ]
        md.append(f"| **{expected}** | {counts[0]} | {counts[1]} | {counts[2]} |")

    md.append("")

    # Failure analysis
    failures = [r for r in results if not r["match"]]
    if failures:
        md.append("## Failure Analysis")
        md.append("")
        md.append(f"**{len(failures)} claims** were incorrectly classified:")
        md.append("")

        # Group by failure type
        failure_types = {}
        for r in failures:
            key = f"{r['expected']} → {r.get('actual', 'ERROR')}"
            if key not in failure_types:
                failure_types[key] = []
            failure_types[key].append(r)

        for failure_type, cases in failure_types.items():
            md.append(f"### {failure_type} ({len(cases)} cases)")
            md.append("")
            for r in cases:
                md.append(f"**{r['claim']}**")
                if "error" in r:
                    md.append(f"- Error: `{r['error']}`")
                elif "reasoning" in r:
                    # Truncate long reasoning
                    reasoning = r['reasoning']
                    if len(reasoning) > 200:
                        reasoning = reasoning[:200] + "..."
                    md.append(f"- Reasoning: {reasoning}")
                md.append("")

    # Insights
    md.append("## Key Insights")
    md.append("")

    # Best performing decision type
    best_decision = max(
        ["APPROVE", "DENY", "UNCERTAIN"],
        key=lambda d: metrics["per_class"][d]["f1"]
    )
    best_f1 = metrics["per_class"][best_decision]["f1"]
    md.append(f"- **Best performing decision**: {best_decision} (F1: {best_f1:.1%})")

    # Weakest decision type
    worst_decision = min(
        ["APPROVE", "DENY", "UNCERTAIN"],
        key=lambda d: metrics["per_class"][d]["f1"]
    )
    worst_f1 = metrics["per_class"][worst_decision]["f1"]
    md.append(f"- **Weakest decision**: {worst_decision} (F1: {worst_f1:.1%})")

    # Common misclassifications
    most_common_error = max(
        cm.items(),
        key=lambda x: x[1] if x[0][0] != x[0][1] else 0
    )
    if most_common_error[1] > 0:
        exp, act = most_common_error[0]
        if exp != act:
            md.append(f"- **Most common error**: {exp} classified as {act} ({most_common_error[1]} cases)")

    md.append("")

    # Future improvements
    md.append("## Potential Improvements")
    md.append("")

    if worst_f1 < 0.8:
        md.append(f"1. **Improve {worst_decision} detection**: F1 score of {worst_f1:.1%} suggests room for improvement")

    if failures:
        md.append("2. **Address failure cases**: Analyze incorrect classifications to identify patterns")

    if avg_latency > 10000:  # 10 seconds
        md.append(f"3. **Optimize latency**: Current average of {avg_latency:.0f}ms could be reduced with caching or parallel processing")

    md.append("")

    # Write report
    with open(output_path, "w") as f:
        f.write("\n".join(md))

    print(f"✅ Report generated: {output_path}")


if __name__ == "__main__":
    results_path = Path("eval/results.json")
    output_path = Path("eval/EVALUATION_REPORT.md")

    if not results_path.exists():
        print(f"❌ Error: {results_path} not found. Run run_benchmark.py first.")
        exit(1)

    generate_report(results_path, output_path)
