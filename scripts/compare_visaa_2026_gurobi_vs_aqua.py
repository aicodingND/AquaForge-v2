#!/usr/bin/env python3
"""
VISAA 2026 Head-to-Head: Gurobi vs AquaOptimizer
=================================================
Runs both optimizers on the IDENTICAL 2026 VISAA psych sheet data
with the IDENTICAL VISAA championship scoring profile, then compares.

Data source: Same SETON_ENTRIES + OPPONENT_ENTRIES from run_visaa_optimizer.py
Scoring: VISAA 16-place championship (20-17-16-15-14-13-12-11-9-7-6-5-4-3-2-1)
"""

import json
import sys
import time
from pathlib import Path

# Add project root (must precede project imports)
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd  # noqa: E402

from scripts.run_visaa_optimizer import OPPONENT_ENTRIES, SETON_ENTRIES  # noqa: E402
from swim_ai_reflex.backend.core.strategies.aqua_optimizer import (  # noqa: E402
    AquaOptimizer,
    FatigueModel,
    ScoringEngine,
    ScoringProfile,
)
from swim_ai_reflex.backend.core.strategies.championship_strategy import (  # noqa: E402
    ChampionshipEntry,
    ChampionshipGurobiStrategy,
)

# Load supplemental opponent data scraped from SwimCloud (missing events)
_SUPPLEMENTAL_PATH = (
    PROJECT_ROOT / "data" / "swimcloud" / "visaa_2026_missing_opponents.json"
)
if _SUPPLEMENTAL_PATH.exists():
    with open(_SUPPLEMENTAL_PATH) as f:
        _supplemental = json.load(f)
    ALL_OPPONENT_ENTRIES = OPPONENT_ENTRIES + _supplemental
else:
    ALL_OPPONENT_ENTRIES = OPPONENT_ENTRIES

# Build swimmer→team lookup for multi-team scoring.
# Sources: supplemental JSON (has team field) + dedicated team lookup file.
_SWIMMER_TEAM: dict[str, str] = {}
_TEAM_LOOKUP_PATH = (
    PROJECT_ROOT / "data" / "swimcloud" / "visaa_2026_swimmer_teams.json"
)
# 1. From supplemental JSON
for _e in ALL_OPPONENT_ENTRIES:
    if "team" in _e and _e["team"]:
        _SWIMMER_TEAM[_e["swimmer"]] = _e["team"]
# 2. From dedicated team lookup (higher priority — scraped per-swimmer)
if _TEAM_LOOKUP_PATH.exists():
    with open(_TEAM_LOOKUP_PATH) as f:
        _SWIMMER_TEAM.update(json.load(f))


def _get_opponent_team(entry: dict) -> str:
    """Get real team name for an opponent entry.

    Falls back to swimmer name as a unique pseudo-team if no mapping exists.
    This ensures each unknown swimmer gets their own per-team cap (1 of 4),
    which is strictly better than pooling all unknowns together.
    """
    if "team" in entry and entry["team"]:
        return entry["team"]
    return _SWIMMER_TEAM.get(entry["swimmer"], f"UNK_{entry['swimmer']}")


SEPARATOR = "=" * 80


def build_championship_entries():
    """Convert the raw dicts into ChampionshipEntry objects for Gurobi."""
    entries = []
    for e in SETON_ENTRIES:
        entries.append(
            ChampionshipEntry(
                swimmer_name=e["swimmer"],
                team="SST",
                event=e["event"],
                seed_time=e["time"],
                gender="M" if "Boys" in e["event"] else "F",
                grade=str(e.get("grade", "")),
            )
        )
    for e in ALL_OPPONENT_ENTRIES:
        entries.append(
            ChampionshipEntry(
                swimmer_name=e["swimmer"],
                team=_get_opponent_team(e),
                event=e["event"],
                seed_time=e["time"],
                gender="M" if "Boys" in e["event"] else "F",
                grade=str(e.get("grade", "")),
            )
        )
    return entries


def run_gurobi(entries):
    """Run Gurobi championship strategy on VISAA 2026 data."""
    print(f"\n{SEPARATOR}")
    print("  GUROBI MILP — VISAA Championship Profile")
    print(SEPARATOR)

    strategy = ChampionshipGurobiStrategy(meet_profile="visaa_championship")

    # Identify divers (diving counts as 1 individual slot)
    divers = set()
    for e in entries:
        if "Diving" in e.event and e.team == "SST":
            divers.add(e.swimmer_name)

    opp_teams = {e.team for e in entries if e.team != "SST"}
    print(f"  Divers identified: {divers or 'none'}")
    print(f"  Total entries: {len(entries)}")
    print(f"  SST entries: {sum(1 for e in entries if e.team == 'SST')}")
    print(f"  Opponent entries: {sum(1 for e in entries if e.team != 'SST')}")
    print(f"  Opponent teams: {len(opp_teams)} (multi-team scoring enabled)")
    print()
    print("  Solving...")

    start = time.time()
    result = strategy.optimize_entries(
        all_entries=entries,
        target_team="SST",
        divers=divers,
        time_limit=120,
    )
    elapsed_ms = (time.time() - start) * 1000

    print(f"  Status: {result.status}")
    print(f"  Solve time: {elapsed_ms:.0f}ms")
    print(f"  Total points: {result.total_points:.0f}")
    print(f"  Baseline points: {result.baseline_points:.0f}")
    print(f"  Improvement: {result.improvement:+.0f}")
    print()

    # Print assignments
    print("  Assignments:")
    for swimmer, events in sorted(result.assignments.items()):
        print(f"    {swimmer:30s}  {', '.join(events)}")

    return result.total_points, elapsed_ms, result


