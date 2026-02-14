#!/usr/bin/env python3
"""
Experiment 4: Outcome Backtest — Does Attrition Improve Score Predictions?

For each championship meet with actual results in the MDB:
  1. Project team standings with attrition DISABLED (raw seed-time scoring)
  2. Project team standings with attrition ENABLED (completion-factor discounted)
  3. Compare both predictions against ACTUAL recorded standings
  4. Measure: which prediction is closer to reality?

Key question: Does attrition-adjusted scoring produce better predictions of
real meet outcomes, or does it introduce systematic bias?

This is the MISSING validation — we proved the model is calibrated (DNS rates
are accurate) and that it doesn't change lineup decisions (A/B test), but we
never checked whether it improves the *accuracy of score predictions*.

Metrics:
  - MAE(predicted, actual) for each team, each meet
  - Rank correlation (Spearman) between predicted and actual standings
  - Delta for Seton specifically (the +112pt question)
"""

import json
import os
import sys
import traceback
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.attrition_validation_utils import ensure_output_dir, print_table
from scripts.championship_backtest import (
    CHAMPIONSHIP_MEETS,
    DB_PATH,
    get_actual_team_standings,
    load_mdb_championship_data,
)
from swim_ai_reflex.backend.core.attrition_model import (
    ATTRITION_RATES,
    AttritionRates,
)
from swim_ai_reflex.backend.services.championship.projection import (
    PointProjectionService,
)
from swim_ai_reflex.backend.utils.mdb_connector import MDBConnector

SETON_KEYWORDS = ["seton"]


def _find_seton_score(standings: dict[str, float]) -> float:
    """Find Seton's score in a standings dict (case-insensitive)."""
    for team, pts in standings.items():
        if any(kw in team.lower() for kw in SETON_KEYWORDS):
            return pts
    return 0.0


def _normalize_team_name(name: str) -> str:
    """Normalize team name for matching across data sources."""
    return name.strip().lower().replace("swimming", "").replace("  ", " ").strip()


def _match_standings(
    predicted: dict[str, float], actual: dict[str, float]
) -> list[tuple[str, float, float]]:
    """Match teams between predicted and actual using fuzzy name matching.

    Returns list of (team_name, predicted_pts, actual_pts) for matched teams.
    """
    # Build normalized lookup for actual
    actual_norm: dict[str, tuple[str, float]] = {}
    for name, pts in actual.items():
        norm = _normalize_team_name(name)
        actual_norm[norm] = (name, pts)

    matched = []
    for pred_name, pred_pts in predicted.items():
        norm = _normalize_team_name(pred_name)
        if norm in actual_norm:
            _, act_pts = actual_norm[norm]
            matched.append((pred_name, pred_pts, act_pts))
        else:
            # Try substring matching
            for act_norm, (act_name, act_pts) in actual_norm.items():
                if norm in act_norm or act_norm in norm:
                    matched.append((pred_name, pred_pts, act_pts))
                    break

    return matched


def _compute_standings_mae(
    predicted: dict[str, float], actual: dict[str, float]
) -> float:
    """Mean absolute error between predicted and actual team standings."""
    matched = _match_standings(predicted, actual)
    if not matched:
        return float("inf")
    errors = [abs(pred - act) for _, pred, act in matched]
    return sum(errors) / len(errors)


def _compute_rank_correlation(
    predicted: dict[str, float], actual: dict[str, float]
) -> float:
    """Spearman rank correlation between predicted and actual standings."""
    matched = _match_standings(predicted, actual)
    if len(matched) < 3:
        return float("nan")

    # Assign ranks (highest score = rank 1)
    by_pred = sorted(matched, key=lambda x: -x[1])
    by_act = sorted(matched, key=lambda x: -x[2])

    pred_rank = {name: i + 1 for i, (name, _, _) in enumerate(by_pred)}
    act_rank = {name: i + 1 for i, (name, _, _) in enumerate(by_act)}

    n = len(matched)
    d_sq_sum = sum((pred_rank[name] - act_rank[name]) ** 2 for name, _, _ in matched)
    return 1 - (6 * d_sq_sum) / (n * (n**2 - 1))


