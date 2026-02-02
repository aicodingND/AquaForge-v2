#!/usr/bin/env python3
"""
Targeted 2024-2026 Season Ingestion

Ingests only meets from 2024-2026 seasons for AquaForge roster comparisons.
"""

import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
from sqlmodel import Session

from swim_ai_reflex.backend.database.engine import create_db_and_tables, engine
from swim_ai_reflex.backend.database.ingest import MDBIngestor
from swim_ai_reflex.backend.utils.mdb_connector import MDBConnector

DB_PATH = "data/real_exports/SSTdata.mdb"

# Date range for 2024-2026 seasons (swim season is typically Sept-Feb)
START_DATE = datetime(2023, 9, 1)  # Fall 2023 for 2024 season
END_DATE = datetime(2026, 12, 31)  # Through 2026


def ingest_2024_2026_seasons():
    """Ingest meets from 2024-2026 seasons only."""
    print("=" * 60)
    print("TARGETED INGESTION: 2024-2026 SEASONS")
    print("=" * 60)

    print("\nInitializing Database...")
    create_db_and_tables()

    print(f"Connecting to MDB: {DB_PATH}")
    connector = MDBConnector(DB_PATH)

    # Load meet table
    meet_df = connector.read_table("MEET")
    result_df = connector.read_table("RESULT")

    # Get meets with results
    meets_with_results = set(result_df["MEET"].unique())

    # Filter by date
    filtered_meets = []
    for _, row in meet_df.iterrows():
        meet_id = row["MEET"]
        if meet_id not in meets_with_results:
            continue

        # Check date
        if "Start" in meet_df.columns:
            try:
                meet_date = pd.to_datetime(row["Start"])
                if (
                    pd.isna(meet_date)
                    or meet_date < pd.Timestamp(START_DATE)
                    or meet_date > pd.Timestamp(END_DATE)
                ):
                    continue
            except (ValueError, TypeError):
                continue

        meet_name = row.get("MName", f"Meet_{meet_id}")
        if not meet_name or str(meet_name).lower() == "nan":
            meet_name = f"Meet_{meet_id}"

        # Determine profile
        name_lower = str(meet_name).lower()
        if "visaa" in name_lower:
            profile = "visaa_championship"
        elif "vcac" in name_lower or "catholic" in name_lower:
            profile = "vcac_championship"
        elif "championship" in name_lower or "invitational" in name_lower:
            profile = "championship"
        else:
            profile = "dual_meet"

        filtered_meets.append((meet_id, meet_name, profile))

    print(f"\nFound {len(filtered_meets)} meets in 2024-2026 range")
    print(
        f"Date filter: {START_DATE.strftime('%Y-%m-%d')} to {END_DATE.strftime('%Y-%m-%d')}"
    )

    ingestor = MDBIngestor(DB_PATH)

    with Session(engine) as session:
        success = 0
        for i, (meet_id, meet_name, profile) in enumerate(filtered_meets):
            try:
                if ingestor.ingest_meet(session, meet_id, meet_name, profile):
                    success += 1
            except Exception as e:
                print(f"Error: {e}")

            if (i + 1) % 20 == 0:
                print(f"  Progress: {i + 1}/{len(filtered_meets)}...")

    print(f"\n{'=' * 60}")
    print("INGESTION COMPLETE")
    print(f"{'=' * 60}")
    print(f"Meets processed: {success}/{len(filtered_meets)}")


if __name__ == "__main__":
    ingest_2024_2026_seasons()
