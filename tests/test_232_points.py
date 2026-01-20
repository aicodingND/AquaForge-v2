"""
Test: Verify dual meet scoring totals exactly 232 points
"""

import sys
import os
import pandas as pd
import asyncio
from pathlib import Path

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from swim_ai_reflex.backend.core.hytek_pdf_parser import parse_hytek_pdf
from swim_ai_reflex.backend.core.event_mapper import filter_to_standard_events
from swim_ai_reflex.backend.core.opponent_model import greedy_opponent_best_lineup
from swim_ai_reflex.backend.core.dual_meet_scoring import (
    score_dual_meet,
    print_dual_meet_summary,
)


async def test_232_points():
    print("\n" + "=" * 80)
    print("🏊‍♀️ TEST: Verify 232 Points Total (Seton + Trinity = 232)")
    print("=" * 80)

    # Parse PDFs
    base_path = Path(__file__).parent.parent / "uploads"
    seton_pdf = (
        base_path / "seton swimming individual times-no manipulation-nov23,25.pdf"
    )
    trinity_pdf = (
        base_path
        / "Trinity Christian swimming individual times-no manipulation-nov23,25.pdf"
    )

    print("\n[1] Parsing and filtering to standard events...")
    seton_df = await asyncio.to_thread(parse_hytek_pdf, str(seton_pdf))
    trinity_df = await asyncio.to_thread(parse_hytek_pdf, str(trinity_pdf))

    # Filter to girls, no relays, no diving
    seton_girls = seton_df[
        (seton_df["gender"] == "F")
        & (~seton_df["is_relay"])
        & (~seton_df["event"].str.contains("Diving|Dives", case=False, na=False))
    ].copy()

    trinity_girls = trinity_df[
        (trinity_df["gender"] == "F")
        & (~trinity_df["is_relay"])
        & (~trinity_df["event"].str.contains("Diving|Dives", case=False, na=False))
    ].copy()

    # Filter to standard 8 events
    seton_standard = filter_to_standard_events(seton_girls, gender="F")
    trinity_standard = filter_to_standard_events(trinity_girls, gender="F")

    print(
        f"  Seton: {len(seton_standard)} entries across {seton_standard['event'].nunique()} events"
    )
    print(
        f"  Trinity: {len(trinity_standard)} entries across {trinity_standard['event'].nunique()} events"
    )

    # Create opponent's best lineup
    print("\n[2] Creating Trinity's optimized lineup...")
    trinity_lineup = greedy_opponent_best_lineup(trinity_standard)
    print(f"  Trinity lineup: {len(trinity_lineup)} entries")

    # For Seton, use greedy top 4 per event
    print("\n[3] Creating Seton's lineup (greedy top 4 per event)...")
    seton_lineup_parts = []
    for event, grp in seton_standard.groupby("event"):
        top4 = grp.sort_values("time", ascending=True).head(4)
        seton_lineup_parts.append(top4)
    seton_lineup = (
        pd.concat(seton_lineup_parts, ignore_index=True)
        if seton_lineup_parts
        else pd.DataFrame()
    )

    # Enforce 2 events per swimmer
    seton_final_parts = []
    for swimmer, grp in seton_lineup.groupby("swimmer"):
        if len(grp) <= 2:
            seton_final_parts.append(grp)
        else:
            seton_final_parts.append(grp.sort_values("time", ascending=True).head(2))
    seton_lineup = (
        pd.concat(seton_final_parts, ignore_index=True)
        if seton_final_parts
        else pd.DataFrame()
    )

    print(f"  Seton lineup: {len(seton_lineup)} entries")

    # Score the meet using new dual meet scoring
    print("\n[4] Scoring dual meet...")
    scored_df, totals = score_dual_meet(seton_lineup, trinity_lineup)

    # Print summary
    print_dual_meet_summary(totals, num_events=8)

    # Detailed validation
    print("\n[5] Detailed Validation:")
    seton_score = totals["seton"]
    trinity_score = totals["opponent"]
    combined = seton_score + trinity_score

    print(f"  Seton:    {seton_score:.1f}")
    print(f"  Trinity:  {trinity_score:.1f}")
    print(f"  Combined: {combined:.1f}")
    print("  Expected: 232.0")
    print(f"  Match:    {'✅ YES' if abs(combined - 232) < 0.1 else '❌ NO'}")

    if abs(combined - 232) > 0.1:
        print(f"\n  ⚠️  ERROR: Total is {combined:.1f}, not 232!")
        print(f"     Missing: {232 - combined:.1f} points")

        # Show event breakdown
        print("\n  Event breakdown:")
        for event in scored_df["event"].unique():
            event_data = scored_df[scored_df["event"] == event]
            event_total = event_data["points"].sum()
            print(f"    {event}: {event_total:.1f} points (expected 29)")
    else:
        print("\n  ✅ SUCCESS: All 232 points accounted for!")

    print("\n" + "=" * 80)


if __name__ == "__main__":
    asyncio.run(test_232_points())