def evaluate_meet(meet_id: int, meet_name: str, profile: str) -> dict[str, Any] | None:
    """Run outcome evaluation for a single meet."""
    try:
        connector = MDBConnector(DB_PATH)
        entries, team_map, _meta = load_mdb_championship_data(connector, meet_id)

        if not entries:
            return None

        # Get actual standings
        actual = get_actual_team_standings(connector, meet_id, team_map)
        if not actual:
            return None

        actual_seton = _find_seton_score(actual)

        # Find Seton team name in entries
        target_team = "Seton Swimming"
        for e in entries:
            if any(kw in e.get("team", "").lower() for kw in SETON_KEYWORDS):
                target_team = e["team"]
                break

        # Project WITH attrition
        svc_on = PointProjectionService(
            meet_profile=profile,
            attrition=ATTRITION_RATES,
        )
        proj_on = svc_on.project_standings(entries, target_team=target_team)
        pred_on = {t: pts for t, pts in proj_on.team_totals.items()}

        # Project WITHOUT attrition
        svc_off = PointProjectionService(
            meet_profile=profile,
            attrition=AttritionRates.disabled(),
        )
        proj_off = svc_off.project_standings(entries, target_team=target_team)
        pred_off = {t: pts for t, pts in proj_off.team_totals.items()}

        # Compute metrics
        mae_on = _compute_standings_mae(pred_on, actual)
        mae_off = _compute_standings_mae(pred_off, actual)
        rank_on = _compute_rank_correlation(pred_on, actual)
        rank_off = _compute_rank_correlation(pred_off, actual)

        seton_pred_on = _find_seton_score(pred_on)
        seton_pred_off = _find_seton_score(pred_off)
        seton_error_on = abs(seton_pred_on - actual_seton)
        seton_error_off = abs(seton_pred_off - actual_seton)

        return {
            "meet_id": meet_id,
            "meet_name": meet_name,
            "profile": profile,
            "n_teams": len(actual),
            # Actual
            "actual_seton": round(actual_seton, 1),
            # Attrition ON
            "pred_seton_on": round(seton_pred_on, 1),
            "seton_error_on": round(seton_error_on, 1),
            "mae_on": round(mae_on, 1),
            "rank_corr_on": round(rank_on, 3) if rank_on == rank_on else None,
            # Attrition OFF
            "pred_seton_off": round(seton_pred_off, 1),
            "seton_error_off": round(seton_error_off, 1),
            "mae_off": round(mae_off, 1),
            "rank_corr_off": round(rank_off, 3) if rank_off == rank_off else None,
            # Deltas
            "seton_error_delta": round(seton_error_on - seton_error_off, 1),
            "mae_delta": round(mae_on - mae_off, 1),
            "attrition_improves_seton": seton_error_on < seton_error_off,
            "attrition_improves_mae": mae_on < mae_off,
        }

    except Exception as e:
        print(f"\n  ERROR on meet {meet_id}: {e}")
        traceback.print_exc()
        return None


