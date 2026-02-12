#!/usr/bin/env python3
"""
Backtest Optimizer Strategies for Meet 512 (VCAC Regular Season Championship).

Loads the pre-exported CSV data (Boys + Girls, projected + actual),
runs multiple optimizer strategies against the projected psych sheet,
then compares optimized lineups against actual meet results.

Usage:
    python scripts/backtest_meet_512.py
"""

import os
import sys
import time
from collections import defaultdict
from typing import Any

import pandas as pd

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from swim_ai_reflex.backend.core.rules import VCACChampRules, get_meet_profile
from swim_ai_reflex.backend.core.scoring import full_meet_scoring
from swim_ai_reflex.backend.pipelines.championship import (
    ChampionshipInput,
    create_championship_pipeline,
)
from swim_ai_reflex.backend.services.championship.projection import (
    PointProjectionService,
)

# =============================================================================
# CONSTANTS
# =============================================================================

MEET_ID = 512
MEET_NAME = "VCAC Regular Season Championship"
MEET_PROFILE = "vcac_championship"

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "backtest", "meet_512")

SETON_ROSTER = os.path.join(DATA_DIR, "seton_roster_512.csv")
OPPONENT_ROSTER = os.path.join(DATA_DIR, "opponent_roster_512.csv")
ACTUAL_RESULTS = os.path.join(DATA_DIR, "actual_results_512.csv")

# Team ID → Display Name mapping (normalized to match projection service output)
# The projection service normalizes "Seton Swimming" → "seton" for internal use,
# then TEAM_DISPLAY_NAMES in entry_schema maps codes to display names.
# We use display names here so projected and actual standings align.
TEAM_ID_MAP = {
    1: "Seton",
    29: "Trinity",
    30: "Fredericksburg Christian",
    48: "Oakcrest",
    158: "Immanuel Christian",
    199: "St. John Paul",
}

# Events in the roster CSVs (column names)
ROSTER_EVENTS = [
    "50 Free",
    "100 Free",
    "200 Free",
    "500 Free",
    "100 Back",
    "100 Breast",
    "100 Fly",
    "200 IM",
]


# =============================================================================
# DATA LOADING
# =============================================================================


def load_roster_as_entries(csv_path: str, team_name: str) -> list[dict[str, Any]]:
    """
    Load a wide-format roster CSV and melt into long-format psych sheet entries.

    Wide format: name, gender, id, 50 Free, 100 Free, ...
    Long format: [{swimmer_name, team, event, seed_time, gender}, ...]
    """
    df = pd.read_csv(csv_path)
    entries = []

    for _, row in df.iterrows():
        swimmer = row.get("name", "")
        gender = row.get("gender", "")
        if not swimmer or pd.isna(swimmer):
            continue

        gender_prefix = "Boys" if gender == "M" else "Girls"

        for event in ROSTER_EVENTS:
            time_val = row.get(event)
            if pd.notna(time_val) and float(time_val) > 0:
                entries.append(
                    {
                        "swimmer_name": swimmer,
                        "team": team_name,
                        "event": f"{gender_prefix} {event}",
                        "seed_time": float(time_val),
                        "gender": gender,
                    }
                )

    return entries


def load_actual_results(csv_path: str) -> pd.DataFrame:
    """
    Load actual meet results CSV.

    Columns: event, athlete, athlete_id, team_id, time, dq
    Returns cleaned DataFrame with team names and gender prefixes.
    """
    df = pd.read_csv(csv_path)

    # Map team IDs to names
    df["team_id"] = pd.to_numeric(df["team_id"], errors="coerce").astype("Int64")
    df["team"] = df["team_id"].map(TEAM_ID_MAP).fillna("Unknown")

    # Clean DQ column - strip whitespace
    df["dq"] = df["dq"].astype(str).str.strip()

    # Filter out DQs (keep only clean swims and exhibition)
    # DQ codes like "R" = scratched, "1A/1J/etc" = DQ, blank/nan = valid swim
    valid_mask = df["dq"].isin(["", "nan", "None"])
    df_valid = df[valid_mask].copy()

    # Clean time values
    df_valid["time"] = pd.to_numeric(df_valid["time"], errors="coerce")
    df_valid = df_valid.dropna(subset=["time"])
    df_valid = df_valid[df_valid["time"] > 0]

    return df_valid


