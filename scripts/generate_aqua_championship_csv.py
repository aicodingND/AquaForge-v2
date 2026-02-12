#!/usr/bin/env python3
"""
Generate organized Aqua Optimizer championship CSV for Meet 512.

Outputs a clean CSV organized by:
  - Boys events in meet order
  - Girls events in meet order
  - Per-event swimmer placements and points
  - Running and final team totals (Seton vs Opponents)

Usage:
    python scripts/generate_aqua_championship_csv.py
"""

import os
import sys
import time

import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from swim_ai_reflex.backend.core.rules import get_meet_profile
from swim_ai_reflex.backend.core.scoring import full_meet_scoring
from swim_ai_reflex.backend.core.strategies.aqua_optimizer import (
    FatigueModel,
    Lineup,
    ScoringEngine,
    ScoringProfile,
    create_aqua_optimizer,
)

# =============================================================================
# CONSTANTS
# =============================================================================

MEET_PROFILE = "vcac_championship"
DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "backtest", "meet_512")
OUTPUT_DIR = DATA_DIR

SETON_ROSTER = os.path.join(DATA_DIR, "seton_roster_512.csv")
OPPONENT_ROSTER = os.path.join(DATA_DIR, "opponent_roster_512.csv")

# Official VCAC meet event order (individual events only)
BOYS_EVENTS = [
    "B 200 Free",
    "B 200 IM",
    "B 50 Free",
    "B 100 Fly",
    "B 100 Free",
    "B 500 Free",
    "B 100 Back",
    "B 100 Breast",
]

GIRLS_EVENTS = [
    "G 200 Free",
    "G 200 IM",
    "G 50 Free",
    "G 100 Fly",
    "G 100 Free",
    "G 500 Free",
    "G 100 Back",
    "G 100 Breast",
]

ALL_EVENTS = BOYS_EVENTS + GIRLS_EVENTS


def load_roster(path: str) -> pd.DataFrame:
    """Load roster CSV and melt into long format (swimmer, event, time)."""
    df = pd.read_csv(path)
    events = [
        "50 Free",
        "100 Free",
        "200 Free",
        "500 Free",
        "100 Back",
        "100 Breast",
        "100 Fly",
        "200 IM",
    ]

    rows = []
    for _, row in df.iterrows():
        name = row["name"]
        gender = row["gender"]
        prefix = "B" if gender == "M" else "G"

        for ev in events:
            if ev in df.columns and pd.notna(row[ev]) and float(row[ev]) > 0:
                rows.append(
                    {
                        "swimmer": name,
                        "event": f"{prefix} {ev}",
                        "time": float(row[ev]),
                        "gender": gender,
                        "team": "Seton" if "seton" in path.lower() else "Opponent",
                    }
                )

    return pd.DataFrame(rows)


def score_lineup_detailed(
    lineup: Lineup,
    seton_roster: pd.DataFrame,
    opponent_roster: pd.DataFrame,
    events: list[str],
    scoring_engine: ScoringEngine,
) -> list[dict]:
    """
    Re-scores a lineup event by event using EXACTLY the same logic as
    ScoringEngine.score_lineup, but captures per-placement detail.

    Mirrors aqua_optimizer.py:528-578 exactly:
      - Seton entries come from the lineup
      - Opponent entries: opp_roster[opp_roster["event"] == event].to_dict("records")[:4]
    """
    event_details = []

    for event in events:
        is_relay = "Relay" in event

        # Seton entries from lineup (same as score_lineup)
        seton_swimmers = lineup.get_event_swimmers(event)
        seton_entries = []
        for swimmer in seton_swimmers:
            row = seton_roster[
                (seton_roster["swimmer"] == swimmer) & (seton_roster["event"] == event)
            ]
            if not row.empty:
                seton_entries.append(row.iloc[0].to_dict())

        # Opponent entries — EXACT same as score_lineup: first 4 rows, NOT sorted
        opp_rows = opponent_roster[opponent_roster["event"] == event]
        opponent_entries = opp_rows.to_dict("records")[:4]

        # Score this event (returns placements with points)
        seton_pts, opp_pts, placements = scoring_engine.score_event(
            seton_entries, opponent_entries, is_relay
        )

        event_details.append(
            {
                "event": event,
                "seton_pts": seton_pts,
                "opp_pts": opp_pts,
                "placements": placements,
                "seton_entries": seton_entries,
                "opp_entries": opponent_entries,
            }
        )

    return event_details


