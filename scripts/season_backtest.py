#!/usr/bin/env python3
"""
Full Season Backtest Script.
Runs AquaOptimizer on all dual meets from a season and compares predicted vs actual scores.
"""

import os
import sys
import time
from typing import Dict, List, Tuple

import pandas as pd

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from swim_ai_reflex.backend.core.strategies.aqua_optimizer import AquaOptimizer
from swim_ai_reflex.backend.utils.mdb_connector import MDBConnector

DB_PATH = "/Volumes/Miguel/swimdatadump/Database Backups/SSTdata.mdb"
SETON_TEAM_ID = 1  # Seton Swimming

# Hy-Tek Stroke Codes
STROKE_MAP = {1: "Free", 2: "Back", 3: "Breast", 4: "Fly", 5: "IM"}

# Target dual meets for 2025-2026 season (meets with Seton vs one opponent)
# We'll focus on meets where Seton has clear head-to-head matchups
DUAL_MEET_IDS = [
    # 2024-2025 Season
    478,  # VCAC Regular Season Championship 2024
    488,  # VCAC Invitational 2025
    512,  # VCAC Regular Season Championship 2026
]


def load_meet_data(connector: MDBConnector, meet_id: int) -> Tuple[pd.DataFrame, Dict]:
    """Load and process meet data from MDB."""
    # Load tables
    result_df = connector.read_table("RESULT")
    athlete_df = connector.read_table("ATHLETE")
    connector.read_table("TEAM")
    meet_df = connector.read_table("MEET")

    # Get meet info
    meet_info = (
        meet_df[meet_df["MEET"] == meet_id].iloc[0].to_dict()
        if meet_id in meet_df["MEET"].values
        else {}
    )

    # Filter results for this meet
    meet_results = result_df[result_df["MEET"] == meet_id].copy()

    if meet_results.empty:
        return pd.DataFrame(), meet_info

    # Merge with athlete info
    athlete_df_slim = athlete_df[["ATHLETE", "FIRST", "LAST", "SEX", "TEAM1"]]
    merged = pd.merge(meet_results, athlete_df_slim, on="ATHLETE", how="left")

    # Filter individual events only
    if "I_R" in merged.columns:
        merged = merged[merged["I_R"] == "I"]

    # Construct swimmer name
    merged["swimmer"] = merged["FIRST"].fillna("") + " " + merged["LAST"].fillna("")

    # Construct event name
    merged["stroke_name"] = merged["STROKE"].map(STROKE_MAP)
    merged = merged.dropna(subset=["stroke_name"])
    merged["event"] = merged["DISTANCE"].astype(str) + " " + merged["stroke_name"]

    # Normalize time
    merged["time"] = pd.to_numeric(merged["SCORE"], errors="coerce")
    merged = merged[merged["time"] > 0]

    # Convert centiseconds if needed
    if merged["time"].max() > 1000:
        merged["time"] = merged["time"] / 100.0

    # Identify Seton vs Opponent
    merged["is_seton"] = merged["TEAM"] == SETON_TEAM_ID
    merged["team"] = merged["is_seton"].apply(lambda x: "seton" if x else "opponent")
    merged["gender"] = merged["SEX"]

    # Final columns
    final_df = merged[
        ["swimmer", "event", "time", "team", "gender", "TEAM", "POINTS"]
    ].copy()

    return final_df, meet_info


def get_actual_score(meet_results: pd.DataFrame) -> Tuple[float, float]:
    """Extract actual recorded score from meet results."""
    seton_points = meet_results[meet_results["team"] == "seton"]["POINTS"].sum()
    opponent_points = meet_results[meet_results["team"] == "opponent"]["POINTS"].sum()
    return seton_points, opponent_points


