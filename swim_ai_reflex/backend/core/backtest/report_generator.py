"""Generate comparison reports in markdown, JSON, and CSV formats."""

from __future__ import annotations

import csv
import json
from pathlib import Path

from swim_ai_reflex.backend.core.backtest.schemas import BacktestReport


def generate_markdown_report(report: BacktestReport, output_path: Path) -> Path:
    """Generate a human-readable markdown comparison report."""
    lines = [
        f"# Backtest Report: {report.meet_name}",
        f"**Optimizer:** {report.optimizer}",
        f"**Meet ID:** {report.meet_id}",
        "",
        "## Score Summary",
        "",
        "| Metric | Value |",
        "|--------|-------|",
        f"| Predicted SST Total | {report.predicted_seton_total:.0f} |",
        f"| Actual SST Total | {report.actual_seton_total:.0f} |",
        f"| Delta (Actual - Predicted) | {report.score_delta:+.0f} |",
        f"| Score Accuracy | {report.score_accuracy_pct:.1f}% |",
        f"| Assignment Match Rate | {report.assignment_match_rate:.0%} |",
        "",
        "## Event-by-Event Comparison",
        "",
        "| Event | Pred Pts | Actual Pts | Delta | Predicted Entries | Actual Entries |",
        "|-------|----------|------------|-------|-------------------|----------------|",
    ]

    for ec in report.event_comparisons:
        pred_names = ", ".join(ec.predicted_seton_entries) or "-"
        actual_names = ", ".join(ec.actual_seton_entries) or "-"
        lines.append(
            f"| {ec.event_name} | {ec.predicted_seton_points:.0f} | "
            f"{ec.actual_seton_points:.0f} | {ec.delta:+.0f} | "
            f"{pred_names} | {actual_names} |"
        )

    lines.extend(
        [
            "",
            "## Swimmer Assignment Comparison",
            "",
            "| Swimmer | Status | Predicted Events | Actual Events | Actual Pts |",
            "|---------|--------|------------------|---------------|------------|",
        ]
    )

    for sc in report.swimmer_comparisons:
        pred = ", ".join(sc.predicted_events) or "-"
        actual = ", ".join(sc.actual_events) or "-"
        lines.append(
            f"| {sc.swimmer} | {sc.status} | {pred} | {actual} | {sc.actual_points:.0f} |"
        )

    content = "\n".join(lines) + "\n"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(content)
    return output_path


def generate_json_report(report: BacktestReport, output_path: Path) -> Path:
    """Generate machine-readable JSON report."""
    data = {
        "meet_id": report.meet_id,
        "meet_name": report.meet_name,
        "optimizer": report.optimizer,
        "predicted_seton_total": report.predicted_seton_total,
        "actual_seton_total": report.actual_seton_total,
        "score_delta": report.score_delta,
        "score_accuracy_pct": report.score_accuracy_pct,
        "assignment_match_rate": report.assignment_match_rate,
        "event_comparisons": [
            {
                "event_name": ec.event_name,
                "predicted_seton_points": ec.predicted_seton_points,
                "actual_seton_points": ec.actual_seton_points,
                "delta": ec.delta,
                "predicted_entries": ec.predicted_seton_entries,
                "actual_entries": ec.actual_seton_entries,
            }
            for ec in report.event_comparisons
        ],
        "swimmer_comparisons": [
            {
                "swimmer": sc.swimmer,
                "status": sc.status,
                "predicted_events": sc.predicted_events,
                "actual_events": sc.actual_events,
                "actual_points": sc.actual_points,
            }
            for sc in report.swimmer_comparisons
        ],
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(data, f, indent=2)
    return output_path


def generate_csv_report(report: BacktestReport, output_dir: Path) -> tuple[Path, Path]:
    """Generate CSV files for event and swimmer comparisons.

    Returns (event_csv_path, swimmer_csv_path).
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    # Event comparison CSV
    event_path = output_dir / "comparison_events.csv"
    with open(event_path, "w", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "event_name",
                "predicted_seton_points",
                "actual_seton_points",
                "delta",
                "predicted_entries",
                "actual_entries",
            ],
        )
        writer.writeheader()
        for ec in report.event_comparisons:
            writer.writerow(
                {
                    "event_name": ec.event_name,
                    "predicted_seton_points": ec.predicted_seton_points,
                    "actual_seton_points": ec.actual_seton_points,
                    "delta": ec.delta,
                    "predicted_entries": "|".join(ec.predicted_seton_entries),
                    "actual_entries": "|".join(ec.actual_seton_entries),
                }
            )

    # Swimmer comparison CSV
    swimmer_path = output_dir / "comparison_swimmers.csv"
    with open(swimmer_path, "w", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "swimmer",
                "team",
                "status",
                "predicted_events",
                "actual_events",
                "actual_points",
            ],
        )
        writer.writeheader()
        for sc in report.swimmer_comparisons:
            writer.writerow(
                {
                    "swimmer": sc.swimmer,
                    "team": sc.team,
                    "status": sc.status,
                    "predicted_events": "|".join(sc.predicted_events),
                    "actual_events": "|".join(sc.actual_events),
                    "actual_points": sc.actual_points,
                }
            )

    return event_path, swimmer_path