def infer_gender_from_roster(
    actual_df: pd.DataFrame,
    seton_entries: list[dict],
    opponent_entries: list[dict],
) -> pd.DataFrame:
    """
    Infer gender for actual results by matching athlete names to roster data.
    """
    # Build name → gender lookup from rosters
    gender_lookup = {}
    for entry in seton_entries + opponent_entries:
        name = entry["swimmer_name"]
        gender = entry["gender"]
        if name and gender:
            gender_lookup[name] = gender

    # Apply to actual results
    df = actual_df.copy()
    df["gender"] = df["athlete"].map(gender_lookup)

    # For any remaining, try to infer from duplicate rows
    # (some swimmers appear in both roster files)
    missing = df["gender"].isna()
    if missing.any():
        print(f"  Warning: {missing.sum()} results have unknown gender (will skip)")
        df = df.dropna(subset=["gender"])

    # Add gender prefix to event names
    df["event_full"] = df.apply(
        lambda r: f"{'Boys' if r['gender'] == 'M' else 'Girls'} {r['event']}", axis=1
    )

    return df


# =============================================================================
# SCORING ENGINE
# =============================================================================


def score_actual_results(
    actual_df: pd.DataFrame, rules: VCACChampRules
) -> dict[str, float]:
    """
    Score actual meet results using VCAC championship rules.

    Returns: {team_name: total_points}
    """
    team_totals: dict[str, float] = defaultdict(float)

    for event_name, event_df in actual_df.groupby("event_full"):
        is_relay = "relay" in str(event_name).lower()
        points_table = rules.relay_points if is_relay else rules.individual_points
        max_scorers = (
            rules.max_scorers_per_team_relay
            if is_relay
            else rules.max_scorers_per_team_individual
        )

        # Sort by time (ascending = faster is better)
        sorted_df = event_df.sort_values("time", ascending=True)

        # Track scorers per team
        team_scorer_count: dict[str, int] = defaultdict(int)
        place = 0

        for _, row in sorted_df.iterrows():
            place += 1
            team = row["team"]

            # Check if team can still score
            if team_scorer_count[team] >= max_scorers:
                continue  # Skip, doesn't earn points

            team_scorer_count[team] += 1

            # Award points based on place
            if place <= len(points_table):
                points = points_table[place - 1]
                team_totals[team] += points

    return dict(team_totals)


def score_projected_lineup(
    all_entries: list[dict],
    optimized_assignments: dict[str, list[str]] | None,
    target_team: str,
    rules: VCACChampRules,
) -> dict[str, float]:
    """
    Score a projected lineup using seed times.

    If optimized_assignments is provided, only include the assigned events
    for the target team swimmers; all opponent entries remain as-is.
    """
    team_totals: dict[str, float] = defaultdict(float)

    # Build entries to score
    if optimized_assignments:
        # Keep all opponent entries
        scoring_entries = [
            e
            for e in all_entries
            if target_team.lower() not in e.get("team", "").lower()
        ]

        # Add only assigned events for target team
        target_entries_by_swimmer = defaultdict(list)
        for e in all_entries:
            if target_team.lower() in e.get("team", "").lower():
                target_entries_by_swimmer[e["swimmer_name"]].append(e)

        for swimmer, events in optimized_assignments.items():
            swimmer_entries = target_entries_by_swimmer.get(swimmer, [])
            for event_name in events:
                # Find matching entry
                for entry in swimmer_entries:
                    if entry["event"] == event_name:
                        scoring_entries.append(entry)
                        break
    else:
        scoring_entries = all_entries

    # Group by event and score
    entries_by_event: dict[str, list[dict]] = defaultdict(list)
    for e in scoring_entries:
        entries_by_event[e.get("event", "")].append(e)

    for event_name, event_entries in entries_by_event.items():
        is_relay = "relay" in event_name.lower()
        points_table = rules.relay_points if is_relay else rules.individual_points
        max_scorers = (
            rules.max_scorers_per_team_relay
            if is_relay
            else rules.max_scorers_per_team_individual
        )

        # Sort by seed time
        sorted_entries = sorted(
            event_entries, key=lambda e: e.get("seed_time", float("inf"))
        )

        team_scorer_count: dict[str, int] = defaultdict(int)
        place = 0

        for entry in sorted_entries:
            place += 1
            team = entry.get("team", "")

            if team_scorer_count[team] >= max_scorers:
                continue

            team_scorer_count[team] += 1

            if place <= len(points_table):
                points = points_table[place - 1]
                team_totals[team] += points

    return dict(team_totals)


