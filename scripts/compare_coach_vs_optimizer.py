#!/usr/bin/env python3
"""
Three-way comparison: Coach's Picks vs Optimizer vs Actual Outcomes.

Fair methodology:
  1. Extract coach's INDIVIDUAL event picks (max 2 per swimmer, relay legs removed)
  2. Score BOTH coach and optimizer lineups using seed times (apples-to-apples)
  3. Also show actual race-day points for reference

Relay leg identification: 50 Free and 100 Free entries beyond 2 individual events
are relay splits (200FR Relay → 50 Free legs, 400FR Relay → 100 Free legs).
"""

import os
import sys
from collections import defaultdict

import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from swim_ai_reflex.backend.core.rules import get_meet_profile
from swim_ai_reflex.backend.pipelines.championship import (
    ChampionshipInput,
    create_championship_pipeline,
)

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "backtest", "meet_512")
MEET_PROFILE = "vcac_championship"
MEET_NAME = "VCAC Regular Season Championship"

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

TEAM_ID_MAP = {
    1: "Seton",
    29: "Trinity",
    30: "Fredericksburg Christian",
    48: "Oakcrest",
    158: "Immanuel Christian",
    199: "St. John Paul",
}

RELAY_LEG_EVENTS = {"50 Free", "100 Free"}  # Events that double as relay leg splits

rules = get_meet_profile(MEET_PROFILE)
PTS_TABLE = rules.individual_points
MAX_SCORERS = rules.max_scorers_per_team_individual
MAX_IND = rules.max_individual_events_per_swimmer  # 2


def load_data():
    seton_df = pd.read_csv(os.path.join(DATA_DIR, "seton_roster_512.csv"))
    opp_df = pd.read_csv(os.path.join(DATA_DIR, "opponent_roster_512.csv"))
    actual_raw = pd.read_csv(os.path.join(DATA_DIR, "actual_results_512.csv"))

    actual_raw["team_id"] = pd.to_numeric(actual_raw["team_id"], errors="coerce")
    athlete_team = {}
    for _, r in actual_raw.iterrows():
        aid, tid = r.get("athlete_id"), r.get("team_id")
        if pd.notna(aid) and pd.notna(tid):
            athlete_team[int(aid)] = TEAM_ID_MAP.get(int(tid), f"Team_{tid}")

    gender_lookup = {}
    for _, r in pd.concat([seton_df, opp_df]).iterrows():
        if pd.notna(r.get("name")) and pd.notna(r.get("gender")):
            gender_lookup[r["name"]] = r["gender"]

    # Melt rosters to long format
    def melt(df, default_team=None):
        out = []
        for _, row in df.iterrows():
            name, gender = row.get("name", ""), row.get("gender", "")
            aid = row.get("id")
            if not name or pd.isna(name):
                continue
            team = default_team or athlete_team.get(
                int(aid) if pd.notna(aid) else -1, "Unknown"
            )
            pfx = "Boys" if gender == "M" else "Girls"
            for ev in ROSTER_EVENTS:
                t = row.get(ev)
                if pd.notna(t) and float(t) > 0:
                    out.append(
                        {
                            "swimmer_name": name,
                            "team": team,
                            "event": f"{pfx} {ev}",
                            "seed_time": float(t),
                            "gender": gender,
                        }
                    )
        return out

    seton_entries = melt(seton_df, "Seton")
    opp_entries = melt(opp_df)
    all_entries = seton_entries + opp_entries

    # Build seed time lookup: (swimmer, event) → seed_time
    seed_lookup = {}
    for e in all_entries:
        seed_lookup[(e["swimmer_name"], e["event"])] = e["seed_time"]

    # Clean actual results
    actual_raw["team"] = actual_raw["team_id"].map(TEAM_ID_MAP).fillna("Unknown")
    actual_raw["dq"] = actual_raw["dq"].astype(str).str.strip()
    valid = actual_raw[actual_raw["dq"].isin(["", "nan", "None"])].copy()
    valid["time"] = pd.to_numeric(valid["time"], errors="coerce")
    valid = valid.dropna(subset=["time"])
    valid = valid[valid["time"] > 0]
    valid["gender"] = valid["athlete"].map(gender_lookup)
    valid = valid.dropna(subset=["gender"])
    valid["event_full"] = valid.apply(
        lambda r: f"{'Boys' if r['gender'] == 'M' else 'Girls'} {r['event']}", axis=1
    )

    return seton_df, all_entries, seton_entries, valid, seed_lookup, gender_lookup


