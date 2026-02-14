#!/usr/bin/env python3
"""
Experiment 5: Predicted vs Actual DNS at Specific Championship Meets

For each championship meet where we have both psych sheet entries AND results:
  1. Count swimmers who were seeded but did not swim (DNS) per event
  2. Compare to model's predicted DNS rate
  3. Report per-event and per-meet accuracy

Unlike Experiment 2 (calibration), this uses the ACTUAL meet result data to
identify true DNS events — not just the model training data.

This answers: "For the specific meets where we'd use attrition,
how well does the model predict who doesn't show up?"
"""

import json
import os
import sys
import traceback
from collections import defaultdict
from pathlib import Path
from typing import Any

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.attrition_validation_utils import ensure_output_dir, print_table
from scripts.championship_backtest import (
    CHAMPIONSHIP_MEETS,
    DB_PATH,
    STROKE_MAP,
)
from swim_ai_reflex.backend.core.attrition_model import (
    DEFAULT_DNS_RATE,
    DNS_RATES,
    STANDARD_EVENTS,
)
from swim_ai_reflex.backend.utils.mdb_connector import MDBConnector


def compute_meet_dns_rates(
    connector: MDBConnector, meet_id: int
) -> dict[str, dict[str, Any]] | None:
    """Compute actual DNS rates for a meet from MDB result table.

    A DNS is identified as an entry with:
      - No valid time (SCORE is null, 0, or negative)
      - Marked as DNS/SCR in the database, OR simply no time recorded

    Returns: {event_name: {seeded: int, dns: int, completed: int, dns_rate: float}}
    """
    try:
        result_df = connector.read_table("RESULT")
        athlete_df = connector.read_table("ATHLETE")

        meet_results = result_df[result_df["MEET"] == meet_id].copy()
        if meet_results.empty:
            return None

        # Merge with athlete info for gender
        athlete_slim = athlete_df[["ATHLETE", "FIRST", "LAST", "SEX"]]
        merged = pd.merge(meet_results, athlete_slim, on="ATHLETE", how="left")

        # Filter to individual events only
        if "I_R" in merged.columns:
            merged = merged[merged["I_R"] == "I"]

        event_stats: dict[str, dict[str, int]] = defaultdict(
            lambda: {"seeded": 0, "dns": 0, "completed": 0}
        )

        for _, row in merged.iterrows():
            stroke = STROKE_MAP.get(row.get("STROKE"), None)
            if stroke is None:
                continue
            distance = int(row.get("DISTANCE", 0))
            event_name = f"{distance} {stroke}"

            if event_name not in STANDARD_EVENTS:
                continue

            event_stats[event_name]["seeded"] += 1

            # Check if DNS: no valid time
            time_val = pd.to_numeric(row.get("SCORE"), errors="coerce")
            if pd.isna(time_val) or time_val <= 0:
                event_stats[event_name]["dns"] += 1
            else:
                event_stats[event_name]["completed"] += 1

        # Compute rates
        result: dict[str, dict[str, Any]] = {}
        for event_name, stats in event_stats.items():
            if stats["seeded"] >= 3:  # Minimum entries
                result[event_name] = {
                    "seeded": stats["seeded"],
                    "dns": stats["dns"],
                    "completed": stats["completed"],
                    "dns_rate": stats["dns"] / stats["seeded"],
                }

        return result if result else None

    except Exception as e:
        print(f"  ERROR computing DNS rates for meet {meet_id}: {e}")
        traceback.print_exc()
        return None


