#!/usr/bin/env python3
"""
Experiment 2: Predicted vs Actual DNS Rate Calibration

For each meet in the MDB database:
  1. Count actual DNS entries per event
  2. Compare to the model's predicted rate (DNS_RATES from attrition_model.py)
  3. Compute calibration metrics: MAE, bias, per-event residuals
  4. Stratify by meet type (championship vs dual vs other)

Key question: The model uses GLOBAL rates (all meet types) but is only
applied to CHAMPIONSHIP meets. Are championship DNS patterns different?
"""

import json
import statistics
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.attrition_validation_utils import (
    compute_per_meet_event_dns_rates,
    ensure_output_dir,
    load_all_mdb_stats,
    print_table,
)
from swim_ai_reflex.backend.core.attrition_model import (
    DEFAULT_DNS_RATE,
    DNS_RATES,
    STANDARD_EVENTS,
)


def compute_calibration_metrics(
    per_meet_rates: list[dict[str, Any]],
    predicted_rates: dict[str, float],
    default_rate: float,
    meet_type_filter: str | None = None,
) -> dict[str, Any]:
    """Compare predicted rates to observed per-event rates across meets.

    Args:
        per_meet_rates: Output from compute_per_meet_event_dns_rates()
        predicted_rates: DNS_RATES dict from attrition_model.py
        default_rate: DEFAULT_DNS_RATE for events not in the rates dict
        meet_type_filter: If set, only include meets of this type

    Returns dict with:
        per_event: {event: {predicted, observed_mean, observed_std, residual, mae, n_meets, n_entries}}
        global_mae: float (entry-weighted)
        global_bias: float (positive = model over-predicts DNS)
        n_meets: int
    """
    # Accumulate observed rates per event: list of (rate, n_entries_in_that_meet)
    event_observations: dict[str, list[tuple[float, int]]] = {}
    for event in STANDARD_EVENTS:
        event_observations[event] = []

    for meet in per_meet_rates:
        if meet_type_filter and meet["meet_type"] != meet_type_filter:
            continue
        for event_name, obs in meet["events"].items():
            if event_name not in STANDARD_EVENTS:
                continue
            if obs["total"] >= 5:  # Minimum entries per event per meet
                event_observations[event_name].append((obs["rate"], obs["total"]))

    per_event: dict[str, dict[str, Any]] = {}
    all_residuals: list[tuple[float, int]] = []  # (residual, weight)

    for event_name in sorted(STANDARD_EVENTS):
        obs_list = event_observations.get(event_name, [])
        if not obs_list:
            continue

        predicted = predicted_rates.get(event_name, default_rate)

        # Weighted mean observed rate (by number of entries)
        total_entries = sum(n for _, n in obs_list)
        weighted_sum = sum(rate * n for rate, n in obs_list)
        observed_mean = weighted_sum / total_entries if total_entries > 0 else 0

        # Standard deviation of per-meet rates (unweighted, for variability)
        rates_only = [r for r, _ in obs_list]
        observed_std = statistics.stdev(rates_only) if len(rates_only) > 1 else 0.0

        residual = predicted - observed_mean  # positive = overprediction
        mae = abs(residual)

        per_event[event_name] = {
            "predicted": round(predicted, 5),
            "observed_mean": round(observed_mean, 5),
            "observed_std": round(observed_std, 5),
            "residual": round(residual, 5),
            "mae": round(mae, 5),
            "n_meets": len(obs_list),
            "n_entries": total_entries,
        }

        all_residuals.append((residual, total_entries))

    # Global metrics (entry-weighted)
    total_weight = sum(w for _, w in all_residuals)
    global_mae = (
        sum(abs(r) * w for r, w in all_residuals) / total_weight
        if total_weight > 0
        else 0
    )
    global_bias = (
        sum(r * w for r, w in all_residuals) / total_weight if total_weight > 0 else 0
    )

    meet_count = len(
        [
            m
            for m in per_meet_rates
            if not meet_type_filter or m["meet_type"] == meet_type_filter
        ]
    )

    return {
        "per_event": per_event,
        "global_mae": round(global_mae, 5),
        "global_bias": round(global_bias, 5),
        "n_meets": meet_count,
    }