def run_aqua(seton_df, opponent_df):
    """Run AquaOptimizer on VISAA 2026 data."""
    print(f"\n{SEPARATOR}")
    print("  AQUAOPTIMIZER — VISAA Championship Profile (thorough)")
    print(SEPARATOR)

    profile = ScoringProfile.visaa_championship()
    fatigue = FatigueModel(enabled=True)

    optimizer = AquaOptimizer(
        profile=profile,
        fatigue=fatigue,
        quality_mode="thorough",
    )

    print(f"  Seton entries: {len(seton_df)}")
    print(f"  Opponent entries: {len(opponent_df)}")
    print("  Quality mode: thorough")
    print()
    print("  Solving...")

    start = time.time()
    best_lineup_df, scored_df, totals, details = optimizer.optimize(
        seton_roster=seton_df,
        opponent_roster=opponent_df,
        scoring_fn=None,
        rules=None,
    )
    elapsed_ms = (time.time() - start) * 1000

    seton_score = totals.get("seton", 0)
    opp_score = totals.get("opponent", 0)

    print(f"  Solve time: {elapsed_ms:.0f}ms")
    print(f"  Seton score: {seton_score:.0f}")
    print(f"  Opponent score: {opp_score:.0f}")
    print(f"  Margin: {seton_score - opp_score:+.0f}")
    print()

    # Print assignments
    if best_lineup_df is not None and len(best_lineup_df) > 0:
        print("  Assignments:")
        lineup = best_lineup_df.sort_values(["swimmer", "event"])
        for swimmer, group in lineup.groupby("swimmer"):
            events = [row["event"] for _, row in group.iterrows()]
            # Skip relay entries
            ind_events = [e for e in events if "Relay" not in e]
            if ind_events:
                print(f"    {swimmer:30s}  {', '.join(ind_events)}")

    return seton_score, elapsed_ms, best_lineup_df


