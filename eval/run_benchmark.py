#!/usr/bin/env python3
import asyncio
import json
import sys
import time
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Optional
import httpx

CLAIMS_DIR = Path("takehome-test-data")
API_BASE = "http://127.0.0.1:8000"
RESULTS_CACHE = Path("data/benchmark_results.json")

async def process_single_claim(claim_dir: Path) -> Dict:
    claim_name = claim_dir.name
    start_time = time.time()

    # Read claim description
    with open(claim_dir / "description.txt") as f:
        description = f.read()

    # Get supporting files
    files = [fp for fp in claim_dir.iterdir()
             if fp.name not in ["answer.json", "description.txt"]]

    # Read expected answer
    with open(claim_dir / "answer.json") as f:
        expected = json.load(f)

    # Call API
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            file_uploads = [
                ("files", (fp.name, open(fp, "rb"), "application/octet-stream"))
                for fp in files
            ]
            response = await client.post(
                f"{API_BASE}/claims",
                data={"description": description},
                files=file_uploads
            )

        latency_ms = (time.time() - start_time) * 1000

        if response.status_code not in (200, 201):
            return {
                "claim": claim_name,
                "expected": expected["decision"],
                "actual": None,
                "match": False,
                "error": f"HTTP {response.status_code}",
                "latency_ms": latency_ms
            }

        result = response.json()
        match = result["decision"] == expected["decision"]
        if not match and "acceptable_decision" in expected:
            match = result["decision"] == expected["acceptable_decision"]
        return {
            "claim": claim_name,
            "expected": expected["decision"],
            "actual": result["decision"],
            "confidence": result["confidence"],
            "reasoning": result["reasoning"],
            "match": match,
            "latency_ms": latency_ms,
            "num_files": len(files)
        }

    except Exception as e:
        return {
            "claim": claim_name,
            "expected": expected["decision"],
            "actual": None,
            "match": False,
            "error": str(e),
            "latency_ms": (time.time() - start_time) * 1000
        }

def calculate_metrics(results: List[Dict]) -> Dict:
    confusion = defaultdict(int)
    for r in results:
        if r["actual"] is not None:
            confusion[(r["expected"], r["actual"])] += 1

    # Calculate per-class metrics
    decision_types = ["APPROVE", "DENY", "UNCERTAIN"]
    metrics = {}

    for decision in decision_types:
        tp = confusion[(decision, decision)]
        fp = sum(confusion[(exp, decision)] for exp in decision_types if exp != decision)
        fn = sum(confusion[(decision, act)] for act in decision_types if act != decision)

        precision = tp / (tp + fp) if (tp + fp) > 0 else 0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0
        f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0

        metrics[decision] = {
            "precision": precision,
            "recall": recall,
            "f1": f1,
            "tp": tp,
            "fp": fp,
            "fn": fn
        }

    return {"per_class": metrics, "confusion_matrix": dict(confusion)}