def _print_calibration(cal: dict[str, Any]) -> None:
    """Print a calibration result as a readable table."""
    headers = ["Event", "Predicted", "Observed", "StdDev", "Residual", "MAE", "N"]
    rows = []
    for event, info in sorted(cal["per_event"].items()):
        rows.append(
            [
                event,
                f"{info['predicted'] * 100:.2f}%",
                f"{info['observed_mean'] * 100:.2f}%",
                f"{info['observed_std'] * 100:.2f}%",
                f"{info['residual'] * 100:+.2f}%",
                f"{info['mae'] * 100:.2f}%",
                str(info["n_entries"]),
            ]
        )
    print_table(headers, rows)
    bias_direction = (
        "(over-predicts DNS)" if cal["global_bias"] > 0 else "(under-predicts DNS)"
    )
    print(f"\n  Global MAE:  {cal['global_mae'] * 100:.3f}%")
    print(f"  Global Bias: {cal['global_bias'] * 100:+.3f}% {bias_direction}")


def main() -> None:
    print("=" * 80)
    print("EXPERIMENT 2: Predicted vs Actual DNS Rate Calibration")
    print("=" * 80)

    print("\nLoading all MDB databases...")
    all_stats = load_all_mdb_stats()
    if not all_stats:
        print("No data loaded. Exiting.")
        return

    per_meet_rates = compute_per_meet_event_dns_rates(all_stats)

    # --- All meets ---
    print(f"\n{'=' * 70}")
    print("ALL MEETS (Global Calibration)")
    print(f"{'=' * 70}")
    cal_all = compute_calibration_metrics(per_meet_rates, DNS_RATES, DEFAULT_DNS_RATE)
    _print_calibration(cal_all)

    # --- By meet type ---
    for meet_type in ["championship", "dual", "other"]:
        count = sum(1 for m in per_meet_rates if m["meet_type"] == meet_type)
        if count < 3:
            continue
        print(f"\n{'=' * 70}")
        print(f"MEET TYPE: {meet_type.upper()} ({count} meets)")
        print(f"{'=' * 70}")
        cal = compute_calibration_metrics(
            per_meet_rates,
            DNS_RATES,
            DEFAULT_DNS_RATE,
            meet_type_filter=meet_type,
        )
        _print_calibration(cal)

    # --- Critical comparison: championship-only vs global ---
    print(f"\n{'=' * 70}")
    print("CRITICAL: Championship-Only vs Global Rates")
    print("(Model uses global rates but is only applied at championships)")
    print(f"{'=' * 70}")

    cal_champ = compute_calibration_metrics(
        per_meet_rates,
        DNS_RATES,
        DEFAULT_DNS_RATE,
        meet_type_filter="championship",
    )

    headers = ["Event", "Model Rate", "Champ Observed", "Residual", "N meets"]
    rows = []
    for event in sorted(STANDARD_EVENTS):
        if event not in cal_champ["per_event"]:
            continue
        info = cal_champ["per_event"][event]
        rows.append(
            [
                event,
                f"{info['predicted'] * 100:.2f}%",
                f"{info['observed_mean'] * 100:.2f}%",
                f"{info['residual'] * 100:+.2f}%",
                str(info["n_meets"]),
            ]
        )
    print_table(headers, rows)
    print(f"\n  Championship-only MAE:  {cal_champ['global_mae'] * 100:.3f}%")
    print(f"  Championship-only Bias: {cal_champ['global_bias'] * 100:+.3f}%")

    if abs(cal_champ["global_bias"]) > 0.02:
        print(
            "\n  WARNING: Model bias exceeds 2% for championships."
            " Consider using championship-specific rates."
        )
    else:
        print("\n  Model is well-calibrated for championships (bias < 2%).")

    # --- Save ---
    out_path = ensure_output_dir() / "calibration_results.json"
    output: dict[str, Any] = {
        "all_meets": cal_all,
        "championship_only": cal_champ,
        "by_meet_type": {},
    }
    for mt in ["championship", "dual", "other"]:
        cal = compute_calibration_metrics(
            per_meet_rates,
            DNS_RATES,
            DEFAULT_DNS_RATE,
            meet_type_filter=mt,
        )
        output["by_meet_type"][mt] = cal

    with open(out_path, "w") as f:
        json.dump(output, f, indent=2)
    print(f"\nSaved: {out_path}")


if __name__ == "__main__":
    main()
