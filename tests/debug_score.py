"""
Debug: Check why Seton score is 149 instead of 128-135
"""

import asyncio
import os
import sys
from pathlib import Path

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from swim_ai_reflex.backend.core.event_mapper import filter_to_standard_events
from swim_ai_reflex.backend.core.hytek_pdf_parser import parse_hytek_pdf
from swim_ai_reflex.backend.core.opponent_model import greedy_opponent_best_lineup


async def debug_scoring():
    print("\n" + "=" * 80)
    print("▸ DEBUG: Why is Seton scoring 149 instead of 128-135?")
    print("=" * 80)

    # Parse and filter
    base_path = Path(__file__).parent.parent / "uploads"
    trinity_pdf = (
        base_path
        / "Trinity Christian swimming individual times-no manipulation-nov23,25.pdf"
    )

    trinity_df = await asyncio.to_thread(parse_hytek_pdf, str(trinity_pdf))

    # Filter to girls, no relays, no diving
    trinity_girls = trinity_df[
        (trinity_df["gender"] == "F")
        & (not trinity_df["is_relay"])
        & (~trinity_df["event"].str.contains("Diving|Dives", case=False, na=False))
    ].copy()

    trinity_standard = filter_to_standard_events(trinity_girls, gender="F")

    print("\n[1] Trinity BEFORE greedy selection:")
    print(f"Total entries: {len(trinity_standard)}")
    print(f"Unique swimmers: {trinity_standard['swimmer'].nunique()}")
    print(f"Events: {trinity_standard['event'].nunique()}")

    for event in sorted(trinity_standard["event"].unique()):
        count = len(trinity_standard[trinity_standard["event"] == event])
        print(f"{event}: {count} swimmers available")

    # Apply greedy model
    trinity_lineup = greedy_opponent_best_lineup(trinity_standard)

    print("\n[2] Trinity AFTER greedy selection:")
    print(f"Total entries: {len(trinity_lineup)}")
    print(f"Unique swimmers: {trinity_lineup['swimmer'].nunique()}")

    for event in sorted(trinity_lineup["event"].unique()):
        count = len(trinity_lineup[trinity_lineup["event"] == event])
        swimmers = trinity_lineup[trinity_lineup["event"] == event]["swimmer"].tolist()
        print(f"{event}: {count} swimmers")
        if count < 4:
            print(f"! MISSING {4 - count} swimmers! Only have: {swimmers}")

    # Count how many events have < 4 swimmers
    missing_slots = 0
    for event in trinity_lineup["event"].unique():
        count = len(trinity_lineup[trinity_lineup["event"] == event])
        missing_slots += max(0, 4 - count)

    print("\n[3] PROBLEM IDENTIFIED:")
    print(f"Missing slots: {missing_slots}")
    print(
        f"This means Trinity forfeits ~{missing_slots * 3} to ~{missing_slots * 8} points"
    )
    print("Those points go to Seton, inflating their score!")

    print("\n" + "=" * 80)


if __name__ == "__main__":
    asyncio.run(debug_scoring())