def print_results(results: List[Dict], metrics: Dict):
    correct = sum(1 for r in results if r["match"])
    total = len(results)
    accuracy = correct / total if total > 0 else 0

    print("\n" + "="*80)
    print("EVALUATION RESULTS")
    print("="*80)

    print(f"\nOverall Accuracy: {accuracy:.1%} ({correct}/{total})")

    avg_latency = sum(r.get("latency_ms", 0) for r in results) / len(results)
    print(f"Average Latency: {avg_latency:.0f}ms")

    print("\nPer-Decision Metrics:")
    print(f"{'Decision':<12} {'Precision':<12} {'Recall':<12} {'F1':<12} {'Support':<12}")
    print("-" * 60)

    for decision in ["APPROVE", "DENY", "UNCERTAIN"]:
        m = metrics["per_class"][decision]
        support = m["tp"] + m["fn"]
        print(f"{decision:<12} {m['precision']:<12.2%} {m['recall']:<12.2%} "
              f"{m['f1']:<12.2%} {support:<12}")

    print("\nConfusion Matrix:")
    print(f"{'Expected ↓':<15} {'APPROVE':<12} {'DENY':<12} {'UNCERTAIN':<12}")
    print("-" * 51)

    cm = metrics["confusion_matrix"]
    for expected in ["APPROVE", "DENY", "UNCERTAIN"]:
        row = f"{expected:<15}"
        for actual in ["APPROVE", "DENY", "UNCERTAIN"]:
            count = cm.get((expected, actual), 0)
            row += f"{count:<12}"
        print(row)

    failures = [r for r in results if not r["match"]]
    if failures:
        print(f"\nFailures ({len(failures)}):")
        print("-" * 80)
        for r in failures:
            print(f"\n{r['claim']}:")
            print(f"  Expected: {r['expected']}, Got: {r.get('actual', 'ERROR')}")
            if "error" in r:
                print(f"  Error: {r['error']}")
            elif "reasoning" in r:
                reasoning = r['reasoning'][:100] + "..." if len(r['reasoning']) > 100 else r['reasoning']
                print(f"  Reasoning: {reasoning}")

    print("\n" + "="*80)


async def main():
    failed_only = "--failed-only" in sys.argv
    specific_claim = None
    for arg in sys.argv[1:]:
        if not arg.startswith("--"):
            specific_claim = arg
            break

    claim_dirs = sorted([
        d for d in CLAIMS_DIR.iterdir()
        if d.is_dir() and d.name.startswith("claim")
    ])

    if specific_claim:
        claim_dirs = [
            d for d in claim_dirs
            if d.name == specific_claim
            or d.name == f"claim {specific_claim}"
            or d.name == f"claim_{specific_claim}"
        ]
        if not claim_dirs:
            print(f"Error: Claim '{specific_claim}' not found")
            sys.exit(1)

    elif failed_only:
        if not RESULTS_CACHE.exists():
            print("Error: No previous results found. Run full benchmark first.")
            sys.exit(1)

        with open(RESULTS_CACHE) as f:
            previous_results = json.load(f)

        failed_claim_names = [
            r["claim"] for r in previous_results
            if not r.get("match", False)
        ]

        claim_dirs = [
            d for d in claim_dirs
            if d.name in failed_claim_names
        ]

        if not claim_dirs:
            print("No failed claims from previous run! All tests passing.")
            sys.exit(0)

        print(f"Rerunning {len(claim_dirs)} failed claim(s) from previous run...")
    else:
        print(f"Running full benchmark...")

    if not failed_only:
        print(f"Evaluating {len(claim_dirs)} claim(s)...")
    print("-" * 80)

    results = []
    for i, claim_dir in enumerate(claim_dirs, 1):
        print(f"[{i:2d}/{len(claim_dirs)}] {claim_dir.name:<20}", end=" ", flush=True)
        result = await process_single_claim(claim_dir)
        results.append(result)

        if result["match"]:
            print(f"✓ {result['actual']:<10} ({result.get('latency_ms', 0):.0f}ms)")
        else:
            actual = result.get('actual', 'ERROR')
            print(f"X Expected {result['expected']}, got {actual}")

    RESULTS_CACHE.parent.mkdir(parents=True, exist_ok=True)
    with open(RESULTS_CACHE, "w") as f:
        json.dump(results, f, indent=2)

    metrics = calculate_metrics(results)

    print_results(results, metrics)

    if not specific_claim:
        output = {
            "accuracy": sum(1 for r in results if r["match"]) / len(results),
            "total_claims": len(results),
            "correct": sum(1 for r in results if r["match"]),
            "metrics": metrics,
            "results": results,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }

        output_path = Path("eval/results.json")
        with open(output_path, "w") as f:
            json.dump(output, f, indent=2)
        print(f"\nDetailed results saved to: {output_path}")


if __name__ == "__main__":
    asyncio.run(main())