def run_single_backtest(
    connector: MDBConnector, meet_id: int, gender: str = "M"
) -> Dict:
    """Run backtest for a single meet."""
    result = {
        "meet_id": meet_id,
        "meet_name": "",
        "gender": gender,
        "predicted_seton": 0,
        "predicted_opponent": 0,
        "actual_seton": 0,
        "actual_opponent": 0,
        "accuracy": 0.0,
        "error": None,
    }

    try:
        full_roster, meet_info = load_meet_data(connector, meet_id)
        result["meet_name"] = meet_info.get("MNAME", f"Meet {meet_id}")

        if full_roster.empty:
            result["error"] = "No data"
            return result

        # Filter by gender
        roster = full_roster[full_roster["gender"] == gender].copy()

        if roster.empty:
            result["error"] = f"No {gender} swimmers"
            return result

        seton_df = roster[roster["team"] == "seton"]
        opponent_df = roster[roster["team"] == "opponent"]

        if seton_df.empty or opponent_df.empty:
            result["error"] = "Missing team data"
            return result

        # Get actual scores
        result["actual_seton"], result["actual_opponent"] = get_actual_score(roster)

        # Run optimizer
        optimizer = AquaOptimizer(quality_mode="fast", use_parallel=False)
        _, _, totals, _ = optimizer.optimize(seton_df, opponent_df, None, None)

        result["predicted_seton"] = totals.get("seton", 0)
        result["predicted_opponent"] = totals.get("opponent", 0)

        # Calculate accuracy (how close predicted margin is to actual margin)
        actual_margin = result["actual_seton"] - result["actual_opponent"]
        predicted_margin = result["predicted_seton"] - result["predicted_opponent"]

        if actual_margin != 0:
            result["accuracy"] = max(
                0, 100 - abs((predicted_margin - actual_margin) / actual_margin * 100)
            )
        else:
            result["accuracy"] = 100 if predicted_margin == 0 else 0

    except Exception as e:
        result["error"] = str(e)

    return result


def run_full_season_backtest(meet_ids: List[int]) -> pd.DataFrame:
    """Run backtest across all specified meets."""
    if not os.path.exists(DB_PATH):
        print(f"MDB not found at {DB_PATH}")
        return pd.DataFrame()

    connector = MDBConnector(DB_PATH)
    results = []

    print("=" * 80)
    print("FULL SEASON BACKTEST")
    print("=" * 80)

    for meet_id in meet_ids:
        print(f"\nProcessing Meet {meet_id}...")

        # Run for both genders
        for gender in ["M", "F"]:
            start = time.time()
            result = run_single_backtest(connector, meet_id, gender)
            elapsed = time.time() - start

            if result["error"]:
                print(f"  {gender}: ERROR - {result['error']}")
            else:
                print(
                    f"  {gender}: Predicted {result['predicted_seton']:.0f}-{result['predicted_opponent']:.0f} | "
                    f"Actual {result['actual_seton']:.0f}-{result['actual_opponent']:.0f} | "
                    f"Accuracy {result['accuracy']:.1f}% ({elapsed:.1f}s)"
                )

            results.append(result)

    # Create summary DataFrame
    df = pd.DataFrame(results)

    # Summary stats
    valid_results = df[df["error"].isna()]
    if not valid_results.empty:
        avg_accuracy = valid_results["accuracy"].mean()
        print("\n" + "=" * 80)
        print(
            f"SUMMARY: {len(valid_results)} backtests, Average Accuracy: {avg_accuracy:.1f}%"
        )
        print("=" * 80)

    return df


def discover_all_dual_meets(connector: MDBConnector) -> List[int]:
    """Discover all meets where Seton participated (multi-team meets)."""
    result_df = connector.read_table("RESULT")
    meet_df = connector.read_table("MEET")

    # Find meets with Seton results
    seton_results = result_df[result_df["TEAM"] == SETON_TEAM_ID]
    seton_meets = seton_results["MEET"].unique()

    # Get meet details
    meets_with_seton = meet_df[meet_df["MEET"].isin(seton_meets)].copy()

    # Parse dates
    meets_with_seton["START_PARSED"] = pd.to_datetime(
        meets_with_seton["START"], errors="coerce"
    )
    meets_with_seton["YEAR"] = meets_with_seton["START_PARSED"].dt.year

    # Filter to recent seasons (2024-2026)
    recent = meets_with_seton[meets_with_seton["YEAR"].isin([2024, 2025, 2026])]

    return recent["MEET"].tolist()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Run full season backtest")
    parser.add_argument(
        "--all", action="store_true", help="Run on all discovered meets"
    )
    parser.add_argument(
        "--meets", nargs="+", type=int, help="Specific meet IDs to test"
    )
    args = parser.parse_args()

    if args.all:
        connector = MDBConnector(DB_PATH)
        meet_ids = discover_all_dual_meets(connector)
        print(f"Discovered {len(meet_ids)} meets with Seton participation")
    elif args.meets:
        meet_ids = args.meets
    else:
        meet_ids = DUAL_MEET_IDS  # Default to sample meets

    results_df = run_full_season_backtest(meet_ids)

    # Save results
    output_path = "data/backtest/season_backtest_results.csv"
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    results_df.to_csv(output_path, index=False)
    print(f"\nResults saved to {output_path}")