# =============================================================================
# OPTIMIZER STRATEGIES
# =============================================================================


def run_pipeline_strategy(
    entries: list[dict], target_team: str, profile: str
) -> dict[str, Any]:
    """Run the default championship pipeline (Gurobi if available, else fallback)."""
    pipeline = create_championship_pipeline(meet_profile=profile)
    input_data = ChampionshipInput(
        entries=entries,
        target_team=target_team,
        meet_name=MEET_NAME,
        meet_profile=profile,
    )
    result = pipeline.run(input_data, stage="entries")
    return {
        "assignments": result.entry_assignments,
        "improvement": result.optimization_improvement,
        "projection": result.projection,
    }


def run_aqua_strategy(
    entries: list[dict], target_team: str, profile: str
) -> dict[str, Any]:
    """Run Aqua optimizer (license-free custom optimizer)."""
    try:
        from swim_ai_reflex.backend.core.strategies.aqua_optimizer import (
            create_aqua_optimizer,
        )

        optimizer = create_aqua_optimizer(profile=profile)
        rules = get_meet_profile(profile)

        # Build roster DataFrames in the format Aqua expects
        target_entries = [
            e for e in entries if target_team.lower() in e.get("team", "").lower()
        ]
        opponent_entries = [
            e for e in entries if target_team.lower() not in e.get("team", "").lower()
        ]

        target_df = pd.DataFrame(
            [
                {
                    "swimmer": e.get("swimmer_name", e.get("swimmer", "")),
                    "event": e.get("event", ""),
                    "time": e.get("seed_time", e.get("time", float("inf"))),
                    "team": e.get("team", ""),
                }
                for e in target_entries
            ]
        )
        opponent_df = pd.DataFrame(
            [
                {
                    "swimmer": e.get("swimmer_name", e.get("swimmer", "")),
                    "event": e.get("event", ""),
                    "time": e.get("seed_time", e.get("time", float("inf"))),
                    "team": e.get("team", ""),
                }
                for e in opponent_entries
            ]
        )

        best_seton_df, scored_df, totals, details = optimizer.optimize(
            seton_roster=target_df,
            opponent_roster=opponent_df,
            scoring_fn=full_meet_scoring,
            rules=rules,
        )

        # Extract assignments from best_seton_df
        assignments: dict[str, list[str]] = {}
        if best_seton_df is not None and not best_seton_df.empty:
            for _, row in best_seton_df.iterrows():
                swimmer = row.get("swimmer", "")
                event = row.get("event", "")
                if swimmer and event:
                    assignments.setdefault(swimmer, []).append(event)

        return {
            "assignments": assignments if assignments else None,
            "improvement": 0,
            "total_points": totals.get("seton", 0) if totals else 0,
            "totals": totals,
            "details": details,
        }
    except Exception as e:
        return {"error": str(e), "assignments": None}


def run_projection_only(
    entries: list[dict], target_team: str, profile: str
) -> dict[str, Any]:
    """Run projection only (no optimization — baseline seed-time scoring)."""
    service = PointProjectionService(profile)
    projection = service.project_standings(entries, target_team, MEET_NAME)
    return {
        "assignments": None,  # No optimization
        "projection": projection,
        "standings": {team: pts for team, pts, _rank in projection.standings},
    }


# =============================================================================
# DISPLAY HELPERS
# =============================================================================


def print_header(title: str):
    print(f"\n{'=' * 78}")
    print(f"  {title}")
    print(f"{'=' * 78}")


def print_standings(standings: dict[str, float], label: str, highlight_team: str = ""):
    sorted_teams = sorted(standings.items(), key=lambda x: -x[1])
    print(f"\n  {label}:")
    print(f"  {'Rank':<6}{'Team':<30}{'Points':>10}")
    print(f"  {'-' * 46}")
    for i, (team, points) in enumerate(sorted_teams, 1):
        marker = (
            " <--" if highlight_team and highlight_team.lower() in team.lower() else ""
        )
        print(f"  {i:<6}{team:<30}{points:>10.1f}{marker}")
    return sorted_teams


