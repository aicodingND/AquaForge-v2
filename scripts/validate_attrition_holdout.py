#!/usr/bin/env python3
"""
Experiment 3: Holdout Cross-Validation of DNS Rates

Split meets into 5 folds (stratified by meet type).
For each fold:
  1. Compute DNS rates from train-only meets (80%)
  2. Evaluate predictions on test meets (20%)
  3. Report train rates vs test rates stability

Key question: Are the DNS rates overfit to the full dataset, or do they
generalize to held-out meets?
"""

import json
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.attrition_validation_utils import (
    build_rates_from_stats,
    compute_default_dns_from_stats,
    compute_per_meet_event_dns_rates,
    ensure_output_dir,
    load_all_mdb_stats,
    print_table,
)
from scripts.validate_attrition_calibration import compute_calibration_metrics
from swim_ai_reflex.backend.core.attrition_model import (
    DEFAULT_DNS_RATE,
    DNS_RATES,
    STANDARD_EVENTS,
)


def stratified_kfold_split(
    all_stats: list[dict],
    k: int = 5,
    seed: int = 42,
) -> list[tuple[list[dict], list[dict]]]:
    """Split meets into k folds, stratified by meet_type.

    Returns list of (train_stats, test_stats) tuples.
    """
    rng = random.Random(seed)

    # Group by meet type
    by_type: dict[str, list[int]] = defaultdict(list)
    for i, stats in enumerate(all_stats):
        by_type[stats["meet_type"]].append(i)

    # Shuffle each group
    for mt in by_type:
        rng.shuffle(by_type[mt])

    # Assign fold indices within each stratum
    fold_assignments: dict[int, int] = {}
    for indices in by_type.values():
        for pos, idx in enumerate(indices):
            fold_assignments[idx] = pos % k

    # Build train/test splits
    splits = []
    for fold in range(k):
        test = [all_stats[i] for i, f in fold_assignments.items() if f == fold]
        train = [all_stats[i] for i, f in fold_assignments.items() if f != fold]
        splits.append((train, test))

    return splits


def evaluate_fold(
    train_stats: list[dict],
    test_stats: list[dict],
    fold_idx: int,
) -> dict[str, Any]:
    """Evaluate one fold: train rates from train set, test on test set."""
    # Compute train rates
    train_rates = build_rates_from_stats(train_stats)
    train_default = compute_default_dns_from_stats(train_stats)

    # Evaluate on test set
    test_per_meet = compute_per_meet_event_dns_rates(test_stats)
    cal = compute_calibration_metrics(test_per_meet, train_rates, train_default)

    return {
        "fold": fold_idx,
        "train_size": len(train_stats),
        "test_size": len(test_stats),
        "train_rates": {k: round(v, 5) for k, v in sorted(train_rates.items())},
        "train_default": round(train_default, 5),
        "test_mae": cal["global_mae"],
        "test_bias": cal["global_bias"],
        "per_event": cal["per_event"],
    }


def _std(values: list[float]) -> float:
    """Sample standard deviation."""
    if len(values) < 2:
        return 0.0
    mean = sum(values) / len(values)
    return (sum((v - mean) ** 2 for v in values) / (len(values) - 1)) ** 0.5


