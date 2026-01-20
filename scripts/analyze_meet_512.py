import os

import pandas as pd

DATA_DIR = "/Users/mpage1/Desktop/AquaForge/AquaForge_v1.0.0-next_2026-01-10/data/real_exports/csv"


def load_csv(filename):
    return pd.read_csv(os.path.join(DATA_DIR, filename), encoding="latin1")


def main():
    print("Loading data...")
    teams_df = load_csv("teams.csv")
    load_csv("athletes.csv")
    meets_df = load_csv("meets.csv")
    results_df = load_csv("results.csv")

    TARGET_MEET_ID = 512
    meet_info = meets_df[meets_df["MEET"] == TARGET_MEET_ID].iloc[0]
    print(f"Target Meet: {meet_info['MNAME']} ({meet_info['START']})")
    print(f"Course: {meet_info['COURSE']}")

    # Filter results for this meet
    meet_results = results_df[results_df["MEET"] == TARGET_MEET_ID]
    print(f"Total Entries/Results in Meet: {len(meet_results)}")

    # Identify Teams
    team_ids = meet_results["TEAM"].unique()
    participating_teams = teams_df[teams_df["TEAM"].isin(team_ids)]
    print("\nParticipating Teams:")
    for _, team in participating_teams.iterrows():
        # Count entries for this team
        entry_count = len(meet_results[meet_results["TEAM"] == team["TEAM"]])
        print(f"- {team['TNAME']} (ID: {team['TEAM']}): {entry_count} entries")

    # Identify Date for Seed Times
    # Ensure START date is datetime
    meet_date = pd.to_datetime(meet_info["START"])
    print(f"\nMeet Date: {meet_date}")

    # Check History for Seton (Team 1)
    seton_athletes = meet_results[meet_results["TEAM"] == 1]["ATHLETE"].unique()
    print(f"\nSeton Athletes in Meet: {len(seton_athletes)}")

    # Check if we have history for these athletes
    # Filter for results BEFORE this meet
    meet_dates = meets_df[["MEET", "START"]].copy()
    try:
        meet_dates["START"] = pd.to_datetime(meet_dates["START"])
    except Exception as e:
        print(f"Warning: Could not parse some dates: {e}")

    results_with_date = results_df.merge(meet_dates, on="MEET", how="left")
    history_results = results_with_date[results_with_date["START"] < meet_date]

    print(f"Total Historical Results potentially available: {len(history_results)}")

    swimmers_with_history = 0
    for athlete_id in seton_athletes:
        athlete_history = history_results[history_results["ATHLETE"] == athlete_id]
        if not athlete_history.empty:
            swimmers_with_history += 1

    print(f"Seton Athletes with History: {swimmers_with_history}/{len(seton_athletes)}")

    # Check Event Coverage
    print("\nEvent Mapping (MTEVENT -> DISTANCE/STROKE):")
    event_mapping = (
        meet_results[["MTEVENT", "DISTANCE", "STROKE"]]
        .drop_duplicates()
        .sort_values("MTEVENT")
    )
    print(event_mapping)

    # Save these as artifacts if useful
    if swimmers_with_history > 0:
        print("\nCan proceed with backtesting.")
    else:
        print(
            "\nWARNING: No history found. Dates might be malformed or this is the first meet."
        )


if __name__ == "__main__":
    main()
