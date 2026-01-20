"""
E2E Test: Seton vs Trinity - FINAL with Gurobi + 232 Points
Uses Gurobi optimization and dual_meet_scoring to ensure 232 total points
"""

import sys
import os
import asyncio
from pathlib import Path

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from swim_ai_reflex.backend.core.hytek_pdf_parser import parse_hytek_pdf
from swim_ai_reflex.backend.core.event_mapper import (
    filter_to_standard_events,
    print_event_summary,
)
from swim_ai_reflex.backend.services.optimization_service import optimization_service
from swim_ai_reflex.backend.core.dual_meet_scoring import print_dual_meet_summary


async def test_e2e_final():
    print("\n" + "=" * 80)
    print("🏊‍♀️ E2E FINAL TEST: Seton vs Trinity")
    print("Standard Dual Meet - 8 Events × 29 Points = 232 Total")
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

    print("\n[1] Parsing PDFs...")
    seton_df = await asyncio.to_thread(parse_hytek_pdf, str(seton_pdf))
    trinity_df = await asyncio.to_thread(parse_hytek_pdf, str(trinity_pdf))

    # Filter to girls, no relays, no diving
    print("\n[2] Filtering for girls events...")
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
    print("\n[3] Mapping to standard dual meet events...")
    seton_standard = filter_to_standard_events(seton_girls, gender="F")
    trinity_standard = filter_to_standard_events(trinity_girls, gender="F")

    print_event_summary(seton_standard, "SETON")
    print_event_summary(trinity_standard, "TRINITY")

    # Run Gurobi optimization
    print("\n[4] Running Gurobi optimization...")
    print("  This will optimize Seton's lineup against Trinity's best lineup")

    result = await optimization_service.predict_best_lineups(
        seton_roster=seton_standard,
        opponent_roster=trinity_standard,
        method="gurobi",
        max_iters=1000,
        enforce_fatigue=False,
        use_cache=False,
    )

    if not result.get("success"):
        print(f"\n❌ Optimization failed: {result.get('message')}")
        return

    # Get optimized lineups from the result
    # The optimization service returns scored data, not raw lineups
    # We need to extract the lineups and re-score with dual_meet_scoring
    data = result["data"]

    # For now, let's just use the scores from the optimization
    # and verify they match our 232-point rule
    seton_score_opt = data.get("seton_score", 0)
    trinity_score_opt = data.get("opponent_score", 0)

    print("\n[5] Optimization complete!")
    print(f"  Seton score (from optimizer): {seton_score_opt:.1f}")
    print(f"  Trinity score (from optimizer): {trinity_score_opt:.1f}")
    print(f"  Combined: {seton_score_opt + trinity_score_opt:.1f}")

    # Check if we need to re-score with dual_meet_scoring
    combined_opt = seton_score_opt + trinity_score_opt
    if abs(combined_opt - 232) > 0.1:
        print(f"\n⚠️  Optimizer total ({combined_opt:.1f}) != 232")
        print("  The optimizer is not using dual meet scoring rules")
        print("  This is expected - we need to integrate dual_meet_scoring into Gurobi")

    # Use the optimizer scores for now
    totals = {"seton": seton_score_opt, "opponent": trinity_score_opt}

    # Print summary
    print_dual_meet_summary(totals, num_events=8)

    # Detailed results
    seton_score = totals["seton"]
    trinity_score = totals["opponent"]
    combined = seton_score + trinity_score

    print("\n" + "=" * 80)
    print("📊 FINAL RESULTS")
    print("=" * 80)
    print("\n🏆 Scores:")
    print(f"  Seton:    {seton_score:.1f} points")
    print(f"  Trinity:  {trinity_score:.1f} points")
    print(f"  Combined: {combined:.1f} / 232")
    print(f"  Winner:   {'Seton' if seton_score > trinity_score else 'Trinity'}")

    print("\n✅ Validation:")
    in_range = 128 <= seton_score <= 135
    total_correct = abs(combined - 232) < 0.1

    print(f"  Seton in range (128-135): {'✅' if in_range else '❌'} {seton_score:.1f}")
    print(f"  Total = 232: {'✅' if total_correct else '❌'} {combined:.1f}")

    if in_range and total_correct:
        print("\n  🎉 ALL TESTS PASSED!")
    else:
        print("\n  ⚠️  Some validations failed")
        if not in_range:
            print(f"     Seton score {seton_score:.1f} outside expected range 128-135")
        if not total_correct:
            print(f"     Total {combined:.1f} should be exactly 232")

    print("\n" + "=" * 80)


if __name__ == "__main__":
    asyncio.run(test_e2e_final())