def extract_coach_individual_events(actual_df):
    """
    Extract each swimmer's individual event entries, removing relay leg splits.

    Logic: For each swimmer, if they have >2 distinct events, the 50 Free / 100 Free
    entries are likely relay legs. Keep the 2 events where they scored or had best
    placement (non-relay events prioritized).
    """
    coach_events = defaultdict(list)  # swimmer → [(event_full, time)]

    # Dedup relay splits first: keep fastest per swimmer per event
    deduped = actual_df.sort_values("time").drop_duplicates(
        subset=["athlete", "event_full"], keep="first"
    )

    for _, row in deduped.iterrows():
        coach_events[row["athlete"]].append(
            {
                "event": row["event_full"],
                "base_event": row["event"],  # without gender prefix
                "time": row["time"],
                "team": row["team"],
            }
        )

    # Now identify individual events (remove relay legs)
    individual_picks = {}
    for swimmer, entries in coach_events.items():
        if len(entries) <= MAX_IND:
            # 2 or fewer events — all individual
            individual_picks[swimmer] = entries
        else:
            # >2 events: need to separate individual from relay legs
            # Non-relay-leg events (200 Free, 500 Free, 100 Back, etc.) are definitely individual
            definite_individual = [
                e for e in entries if e["base_event"] not in RELAY_LEG_EVENTS
            ]
            maybe_relay = [e for e in entries if e["base_event"] in RELAY_LEG_EVENTS]

            if len(definite_individual) >= MAX_IND:
                # All individual slots filled by non-relay-leg events
                individual_picks[swimmer] = definite_individual[:MAX_IND]
            else:
                # Fill remaining slots with the fastest 50 Free / 100 Free
                remaining = MAX_IND - len(definite_individual)
                maybe_relay.sort(key=lambda x: x["time"])
                individual_picks[swimmer] = (
                    definite_individual + maybe_relay[:remaining]
                )

    return individual_picks


def score_lineup_with_seeds(
    swimmer_events, seed_lookup, all_entries, team_filter="Seton"
):
    """
    Score a lineup using seed times against all opponents.
    swimmer_events: {swimmer: [event_full, ...]}
    Returns: {swimmer: {event: pts}}
    """
    # Build event pools: opponents + our lineup
    opp_by_event = defaultdict(list)
    for e in all_entries:
        if team_filter.lower() not in e["team"].lower():
            opp_by_event[e["event"]].append(e)

    our_by_event = defaultdict(list)
    for swimmer, events in swimmer_events.items():
        for ev in events:
            seed = seed_lookup.get((swimmer, ev))
            if seed:
                our_by_event[ev].append(
                    {
                        "swimmer_name": swimmer,
                        "team": team_filter,
                        "event": ev,
                        "seed_time": seed,
                    }
                )

    # Score each event
    results = {}
    for event in set(list(opp_by_event.keys()) + list(our_by_event.keys())):
        pool = opp_by_event.get(event, []) + our_by_event.get(event, [])
        pool.sort(key=lambda x: x["seed_time"])

        team_count = defaultdict(int)
        place = 0
        for e in pool:
            place += 1
            team = e["team"]
            if team_count[team] >= MAX_SCORERS:
                continue
            team_count[team] += 1
            pts = PTS_TABLE[place - 1] if place <= len(PTS_TABLE) else 0
            if team_filter.lower() in team.lower():
                swimmer = e["swimmer_name"]
                results.setdefault(swimmer, {})[event] = {
                    "pts": pts,
                    "seed": e["seed_time"],
                    "place": place,
                }

    return results