def evaluate_meet(
    meet_id: int, meet_name: str, connector: MDBConnector
) -> dict[str, Any] | None:
    """Evaluate DNS prediction accuracy for a single meet."""
    actual_rates = compute_meet_dns_rates(connector, meet_id)
    if not actual_rates:
        return None

    per_event: list[dict[str, Any]] = []
    all_residuals: list[float] = []
    total_seeded = 0
    total_dns = 0
    total_predicted_dns = 0.0

    for event_name, obs in sorted(actual_rates.items()):
        predicted_rate = DNS_RATES.get(event_name, DEFAULT_DNS_RATE)
        actual_rate = obs["dns_rate"]
        residual = predicted_rate - actual_rate  # positive = over-predict DNS
        predicted_dns_count = predicted_rate * obs["seeded"]

        per_event.append(
            {
                "event": event_name,
                "seeded": obs["seeded"],
                "actual_dns": obs["dns"],
                "actual_rate": round(actual_rate, 4),
                "predicted_rate": round(predicted_rate, 4),
                "residual": round(residual, 4),
                "abs_error": round(abs(residual), 4),
                "predicted_dns_count": round(predicted_dns_count, 1),
            }
        )
        all_residuals.append(residual)
        total_seeded += obs["seeded"]
        total_dns += obs["dns"]
        total_predicted_dns += predicted_dns_count

    if not per_event:
        return None

    actual_global_rate = total_dns / total_seeded if total_seeded > 0 else 0
    mae = sum(abs(r) for r in all_residuals) / len(all_residuals)
    bias = sum(all_residuals) / len(all_residuals)

    return {
        "meet_id": meet_id,
        "meet_name": meet_name,
        "n_events": len(per_event),
        "total_seeded": total_seeded,
        "total_actual_dns": total_dns,
        "total_predicted_dns": round(total_predicted_dns, 1),
        "actual_global_rate": round(actual_global_rate, 4),
        "predicted_global_rate": round(DEFAULT_DNS_RATE, 4),
        "mae": round(mae, 4),
        "bias": round(bias, 4),
        "per_event": per_event,
    }


