import sys
from pathlib import Path

import pandas as pd

# Add project root to path
sys.path.insert(0, str(Path.cwd()))
from swim_ai_reflex.backend.utils.mdb_connector import MDBConnector


def verify_scoring():
    db_path = Path("data/real_exports/SSTdata.mdb")
    if not db_path.exists():
        print(f"Database not found at {db_path}")
        return

    connector = MDBConnector(str(db_path))

    # 1. MEET Table Analysis
    print("Loading MEET table...")
    meets = connector.read_table("MEET")

    # Dynamic Column Detection for MEET
    meet_name_col = next(
        (c for c in meets.columns if "name" in c.lower() or "title" in c.lower()),
        "MName",
    )
    meet_start_col = next(
        (c for c in meets.columns if "start" in c.lower() or "date" in c.lower()),
        "Start",
    )
    meet_id_col = next(
        (c for c in meets.columns if "id" in c.lower() or c.lower() == "meet"),
        meets.columns[0],
    )

    print(
        f"Detected MEET Cols -> Name: {meet_name_col}, Start: {meet_start_col}, ID: {meet_id_col}"
    )

    # Find Target Meet
    target_meet = meets[
        meets[meet_name_col]
        .astype(str)
        .str.contains("VCAC Championship", case=False, na=False)
    ]

    if target_meet.empty:
        print("Could not find VCAC Championship meet.")
        return

    # Select most recent
    target_meet = target_meet.sort_values(meet_start_col, ascending=False).iloc[0]
    meet_id = target_meet[meet_id_col]
    meet_name = target_meet[meet_name_col]

    print(f"\nTarget Meet: {meet_name} (ID: {meet_id})")

    # 2. RESULT Table Analysis
    print("Loading RESULT table...")
    results = connector.read_table("RESULT")

    # Dynamic Column Detection for RESULT
    res_meet_link_col = next(
        (c for c in results.columns if "meet" in c.lower()), "Meet"
    )
    res_points_col = next(
        (c for c in results.columns if "point" in c.lower()), "Points"
    )
    # Prefer SCORE_PL or PLACE
    res_place_col = next(
        (c for c in results.columns if "score" in c.lower() and "pl" in c.lower()),
        "SCORE_PL",
    )
    if res_place_col not in results.columns:
        res_place_col = next(
            (c for c in results.columns if "place" in c.lower()), "Place"
        )

    res_event_col = next((c for c in results.columns if "event" in c.lower()), "Event")

    print(
        f"Detected RESULT Cols -> Link: {res_meet_link_col}, Points: {res_points_col}, Place: {res_place_col}, Event: {res_event_col}"
    )

    # Filter Results
    meet_results = results[results[res_meet_link_col] == meet_id].copy()

    # Clean Data
    meet_results[res_points_col] = pd.to_numeric(
        meet_results[res_points_col], errors="coerce"
    ).fillna(0)
    meet_results[res_place_col] = pd.to_numeric(
        meet_results[res_place_col], errors="coerce"
    ).fillna(999)
    meet_results[res_event_col] = pd.to_numeric(
        meet_results[res_event_col], errors="coerce"
    )

    print("\n--- Verification Data (All Events) ---")

    # Filter for > 0 points
    scoring_results = meet_results[meet_results[res_points_col] > 0]

    if scoring_results.empty:
        print("No scoring results found.")
    else:
        # Sort by points descending to see the high scores (20, 17...)
        unique_points = sorted(scoring_results[res_points_col].unique(), reverse=True)
        print("Unique Point Values Found:", unique_points)

        print("\nTop 40 Scoring Rows (Sample):")
        # Sort by event then place to see structure
        scoring_results = scoring_results.sort_values(
            [res_event_col, res_place_col], ascending=[True, True]
        )
        print(
            scoring_results[[res_place_col, res_points_col, res_event_col]]
            .head(40)
            .to_string(index=False)
        )


if __name__ == "__main__":
    verify_scoring()
