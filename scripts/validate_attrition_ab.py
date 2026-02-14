#!/usr/bin/env python3
"""
Experiment 1: A/B Backtest — Attrition ON vs OFF

For each championship meet in CHAMPIONSHIP_MEETS:
  1. Run ChampionshipGurobiStrategy with attrition=ATTRITION_RATES -> lineup_ON
  2. Run ChampionshipGurobiStrategy with attrition=disabled() -> lineup_OFF
  3. Score BOTH lineups with undiscounted PointProjectionService (fair comparison)
  4. Score coach's actual lineup the same way
  5. Compare: net_effect = score_ON - score_OFF

Key question: Does attrition-aware optimization produce better or worse
lineups than attrition-blind optimization, when scored by the same method?
"""

import json
import os
import sys
import traceback
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.attrition_validation_utils import ensure_output_dir, print_table

# Reuse infrastructure from championship_backtest.py
from scripts.championship_backtest import (
    CHAMPIONSHIP_MEETS,
    DB_PATH,
    load_mdb_championship_data,
)
from swim_ai_reflex.backend.core.attrition_model import (
    ATTRITION_RATES,
    AttritionRates,
)
from swim_ai_reflex.backend.core.strategies.championship_strategy import (
    ChampionshipEntry,
    ChampionshipGurobiStrategy,
    ChampionshipOptimizationResult,
)
from swim_ai_reflex.backend.services.championship.projection import (
    PointProjectionService,
)
from swim_ai_reflex.backend.utils.mdb_connector import MDBConnector

# Seton appears as various names in MDB data; match case-insensitively
SETON_KEYWORDS = ["seton"]


def _find_seton_team_name(entries: list[dict]) -> str:
    """Find the actual team name string used for Seton in this meet's data."""
    for e in entries:
        team = e.get("team", "")
        if any(kw in team.lower() for kw in SETON_KEYWORDS):
            return team
    return "Seton Swimming"  # fallback


def _get_seton_score(result: Any) -> float:
    """Extract Seton's score from a StandingsProjection, case-insensitive."""
    for team_name, pts in result.team_totals.items():
        if any(kw in team_name.lower() for kw in SETON_KEYWORDS):
            return pts
    return 0.0


def run_optimizer(
    entries: list[dict],
    target_team: str,
    profile: str,
    attrition: AttritionRates,
) -> ChampionshipOptimizationResult:
    """Run ChampionshipGurobiStrategy with specified attrition setting."""
    champ_entries = [
        ChampionshipEntry(
            swimmer_name=e.get("swimmer_name", e.get("swimmer", "")),
            team=e.get("team", ""),
            event=e.get("event", ""),
            seed_time=e.get("seed_time", float("inf")),
            gender=e.get("gender", ""),
        )
        for e in entries
    ]

    strategy = ChampionshipGurobiStrategy(
        meet_profile=profile,
        attrition=attrition,
    )
    return strategy.optimize_entries(
        all_entries=champ_entries,
        target_team=target_team,
        time_limit=30,  # Faster solve for backtesting
    )


def score_lineup_undiscounted(
    assignments: dict[str, list[str]],
    all_entries: list[dict],
    target_team: str,
    profile: str,
) -> float:
    """Score a lineup using PointProjectionService with attrition DISABLED.

    Reconstructs entries list with only assigned swimmers from target_team
    plus all opponent entries. This ensures fair comparison — both lineups
    scored identically, only assignment decisions differ.
    """
    # Build set of assigned (swimmer, event) pairs
    assigned_set: set[tuple[str, str]] = set()
    for swimmer, events in assignments.items():
        for event in events:
            assigned_set.add((swimmer, event))

    # Keep opponents as-is, filter target team to only assigned entries
    scored_entries = []
    for e in all_entries:
        swimmer = e.get("swimmer_name", e.get("swimmer", ""))
        team = e.get("team", "")
        event = e.get("event", "")

        if any(kw in team.lower() for kw in SETON_KEYWORDS):
            if (swimmer, event) in assigned_set:
                scored_entries.append(e)
        else:
            scored_entries.append(e)

    svc = PointProjectionService(
        meet_profile=profile,
        attrition=AttritionRates.disabled(),
    )
    result = svc.project_standings(scored_entries, target_team=target_team)
    return _get_seton_score(result)


def score_coach_baseline(
    all_entries: list[dict],
    target_team: str,
    profile: str,
) -> float:
    """Score the coach's actual lineup (all entries as-is) with no attrition."""
    svc = PointProjectionService(
        meet_profile=profile,
        attrition=AttritionRates.disabled(),
    )
    result = svc.project_standings(all_entries, target_team=target_team)
    return _get_seton_score(result)