def main():
    print("Loading data...")
    seton_df, all_entries, seton_entries, actual_df, seed_lookup, gender_lookup = (
        load_data()
    )

    # --- 1) Extract coach's individual events (relay legs removed) ---
    print("Extracting coach's individual picks (relay legs removed)...")
    coach_ind = extract_coach_individual_events(actual_df)

    # Filter to Seton only
    seton_swimmers = set(seton_df["name"].dropna().tolist())
    coach_seton = {s: evts for s, evts in coach_ind.items() if s in seton_swimmers}

    # Verify
    max_ev = max(len(v) for v in coach_seton.values()) if coach_seton else 0
    print(f"  Max individual events per Seton swimmer: {max_ev}")
    entered = sum(1 for v in coach_seton.values() if v)
    print(f"  Seton swimmers entered: {entered}")

    # --- 2) Run Gurobi optimizer ---
    print("Running Gurobi optimizer...")
    try:
        pipeline = create_championship_pipeline(meet_profile=MEET_PROFILE)
        inp = ChampionshipInput(
            entries=all_entries,
            target_team="Seton",
            meet_name=MEET_NAME,
            meet_profile=MEET_PROFILE,
        )
        result = pipeline.run(inp, stage="entries")
        opt_assignments = result.entry_assignments or {}
        print(f"  Gurobi assigned {len(opt_assignments)} swimmers")
    except Exception as e:
        print(f"  Gurobi failed: {e}")
        opt_assignments = {}

    # --- 3) Score both lineups using seed times (fair comparison) ---
    print("Scoring both lineups with seed times...")

    # Coach lineup: convert to {swimmer: [event_full, ...]}
    coach_lineup = {s: [e["event"] for e in evts] for s, evts in coach_seton.items()}
    coach_scores = score_lineup_with_seeds(coach_lineup, seed_lookup, all_entries)

    # Optimizer lineup
    opt_scores = score_lineup_with_seeds(opt_assignments, seed_lookup, all_entries)

    # --- 4) Also score actual results for reference ---
    print("Scoring actual results for reference...")
    actual_event_pts = {}
    for event_name, ev_df in actual_df.drop_duplicates(
        subset=["athlete", "event_full"], keep="first"
    ).groupby("event_full"):
        sorted_ev = ev_df.sort_values("time")
        team_count = defaultdict(int)
        place = 0
        for _, row in sorted_ev.iterrows():
            place += 1
            team = row["team"]
            if team_count[team] >= MAX_SCORERS:
                continue
            team_count[team] += 1
            pts = PTS_TABLE[place - 1] if place <= len(PTS_TABLE) else 0
            if team == "Seton":
                actual_event_pts.setdefault(row["athlete"], {})[event_name] = pts

    # --- 5) Build comparison table ---
    rows = []
    for _, rrow in seton_df.iterrows():
        swimmer = rrow["name"]
        gender = rrow["gender"]
        if pd.isna(swimmer):
            continue

        # Coach (individual events, seed-scored)
        c_evts = coach_seton.get(swimmer, [])
        c_scored = coach_scores.get(swimmer, {})
        c_seed_pts = sum(v["pts"] for v in c_scored.values())
        c_actual_pts = sum(actual_event_pts.get(swimmer, {}).values())
        c_event_strs = []
        for e in c_evts:
            ev = e["event"]
            short = ev.replace("Girls ", "G ").replace("Boys ", "B ")
            info = c_scored.get(ev, {})
            seed = seed_lookup.get((swimmer, ev), 0)
            seed_pts = info.get("pts", 0)
            seed_place = info.get("place", "?")
            c_event_strs.append(
                f"{short} (seed:{seed:.1f} P{seed_place} {seed_pts}pts)"
            )

        # Optimizer (seed-scored)
        o_evts = opt_assignments.get(swimmer, [])
        o_scored = opt_scores.get(swimmer, {})
        o_seed_pts = sum(v["pts"] for v in o_scored.values())
        o_event_strs = []
        for ev in o_evts:
            short = ev.replace("Girls ", "G ").replace("Boys ", "B ")
            info = o_scored.get(ev, {})
            seed = seed_lookup.get((swimmer, ev), 0)
            seed_pts = info.get("pts", 0)
            seed_place = info.get("place", "?")
            o_event_strs.append(
                f"{short} (seed:{seed:.1f} P{seed_place} {seed_pts}pts)"
            )

        # Status
        c_set = set(e["event"] for e in c_evts)
        o_set = set(o_evts)
        if not c_evts and not o_evts:
            status = "Neither"
        elif c_set == o_set:
            status = "MATCH"
        elif not c_evts:
            status = "Opt only"
        elif not o_evts:
            status = "Coach only"
        else:
            status = "DIFFER"

        rows.append(
            {
                "swimmer": swimmer,
                "gender": gender,
                "status": status,
                "coach_events": " | ".join(c_event_strs) if c_event_strs else "-",
                "coach_seed_pts": c_seed_pts,
                "coach_actual_pts": c_actual_pts,
                "optimizer_events": " | ".join(o_event_strs) if o_event_strs else "-",
                "optimizer_seed_pts": o_seed_pts,
                "delta_seed": o_seed_pts - c_seed_pts,
            }
        )

    df = pd.DataFrame(rows)

    # Split and save
    girls = (
        df[df["gender"] == "F"]
        .sort_values("delta_seed", ascending=False)
        .reset_index(drop=True)
    )
    boys = (
        df[df["gender"] == "M"]
        .sort_values("delta_seed", ascending=False)
        .reset_index(drop=True)
    )

    girls_path = os.path.join(DATA_DIR, "comparison_girls_512.csv")
    boys_path = os.path.join(DATA_DIR, "comparison_boys_512.csv")
    girls.to_csv(girls_path, index=False)
    boys.to_csv(boys_path, index=False)

    # Print
    for label, sub in [("GIRLS", girls), ("BOYS", boys)]:
        print(f"\n{'=' * 85}")
        print(f"  {label}  (seed-time scoring, relay legs removed)")
        print(f"{'=' * 85}")
        active = sub[sub["status"] != "Neither"]
        print(
            f"\n  {'Swimmer':<22} {'Status':<10} {'Coach':>7} {'Optim':>7} {'Delta':>7}  {'Actual':>7}"
        )
        print(f"  {'-' * 62}")
        for _, r in active.iterrows():
            d = f"{r['delta_seed']:+.0f}" if r["delta_seed"] != 0 else "0"
            actual = (
                f"{r['coach_actual_pts']:.0f}" if r["coach_actual_pts"] > 0 else "-"
            )
            print(
                f"  {r['swimmer']:<22} {r['status']:<10} {r['coach_seed_pts']:>7.0f} {r['optimizer_seed_pts']:>7.0f} {d:>7}  {actual:>7}"
            )

        # Differ details
        differs = active[active["status"] == "DIFFER"]
        if not differs.empty:
            print("\n  Event Detail (DIFFER):")
            for _, r in differs.iterrows():
                if r["delta_seed"] == 0:
                    continue
                print(f"    {r['swimmer']}  (delta: {r['delta_seed']:+.0f}):")
                print(f"      Coach: {r['coach_events']}")
                print(f"      Optim: {r['optimizer_events']}")

    # Summary
    print(f"\n{'=' * 85}")
    print("  SUMMARY (Seed-Time Scored, Fair Comparison)")
    print(f"{'=' * 85}")
    active = df[df["status"] != "Neither"]
    for label, sub in [
        ("Girls", active[active["gender"] == "F"]),
        ("Boys", active[active["gender"] == "M"]),
        ("Total", active),
    ]:
        c = sub["coach_seed_pts"].sum()
        o = sub["optimizer_seed_pts"].sum()
        a = sub["coach_actual_pts"].sum()
        m = (sub["status"] == "MATCH").sum()
        d = (sub["status"] == "DIFFER").sum()
        print(f"\n  {label}:")
        print(f"    Coach (seed):      {c:>5.0f} pts")
        print(f"    Optimizer (seed):  {o:>5.0f} pts")
        print(f"    Delta:             {o - c:>+5.0f} pts")
        print(f"    Coach (actual):    {a:>5.0f} pts  (race-day reference)")
        print(f"    Matches: {m}  |  Differs: {d}")

    print(f"\n  Saved: {girls_path}")
    print(f"  Saved: {boys_path}")


if __name__ == "__main__":
    main()