def main() -> None:
    if not os.path.exists(DB_PATH):
        print(f"MDB not found at {DB_PATH}")
        print("This script requires the SST HyTek database.")
        return

    print("=" * 80)
    print("EXPERIMENT 4: Outcome Backtest — Attrition vs Actual Scores")
    print("=" * 80)
    print(f"\nDatabase: {DB_PATH}")
    print(f"Meets to test: {len(CHAMPIONSHIP_MEETS)}")
    print(
        f"Model DNS rates: {len(ATTRITION_RATES.dns_rates)} events, "
        f"default={ATTRITION_RATES.default_dns * 100:.1f}%"
    )

    results: list[dict[str, Any]] = []

    for meet_id, meet_name, profile in CHAMPIONSHIP_MEETS:
        short_name = meet_name[:45]
        print(f"\n  [{meet_id}] {short_name}...", end=" ", flush=True)
        r = evaluate_meet(meet_id, meet_name, profile)
        if r:
            imp = "BETTER" if r["attrition_improves_seton"] else "worse"
            print(
                f"SST err: ON={r['seton_error_on']:.0f} OFF={r['seton_error_off']:.0f} "
                f"({imp})  MAE: ON={r['mae_on']:.0f} OFF={r['mae_off']:.0f}"
            )
            results.append(r)
        else:
            print("SKIPPED (no data or no actual standings)")

    if not results:
        print("\nNo valid results.")
        return

    # --- Results table ---
    print(f"\n{'=' * 80}")
    print("RESULTS: Seton Score Prediction Accuracy")
    print(f"{'=' * 80}")

    headers = [
        "Meet",
        "Actual",
        "Pred+Att",
        "Pred-Att",
        "Err+Att",
        "Err-Att",
        "Better?",
    ]
    rows = []
    for r in results:
        better = "YES" if r["attrition_improves_seton"] else "no"
        rows.append(
            [
                r["meet_name"][:30],
                f"{r['actual_seton']:.0f}",
                f"{r['pred_seton_on']:.0f}",
                f"{r['pred_seton_off']:.0f}",
                f"{r['seton_error_on']:.0f}",
                f"{r['seton_error_off']:.0f}",
                better,
            ]
        )
    print_table(headers, rows)

    # --- Standings MAE table ---
    print(f"\n{'=' * 80}")
    print("RESULTS: All-Team Standings MAE")
    print(f"{'=' * 80}")

    headers2 = ["Meet", "MAE+Att", "MAE-Att", "Rank+Att", "Rank-Att", "Better?"]
    rows2 = []
    for r in results:
        better = "YES" if r["attrition_improves_mae"] else "no"
        rc_on = f"{r['rank_corr_on']:.3f}" if r["rank_corr_on"] is not None else "n/a"
        rc_off = (
            f"{r['rank_corr_off']:.3f}" if r["rank_corr_off"] is not None else "n/a"
        )
        rows2.append(
            [
                r["meet_name"][:30],
                f"{r['mae_on']:.0f}",
                f"{r['mae_off']:.0f}",
                rc_on,
                rc_off,
                better,
            ]
        )
    print_table(headers2, rows2)

    # --- Verdict ---
    seton_helps = sum(1 for r in results if r["attrition_improves_seton"])
    seton_hurts = sum(1 for r in results if not r["attrition_improves_seton"])
    mae_helps = sum(1 for r in results if r["attrition_improves_mae"])
    mae_hurts = sum(1 for r in results if not r["attrition_improves_mae"])

    mean_err_on = sum(r["seton_error_on"] for r in results) / len(results)
    mean_err_off = sum(r["seton_error_off"] for r in results) / len(results)
    mean_mae_on = sum(r["mae_on"] for r in results) / len(results)
    mean_mae_off = sum(r["mae_off"] for r in results) / len(results)

    # Rank correlations (skip NaN)
    valid_rc = [r for r in results if r["rank_corr_on"] is not None]
    mean_rc_on = (
        sum(r["rank_corr_on"] for r in valid_rc) / len(valid_rc)
        if valid_rc
        else float("nan")
    )
    mean_rc_off = (
        sum(r["rank_corr_off"] for r in valid_rc) / len(valid_rc)
        if valid_rc
        else float("nan")
    )

    print(f"\n{'=' * 80}")
    print("VERDICT")
    print(f"{'=' * 80}")
    print(f"  Meets tested:                    {len(results)}")
    print("\n  SETON SCORE PREDICTION:")
    print(f"    Mean error (attrition ON):     {mean_err_on:.1f} pts")
    print(f"    Mean error (attrition OFF):    {mean_err_off:.1f} pts")
    print(f"    Attrition helps in:            {seton_helps}/{len(results)} meets")
    print(f"    Attrition hurts in:            {seton_hurts}/{len(results)} meets")

    print("\n  ALL-TEAM STANDINGS:")
    print(f"    Mean MAE (attrition ON):       {mean_mae_on:.1f} pts")
    print(f"    Mean MAE (attrition OFF):      {mean_mae_off:.1f} pts")
    print(f"    Mean rank corr (att ON):       {mean_rc_on:.3f}")
    print(f"    Mean rank corr (att OFF):      {mean_rc_off:.3f}")
    print(f"    Attrition helps MAE in:        {mae_helps}/{len(results)} meets")
    print(f"    Attrition hurts MAE in:        {mae_hurts}/{len(results)} meets")

    # Conclusion
    if mean_err_on < mean_err_off - 1.0:
        seton_conclusion = f"Attrition IMPROVES Seton prediction by ~{mean_err_off - mean_err_on:.1f} pts"
    elif mean_err_on > mean_err_off + 1.0:
        seton_conclusion = f"Attrition WORSENS Seton prediction by ~{mean_err_on - mean_err_off:.1f} pts"
    else:
        seton_conclusion = (
            "Attrition has NEGLIGIBLE effect on Seton prediction accuracy"
        )

    if mean_mae_on < mean_mae_off - 1.0:
        mae_conclusion = f"Attrition IMPROVES standings prediction by ~{mean_mae_off - mean_mae_on:.1f} pts MAE"
    elif mean_mae_on > mean_mae_off + 1.0:
        mae_conclusion = f"Attrition WORSENS standings prediction by ~{mean_mae_on - mean_mae_off:.1f} pts MAE"
    else:
        mae_conclusion = "Attrition has NEGLIGIBLE effect on standings MAE"

    print(f"\n  SETON CONCLUSION: {seton_conclusion}")
    print(f"  STANDINGS CONCLUSION: {mae_conclusion}")

    # --- +112pt delta measurement ---
    print(f"\n{'=' * 80}")
    print("+112pt DELTA IMPACT")
    print(f"{'=' * 80}")

    # For meet 512 specifically (the meet where +112 was measured)
    meet_512 = [r for r in results if r["meet_id"] == 512]
    if meet_512:
        m = meet_512[0]
        print(f"  Meet 512 ({m['meet_name']}):")
        print(f"    Actual Seton score:     {m['actual_seton']:.0f} pts")
        print(f"    Predicted (no att):     {m['pred_seton_off']:.0f} pts")
        print(f"    Predicted (with att):   {m['pred_seton_on']:.0f} pts")
        discount = m["pred_seton_off"] - m["pred_seton_on"]
        print(f"    Attrition discount:     {discount:+.0f} pts")
        print(f"    Prediction error (no att):   {m['seton_error_off']:.0f} pts")
        print(f"    Prediction error (with att): {m['seton_error_on']:.0f} pts")
    else:
        print("  Meet 512 not found in results.")

    # --- Save ---
    out_path = ensure_output_dir() / "outcome_results.json"
    output: dict[str, Any] = {
        "results": results,
        "summary": {
            "n_meets": len(results),
            "mean_seton_error_on": round(mean_err_on, 1),
            "mean_seton_error_off": round(mean_err_off, 1),
            "seton_helps": seton_helps,
            "seton_hurts": seton_hurts,
            "mean_mae_on": round(mean_mae_on, 1),
            "mean_mae_off": round(mean_mae_off, 1),
            "mean_rank_corr_on": round(mean_rc_on, 3)
            if mean_rc_on == mean_rc_on
            else None,
            "mean_rank_corr_off": round(mean_rc_off, 3)
            if mean_rc_off == mean_rc_off
            else None,
            "mae_helps": mae_helps,
            "mae_hurts": mae_hurts,
            "seton_conclusion": seton_conclusion,
            "mae_conclusion": mae_conclusion,
        },
    }
    with open(out_path, "w") as f:
        json.dump(output, f, indent=2)
    print(f"\n  Saved: {out_path}")


if __name__ == "__main__":
    main()