def run_ab_test_single_meet(
    meet_id: int, meet_name: str, profile: str
) -> dict[str, Any] | None:
    """Run A/B comparison for a single meet."""
    try:
        connector = MDBConnector(DB_PATH)
        entries, _team_map, _meet_meta = load_mdb_championship_data(connector, meet_id)

        if not entries:
            return None

        target_team = _find_seton_team_name(entries)

        # Check if Seton has any entries
        seton_entries = [
            e
            for e in entries
            if any(kw in e.get("team", "").lower() for kw in SETON_KEYWORDS)
        ]
        if not seton_entries:
            return None

        # Score coach baseline (all entries, no discount)
        coach_score = score_coach_baseline(entries, target_team, profile)

        # Run optimizer WITH attrition
        result_on = run_optimizer(entries, target_team, profile, ATTRITION_RATES)

        # Run optimizer WITHOUT attrition
        result_off = run_optimizer(
            entries, target_team, profile, AttritionRates.disabled()
        )

        # Score both lineups undiscounted (fair comparison)
        score_on = 0.0
        score_off = 0.0

        if result_on.assignments:
            score_on = score_lineup_undiscounted(
                result_on.assignments, entries, target_team, profile
            )
        if result_off.assignments:
            score_off = score_lineup_undiscounted(
                result_off.assignments, entries, target_team, profile
            )

        # Check if lineups actually differ
        assignments_differ = result_on.assignments != result_off.assignments

        return {
            "meet_id": meet_id,
            "meet_name": meet_name,
            "profile": profile,
            "coach_score": round(coach_score, 1),
            "optimizer_attrition_on": round(score_on, 1),
            "optimizer_attrition_off": round(score_off, 1),
            "delta_on": round(score_on - coach_score, 1),
            "delta_off": round(score_off - coach_score, 1),
            "net_effect": round(score_on - score_off, 1),
            "assignments_differ": assignments_differ,
            "on_status": result_on.status,
            "off_status": result_off.status,
            "on_n_swimmers": len(result_on.assignments),
            "off_n_swimmers": len(result_off.assignments),
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
    print("EXPERIMENT 1: A/B Backtest — Attrition ON vs OFF")
    print("=" * 80)
    print(f"\nDatabase: {DB_PATH}")
    print(f"Meets to test: {len(CHAMPIONSHIP_MEETS)}")
    print(
        f"Model DNS rates: {len(ATTRITION_RATES.dns_rates)} events, "
        f"default={ATTRITION_RATES.default_dns * 100:.1f}%"
    )

    results: list[dict[str, Any]] = []

    for meet_id, meet_name, profile in CHAMPIONSHIP_MEETS:
        short_name = meet_name[:40]
        print(f"\n  [{meet_id}] {short_name}...", end=" ", flush=True)
        r = run_ab_test_single_meet(meet_id, meet_name, profile)
        if r:
            differ_flag = "DIFFER" if r["assignments_differ"] else "same"
            print(
                f"net={r['net_effect']:+.1f}  "
                f"[{differ_flag}]  "
                f"on={r['on_status']} off={r['off_status']}"
            )
            results.append(r)
        else:
            print("SKIPPED (no data or no Seton entries)")

    if not results:
        print("\nNo valid results. Check DB_PATH and meet data.")
        return

    # --- Results table ---
    print(f"\n{'=' * 80}")
    print("RESULTS")
    print(f"{'=' * 80}")

    headers = [
        "Meet",
        "Coach",
        "Opt+Att",
        "Opt-Att",
        "Delta+",
        "Delta-",
        "Net",
        "Differ?",
    ]
    rows = []
    for r in results:
        rows.append(
            [
                r["meet_name"][:28],
                f"{r['coach_score']:.0f}",
                f"{r['optimizer_attrition_on']:.0f}",
                f"{r['optimizer_attrition_off']:.0f}",
                f"{r['delta_on']:+.0f}",
                f"{r['delta_off']:+.0f}",
                f"{r['net_effect']:+.1f}",
                "YES" if r["assignments_differ"] else "no",
            ]
        )
    print_table(headers, rows)

    # --- Verdict ---
    net_effects = [r["net_effect"] for r in results]
    differ_count = sum(1 for r in results if r["assignments_differ"])
    helps = sum(1 for n in net_effects if n > 0.5)
    hurts = sum(1 for n in net_effects if n < -0.5)
    neutral = len(net_effects) - helps - hurts

    mean_net = sum(net_effects) / len(net_effects)
    sorted_nets = sorted(net_effects)
    median_net = sorted_nets[len(sorted_nets) // 2]

    print(f"\n{'=' * 80}")
    print("VERDICT")
    print(f"{'=' * 80}")
    print(f"  Meets tested:               {len(results)}")
    print(f"  Meets where lineups differ:  {differ_count}")
    print(f"  Mean net effect:             {mean_net:+.2f} pts")
    print(f"  Median net effect:           {median_net:+.2f} pts")
    print(f"  Attrition helps in:          {helps} meets")
    print(f"  Attrition hurts in:          {hurts} meets")
    print(f"  No meaningful difference:    {neutral} meets")

    if mean_net > 1.0:
        conclusion = (
            f"Attrition HELPS optimizer by ~{mean_net:.1f} pts/meet on average."
        )
    elif mean_net < -1.0:
        conclusion = (
            f"Attrition HURTS optimizer by ~{abs(mean_net):.1f} pts/meet on average."
            " Consider disabling for VCAC."
        )
    else:
        conclusion = (
            f"Attrition has NEGLIGIBLE effect ({mean_net:+.1f} pts/meet)."
            " Assignments rarely change."
        )
    print(f"\n  CONCLUSION: {conclusion}")

    # --- Save ---
    out_path = ensure_output_dir() / "ab_results.json"
    output = {
        "results": results,
        "summary": {
            "n_meets": len(results),
            "n_differ": differ_count,
            "mean_net": round(mean_net, 2),
            "median_net": round(median_net, 2),
            "helps": helps,
            "hurts": hurts,
            "neutral": neutral,
            "conclusion": conclusion,
        },
    }
    with open(out_path, "w") as f:
        json.dump(output, f, indent=2)
    print(f"\n  Saved: {out_path}")


if __name__ == "__main__":
    main()
