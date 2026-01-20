import os

import pandas as pd

DATA_DIR = "/Users/mpage1/Desktop/AquaForge/AquaForge_v1.0.0-next_2026-01-10/data/real_exports/csv"
OUTPUT_DIR = "/Users/mpage1/Desktop/AquaForge/AquaForge_v1.0.0-next_2026-01-10/data/backtest/meet_512"

os.makedirs(OUTPUT_DIR, exist_ok=True)


def load_csv(filename):
    return pd.read_csv(os.path.join(DATA_DIR, filename), encoding="latin1")


def yards_to_seconds(time_str):
    # This is a placeholder. In real data, 'SCORE' in results.csv is often centiseconds.
    # We need to check how results are stored.
    # Based on previous analysis, 'SCORE' is an integer, likely centiseconds?
    # e.g., 2707 -> 27.07 seconds.
    return time_str / 100.0


def main():
    print("Loading data...")
    load_csv("teams.csv")
    athletes_df = load_csv("athletes.csv")
    meets_df = load_csv("meets.csv")
    results_df = load_csv("results.csv")

    TARGET_MEET_ID = 512
    # Ensure date parsing works
    meets_df["START"] = pd.to_datetime(meets_df["START"], errors="coerce")
    meet_info = meets_df[meets_df["MEET"] == TARGET_MEET_ID].iloc[0]
    meet_date = meet_info["START"]
    print(f"Generating inputs for Meet {TARGET_MEET_ID} ({meet_date})...")

    # 1. Filter results for this meet to get the roster
    meet_results = results_df[results_df["MEET"] == TARGET_MEET_ID]

    # 2. Separate Seton and Opponents
    SETON_TEAM_ID = 1
    # Find active opponent teams in this meet
    opponent_team_ids = meet_results[meet_results["TEAM"] != SETON_TEAM_ID][
        "TEAM"
    ].unique()

    print(f"Seton Team ID: {SETON_TEAM_ID}")
    print(f"Opponent Team IDs: {opponent_team_ids}")

    # 3. Calculate Seed Times (Best times prior to meet)
    # Join results with meet dates
    results_with_date = results_df.merge(
        meets_df[["MEET", "START"]], on="MEET", how="left"
    )
    # Filter for history
    history_df = results_with_date[results_with_date["START"] < meet_date]

    # Define events of interest (standard HS events)
    # Map (distance, stroke) to Event Name
    # 1=Free, 2=Back, 3=Breast, 4=Fly, 5=IM
    event_map = {
        (50, 1): "50 Free",
        (100, 1): "100 Free",
        (200, 1): "200 Free",
        (500, 1): "500 Free",
        (100, 2): "100 Back",
        (100, 3): "100 Breast",
        (100, 4): "100 Fly",
        (200, 5): "200 IM",
    }

    def get_best_times(team_id_list, output_filename):
        roster_data = []

        # Get athletes for these teams who are IN THE MEET
        meet_participants = meet_results[meet_results["TEAM"].isin(team_id_list)][
            "ATHLETE"
        ].unique()

        for athlete_id in meet_participants:
            athlete_row = athletes_df[athletes_df["ATHLETE"] == athlete_id]
            if athlete_row.empty:
                continue

            athlete_name = (
                f"{athlete_row.iloc[0]['FIRST']} {athlete_row.iloc[0]['LAST']}"
            )
            gender = athlete_row.iloc[0]["SEX"]

            # Initialize swimmer dict
            swimmer_entry = {"name": athlete_name, "gender": gender, "id": athlete_id}

            # Find best times in history
            athlete_history = history_df[history_df["ATHLETE"] == athlete_id]

            for (dist, stroke), event_name in event_map.items():
                # Filter history for this event (assuming Course='Y' for Yards)
                # Note: 'COURSE' column in results might need checking. "S"=Short Course Yards in CSV? Or "Y"?
                # Let's assume all valid times for now.
                event_history = athlete_history[
                    (athlete_history["DISTANCE"] == dist)
                    & (athlete_history["STROKE"] == stroke)
                    & (athlete_history["SCORE"] > 0)  # Valid times only
                ]

                if not event_history.empty:
                    # Find min score
                    best_time_centiseconds = event_history["SCORE"].min()
                    swimmer_entry[event_name] = best_time_centiseconds / 100.0
                else:
                    swimmer_entry[event_name] = None

            roster_data.append(swimmer_entry)

        # Convert to DataFrame
        roster_df = pd.DataFrame(roster_data)
        out_path = os.path.join(OUTPUT_DIR, output_filename)
        roster_df.to_csv(out_path, index=False)
        print(f"Saved {len(roster_df)} athletes to {out_path}")
        return roster_df

    # Generate Seton Roster
    print("Generating Seton Roster...")
    get_best_times([SETON_TEAM_ID], "seton_roster_512.csv")

    # Generate Opponent Roster
    print("Generating Opponent Roster...")
    get_best_times(opponent_team_ids, "opponent_roster_512.csv")

    # Generate Actual Results for comparison
    # We want a format that links Event Name -> Time for each athlete
    # Or just a detailed list of results for this meet
    results_data = []
    for idx, row in meet_results.iterrows():
        key = (row["DISTANCE"], row["STROKE"])
        if key in event_map:
            event_name = event_map[key]
            athlete_id = row["ATHLETE"]
            score = row["SCORE"]
            dq = row["DQCODE"]

            # Get athlete name
            athlete_row = athletes_df[athletes_df["ATHLETE"] == athlete_id]
            if not athlete_row.empty:
                full_name = (
                    f"{athlete_row.iloc[0]['FIRST']} {athlete_row.iloc[0]['LAST']}"
                )

                results_data.append(
                    {
                        "event": event_name,
                        "athlete": full_name,
                        "athlete_id": athlete_id,
                        "team_id": row["TEAM"],
                        "time": score / 100.0 if score > 0 else None,
                        "dq": dq,
                    }
                )

    results_out_df = pd.DataFrame(results_data)
    results_out_path = os.path.join(OUTPUT_DIR, "actual_results_512.csv")
    results_out_df.to_csv(results_out_path, index=False)
    print(f"Saved actual results to {results_out_path}")


if __name__ == "__main__":
    main()