def main():
    print("=" * 78)
    print("  AQUA OPTIMIZER — MEET 512 CHAMPIONSHIP BREAKDOWN")
    print("  VCAC Regular Season Championship | vcac_championship scoring")
    print("=" * 78)
    print()

    # Load rosters
    print("Loading rosters...")
    seton_df = load_roster(SETON_ROSTER)
    opp_df = load_roster(OPPONENT_ROSTER)
    print(f"  Seton entries: {len(seton_df)}")
    print(f"  Opponent entries: {len(opp_df)}")

    # Run optimizer
    print("\nRunning Aqua optimizer...")
    rules = get_meet_profile(MEET_PROFILE)
    print(f"  Profile: {MEET_PROFILE}")
    print(f"  Ind points: {rules.individual_points}")
    print(f"  Relay points: {rules.relay_points}")

    optimizer = create_aqua_optimizer(profile=MEET_PROFILE)

    t0 = time.time()
    best_seton_df, _scored_df, totals, details = optimizer.optimize(
        seton_roster=seton_df,
        opponent_roster=opp_df,
        scoring_fn=full_meet_scoring,
        rules=rules,
    )
    elapsed = time.time() - t0

    seton_total = totals.get("seton", 0)
    opp_total = totals.get("opponent", 0)
    print(f"\n  Aqua completed in {elapsed:.1f}s")
    print(f"  Seton: {seton_total:.0f} pts  |  Opponent: {opp_total:.0f} pts")

    # Reconstruct the Lineup object from best_seton_df
    assignments: dict[str, list[str]] = {}
    if best_seton_df is not None and not best_seton_df.empty:
        for _, row in best_seton_df.iterrows():
            swimmer = row["swimmer"]
            event = row["event"]
            assignments.setdefault(swimmer, []).append(event)
    lineup = Lineup(assignments=assignments)

    # Use the same scoring engine the optimizer uses internally
    profile = ScoringProfile.vcac_championship()
    fatigue = FatigueModel(enabled=True)
    scoring_engine = ScoringEngine(profile, fatigue)

    # Re-score with detailed per-event breakdown (matching optimizer internals)
    print("\nRe-scoring lineup event by event...")
    event_details = score_lineup_detailed(
        lineup, seton_df, opp_df, ALL_EVENTS, scoring_engine
    )

    # Verify totals match
    verify_seton = sum(d["seton_pts"] for d in event_details)
    verify_opp = sum(d["opp_pts"] for d in event_details)
    print(f"  Verification: Seton={verify_seton:.0f}  Opp={verify_opp:.0f}")
    if abs(verify_seton - seton_total) > 1:
        print(
            f"  WARNING: Seton total mismatch! Optimizer={seton_total:.0f} vs Rescore={verify_seton:.0f}"
        )

    # Build the organized CSV
    csv_rows = []
    boys_seton = 0.0
    boys_opp = 0.0
    girls_seton = 0.0
    girls_opp = 0.0
    running_seton = 0.0
    running_opp = 0.0

    for section_label, section_events in [
        ("Boys", BOYS_EVENTS),
        ("Girls", GIRLS_EVENTS),
    ]:
        # Section header
        csv_rows.append(
            {
                "section": section_label,
                "event": f"--- {section_label.upper()} EVENTS ---",
                "place": "",
                "swimmer": "",
                "team": "",
                "seed_time": "",
                "points": "",
                "event_sst": "",
                "event_opp": "",
                "running_sst": "",
                "running_opp": "",
            }
        )

        section_seton = 0.0
        section_opp = 0.0

        for ed in event_details:
            if ed["event"] not in section_events:
                continue

            ev = ed["event"]
            seton_pts = ed["seton_pts"]
            opp_pts = ed["opp_pts"]
            running_seton += seton_pts
            running_opp += opp_pts
            section_seton += seton_pts
            section_opp += opp_pts

            # Build placement rows from the actual scored placements
            place_num = 0
            for p in ed["placements"]:
                pts = p.get("points", 0)
                is_eligible = p.get("scoring_eligible", False)
                team = p.get("team", "")
                team_label = "SST" if team == "seton" else "OPP"
                t = p.get("time", 0)

                if is_eligible and pts > 0:
                    place_num += 1
                    csv_rows.append(
                        {
                            "section": section_label,
                            "event": ev,
                            "place": place_num,
                            "swimmer": p.get("swimmer", "?"),
                            "team": team_label,
                            "seed_time": f"{t:.2f}" if t else "",
                            "points": int(pts),
                            "event_sst": seton_pts if place_num == 1 else "",
                            "event_opp": opp_pts if place_num == 1 else "",
                            "running_sst": running_seton if place_num == 1 else "",
                            "running_opp": running_opp if place_num == 1 else "",
                        }
                    )

        # Section subtotal
        if section_label == "Boys":
            boys_seton = section_seton
            boys_opp = section_opp
        else:
            girls_seton = section_seton
            girls_opp = section_opp

        csv_rows.append(
            {
                "section": section_label,
                "event": f"{section_label.upper()} SUBTOTAL",
                "place": "",
                "swimmer": "",
                "team": "",
                "seed_time": "",
                "points": "",
                "event_sst": section_seton,
                "event_opp": section_opp,
                "running_sst": running_seton,
                "running_opp": running_opp,
            }
        )

        # Spacer between boys and girls
        csv_rows.append({k: "" for k in csv_rows[0]})

    # Grand total
    grand_seton = boys_seton + girls_seton
    grand_opp = boys_opp + girls_opp
    csv_rows.append(
        {
            "section": "TOTAL",
            "event": "GRAND TOTAL",
            "place": "",
            "swimmer": "",
            "team": "",
            "seed_time": "",
            "points": "",
            "event_sst": grand_seton,
            "event_opp": grand_opp,
            "running_sst": grand_seton,
            "running_opp": grand_opp,
        }
    )

    # Write CSV
    out_df = pd.DataFrame(csv_rows)
    out_path = os.path.join(OUTPUT_DIR, "aqua_championship_breakdown_512.csv")
    out_df.to_csv(out_path, index=False)

    # Print clean summary
    print(f"\n{'=' * 78}")
    print(f"  OUTPUT: {out_path}")
    print(f"{'=' * 78}")

    print(f"\n  {'Event':<20} {'SST':>6} {'OPP':>6} {'Margin':>8}")
    print(f"  {'─' * 42}")

    for section_label, section_events in [
        ("BOYS", BOYS_EVENTS),
        ("GIRLS", GIRLS_EVENTS),
    ]:
        print(f"\n  --- {section_label} ---")
        for ed in event_details:
            if ed["event"] in section_events:
                s, o = ed["seton_pts"], ed["opp_pts"]
                margin = s - o
                sign = "+" if margin >= 0 else ""
                print(f"  {ed['event']:<20} {s:>6.0f} {o:>6.0f} {sign}{margin:>7.0f}")

    print(f"\n  {'─' * 42}")
    print(
        f"  {'Boys subtotal':<20} {boys_seton:>6.0f} {boys_opp:>6.0f} {'+' if boys_seton >= boys_opp else ''}{boys_seton - boys_opp:>7.0f}"
    )
    print(
        f"  {'Girls subtotal':<20} {girls_seton:>6.0f} {girls_opp:>6.0f} {'+' if girls_seton >= girls_opp else ''}{girls_seton - girls_opp:>7.0f}"
    )
    print(f"  {'─' * 42}")
    print(
        f"  {'GRAND TOTAL':<20} {grand_seton:>6.0f} {grand_opp:>6.0f} {'+' if grand_seton >= grand_opp else ''}{grand_seton - grand_opp:>7.0f}"
    )
    print(f"\n  Optimizer reported: Seton={seton_total:.0f}  Opp={opp_total:.0f}")


if __name__ == "__main__":
    main()
