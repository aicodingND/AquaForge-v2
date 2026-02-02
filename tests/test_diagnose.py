"""
Quick diagnostic to see what events are being processed
"""

import asyncio
import os
import sys
from pathlib import Path

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from swim_ai_reflex.backend.core.hytek_pdf_parser import parse_hytek_pdf
from swim_ai_reflex.backend.core.opponent_model import greedy_opponent_best_lineup
from swim_ai_reflex.backend.core.rules import VISAADualRules


async def diagnose():
    base_path = Path(__file__).parent.parent / "uploads"
    seton_pdf = (
        base_path / "seton swimming individual times-no manipulation-nov23,25.pdf"
    )
    trinity_pdf = (
        base_path
        / "Trinity Christian swimming individual times-no manipulation-nov23,25.pdf"
    )

    print("Parsing PDFs...")
    seton_df = await asyncio.to_thread(parse_hytek_pdf, str(seton_pdf))
    trinity_df = await asyncio.to_thread(parse_hytek_pdf, str(trinity_pdf))

    # Filter girls only
    seton_girls = seton_df[
        (seton_df["gender"] == "F") & (not seton_df["is_relay"])
    ].copy()
    trinity_girls = trinity_df[
        (trinity_df["gender"] == "F") & (not trinity_df["is_relay"])
    ].copy()

    print(f"\nSeton girls events: {sorted(seton_girls['event'].unique())}")
    print(f"\nTrinity girls events: {sorted(trinity_girls['event'].unique())}")

    # Find common events
    seton_events = set(seton_girls["event"].unique())
    trinity_events = set(trinity_girls["event"].unique())
    common_events = seton_events & trinity_events

    print(f"\n\nCommon events: {len(common_events)}")
    for event in sorted(common_events):
        seton_count = len(seton_girls[seton_girls["event"] == event])
        trinity_count = len(trinity_girls[trinity_girls["event"] == event])
        print(f"  {event}: Seton={seton_count}, Trinity={trinity_count}")

    print(f"\n\nSeton-only events: {sorted(seton_events - trinity_events)}")
    print(f"\nTrinity-only events: {sorted(trinity_events - seton_events)}")

    # Try greedy opponent lineup
    print("\n\nTrying greedy opponent lineup...")
    rules = VISAADualRules()
    try:
        opponent_lineup = greedy_opponent_best_lineup(trinity_girls, rules)
        print(f"Opponent lineup created: {len(opponent_lineup)} entries")
        print(f"Events in opponent lineup: {sorted(opponent_lineup['event'].unique())}")
    except Exception as e:
        print(f"ERROR creating opponent lineup: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(diagnose())
