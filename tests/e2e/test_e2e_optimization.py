"""
E2E Test Script - Full Optimization Flow
Tests the complete optimization pipeline with proper handling
"""

import os
import sys

sys.path.insert(0, r"c:\Users\Michael\Desktop\AquaForgeFinal")

import asyncio

import pandas as pd

from swim_ai_reflex.backend.core.rules import VISAADualRules
from swim_ai_reflex.backend.services.data_filter_service import data_filter_service
from swim_ai_reflex.backend.services.data_service import data_service
from swim_ai_reflex.backend.services.meet_alignment_service import align_meet_data
from swim_ai_reflex.backend.services.optimization_service import optimization_service

UPLOAD_DIR = r"c:\Users\Michael\Desktop\AquaForgeFinal\uploads"


async def test_optimization():
    print("=" * 60)
    print("E2E OPTIMIZATION TEST")
    print("=" * 60)

    # Load files
    seton_file = os.path.join(UPLOAD_DIR, "Seton Boys v3.1.xlsx")
    immanuel_file = os.path.join(UPLOAD_DIR, "Immanuel Boys V3.xlsx")

    print("\n1. Loading files...")
    seton_result = await data_service.load_roster_from_path(seton_file)
    immanuel_result = await data_service.load_roster_from_path(immanuel_file)

    if not seton_result["success"] or not immanuel_result["success"]:
        print("ERROR: Failed to load files")
        return

    df_seton = seton_result["data"]
    df_immanuel = immanuel_result["data"]

    # Filter for Boys
    print("\n2. Filtering for Boys...")
    rules = VISAADualRules()

    df_seton_filt = data_filter_service.filter_for_dual_meet(
        df_seton,
        gender="M",
        include_individual=True,
        include_relay=False,
        include_diving=False,
        grades=[8, 9, 10, 11, 12],
        rules=rules,
    )
    df_seton_filt["team"] = "seton"

    df_imm_filt = data_filter_service.filter_for_dual_meet(
        df_immanuel,
        gender="M",
        include_individual=True,
        include_relay=False,
        include_diving=False,
        grades=[8, 9, 10, 11, 12],
        rules=rules,
    )
    df_imm_filt["team"] = "opponent"

    print(
        f"   Seton: {len(df_seton_filt)} entries, {df_seton_filt['swimmer'].nunique()} swimmers"
    )
    print(
        f"   Immanuel: {len(df_imm_filt)} entries, {df_imm_filt['swimmer'].nunique()} swimmers"
    )

    # Align meet data - returns tuple!
    print("\n3. Aligning meet data...")
    seton_aligned, opponent_aligned, alignment_info = align_meet_data(
        df_seton_filt, df_imm_filt
    )

    print(f"   Alignment aligned: {alignment_info.get('aligned', False)}")
    print(f"   Alignment method: {alignment_info.get('alignment_method', 'none')}")
    print(f"   Seton post-alignment: {len(seton_aligned)} entries")
    print(f"   Opponent post-alignment: {len(opponent_aligned)} entries")

    # Even without perfect alignment, we proceed (simulating user confirmation)
    print("\n4. Running optimization...")
    print("   Backend: heuristic")
    print("   Enforce fatigue: True")

    # Convert to dicts for optimization service
    seton_data = seton_aligned.to_dict("records")
    opponent_data = opponent_aligned.to_dict("records")

    try:
        response = await optimization_service.predict_best_lineups(
            pd.DataFrame(seton_data),
            pd.DataFrame(opponent_data),
            method="gurobi",
            max_iters=100,
            enforce_fatigue=True,
            scoring_type="individual",
        )

        print(f"\n   Optimization Success: {response['success']}")

        if response["success"]:
            results = response["data"]
            print("\n   === RESULTS ===")
            print(f"   Seton Score: {results.get('seton_score', 'N/A')}")
            print(f"   Opponent Score: {results.get('opponent_score', 'N/A')}")

            lineup = results.get("details", [])
            print(f"   Lineup entries: {len(lineup)}")

            if lineup:
                print("\n   Sample lineup (first 8 entries):")
                seton_entries = [
                    e for e in lineup if e.get("team", "").lower() == "seton"
                ][:4]
                opp_entries = [
                    e for e in lineup if e.get("team", "").lower() != "seton"
                ][:4]

                print("   Seton:")
                for entry in seton_entries:
                    print(
                        f"      {entry.get('event', 'N/A')}: {entry.get('swimmer', 'N/A')} - {entry.get('time', 'N/A')}s (pts: {entry.get('points', 0)})"
                    )

                print("   Opponent:")
                for entry in opp_entries:
                    print(
                        f"      {entry.get('event', 'N/A')}: {entry.get('swimmer', 'N/A')} - {entry.get('time', 'N/A')}s (pts: {entry.get('points', 0)})"
                    )

            # Validation
            print("\n   === VALIDATION ===")
            seton_score = results.get("seton_score", 0)
            opp_score = results.get("opponent_score", 0)

            if seton_score > 150 or opp_score > 150:
                print(
                    f"   ⚠️ WARNING: Scores seem inflated ({seton_score}, {opp_score})"
                )
            elif seton_score < 10 or opp_score < 10:
                print(f"   ⚠️ WARNING: Scores seem too low ({seton_score}, {opp_score})")
            else:
                print(
                    f"   ✅ Scores look reasonable: Seton {seton_score} - Opponent {opp_score}"
                )

            # Check unique swimmers per team
            df_lineup = pd.DataFrame(lineup)
            if not df_lineup.empty:
                seton_swimmers = df_lineup[df_lineup["team"].str.lower() == "seton"][
                    "swimmer"
                ].nunique()
                opp_swimmers = df_lineup[df_lineup["team"].str.lower() != "seton"][
                    "swimmer"
                ].nunique()
                print(f"   Seton swimmers in lineup: {seton_swimmers}")
                print(f"   Opponent swimmers in lineup: {opp_swimmers}")
        else:
            print(f"   ERROR: {response.get('message', 'Unknown error')}")

    except Exception as e:
        print(f"   EXCEPTION: {str(e)}")
        import traceback

        traceback.print_exc()

    print("\n" + "=" * 60)
    print("OPTIMIZATION TEST COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_optimization())
