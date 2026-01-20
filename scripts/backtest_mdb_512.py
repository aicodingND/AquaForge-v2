import os
import sys
import time

import pandas as pd

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from swim_ai_reflex.backend.core.strategies.aqua_optimizer import AquaOptimizer
from swim_ai_reflex.backend.utils.mdb_connector import MDBConnector

DB_PATH = "/Volumes/Miguel/swimdatadump/Database Backups/SSTdata.mdb"

# Hy-Tek Stroke Codes
STROKE_MAP = {1: "Free", 2: "Back", 3: "Breast", 4: "Fly", 5: "IM"}


def load_mdb_data():
    if not os.path.exists(DB_PATH):
        raise FileNotFoundError(f"MDB at {DB_PATH} not found.")

    connector = MDBConnector(DB_PATH)
    print("Loading tables from MDB...")

    # 1. Meets
    meet_df = connector.read_table("MEET")
    # Find VCAC Regular Season Championship
    matches = meet_df[
        meet_df["MNAME"]
        .astype(str)
        .str.contains("VCAC Regular Season Championship", case=False, na=False)
    ]
    if matches.empty:
        raise ValueError(
            "Could not find VCAC Regular Season Championship in MEET table."
        )

    # Target Meet 512 specifically if available
    target_match = matches[matches["MEET"] == 512]
    if not target_match.empty:
        meet_id = 512
        print(f"Target Meet ID: {meet_id} (Verfied ID 512)")
    else:
        # Fallback to first match
        meet_id = matches["MEET"].values[0]
        print(f"Target Meet ID: {meet_id} ({matches['MNAME'].values[0]})")

    # 2. Teams
    team_df = connector.read_table("TEAM")
    seton_matches = team_df[team_df["TCODE"] == "SST"]
    if seton_matches.empty:
        raise ValueError("Could not find Seton (SST) in TEAM table.")
    seton_id = seton_matches["TEAM"].values[0]
    print(f"Seton Team ID: {seton_id}")

    # 3. Athletes
    athlete_df = connector.read_table("ATHLETE")
    # Keep only relevant cols: Athlete (ID), First, Last, Sex, Team(FK) -> TEAM1
    athlete_df = athlete_df[["ATHLETE", "FIRST", "LAST", "SEX", "TEAM1"]]

    # 4. Results
    print(f"Loading Results for Meet {meet_id}...")
    all_res = connector.read_table("RESULT")
    res_df = all_res[all_res["MEET"] == meet_id].copy()

    if res_df.empty:
        raise ValueError(f"No results found for Meet {meet_id}.")

    print(f"Found {len(res_df)} result entries.")

    return res_df, athlete_df, seton_id


def process_rosters(res_df, athlete_df, seton_id):
    # Merge Athlete Info
    # res_df 'ATHLETE' -> athlete_df 'ATHLETE'
    merged = pd.merge(
        res_df, athlete_df, left_on="ATHLETE", right_on="ATHLETE", how="left"
    )

    # Filter Individual events only
    # Assuming 'I_R' column exists. If strictly 'I', otherwise 'R'.
    # Discovery output showed 'I_R' col.
    if "I_R" in merged.columns:
        merged = merged[merged["I_R"] == "I"]

    # Construct Swimmer Name
    merged["swimmer"] = merged["FIRST"] + " " + merged["LAST"]

    # Construct Event Name
    # Map STROKE
    merged["stroke_name"] = merged["STROKE"].map(STROKE_MAP)
    merged = merged.dropna(subset=["stroke_name"])  # Drop relays/unknowns (6,7)

    merged["event"] = merged["DISTANCE"].astype(str) + " " + merged["stroke_name"]

    # Normalize SCORE (Time)
    # Ensure float
    merged["time"] = pd.to_numeric(merged["SCORE"], errors="coerce")

    # Filter 0s (NT/DQ)
    merged = merged[merged["time"] > 0]

    # Convert centiseconds to seconds
    # Heuristic: if time > 200 (200s is 3:20, 50 free is ~20s).
    # 50 Free in centiseconds is 2000+.
    # 50 Free in seconds is 20.
    # If standard is centiseconds, typical times > 1000.
    # Check max time
    if merged["time"].max() > 1000:
        merged["time"] = merged["time"] / 100.0

    merged = merged.dropna(subset=["time"])

    # Identify Team
    # res_df 'TEAM' (this is the athlete's team for this result? or ATHLETE table has Team?)
    # RESULT table has TEAM column. Athlete table has Team column.
    # Usually RESULT.TEAM is reliable for that meet.
    merged["is_seton"] = merged["TEAM"] == seton_id

    # Split into Seton and Opponent
    items = []
    for _, row in merged.iterrows():
        items.append(
            {
                "swimmer": row["swimmer"],
                "event": row["event"],
                "time": row["time"],
                "team": "seton" if row["is_seton"] else "opponent",
                "gender": row["SEX"],  # Might separate M/F?
                # AquaOptimizer usually optimizes ONE gender or MIXED?
                # Existing backtest separated genders? No, seemed mixed ("Dominic Judge", "Melissa Paradise" in same list).
                # If mixed, we optimize together?
                # Usually meets are separated by gender (Boys 50 Free, Girls 50 Free).
                # AquaOptimizer optimization function takes `events`.
                # "50 Free" is ambiguous. Usually "Boys 50 Free".
                # If we pass mixed, AquaOptimizer handles check constraints?
                # `ConstraintEngine` checks `max_entries_per_event`.
                # If we mix genders, Boys might swim against Girls?
                # We should probably SPLIT by gender.
                # "Dominic Judge" (M) vs "Melissa Paradise" (F).
                # In `optimized_results.csv` from previous run, output showed BOTH.
                # This implies the optimizer was running logically MIXED, which is WRONG for swimming (unless mixed relay).
                # But the user didn't complain yet.
                # I should PROBABLY filter for one gender, e.g. Boys.
            }
        )

    df = pd.DataFrame(items)
    return df


def main():
    try:
        res_df, athlete_df, seton_id = load_mdb_data()
        full_roster = process_rosters(res_df, athlete_df, seton_id)

        # Filter for Boys (M) optimization first (Simpler)
        boys_roster = full_roster[full_roster["gender"] == "M"].copy()

        seton_df = boys_roster[boys_roster["team"] == "seton"]
        opponent_df = boys_roster[boys_roster["team"] == "opponent"]

        print(f"Seton Boys Entries: {len(seton_df)}")
        print(f"Opponent Boys Entries: {len(opponent_df)}")

        # Optimize
        optimizer = AquaOptimizer(quality_mode="fast", use_parallel=False)

        print("Starting Optimization for Boys...")
        start_time = time.time()
        best_df, scored_df, totals, details = optimizer.optimize(
            seton_df, opponent_df, None, None
        )
        duration = time.time() - start_time

        print(f"Optimization Completed in {duration:.2f}s")
        print(f"Totals Dict: {totals}")
        print(
            f"Projected Score: Seton {totals.get('seton', 0)} - {totals.get('opponent', 0)} Opponent"
        )

        # Print optimized lineup
        events = sorted(seton_df["event"].unique())
        print("\nAssignments:")
        for event in events:
            entries = best_df[best_df["event"] == event]
            if not entries.empty:
                print(f"--- {event} ---")
                for _, row in entries.iterrows():
                    print(f"  {row['swimmer']} ({row['time']:.2f})")

    except Exception as e:
        print(f"Backtest Failed: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