def main():
    print(SEPARATOR)
    print("  AQUAFORGE — VISAA 2026 HEAD-TO-HEAD COMPARISON")
    print("  Gurobi MILP vs AquaOptimizer (Nash+Beam+SA)")
    print(SEPARATOR)
    print()
    print("  Scoring profile: VISAA Championship (16-place)")
    print("  Individual: 20-17-16-15-14-13-12-11-9-7-6-5-4-3-2-1")
    print("  Relay: 2x individual (40-34-32-30-28-26-24-22-18-14-12-10-8-6-4-2)")
    print("  Data: SwimCloud Meet 350494 (Feb 14, 2026)")
    print()

    # Show opponent data coverage
    seton_events = {e["event"] for e in SETON_ENTRIES}
    opponent_events = {e["event"] for e in ALL_OPPONENT_ENTRIES}
    missing = seton_events - opponent_events
    print(f"  Seton event coverage: {len(seton_events)} events")
    print(f"  Opponent data for:    {len(opponent_events)} events")
    if missing:
        print(f"  MISSING opponent data: {sorted(missing)}")
    else:
        print("  All SST events have opponent data!")
    print(
        f"  Supplemental entries: {len(ALL_OPPONENT_ENTRIES) - len(OPPONENT_ENTRIES)} (from scrape)"
    )
    print()

    # Build data structures
    all_entries = build_championship_entries()

    seton_df = pd.DataFrame(SETON_ENTRIES)
    seton_df["team"] = "seton"

    opponent_df = pd.DataFrame(ALL_OPPONENT_ENTRIES)
    opponent_df["team"] = "opponent"

    # ─── Run Gurobi ───────────────────────────────────────────────
    try:
        gurobi_score, gurobi_time, gurobi_result = run_gurobi(all_entries)
    except Exception as e:
        print(f"\n  GUROBI ERROR: {e}")
        gurobi_score, gurobi_time, gurobi_result = 0, 0, None

    # ─── Run AquaOptimizer ────────────────────────────────────────
    try:
        aqua_score, aqua_time, aqua_lineup = run_aqua(seton_df, opponent_df)
    except Exception as e:
        print(f"\n  AQUA ERROR: {e}")
        aqua_score, aqua_time, aqua_lineup = 0, 0, None

    # ─── UNIFIED RE-SCORING ────────────────────────────────────────
    # Both optimizers define "score" differently:
    # - Gurobi: only scores events where it assigned swimmers
    # - AquaOptimizer: scores all events with whatever swimmers are entered
    # For a fair comparison, re-score both using the SAME scoring engine.
    print(f"\n{SEPARATOR}")
    print("  UNIFIED RE-SCORING (apples-to-apples)")
    print(SEPARATOR)
    print()

    profile = ScoringProfile.visaa_championship()
    engine = ScoringEngine(profile, FatigueModel(enabled=True))
    all_events = sorted(set(e["event"] for e in SETON_ENTRIES))

    def rescore_assignments(assignments: dict[str, list[str]], label: str) -> float:
        """Re-score a set of assignments using ScoringEngine.score_event()."""
        total = 0.0
        for event in all_events:
            is_relay = "Relay" in event
            # Get the assigned swimmers for this event
            assigned = {s for s, evts in assignments.items() if event in evts}
            seton_entries = [
                e
                for e in SETON_ENTRIES
                if e["event"] == event and e["swimmer"] in assigned
            ]
            opp_entries = [e for e in ALL_OPPONENT_ENTRIES if e["event"] == event]
            s_pts, _, _ = engine.score_event(
                seton_entries, opp_entries, is_relay=is_relay, event_name=event
            )
            total += s_pts
        return total

    # Build assignment dicts (swimmer -> [events])
    gurobi_assign = {}
    if gurobi_result:
        gurobi_assign = gurobi_result.assignments

    aqua_assign: dict[str, list[str]] = {}
    if aqua_lineup is not None and len(aqua_lineup) > 0:
        for _, row in aqua_lineup.iterrows():
            swimmer = row.get("swimmer", "")
            event = row.get("event", "")
            if swimmer:
                aqua_assign.setdefault(swimmer, []).append(event)

    gurobi_rescore = rescore_assignments(gurobi_assign, "Gurobi")
    aqua_rescore = rescore_assignments(aqua_assign, "Aqua")

    diff_rescore = aqua_rescore - gurobi_rescore
    winner_rescore = (
        "Aqua" if diff_rescore > 0 else "Gurobi" if diff_rescore < 0 else "Tie"
    )

    print(f"  {'Metric':<25s} {'Gurobi':>12s} {'AquaOptimizer':>15s} {'Diff':>10s}")
    print(f"  {'─' * 65}")
    print(
        f"  {'Unified SST Points':<25s} {gurobi_rescore:>12.0f} {aqua_rescore:>15.0f} {f'{diff_rescore:+.0f} ({winner_rescore})':>10s}"
    )
    print(
        f"  {'Solve Time (ms)':<25s} {gurobi_time:>12.0f} {aqua_time:>15.0f} {'':>10s}"
    )
    print()
    print("  Note: 'Unified' = same ScoringEngine re-scores both lineups.")
    print(f"  Gurobi's own score ({gurobi_score:.0f}) only counts assigned swimmers.")
    print(
        f"  AquaOptimizer's own score ({aqua_score:.0f}) counts all event participants."
    )
    print()

    # ─── Assignment Comparison ────────────────────────────────────
    if gurobi_result and aqua_lineup is not None and len(aqua_lineup) > 0:
        print(f"\n{SEPARATOR}")
        print("  ASSIGNMENT DIFFERENCES (Individual events only)")
        print(SEPARATOR)
        print()

        # Extract Gurobi assignments
        gurobi_assignments = {}
        if gurobi_result:
            for swimmer, events in gurobi_result.assignments.items():
                ind_events = sorted(
                    e for e in events if "Relay" not in e and "Diving" not in e
                )
                if ind_events:
                    gurobi_assignments[swimmer] = ind_events

        # Extract Aqua assignments
        aqua_assignments = {}
        for _, row in aqua_lineup.iterrows():
            swimmer = row.get("swimmer", "")
            event = row.get("event", "")
            if (
                "Relay" not in event
                and "Seton" not in swimmer
                and "Diving" not in event
            ):
                if swimmer not in aqua_assignments:
                    aqua_assignments[swimmer] = []
                aqua_assignments[swimmer].append(event)
        for k in aqua_assignments:
            aqua_assignments[k] = sorted(aqua_assignments[k])

        all_swimmers = sorted(
            set(list(gurobi_assignments.keys()) + list(aqua_assignments.keys()))
        )

        matches = 0
        diffs = 0
        for swimmer in all_swimmers:
            g_events = set(gurobi_assignments.get(swimmer, []))
            a_events = set(aqua_assignments.get(swimmer, []))
            if g_events == a_events:
                matches += 1
            else:
                diffs += 1
                g_str = ", ".join(sorted(g_events)) if g_events else "(not assigned)"
                a_str = ", ".join(sorted(a_events)) if a_events else "(not assigned)"
                print(f"  {swimmer}:")
                print(f"    Gurobi: {g_str}")
                print(f"    Aqua:   {a_str}")
                print()

        print(f"  Identical assignments: {matches}")
        print(f"  Different assignments: {diffs}")

    print(f"\n{SEPARATOR}")
    print("  Generated by AquaForge v1.0.0-next")
    print(SEPARATOR)


if __name__ == "__main__":
    main()