def get_team_rank(standings: dict[str, float], team_keyword: str) -> tuple[int, float]:
    """Get rank and points for a team matching keyword."""
    sorted_teams = sorted(standings.items(), key=lambda x: -x[1])
    for i, (team, points) in enumerate(sorted_teams, 1):
        if team_keyword.lower() in team.lower():
            return i, points
    return 0, 0.0


# =============================================================================
# MAIN BACKTEST
# =============================================================================


def main():
    print_header(f"BACKTEST: {MEET_NAME} (Meet #{MEET_ID})")
    print(f"  Profile: {MEET_PROFILE}")
    print(f"  Data: {DATA_DIR}")

    rules = get_meet_profile(MEET_PROFILE)

    # ─── Step 1: Load Data ────────────────────────────────────────────────
    print_header("STEP 1: Loading Data")

    seton_entries = load_roster_as_entries(SETON_ROSTER, "Seton")
    print(f"  Seton roster: {len(seton_entries)} entries")

    # Load opponent roster — need to identify teams
    opp_df = pd.read_csv(OPPONENT_ROSTER)
    opponent_entries = []

    # The opponent roster doesn't have a team column — we need to match
    # athlete IDs from actual results to get team assignments
    actual_raw = pd.read_csv(ACTUAL_RESULTS)
    actual_raw["team_id"] = pd.to_numeric(
        actual_raw["team_id"], errors="coerce"
    ).astype("Int64")

    # Build athlete_id → team_name mapping from actual results
    athlete_team_map = {}
    for _, row in actual_raw.iterrows():
        aid = row.get("athlete_id")
        tid = row.get("team_id")
        if pd.notna(aid) and pd.notna(tid):
            team_name = TEAM_ID_MAP.get(int(tid), f"Team_{tid}")
            athlete_team_map[int(aid)] = team_name

    # Now melt opponent roster with team assignments
    for _, row in opp_df.iterrows():
        swimmer = row.get("name", "")
        gender = row.get("gender", "")
        athlete_id = row.get("id")

        if not swimmer or pd.isna(swimmer):
            continue

        team_name = athlete_team_map.get(
            int(athlete_id) if pd.notna(athlete_id) else -1, "Unknown"
        )
        gender_prefix = "Boys" if gender == "M" else "Girls"

        for event in ROSTER_EVENTS:
            time_val = row.get(event)
            if pd.notna(time_val) and float(time_val) > 0:
                opponent_entries.append(
                    {
                        "swimmer_name": swimmer,
                        "team": team_name,
                        "event": f"{gender_prefix} {event}",
                        "seed_time": float(time_val),
                        "gender": gender,
                    }
                )

    print(f"  Opponent roster: {len(opponent_entries)} entries")

    # Combine all projected entries
    all_projected = seton_entries + opponent_entries

    # Count by team
    team_counts = defaultdict(int)
    for e in all_projected:
        team_counts[e["team"]] += 1
    for team, count in sorted(team_counts.items()):
        if team != "Unknown":
            print(f"    {team}: {count} entries")

    # Count by gender
    boys = sum(1 for e in all_projected if e["gender"] == "M")
    girls = sum(1 for e in all_projected if e["gender"] == "F")
    print(f"  Gender split: Boys={boys}, Girls={girls}")

    # ─── Step 2: Score Actual Results ─────────────────────────────────────
    print_header("STEP 2: Scoring Actual Meet Results")

    actual_df = load_actual_results(ACTUAL_RESULTS)
    actual_df = infer_gender_from_roster(actual_df, seton_entries, opponent_entries)
    print(f"  Valid results: {len(actual_df)} swims")

    actual_standings = score_actual_results(actual_df, rules)
    print_standings(actual_standings, "ACTUAL MEET STANDINGS", "Seton")
    actual_rank, actual_pts = get_team_rank(actual_standings, "Seton")
    print(f"\n  Seton Actual: Rank #{actual_rank}, {actual_pts:.1f} pts")

    # ─── Step 3: Baseline Projection (No Optimization) ────────────────────
    print_header("STEP 3: Baseline Projection (Seed Times, No Optimization)")

    t0 = time.time()
    baseline = run_projection_only(all_projected, "Seton", MEET_PROFILE)
    t_baseline = time.time() - t0

    baseline_standings = baseline["standings"]
    print_standings(baseline_standings, "PROJECTED STANDINGS (Baseline)", "Seton")
    baseline_rank, baseline_pts = get_team_rank(baseline_standings, "seton")
    print(f"\n  Seton Projected: Rank #{baseline_rank}, {baseline_pts:.1f} pts")
    print(f"  Time: {t_baseline:.2f}s")

    # ─── Step 4: Championship Pipeline (Gurobi) ──────────────────────────
    print_header("STEP 4: Championship Pipeline Optimizer (Gurobi)")
    print("  NOTE: Optimizer constrains Seton to max 2 individual events/swimmer.")
    print("  'Improvement' = gain over a greedy constrained baseline (not the")
    print("  unconstrained psych sheet projection from Step 3).")

    gurobi_improvement = 0.0
    gurobi_proj_standings = {}
    t0 = time.time()
    try:
        gurobi_result = run_pipeline_strategy(all_projected, "Seton", MEET_PROFILE)
        t_gurobi = time.time() - t0

        if gurobi_result.get("assignments"):
            assignments = gurobi_result["assignments"]
            gurobi_improvement = gurobi_result["improvement"]
            print(
                f"\n  Constrained improvement: {gurobi_improvement:+.1f} pts vs greedy baseline"
            )
            print(f"  Swimmers assigned: {len(assignments)}")

            # Show projected standings from pipeline
            if gurobi_result.get("projection"):
                gp = gurobi_result["projection"]
                gurobi_proj_standings = {team: pts for team, pts, _rank in gp.standings}
                print_standings(
                    gurobi_proj_standings,
                    "PROJECTED STANDINGS (with Gurobi optimization)",
                    "Seton",
                )

            # Show top assignments
            print("\n  Gurobi Lineup (top 15):")
            for swimmer, events in sorted(assignments.items())[:15]:
                print(f"    {swimmer}: {', '.join(events)}")
            if len(assignments) > 15:
                print(f"    ... and {len(assignments) - 15} more")
        else:
            print("  Gurobi optimization not available (no license?)")
            assignments = None

        print(f"\n  Time: {t_gurobi:.2f}s")
    except Exception as e:
        print(f"  ERROR: {e}")
        t_gurobi = 0
        assignments = None

    # ─── Step 5: Aqua Optimizer ───────────────────────────────────────────
    print_header("STEP 5: Aqua Optimizer (License-Free)")
    print("  NOTE: Aqua uses Nash equilibrium + hill climbing. Optimizes for")
    print("  dual-meet-style scoring (Seton vs field).")

    aqua_seton_pts = 0.0
    aqua_opp_pts = 0.0
    t0 = time.time()
    try:
        aqua_result = run_aqua_strategy(all_projected, "Seton", MEET_PROFILE)
        t_aqua = time.time() - t0

        if aqua_result.get("error"):
            print(f"  Aqua error: {aqua_result['error']}")
        elif aqua_result.get("assignments"):
            aqua_assignments = aqua_result["assignments"]
            print(f"\n  Swimmers assigned: {len(aqua_assignments)}")

            if aqua_result.get("totals"):
                aqua_seton_pts = aqua_result["totals"].get("seton", 0)
                aqua_opp_pts = aqua_result["totals"].get("opponent", 0)
                print(
                    f"  Aqua Score: Seton {aqua_seton_pts:.0f} vs Opponents {aqua_opp_pts:.0f}"
                )

            # Show top assignments
            print("\n  Aqua Lineup (top 15):")
            for swimmer, events in sorted(aqua_assignments.items())[:15]:
                evts = events if isinstance(events, list) else [events]
                print(f"    {swimmer}: {', '.join(evts)}")
            if len(aqua_assignments) > 15:
                print(f"    ... and {len(aqua_assignments) - 15} more")
        else:
            print("  Aqua returned no assignments")

        print(f"\n  Time: {t_aqua:.2f}s")
    except Exception as e:
        print(f"  ERROR: {e}")
        import traceback

        traceback.print_exc()
        t_aqua = 0

    # ─── Step 6: Comparison Dashboard ─────────────────────────────────────
    print_header("COMPARISON DASHBOARD")

    # Use the baseline projection for the Seton score comparisons
    # (Gurobi/Aqua optimization improves relative to their own baselines)
    gurobi_label_pts = (
        baseline_pts + gurobi_improvement if assignments else baseline_pts
    )

    print(
        f"\n  {'Strategy':<25}{'Seton Pts':>12}{'Rank':>8}{'vs Actual':>12}{'Time':>10}"
    )
    print(f"  {'-' * 67}")

    strategies = [
        ("Actual Results", actual_pts, actual_rank, "-"),
        ("Baseline Projection", baseline_pts, baseline_rank, f"{t_baseline:.2f}s"),
    ]

    if assignments:
        gurobi_rank_val = (
            get_team_rank(gurobi_proj_standings, "seton")[0]
            if gurobi_proj_standings
            else baseline_rank
        )
        strategies.append(
            (
                "Gurobi (constrained)",
                gurobi_label_pts,
                gurobi_rank_val,
                f"{t_gurobi:.2f}s",
            )
        )

    if aqua_seton_pts > 0:
        strategies.append(("Aqua (Seton score)", aqua_seton_pts, 0, f"{t_aqua:.2f}s"))

    for name, pts, rank, elapsed in strategies:
        delta = pts - actual_pts if name != "Actual Results" else 0
        delta_str = f"{'+' if delta >= 0 else ''}{delta:.1f}" if delta != 0 else "-"
        rank_str = f"#{rank}" if rank > 0 else "n/a"
        print(f"  {name:<25}{pts:>12.1f}{rank_str:>8}{delta_str:>12}{elapsed:>10}")

    # Key insight
    print("\n  Key Insight:")
    print(
        f"    Seton overperformed projections by {actual_pts - baseline_pts:+.0f} pts"
    )
    if gurobi_improvement != 0 and assignments:
        print(
            f"    Gurobi optimizer found {gurobi_improvement:+.1f} pts vs greedy constrained baseline"
        )
        print(
            "    (Negative means constraints force suboptimal swaps - normal for small meets)"
        )

    # ─── Step 7: Event-by-Event Breakdown ─────────────────────────────────
    print_header("EVENT-BY-EVENT: PROJECTED vs ACTUAL (Seton Points)")

    # Get baseline projection event breakdown
    if baseline.get("projection"):
        proj = baseline["projection"]
        print(f"\n  {'Event':<25}{'Projected':>12}{'Actual':>12}{'Delta':>10}")
        print(f"  {'-' * 59}")

        # Build actual event scores for Seton
        actual_seton_events: dict[str, float] = defaultdict(float)
        for event_name, event_df in actual_df.groupby("event_full"):
            is_relay = "relay" in str(event_name).lower()
            pts_table = rules.relay_points if is_relay else rules.individual_points
            max_sc = (
                rules.max_scorers_per_team_relay
                if is_relay
                else rules.max_scorers_per_team_individual
            )
            sorted_ev = event_df.sort_values("time", ascending=True)
            team_sc: dict[str, int] = defaultdict(int)
            place = 0
            for _, row in sorted_ev.iterrows():
                place += 1
                team = row["team"]
                if team_sc[team] >= max_sc:
                    continue
                team_sc[team] += 1
                if "seton" in team.lower() and place <= len(pts_table):
                    actual_seton_events[event_name] += pts_table[place - 1]

        # Merge projected and actual
        all_events = sorted(
            set(list(proj.event_projections.keys()) + list(actual_seton_events.keys()))
        )
        total_proj = 0.0
        total_actual = 0.0

        for event in all_events:
            proj_pts = 0.0
            if event in proj.event_projections:
                ep = proj.event_projections[event]
                for tp_team, tp_pts in ep.team_points.items():
                    if "seton" in tp_team.lower():
                        proj_pts = tp_pts
                        break

            actual_ev_pts = actual_seton_events.get(event, 0.0)
            delta = actual_ev_pts - proj_pts
            delta_str = f"{'+' if delta >= 0 else ''}{delta:.0f}" if delta != 0 else "-"

            total_proj += proj_pts
            total_actual += actual_ev_pts

            if proj_pts > 0 or actual_ev_pts > 0:
                print(
                    f"  {event:<25}{proj_pts:>12.0f}{actual_ev_pts:>12.0f}{delta_str:>10}"
                )

        print(f"  {'-' * 59}")
        total_delta = total_actual - total_proj
        total_delta_str = f"{'+' if total_delta >= 0 else ''}{total_delta:.0f}"
        print(
            f"  {'TOTAL':<25}{total_proj:>12.0f}{total_actual:>12.0f}{total_delta_str:>10}"
        )

    # ─── Step 8: Full Team Comparison ─────────────────────────────────────
    print_header("ALL TEAMS: PROJECTED vs ACTUAL")

    all_teams = sorted(
        set(list(baseline_standings.keys()) + list(actual_standings.keys()))
    )
    print(
        f"\n  {'Team':<30}{'Proj Pts':>10}{'Proj Rank':>10}{'Act Pts':>10}{'Act Rank':>10}{'Delta':>8}"
    )
    print(f"  {'-' * 78}")

    proj_ranked = sorted(baseline_standings.items(), key=lambda x: -x[1])
    actual_ranked = sorted(actual_standings.items(), key=lambda x: -x[1])

    proj_rank_map = {team: i + 1 for i, (team, _) in enumerate(proj_ranked)}
    actual_rank_map = {team: i + 1 for i, (team, _) in enumerate(actual_ranked)}

    for team in sorted(all_teams, key=lambda t: -baseline_standings.get(t, 0)):
        p_pts = baseline_standings.get(team, 0)
        a_pts = actual_standings.get(team, 0)
        p_rank = proj_rank_map.get(team, "-")
        a_rank = actual_rank_map.get(team, "-")
        delta = a_pts - p_pts
        delta_str = f"{'+' if delta >= 0 else ''}{delta:.0f}"

        marker = " <--" if "seton" in team.lower() else ""
        print(
            f"  {team:<30}{p_pts:>10.0f}{'#' + str(p_rank):>10}{a_pts:>10.0f}{'#' + str(a_rank):>10}{delta_str:>8}{marker}"
        )

    # ─── Step 9: Accuracy Metrics ─────────────────────────────────────────
    print_header("ACCURACY METRICS")

    # Rank accuracy (exclude "UNKN" team)
    real_teams = [t for t in all_teams if t not in ("UNKN", "Unknown")]
    rank_correct = sum(
        1 for team in real_teams if proj_rank_map.get(team) == actual_rank_map.get(team)
    )
    print(f"  Exact rank matches: {rank_correct}/{len(real_teams)} teams")

    # Points RMSE
    shared_teams = set(baseline_standings.keys()) & set(actual_standings.keys())
    shared_teams -= {"UNKN", "Unknown"}
    if shared_teams:
        sq_errors = [
            (baseline_standings[t] - actual_standings[t]) ** 2 for t in shared_teams
        ]
        rmse = (sum(sq_errors) / len(sq_errors)) ** 0.5
        print(f"  Points RMSE: {rmse:.1f} pts")

        # Mean absolute error
        mae = sum(
            abs(baseline_standings[t] - actual_standings[t]) for t in shared_teams
        ) / len(shared_teams)
        print(f"  Points MAE: {mae:.1f} pts")

    # Seton-specific
    print(
        f"\n  Seton Rank Accuracy: Predicted #{baseline_rank} vs Actual #{actual_rank}"
    )
    seton_pts_error = abs(baseline_pts - actual_pts)
    seton_pct_error = (seton_pts_error / actual_pts * 100) if actual_pts > 0 else 0
    print(f"  Seton Points Error: {seton_pts_error:.1f} pts ({seton_pct_error:.1f}%)")
    print(
        f"    Predicted: {baseline_pts:.1f} | Actual: {actual_pts:.1f} | Delta: {actual_pts - baseline_pts:+.1f}"
    )

    if gurobi_improvement != 0:
        print(
            f"\n  Gurobi Optimizer Gain: {gurobi_improvement:+.1f} pts (vs constrained greedy)"
        )

    if aqua_seton_pts > 0:
        print(f"  Aqua Optimizer Score: {aqua_seton_pts:.0f} pts (dual-meet scoring)")

    # ─── Save Results ─────────────────────────────────────────────────────
    print_header("RESULTS SAVED")

    results_df = pd.DataFrame(
        strategies, columns=["strategy", "seton_pts", "rank", "time"]
    )
    output_path = os.path.join(DATA_DIR, "backtest_comparison_512.csv")
    results_df.to_csv(output_path, index=False)
    print(f"  Saved to: {output_path}")

    print(f"\n{'=' * 78}")
    print("  BACKTEST COMPLETE")
    print(f"{'=' * 78}\n")


if __name__ == "__main__":
    main()