def main() -> None:
    K = 5
    SEED = 42

    print("=" * 80)
    print(f"EXPERIMENT 3: {K}-Fold Cross-Validation of DNS Rates")
    print("=" * 80)

    print("\nLoading all MDB databases...")
    all_stats = load_all_mdb_stats()
    if not all_stats:
        print("No data loaded. Exiting.")
        return

    type_counts = Counter(s["meet_type"] for s in all_stats)
    print(f"Meet types: {dict(type_counts)}")

    # --- K-fold cross-validation ---
    splits = stratified_kfold_split(all_stats, k=K, seed=SEED)

    fold_results = []
    for fold_idx, (train, test) in enumerate(splits):
        print(
            f"\n--- Fold {fold_idx + 1}/{K} (train={len(train)}, test={len(test)}) ---"
        )
        result = evaluate_fold(train, test, fold_idx)
        fold_results.append(result)
        print(
            f"  MAE: {result['test_mae'] * 100:.3f}%  "
            f"Bias: {result['test_bias'] * 100:+.3f}%"
        )

    # --- Summary ---
    maes = [r["test_mae"] for r in fold_results]
    biases = [r["test_bias"] for r in fold_results]

    print(f"\n{'=' * 80}")
    print("CROSS-VALIDATION SUMMARY")
    print(f"{'=' * 80}")
    print(f"  Mean MAE across folds:  {sum(maes) / len(maes) * 100:.3f}%")
    print(f"  Std MAE across folds:   {_std(maes) * 100:.3f}%")
    print(f"  Mean Bias across folds: {sum(biases) / len(biases) * 100:+.3f}%")
    print(f"  Std Bias across folds:  {_std(biases) * 100:.3f}%")

    overfit_threshold = 0.02  # 2%
    if _std(maes) > overfit_threshold:
        print(
            f"\n  WARNING: High MAE variance ({_std(maes) * 100:.3f}%) suggests overfitting."
        )
    else:
        print(
            f"\n  Rates are STABLE across folds (MAE std < {overfit_threshold * 100:.0f}%)."
        )

    # --- Rate stability table ---
    print(f"\n{'=' * 70}")
    print("RATE STABILITY: Per-Event Train Rate Range Across Folds")
    print(f"{'=' * 70}")

    event_train_rates: dict[str, list[float]] = defaultdict(list)
    for r in fold_results:
        for event, rate in r["train_rates"].items():
            event_train_rates[event].append(rate)

    headers = ["Event", "Full Rate", "Min Train", "Max Train", "Range", "Stable?"]
    rows = []
    for event in sorted(STANDARD_EVENTS):
        if event not in event_train_rates:
            continue
        train_vals = event_train_rates[event]
        full_rate = DNS_RATES.get(event, DEFAULT_DNS_RATE)
        min_r = min(train_vals)
        max_r = max(train_vals)
        range_r = max_r - min_r
        if range_r < 0.02:
            stability = "YES"
        elif range_r > 0.05:
            stability = "UNSTABLE"
        else:
            stability = "ok"
        rows.append(
            [
                event,
                f"{full_rate * 100:.2f}%",
                f"{min_r * 100:.2f}%",
                f"{max_r * 100:.2f}%",
                f"{range_r * 100:.2f}%",
                stability,
            ]
        )
    print_table(headers, rows)

    # --- Championship-only cross-validation ---
    print(f"\n{'=' * 70}")
    print("BONUS: Championship-Only Meets Cross-Validation")
    print(f"{'=' * 70}")

    champ_stats = [s for s in all_stats if s["meet_type"] == "championship"]
    print(f"  Championship meets: {len(champ_stats)}")

    champ_k = min(K, max(2, len(champ_stats) // 4))
    if len(champ_stats) >= champ_k * 2:
        champ_splits = stratified_kfold_split(champ_stats, k=champ_k, seed=SEED)
        champ_results = []
        for fold_idx, (train, test) in enumerate(champ_splits):
            result = evaluate_fold(train, test, fold_idx)
            champ_results.append(result)

        champ_maes = [r["test_mae"] for r in champ_results]
        mean_champ_mae = sum(champ_maes) / len(champ_maes)
        mean_all_mae = sum(maes) / len(maes)

        print(f"  Mean MAE (champ-only):  {mean_champ_mae * 100:.3f}%")
        print(f"  Mean MAE (all meets):   {mean_all_mae * 100:.3f}%")

        if mean_champ_mae < mean_all_mae * 0.9:
            print(
                "  --> Championship-only rates are BETTER calibrated."
                " Consider using championship-specific rates."
            )
        elif mean_champ_mae > mean_all_mae * 1.1:
            print(
                "  --> Global rates are BETTER than championship-only."
                " Larger training set helps."
            )
        else:
            print("  --> No significant difference. Global rates are fine.")
    else:
        print(
            f"  Too few championship meets ({len(champ_stats)}) "
            f"for {champ_k}-fold cross-validation."
        )

    # --- Save ---
    out_path = ensure_output_dir() / "holdout_results.json"
    output: dict[str, Any] = {
        "k": K,
        "seed": SEED,
        "n_meets": len(all_stats),
        "fold_results": [
            {k: v for k, v in r.items() if k != "per_event"} for r in fold_results
        ],
        "summary": {
            "mean_mae": round(sum(maes) / len(maes), 5),
            "std_mae": round(_std(maes), 5),
            "mean_bias": round(sum(biases) / len(biases), 5),
            "std_bias": round(_std(biases), 5),
        },
    }
    with open(out_path, "w") as f:
        json.dump(output, f, indent=2)
    print(f"\nSaved: {out_path}")


if __name__ == "__main__":
    main()
