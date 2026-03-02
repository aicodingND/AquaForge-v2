#!/usr/bin/env python3
"""Run backtest comparison: optimizer prediction vs actual meet results.

Usage:
    python scripts/run_backtest_comparison.py visaa_2026
    python scripts/run_backtest_comparison.py visaa_2026 --optimizer gurobi
    python scripts/run_backtest_comparison.py --list
"""

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

BACKTEST_DIR = PROJECT_ROOT / "data" / "backtest"


def list_meets() -> None:
    """List available meets with backtest data."""
    registry_path = BACKTEST_DIR / "registry.json"
    if registry_path.exists():
        with open(registry_path) as f:
            registry = json.load(f)
        print(f"\n{'Meet ID':<20}  {'Actual?':<8}  {'Name'}")
        print("-" * 70)
        for meet in registry.get("meets", []):
            has_actual = "Y" if meet.get("has_actual_results") else "N"
            print(f"  {meet['id']:<18}  {has_actual:<8}  {meet['name']}")
    else:
        print("\nScanning data/backtest/ directories...")
        for d in sorted(BACKTEST_DIR.iterdir()):
            if d.is_dir():
                has_actual = (d / "actual_results.json").exists()
                has_aqua = (d / "optimizer_prediction_aqua.json").exists()
                has_gurobi = (d / "optimizer_prediction_gurobi.json").exists()
                status = []
                if has_actual:
                    status.append("actual")
                if has_aqua:
                    status.append("aqua")
                if has_gurobi:
                    status.append("gurobi")
                print(f"  {d.name:<20}  [{', '.join(status) or 'empty'}]")
    print()


def run_comparison(meet_id: str, optimizer: str = "aqua") -> None:
    """Run comparison for a specific meet."""
    from swim_ai_reflex.backend.core.backtest.comparator import (
        compare_prediction_vs_actual,
    )
    from swim_ai_reflex.backend.core.backtest.loader import (
        load_actual_results_json,
        load_prediction_snapshot,
    )
    from swim_ai_reflex.backend.core.backtest.report_generator import (
        generate_csv_report,
        generate_json_report,
        generate_markdown_report,
    )

    meet_dir = BACKTEST_DIR / meet_id

    actual_path = meet_dir / "actual_results.json"
    pred_path = meet_dir / f"optimizer_prediction_{optimizer}.json"

    if not actual_path.exists():
        print(f"ERROR: No actual results found at {actual_path}")
        print(f"  Create {actual_path} with event results to enable comparison.")
        sys.exit(1)
    if not pred_path.exists():
        print(f"ERROR: No {optimizer} prediction found at {pred_path}")
        print("  Run the optimizer with --save-prediction to create this file.")
        sys.exit(1)

    actual = load_actual_results_json(actual_path)
    prediction = load_prediction_snapshot(pred_path)

    report = compare_prediction_vs_actual(prediction, actual)

    # Generate all report formats
    md_path = generate_markdown_report(report, meet_dir / "comparison_report.md")
    json_path = generate_json_report(report, meet_dir / "comparison_report.json")
    event_csv, swimmer_csv = generate_csv_report(report, meet_dir)

    # Print summary to stdout
    print(f"\n{'=' * 70}")
    print(f"  BACKTEST: {report.meet_name}")
    print(f"  Optimizer: {report.optimizer}")
    print(f"{'=' * 70}")
    print(f"  Predicted SST: {report.predicted_seton_total:.0f}")
    print(f"  Actual SST:    {report.actual_seton_total:.0f}")
    print(f"  Delta:         {report.score_delta:+.0f}")
    print(f"  Accuracy:      {report.score_accuracy_pct:.1f}%")
    print(f"  Match Rate:    {report.assignment_match_rate:.0%}")

    # Show event breakdown
    if report.event_comparisons:
        print(f"\n  {'Event':<25}  {'Pred':>5}  {'Actual':>6}  {'Delta':>6}")
        print(f"  {'-' * 50}")
        for ec in report.event_comparisons:
            print(
                f"  {ec.event_name:<25}  {ec.predicted_seton_points:>5.0f}  "
                f"{ec.actual_seton_points:>6.0f}  {ec.delta:>+6.0f}"
            )

    print("\n  Reports saved:")
    print(f"    {md_path}")
    print(f"    {json_path}")
    print(f"    {event_csv}")
    print(f"    {swimmer_csv}")
    print()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Compare optimizer predictions vs actual meet results"
    )
    parser.add_argument(
        "meet_id", nargs="?", help="Meet ID (directory name under data/backtest/)"
    )
    parser.add_argument(
        "--optimizer",
        default="aqua",
        choices=["aqua", "gurobi"],
        help="Which optimizer prediction to compare (default: aqua)",
    )
    parser.add_argument("--list", action="store_true", help="List available meets")
    args = parser.parse_args()

    if args.list:
        list_meets()
    elif args.meet_id:
        run_comparison(args.meet_id, args.optimizer)
    else:
        parser.print_help()
