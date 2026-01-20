"""
Debug: Compare Seton vs Trinity swimmer counts and times
"""

import sys
import os
import asyncio
from pathlib import Path

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from swim_ai_reflex.backend.core.hytek_pdf_parser import parse_hytek_pdf
from swim_ai_reflex.backend.core.event_mapper import filter_to_standard_events


async def compare_teams():
    print("\n" + "=" * 60)
    print("🏊 Team Comparison: Who should win?")
    print("=" * 60)

    base_path = Path(__file__).parent.parent / "uploads"
    seton_df = await asyncio.to_thread(
        parse_hytek_pdf,
        str(base_path / "seton swimming individual times-no manipulation-nov23,25.pdf"),
    )
    trinity_df = await asyncio.to_thread(
        parse_hytek_pdf,
        str(
            base_path
            / "Trinity Christian swimming individual times-no manipulation-nov23,25.pdf"
        ),
    )

    # Filter
    seton = filter_to_standard_events(
        seton_df[
            (seton_df["gender"] == "F")
            & (~seton_df["is_relay"])
            & (~seton_df["event"].str.contains("Diving", na=False))
        ]
    )
    trinity = filter_to_standard_events(
        trinity_df[
            (trinity_df["gender"] == "F")
            & (~trinity_df["is_relay"])
            & (~trinity_df["event"].str.contains("Diving", na=False))
        ]
    )

    print("\n📊 Team Size:")
    print(f"  Seton:   {seton['swimmer'].nunique()} swimmers, {len(seton)} entries")
    print(f"  Trinity: {trinity['swimmer'].nunique()} swimmers, {len(trinity)} entries")

    print("\n📊 Fastest Time per Event (head-to-head):")
    events = sorted(set(seton["event"].unique()) & set(trinity["event"].unique()))

    seton_wins = 0
    trinity_wins = 0

    for event in events:
        s_time = seton[seton["event"] == event]["time"].min()
        t_time = trinity[trinity["event"] == event]["time"].min()
        winner = "SETON" if s_time < t_time else "TRINITY"
        if s_time < t_time:
            seton_wins += 1
        else:
            trinity_wins += 1
        print(f"  {event}: Seton {s_time:.2f} vs Trinity {t_time:.2f} → {winner}")

    print("\n🏆 Head-to-head fastest per event:")
    print(f"  Seton wins: {seton_wins}")
    print(f"  Trinity wins: {trinity_wins}")
    print(f"  Expected winner: {'SETON' if seton_wins > trinity_wins else 'TRINITY'}")

    print("\n" + "=" * 60)


if __name__ == "__main__":
    asyncio.run(compare_teams())
