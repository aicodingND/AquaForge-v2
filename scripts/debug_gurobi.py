#!/usr/bin/env python3
"""
Gurobi Championship Optimizer — Diagnostic Script
===================================================
Debugs why Gurobi scores only 117 points with 9 swimmers, while
AquaOptimizer scores 1014 with 40 swimmers on the same data.

Examines:
  1. The point matrix from _build_point_matrix()
  2. Per-swimmer, per-event expected points
  3. How many (swimmer, event) pairs have >0 points
  4. How many swimmers have at least 1 event with >0 points
  5. Constraint counts by type
  6. Gurobi solution variable values
"""

import json
import sys
import time
from collections import defaultdict
from pathlib import Path

# Add project root
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.run_visaa_optimizer import OPPONENT_ENTRIES, SETON_ENTRIES  # noqa: E402
from swim_ai_reflex.backend.core.championship_factors import (  # noqa: E402
    adjust_time,
)
from swim_ai_reflex.backend.core.strategies.championship_strategy import (  # noqa: E402
    ChampionshipEntry,
    ChampionshipGurobiStrategy,
)
from swim_ai_reflex.backend.services.constraint_validator import (  # noqa: E402
    get_blocked_events,
    normalize_event_name,
)

SEP = "=" * 80
THIN = "-" * 80


# ─── Load Data (identical to compare_visaa_2026_gurobi_vs_aqua.py) ────────
def load_supplemental():
    path = PROJECT_ROOT / "data" / "swimcloud" / "visaa_2026_missing_opponents.json"
    if path.exists():
        with open(path) as f:
            data = json.load(f)
        for entry in data:
            entry.pop("team", None)
        return data
    return []


def build_championship_entries(all_opponent_entries):
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
    for e in all_opponent_entries:
        entries.append(
            ChampionshipEntry(
                swimmer_name=e["swimmer"],
                team="OPP",
                event=e["event"],
                seed_time=e["time"],
                gender="M" if "Boys" in e["event"] else "F",
                grade=str(e.get("grade", "")),
            )
        )
    return entries


