"""
Check: Do both teams have 1-event swimmers as needed?
"""

import asyncio
import os
import sys
from pathlib import Path

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from swim_ai_reflex.backend.core.event_mapper import filter_to_standard_events
from swim_ai_reflex.backend.core.hytek_pdf_parser import parse_hytek_pdf
from swim_ai_reflex.backend.core.opponent_model import greedy_opponent_best_lineup


async def check_event_distribution():
    print("\n" + "=" * 60)
    print("▸ Checking 1-Event vs 2-Event Swimmer Distribution")
    print("=" * 60)

    base_path = Path(__file__).parent.parent / "uploads"
    trinity_pdf = (
        base_path
        / "Trinity Christian swimming individual times-no manipulation-nov23,25.pdf"
    )

    trinity_df = await asyncio.to_thread(parse_hytek_pdf, str(trinity_pdf))

    trinity_girls = trinity_df[
        (trinity_df["gender"] == "F")
        & (not trinity_df["is_relay"])
        & (~trinity_df["event"].str.contains("Diving|Dives", case=False, na=False))
    ].copy()

    trinity_standard = filter_to_standard_events(trinity_girls, gender="F")
    trinity_lineup = greedy_opponent_best_lineup(trinity_standard)

    print("\n▸ TRINITY Lineup Distribution:")
    swimmer_counts = trinity_lineup.groupby("swimmer").size()

    one_event = (swimmer_counts == 1).sum()
    two_event = (swimmer_counts == 2).sum()

    print(f"1-event swimmers: {one_event}")
    print(f"2-event swimmers: {two_event}")
    print(f"Total swimmers: {len(swimmer_counts)}")
    print(f"Total entries: {len(trinity_lineup)}")

    print("\nSwimmer breakdown:")
    for swimmer, count in swimmer_counts.items():
        marker = "" if count == 2 else " "
        print(f"{marker} {swimmer}: {count} event(s)")

    # Verify: 1*one_event + 2*two_event should equal total entries
    expected = one_event + 2 * two_event
    actual = len(trinity_lineup)
    print(
        f"\n✓ Math check: {one_event} + 2*{two_event} = {expected} (actual: {actual}) {'✓' if expected == actual else '✗'}"
    )

    print("\n" + "=" * 60)


if __name__ == "__main__":
    asyncio.run(check_event_distribution())
