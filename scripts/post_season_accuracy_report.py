"""
Post-Season Accuracy Report

Runs backtesting across all meets in the registry that have actual results,
compares optimizer predictions vs actual outcomes, and generates a summary.

Usage:
    python scripts/post_season_accuracy_report.py
    python scripts/post_season_accuracy_report.py --meet visaa_2026
    python scripts/post_season_accuracy_report.py --verbose
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from swim_ai_reflex.backend.core.backtest.comparator import (  # noqa: E402
    compare_prediction_vs_actual,
)
from swim_ai_reflex.backend.core.backtest.loader import (  # noqa: E402
    load_actual_results_json,
    load_prediction_snapshot,
)
from swim_ai_reflex.backend.core.backtest.report_generator import (  # noqa: E402
    generate_csv_report,
    generate_json_report,
    generate_markdown_report,
)
from swim_ai_reflex.backend.core.backtest.schemas import BacktestReport  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

DATA_DIR = PROJECT_ROOT / "data" / "backtest"
REPORTS_DIR = PROJECT_ROOT / "data" / "reports" / "post_season"


def load_registry() -> list[dict]:
    """Load the backtest registry."""
    registry_path = DATA_DIR / "registry.json"
    if not registry_path.exists():
        logger.error("Registry not found at %s", registry_path)
        return []
    with open(registry_path) as f:
        data = json.load(f)
    return data.get("meets", [])


def run_meet_backtest(meet_entry: dict, verbose: bool = False) -> list[BacktestReport]:
    """Run backtesting for a single meet entry. Returns reports for each optimizer."""
    meet_id = meet_entry["id"]
    meet_dir = DATA_DIR / meet_entry["directory"]
    reports: list[BacktestReport] = []

    # Load actual results
    actual_path = meet_dir / "actual_results.json"
    if not actual_path.exists():
        logger.warning("No actual_results.json for %s, skipping", meet_id)
        return reports

    actual = load_actual_results_json(actual_path)

    # Check if there are any events with results
    events_with_data = sum(1 for e in actual.events if e.results)
    if events_with_data == 0 and not actual.team_scores:
        logger.warning("No event results or team scores for %s, skipping", meet_id)
        return reports

    if verbose:
        logger.info(
            "Loaded %s: %d events with data, %d total team scores",
            meet_id,
            events_with_data,
            sum(len(v) for v in actual.team_scores.values())
            if isinstance(actual.team_scores, dict)
            else 0,
        )

    # Try each optimizer prediction
    for optimizer in ["aqua", "gurobi"]:
        pred_path = meet_dir / f"optimizer_prediction_{optimizer}.json"
        if not pred_path.exists():
            if verbose:
                logger.info("  No %s prediction for %s", optimizer, meet_id)
            continue

        prediction = load_prediction_snapshot(pred_path)
        report = compare_prediction_vs_actual(prediction, actual)
        reports.append(report)

        if verbose:
            logger.info(
                "  %s: predicted=%.0f actual=%.0f delta=%+.0f accuracy=%.1f%%",
                optimizer,
                report.predicted_seton_total,
                report.actual_seton_total,
                report.score_delta,
                report.score_accuracy_pct,
            )

    return reports


def generate_summary(all_reports: dict[str, list[BacktestReport]]) -> str:
    """Generate a text summary across all meets and optimizers."""
    lines = [
        "=" * 70,
        "POST-SEASON ACCURACY REPORT — 2025-2026 Season",
        "=" * 70,
        "",
    ]

    total_meets_with_data = 0
    total_predictions = 0

    for meet_id, reports in all_reports.items():
        if not reports:
            lines.append(f"  {meet_id}: No predictions to compare")
            continue

        total_meets_with_data += 1
        lines.append(f"  Meet: {reports[0].meet_name} ({meet_id})")

        for report in reports:
            total_predictions += 1
            lines.append(f"    Optimizer: {report.optimizer}")
            lines.append(f"      Predicted SST: {report.predicted_seton_total:.0f}")
            lines.append(f"      Actual SST:    {report.actual_seton_total:.0f}")
            lines.append(f"      Delta:         {report.score_delta:+.0f}")
            lines.append(f"      Accuracy:      {report.score_accuracy_pct:.1f}%")
            lines.append(
                f"      Assignment Match Rate: {report.assignment_match_rate:.0%}"
            )

            # Event-level highlights
            if report.event_comparisons:
                best_delta = min(report.event_comparisons, key=lambda e: abs(e.delta))
                worst_delta = max(report.event_comparisons, key=lambda e: abs(e.delta))
                lines.append(
                    f"      Best event:  {best_delta.event_name} (delta {best_delta.delta:+.0f})"
                )
                lines.append(
                    f"      Worst event: {worst_delta.event_name} (delta {worst_delta.delta:+.0f})"
                )
        lines.append("")

    lines.extend(
        [
            "-" * 70,
            f"Total: {total_meets_with_data} meets analyzed, {total_predictions} optimizer comparisons",
            "",
        ]
    )

    if total_predictions > 0:
        avg_accuracy = (
            sum(
                r.score_accuracy_pct
                for reports in all_reports.values()
                for r in reports
            )
            / total_predictions
        )
        lines.append(f"Average Score Accuracy: {avg_accuracy:.1f}%")
    else:
        lines.append(
            "No optimizer predictions found. Run optimizers and save predictions first."
        )
        lines.append(
            "  Use prediction_saver.save_aqua_prediction() or save_gurobi_prediction()"
        )

    lines.append("=" * 70)
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Post-season accuracy report")
    parser.add_argument("--meet", type=str, help="Run for specific meet ID only")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument(
        "--output-dir",
        type=str,
        default=str(REPORTS_DIR),
        help="Output directory for reports",
    )
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    registry = load_registry()
    if not registry:
        logger.error("No meets in registry")
        sys.exit(1)

    # Filter to specific meet if requested
    if args.meet:
        registry = [m for m in registry if m["id"] == args.meet]
        if not registry:
            logger.error("Meet '%s' not found in registry", args.meet)
            sys.exit(1)

    # Run backtests
    all_reports: dict[str, list[BacktestReport]] = {}

    for meet_entry in registry:
        meet_id = meet_entry["id"]
        logger.info("Processing %s...", meet_id)
        reports = run_meet_backtest(meet_entry, verbose=args.verbose)
        all_reports[meet_id] = reports

        # Generate per-meet reports
        meet_output_dir = output_dir / meet_id
        for report in reports:
            generate_markdown_report(
                report,
                meet_output_dir / f"backtest_{report.optimizer}.md",
            )
            generate_json_report(
                report,
                meet_output_dir / f"backtest_{report.optimizer}.json",
            )
            generate_csv_report(report, meet_output_dir)

    # Generate summary
    summary = generate_summary(all_reports)
    print(summary)

    # Save summary
    summary_path = output_dir / "season_summary.txt"
    summary_path.write_text(summary)
    logger.info("Summary saved to %s", summary_path)


if __name__ == "__main__":
    main()