def main():
    print(SEP)
    print("  GUROBI DIAGNOSTIC — Why Only 117 Points / 9 Swimmers?")
    print(SEP)
    print()

    # Load data
    supplemental = load_supplemental()
    all_opponent_entries = OPPONENT_ENTRIES + supplemental
    all_entries = build_championship_entries(all_opponent_entries)

    print(f"  Total entries:        {len(all_entries)}")
    print(f"  SST entries:          {sum(1 for e in all_entries if e.team == 'SST')}")
    print(f"  Opponent entries:     {sum(1 for e in all_entries if e.team != 'SST')}")
    print(f"  Supplemental loaded:  {len(supplemental)}")
    print()

    # ─── Setup strategy (same as compare script) ──────────────────────────
    strategy = ChampionshipGurobiStrategy(meet_profile="visaa_championship")
    rules = strategy.rules

    print(f"  Meet profile: {rules.name}")
    print(
        f"  Points table ({len(rules.individual_points)} places): {rules.individual_points}"
    )
    print(f"  Max scorers per team per event: {strategy.max_scorers}")
    print(
        f"  Max entries per team per event: {getattr(rules, 'max_entries_per_team_per_event', 'N/A')}"
    )
    print(
        f"  Relay 3 counts as individual:   {getattr(rules, 'relay_3_counts_as_individual', False)}"
    )
    print()

    # ─── Filter entries the same way Gurobi does ─────────────────────────
    individual_entries = [
        e
        for e in all_entries
        if "relay" not in e.event.lower() and "diving" not in e.event.lower()
    ]
    team_entries = [e for e in individual_entries if e.team.upper() == "SST"]

    swimmers = sorted(set(e.swimmer_name for e in team_entries))
    events = sorted(set(e.event for e in individual_entries))

    swimmer_event_lookup = {}
    for e in team_entries:
        swimmer_event_lookup[(e.swimmer_name, e.event)] = e

    print(f"  Individual entries (all):  {len(individual_entries)}")
    print(f"  SST individual entries:    {len(team_entries)}")
    print(f"  Unique SST swimmers:       {len(swimmers)}")
    print(f"  Unique events (all teams): {len(events)}")
    print()

    # Show which SST entries got FILTERED OUT (relays, diving)
    filtered_out = [
        e
        for e in all_entries
        if e.team.upper() == "SST"
        and ("relay" in e.event.lower() or "diving" in e.event.lower())
    ]
    if filtered_out:
        print(f"  SST entries filtered out (relay/diving): {len(filtered_out)}")
        for e in filtered_out:
            print(f"    {e.swimmer_name:30s}  {e.event}  ({e.seed_time})")
        print()

    # ─── BUILD POINT MATRIX ──────────────────────────────────────────────
    print(SEP)
    print("  SECTION 1: POINT MATRIX ANALYSIS")
    print(SEP)
    print()

    point_matrix = strategy._build_point_matrix(
        individual_entries, swimmers, events, "SST"
    )

    # Show per-swimmer, per-event points
    print(
        f"  {'Swimmer':30s}  {'Event':25s}  {'Seed':>8s}  {'Adj Seed':>8s}  {'Opp Rank':>8s}  {'Points':>7s}"
    )
    print(f"  {THIN}")

    factors = strategy.factors
    swimmers_with_points = set()
    pairs_with_points = 0
    total_zero_pairs = 0
    swimmer_point_summary = {}

    for swimmer in sorted(swimmers):
        swimmer_events = [e for e in events if (swimmer, e) in swimmer_event_lookup]
        swimmer_pts = []
        for event in swimmer_events:
            entry = swimmer_event_lookup[(swimmer, event)]
            pts = point_matrix.get((swimmer, event), 0.0)
            adj_time = adjust_time(entry.seed_time, event, factors)

            # Compute opponent rank for display
            import bisect

            opponent_times = sorted(
                adjust_time(e.seed_time, event, factors)
                for e in individual_entries
                if e.event == event and e.seed_time > 0 and e.team.upper() != "SST"
            )
            opp_rank = bisect.bisect_left(opponent_times, adj_time) + 1

            marker = " " if pts > 0 else " [ZERO]"
            print(
                f"  {swimmer:30s}  {event:25s}  {entry.seed_time:8.2f}  {adj_time:8.2f}  "
                f"{opp_rank:>8d}  {pts:7.1f}{marker}"
            )

            swimmer_pts.append((event, pts, opp_rank))
            if pts > 0:
                pairs_with_points += 1
                swimmers_with_points.add(swimmer)
            else:
                total_zero_pairs += 1

        swimmer_point_summary[swimmer] = swimmer_pts

    print()
    print("  POINT MATRIX SUMMARY")
    print(f"  {THIN}")
    print(f"  (swimmer, event) pairs with >0 points: {pairs_with_points}")
    print(f"  (swimmer, event) pairs with  0 points: {total_zero_pairs}")
    print(
        f"  Total swimmer-event pairs:             {pairs_with_points + total_zero_pairs}"
    )
    print(
        f"  Swimmers with at least 1 scorable event: {len(swimmers_with_points)} / {len(swimmers)}"
    )
    print()

    # Swimmers with NO scoring opportunities
    no_score_swimmers = set(swimmers) - swimmers_with_points
    if no_score_swimmers:
        print(f"  Swimmers with ZERO scoring events ({len(no_score_swimmers)}):")
        for s in sorted(no_score_swimmers):
            evts = [e for e in events if (s, e) in swimmer_event_lookup]
            print(f"    {s:30s}  entries: {', '.join(evts)}")
        print()

    # ─── CONSTRAINT ANALYSIS ─────────────────────────────────────────────
    print(SEP)
    print("  SECTION 2: CONSTRAINT ANALYSIS")
    print(SEP)
    print()

    # Divers (same logic as compare script)
    divers = set()
    for e in all_entries:
        if "Diving" in e.event and e.team == "SST":
            divers.add(e.swimmer_name)
    print(f"  Divers: {divers or 'none'}")

    # No relay swimmers passed in compare script
    relay_1_swimmers = set()
    relay_2_swimmers = set()
    relay_3_swimmers = set()

    relay_3_penalty = getattr(rules, "relay_3_counts_as_individual", False)
    print(f"  Relay 3 penalty: {relay_3_penalty}")
    print()

    # Count constraints by type
    no_time_count = 0
    max_indiv_constraints = {}
    b2b_individual_count = 0
    relay_block_count = 0

    # 1. no_time constraints
    for s in swimmers:
        for e in events:
            if (s, e) not in swimmer_event_lookup:
                no_time_count += 1

    # 2. max_indiv constraints
    for s in swimmers:
        limit = 2
        if s in divers:
            limit -= 1
        if relay_3_penalty and s in relay_3_swimmers:
            limit -= 1
        limit = max(0, limit)
        max_indiv_constraints[s] = limit

    # 3. max_entries constraints
    max_entries = getattr(rules, "max_entries_per_team_per_event", 4)

    # 4a. back-to-back (individual <-> individual)
    b2b_pairs = []
    for s in swimmers:
        swimmer_events_list = [e for e in events if (s, e) in swimmer_event_lookup]
        for event1 in swimmer_events_list:
            blocked = get_blocked_events(event1)
            for event2 in swimmer_events_list:
                if event1 == event2:
                    continue
                norm_event2 = normalize_event_name(event2)
                if norm_event2 in blocked:
                    b2b_pairs.append((s, event1, event2))
                    b2b_individual_count += 1

    # 4b. relay <-> individual blocking
    relay_map = {
        "200 Medley Relay": relay_1_swimmers,
        "200 Free Relay": relay_2_swimmers,
        "400 Free Relay": relay_3_swimmers,
    }
    relay_blocks = []
    for relay_name, relay_participants in relay_map.items():
        blocked_after = get_blocked_events(relay_name)
        for s in swimmers:
            if s not in relay_participants:
                continue
            swimmer_events_list = [e for e in events if (s, e) in swimmer_event_lookup]
            for ind_event in swimmer_events_list:
                norm_ind = normalize_event_name(ind_event)
                if relay_name in get_blocked_events(norm_ind):
                    relay_blocks.append((s, ind_event, f"pre-{relay_name}"))
                    relay_block_count += 1
                if norm_ind in blocked_after:
                    relay_blocks.append((s, ind_event, f"post-{relay_name}"))
                    relay_block_count += 1

    print("  CONSTRAINT COUNTS")
    print(f"  {THIN}")
    print(f"  no_time (swimmer has no entry for event):     {no_time_count}")
    print(
        f"  max_indiv (max 2 individual per swimmer):     {len(swimmers)} constraints"
    )
    for s in sorted(swimmers):
        lim = max_indiv_constraints[s]
        tag = ""
        if s in divers:
            tag = f" [DIVER: limit reduced to {lim}]"
        if lim != 2:
            print(f"    {s:30s}  limit={lim}{tag}")
    print(
        f"  max_entries (max {max_entries} per team per event):  {len(events)} constraints"
    )
    print(f"  back-to-back individual constraints:          {b2b_individual_count}")
    print(f"  relay blocking constraints:                   {relay_block_count}")
    print()

    # Show all back-to-back pairs
    if b2b_pairs:
        print(f"  BACK-TO-BACK PAIRS ({len(b2b_pairs)} constraints):")
        for s, e1, e2 in sorted(b2b_pairs):
            pts1 = point_matrix.get((s, e1), 0)
            pts2 = point_matrix.get((s, e2), 0)
            print(
                f"    {s:30s}  {e1:25s} ({pts1:5.1f}pts) <-> {e2:25s} ({pts2:5.1f}pts)"
            )
        print()

    if relay_blocks:
        print(f"  RELAY BLOCKING ({len(relay_blocks)} constraints):")
        for s, ind_event, description in sorted(relay_blocks):
            print(f"    {s:30s}  {ind_event:25s}  {description}")
        print()

    # ─── RUN GUROBI AND INSPECT SOLUTION ─────────────────────────────────
    print(SEP)
    print("  SECTION 3: GUROBI SOLUTION INSPECTION")
    print(SEP)
    print()

    try:
        strategy._setup_gurobi_license()
        import gurobipy as gp
        from gurobipy import GRB
    except ImportError:
        print("  ERROR: Gurobi not installed. Cannot inspect solution.")
        return

    # Build model manually to inspect it
    m = gp.Model("DiagnosticModel")
    m.setParam("OutputFlag", 0)
    m.setParam("TimeLimit", 120)

    x = m.addVars(swimmers, events, vtype=GRB.BINARY, name="x")

    # Add constraints (same as championship_strategy.py)
    constraint_counts = defaultdict(int)

    # 1. no_time
    for s in swimmers:
        for e in events:
            if (s, e) not in swimmer_event_lookup:
                m.addConstr(x[s, e] == 0, name=f"no_time_{s}_{e}")
                constraint_counts["no_time"] += 1

    # 2. max_indiv
    for s in swimmers:
        limit = max_indiv_constraints[s]
        m.addConstr(
            gp.quicksum(x[s, e] for e in events) <= limit, name=f"max_indiv_{s}"
        )
        constraint_counts["max_indiv"] += 1

    # 3. max_entries
    for e in events:
        m.addConstr(
            gp.quicksum(x[s, e] for s in swimmers) <= max_entries,
            name=f"max_entries_{e}",
        )
        constraint_counts["max_entries"] += 1

    # 4a. back-to-back individual
    for s in swimmers:
        swimmer_events_list = [e for e in events if (s, e) in swimmer_event_lookup]
        for event1 in swimmer_events_list:
            blocked = get_blocked_events(event1)
            for event2 in swimmer_events_list:
                if event1 == event2:
                    continue
                norm_event2 = normalize_event_name(event2)
                if norm_event2 in blocked:
                    m.addConstr(
                        x[s, event1] + x[s, event2] <= 1,
                        name=f"no_b2b_{s}_{event1[:10]}_{event2[:10]}",
                    )
                    constraint_counts["no_b2b"] += 1

    # 4b. relay blocking
    for relay_name, relay_participants in relay_map.items():
        blocked_after = get_blocked_events(relay_name)
        for s in swimmers:
            if s not in relay_participants:
                continue
            swimmer_events_list = [e for e in events if (s, e) in swimmer_event_lookup]
            for ind_event in swimmer_events_list:
                norm_ind = normalize_event_name(ind_event)
                if relay_name in get_blocked_events(norm_ind):
                    m.addConstr(
                        x[s, ind_event] == 0, name=f"block_pre_relay_{s}_{ind_event}"
                    )
                    constraint_counts["relay_block_pre"] += 1
                if norm_ind in blocked_after:
                    m.addConstr(
                        x[s, ind_event] == 0, name=f"block_post_relay_{s}_{ind_event}"
                    )
                    constraint_counts["relay_block_post"] += 1

    # Objective
    m.setObjective(
        gp.quicksum(
            point_matrix.get((s, e), 0) * x[s, e] for s in swimmers for e in events
        ),
        GRB.MAXIMIZE,
    )

    print("  Gurobi model built:")
    print(f"    Variables:   {m.NumVars}")
    print(f"    Constraints: {m.NumConstrs}")
    print()
    print("  Constraint breakdown:")
    for ctype, count in sorted(constraint_counts.items()):
        print(f"    {ctype:25s}  {count:>6d}")
    print()

    # Solve
    print("  Solving...")
    start = time.time()
    m.optimize()
    elapsed = (time.time() - start) * 1000
    print(f"  Status: {m.Status} ({'OPTIMAL' if m.Status == GRB.OPTIMAL else 'OTHER'})")
    print(f"  Solve time: {elapsed:.0f}ms")
    print(f"  Objective value: {m.ObjVal:.1f}")
    print()

    # Extract and display solution
    print("  SOLUTION VARIABLES (x=1):")
    print(f"  {THIN}")
    print(f"  {'Swimmer':30s}  {'Event':25s}  {'Points':>7s}")

    assigned_swimmers = set()
    total_obj_points = 0.0
    assigned_pairs = []

    for s in sorted(swimmers):
        for e in sorted(events):
            if x[s, e].X > 0.5:
                pts = point_matrix.get((s, e), 0)
                print(f"  {s:30s}  {e:25s}  {pts:7.1f}")
                assigned_swimmers.add(s)
                total_obj_points += pts
                assigned_pairs.append((s, e, pts))

    print()
    print(f"  Assigned swimmers: {len(assigned_swimmers)}")
    print(f"  Assigned (swimmer, event) pairs: {len(assigned_pairs)}")
    print(f"  Objective points (sum of matrix values): {total_obj_points:.1f}")
    print()

    # ─── UNASSIGNED ANALYSIS ─────────────────────────────────────────────
    print(SEP)
    print("  SECTION 4: WHY SWIMMERS ARE UNASSIGNED")
    print(SEP)
    print()

    unassigned = set(swimmers) - assigned_swimmers
    if not unassigned:
        print("  All swimmers are assigned!")
    else:
        print(f"  Unassigned swimmers: {len(unassigned)}")
        print()
        for s in sorted(unassigned):
            s_events = [e for e in events if (s, e) in swimmer_event_lookup]
            best_pts = (
                max(point_matrix.get((s, e), 0) for e in s_events) if s_events else 0
            )
            reason = []
            if best_pts == 0:
                reason.append("ALL events have 0 points (ranked > 16th in every event)")
            elif s in divers and max_indiv_constraints[s] == 0:
                reason.append("Diver with 0 individual slots left")
            else:
                # Check back-to-back conflicts
                scorable = [
                    (e, point_matrix.get((s, e), 0))
                    for e in s_events
                    if point_matrix.get((s, e), 0) > 0
                ]
                if scorable:
                    reason.append(
                        f"Has {len(scorable)} scorable events but not assigned — check constraints"
                    )
                    for evt, pts in scorable:
                        reason.append(f"  {evt}: {pts:.1f} pts")

            events_str = ", ".join(s_events) if s_events else "none"
            print(f"  {s:30s}  best_pts={best_pts:.1f}  entries=[{events_str}]")
            for r in reason:
                print(f"    -> {r}")
            print()

    # ─── RE-SCORE (to match compare script output) ───────────────────────
    print(SEP)
    print("  SECTION 5: RE-SCORED RESULT (accurate placement)")
    print(SEP)
    print()

    assignments = {}
    for s, e, pts in assigned_pairs:
        if s not in assignments:
            assignments[s] = []
        assignments[s].append(e)

    if assignments:
        total_rescored, event_breakdown = strategy._rescore_solution(
            assignments, all_entries, "SST"
        )
        print(f"  Re-scored total: {total_rescored:.0f} points")
        print()
        print(f"  {'Event':30s}  {'Points':>7s}")
        print(f"  {THIN}")
        for evt, pts in sorted(event_breakdown.items()):
            print(f"  {evt:30s}  {pts:7.1f}")
        print()
        print(f"  NOTE: Objective = {total_obj_points:.1f} (opponent-only ranking)")
        print(
            f"  NOTE: Re-scored = {total_rescored:.1f} (all-swimmer ranking, max 4 scorers/event)"
        )
        print(
            "  The re-scored value is what gets reported as the final 'total_points'."
        )
    else:
        print("  No assignments to re-score.")

    # ─── DIAGNOSIS SUMMARY ───────────────────────────────────────────────
    print()
    print(SEP)
    print("  DIAGNOSIS SUMMARY")
    print(SEP)
    print()

    total_possible_swimmers = len(swimmers)
    scorable_swimmers = len(swimmers_with_points)
    assigned_count = len(assigned_swimmers)

    if scorable_swimmers < total_possible_swimmers * 0.5:
        print("  [A] LIKELY CAUSE: Point matrix is zero for most swimmers.")
        print(
            f"      Only {scorable_swimmers}/{total_possible_swimmers} swimmers have any scorable event."
        )
        print(
            f"      This means {total_possible_swimmers - scorable_swimmers} swimmers rank > 16th in ALL events."
        )
        print()
    if b2b_individual_count > 0:
        # Check how many scorable pairs are eliminated by b2b
        b2b_impact = 0
        for s, e1, e2 in b2b_pairs:
            if point_matrix.get((s, e1), 0) > 0 and point_matrix.get((s, e2), 0) > 0:
                b2b_impact += 1
        if b2b_impact > 0:
            print(
                f"  [B] POSSIBLE FACTOR: Back-to-back constraints eliminate {b2b_impact} scorable pairs."
            )
            print(
                "      (Pairs where both events have >0 points, only 1 can be chosen.)"
            )
            print()
    if max_entries < 999:
        print(
            f"  [C] POSSIBLE FACTOR: max_entries={max_entries} per event limits team entries."
        )
        print()
    else:
        print(f"  [C] max_entries={max_entries} — NOT limiting (unlimited).")
        print()

    # Check if the issue is REALLY the point matrix
    scorable_by_event = defaultdict(int)
    for (s, e), pts in point_matrix.items():
        if pts > 0:
            scorable_by_event[e] += 1

    print("  Scorable swimmers per event:")
    for e in sorted(events):
        cnt = scorable_by_event.get(e, 0)
        marker = " <-- SPARSE" if cnt <= 2 else ""
        print(f"    {e:30s}  {cnt:>3d} swimmers{marker}")
    print()

    print("  FINAL NUMBERS:")
    print(f"    Total SST swimmers in model:    {total_possible_swimmers}")
    print(f"    Swimmers with scorable events:   {scorable_swimmers}")
    print(f"    Swimmers assigned by Gurobi:     {assigned_count}")
    print(f"    Objective (opponent-only rank):   {total_obj_points:.1f}")
    if assignments:
        print(f"    Re-scored (accurate placement):  {total_rescored:.1f}")
    print()

    print(SEP)
    print("  End of diagnostic")
    print(SEP)


if __name__ == "__main__":
    main()
