#!/usr/bin/env python3
"""
Season Backtest Discovery Script.
Queries all meets from SSTdata.mdb and assembles data needed for full-season backtesting.
"""

import os
import sys

import pandas as pd

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from swim_ai_reflex.backend.utils.mdb_connector import MDBConnector

DB_PATH = "/Volumes/Miguel/swimdatadump/Database Backups/SSTdata.mdb"


def discover_season_meets():
    """Discover all meets for a season and summarize data availability."""
    if not os.path.exists(DB_PATH):
        print(f"MDB not found at {DB_PATH}")
        return

    connector = MDBConnector(DB_PATH)

    # Load MEET table
    meet_df = connector.read_table("MEET")
    print(f"Total Meets in DB: {len(meet_df)}")

    # Parse START date (format: 'MM/DD/YY HH:MM:SS')
    meet_df["START_PARSED"] = pd.to_datetime(meet_df["START"], errors="coerce")
    meet_df["YEAR"] = meet_df["START_PARSED"].dt.year

    # Group by year
    print("\nMeets by Year:")
    year_counts = meet_df.groupby("YEAR").size()
    print(year_counts)

    # Latest season (2026 based on previous discovery)
    # Let's also look at 2025 and 2024
    recent_years = [2024, 2025, 2026]
    for year in recent_years:
        year_meets = meet_df[meet_df["YEAR"] == year]
        if not year_meets.empty:
            print(f"\n=== {year} Season ({len(year_meets)} meets) ===")
            for _, row in year_meets.iterrows():
                print(
                    f"  {row['MEET']}: {row['MNAME']} ({row['START_PARSED'].strftime('%Y-%m-%d') if pd.notna(row['START_PARSED']) else 'N/A'})"
                )

    # Load RESULT table to check data completeness
    result_df = connector.read_table("RESULT")

    # Count results per meet
    result_counts = result_df.groupby("MEET").size().reset_index(name="result_count")

    # Merge with meets to see which have data
    meet_with_results = pd.merge(meet_df, result_counts, on="MEET", how="left")
    meet_with_results["result_count"] = (
        meet_with_results["result_count"].fillna(0).astype(int)
    )

    # Show meets with results for recent years
    print("\n=== Meets with Results (2024-2026) ===")
    recent_with_data = meet_with_results[
        (meet_with_results["YEAR"].isin(recent_years))
        & (meet_with_results["result_count"] > 0)
    ].sort_values("START_PARSED")

    print(f"{'ID':<6} {'DATE':<12} {'RESULTS':<8} {'NAME'}")
    print("-" * 70)
    for _, row in recent_with_data.iterrows():
        date_str = (
            row["START_PARSED"].strftime("%Y-%m-%d")
            if pd.notna(row["START_PARSED"])
            else "N/A"
        )
        print(
            f"{row['MEET']:<6} {date_str:<12} {row['result_count']:<8} {row['MNAME'][:50]}"
        )

    return recent_with_data


def analyze_meet_structure(meet_id: int):
    """Analyze structure of a single meet for backtest feasibility."""
    connector = MDBConnector(DB_PATH)

    # Load RESULT for this meet
    result_df = connector.read_table("RESULT")
    meet_results = result_df[result_df["MEET"] == meet_id]

    if meet_results.empty:
        print(f"No results for Meet {meet_id}")
        return

    print(f"\nMeet {meet_id} Analysis:")
    print(f"  Total Results: {len(meet_results)}")

    # Individual vs Relay
    if "I_R" in meet_results.columns:
        ir_counts = meet_results["I_R"].value_counts()
        print(f"  Individual (I): {ir_counts.get('I', 0)}")
        print(f"  Relay (R): {ir_counts.get('R', 0)}")

    # Teams participating
    team_counts = meet_results["TEAM"].value_counts()
    print(f"  Teams: {len(team_counts)}")

    # Load TEAM names
    team_df = connector.read_table("TEAM")
    for team_id, count in team_counts.head(10).items():
        team_name = team_df[team_df["TEAM"] == team_id]["TNAME"].values
        name = team_name[0] if len(team_name) > 0 else "Unknown"
        print(f"    {team_id}: {name} ({count} entries)")

    # Check POINTS column (actual scored points)
    if "POINTS" in meet_results.columns:
        total_points = meet_results["POINTS"].sum()
        print(f"  Total Points Recorded: {total_points}")


if __name__ == "__main__":
    recent_meets = discover_season_meets()

    if recent_meets is not None and not recent_meets.empty:
        # Analyze first few meets with data
        sample_meets = recent_meets["MEET"].head(3).tolist()
        for meet_id in sample_meets:
            analyze_meet_structure(meet_id)