def main() -> None:
    if not os.path.exists(DB_PATH):
        print(f"MDB not found at {DB_PATH}")
        return

    print("=" * 80)
    print("EXPERIMENT 5: Predicted vs Actual DNS at Specific Meets")
    print("=" * 80)
    print(f"\nDatabase: {DB_PATH}")
    print(f"Meets to test: {len(CHAMPIONSHIP_MEETS)}")

    connector = MDBConnector(DB_PATH)
    results: list[dict[str, Any]] = []

    for meet_id, meet_name, profile in CHAMPIONSHIP_MEETS:
        short = meet_name[:45]
        print(f"\n  [{meet_id}] {short}...", end=" ", flush=True)
        r = evaluate_meet(meet_id, meet_name, connector)
        if r:
            print(
                f"MAE={r['mae'] * 100:.1f}%  "
                f"DNS: actual={r['total_actual_dns']}/{r['total_seeded']} "
                f"pred={r['total_predicted_dns']:.0f}"
            )
            results.append(r)
        else:
            print("SKIPPED")

    if not results:
        print("\nNo valid results.")
        return

    # --- Per-meet summary table ---
    print(f"\n{'=' * 80}")
    print("RESULTS: Per-Meet DNS Prediction Accuracy")
    print(f"{'=' * 80}")

    headers = [
        "Meet",
        "Seeded",
        "DNS(act)",
        "DNS(pred)",
        "Rate(act)",
        "Rate(pred)",
        "MAE",
        "Bias",
    ]
    rows = []
    for r in results:
        rows.append(
            [
                r["meet_name"][:30],
                str(r["total_seeded"]),
                str(r["total_actual_dns"]),
                f"{r['total_predicted_dns']:.0f}",
                f"{r['actual_global_rate'] * 100:.1f}%",
                f"{r['predicted_global_rate'] * 100:.1f}%",
                f"{r['mae'] * 100:.1f}%",
                f"{r['bias'] * 100:+.1f}%",
            ]
        )
    print_table(headers, rows)

    # --- Aggregate per-event accuracy ---
    print(f"\n{'=' * 80}")
    print("AGGREGATE: Per-Event DNS Accuracy Across All Meets")
    print(f"{'=' * 80}")

    # Pool all per-event observations
    event_pool: dict[str, list[dict]] = defaultdict(list)
    for r in results:
        for ev in r["per_event"]:
            event_pool[ev["event"]].append(ev)

    headers2 = ["Event", "N Meets", "Pred Rate", "Mean Actual", "MAE", "Bias"]
    rows2 = []
    for event_name in sorted(STANDARD_EVENTS):
        observations = event_pool.get(event_name, [])
        if not observations:
            continue
        pred = DNS_RATES.get(event_name, DEFAULT_DNS_RATE)
        actual_rates = [o["actual_rate"] for o in observations]
        mean_actual = sum(actual_rates) / len(actual_rates)
        residuals = [o["residual"] for o in observations]
        mae = sum(abs(r) for r in residuals) / len(residuals)
        bias = sum(residuals) / len(residuals)

        rows2.append(
            [
                event_name,
                str(len(observations)),
                f"{pred * 100:.1f}%",
                f"{mean_actual * 100:.1f}%",
                f"{mae * 100:.1f}%",
                f"{bias * 100:+.1f}%",
            ]
        )
    print_table(headers2, rows2)

    # --- Verdict ---
    mean_mae = sum(r["mae"] for r in results) / len(results)
    mean_bias = sum(r["bias"] for r in results) / len(results)
    total_dns_all = sum(r["total_actual_dns"] for r in results)
    total_pred_all = sum(r["total_predicted_dns"] for r in results)
    total_seeded_all = sum(r["total_seeded"] for r in results)

    print(f"\n{'=' * 80}")
    print("VERDICT")
    print(f"{'=' * 80}")
    print(f"  Meets tested:          {len(results)}")
    print(f"  Total seeded entries:  {total_seeded_all}")
    print(
        f"  Total actual DNS:      {total_dns_all} ({total_dns_all / total_seeded_all * 100:.1f}%)"
    )
    print(
        f"  Total predicted DNS:   {total_pred_all:.0f} ({total_pred_all / total_seeded_all * 100:.1f}%)"
    )
    print(f"  Mean per-meet MAE:     {mean_mae * 100:.1f}%")
    print(f"  Mean per-meet Bias:    {mean_bias * 100:+.1f}%")

    dns_count_error = abs(total_dns_all - total_pred_all)
    print(
        f"\n  DNS count error:       {dns_count_error:.0f} swimmers "
        f"({dns_count_error / total_seeded_all * 100:.1f}% of entries)"
    )

    if mean_mae < 0.05:
        accuracy_verdict = "EXCELLENT (MAE < 5%)"
    elif mean_mae < 0.10:
        accuracy_verdict = "GOOD (MAE < 10%)"
    elif mean_mae < 0.20:
        accuracy_verdict = "FAIR (MAE < 20%)"
    else:
        accuracy_verdict = "POOR (MAE >= 20%)"

    bias_direction = "over-predicts" if mean_bias > 0 else "under-predicts"
    print(f"\n  ACCURACY: {accuracy_verdict}")
    print(
        f"  BIAS: Model {bias_direction} DNS by {abs(mean_bias) * 100:.1f}% on average"
    )

    # --- Save ---
    out_path = ensure_output_dir() / "dns_actual_results.json"
    output: dict[str, Any] = {
        "results": [{k: v for k, v in r.items() if k != "per_event"} for r in results],
        "per_event_aggregate": {
            event: {
                "n_meets": len(obs),
                "predicted_rate": DNS_RATES.get(event, DEFAULT_DNS_RATE),
                "mean_actual_rate": sum(o["actual_rate"] for o in obs) / len(obs),
                "mae": sum(abs(o["residual"]) for o in obs) / len(obs),
                "bias": sum(o["residual"] for o in obs) / len(obs),
            }
            for event, obs in event_pool.items()
        },
        "summary": {
            "n_meets": len(results),
            "total_seeded": total_seeded_all,
            "total_actual_dns": total_dns_all,
            "total_predicted_dns": round(total_pred_all, 1),
            "mean_mae": round(mean_mae, 4),
            "mean_bias": round(mean_bias, 4),
            "accuracy_verdict": accuracy_verdict,
        },
    }
    with open(out_path, "w") as f:
        json.dump(output, f, indent=2)
    print(f"\n  Saved: {out_path}")


if __name__ == "__main__":
    main()
