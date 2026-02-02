"""
E2E Test: Seton vs Trinity - Girls Events Only (No Diving, No Relays) - GUROBI
"""

import asyncio
import os
import sys
from pathlib import Path

import pandas as pd

# Ensure project root is in path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

try:
    from swim_ai_reflex.backend.core.hytek_pdf_parser import parse_hytek_pdf
    from swim_ai_reflex.backend.services.optimization_service import (
        optimization_service,
    )

    print("[TEST] ✅ Imports successful.")
except ImportError as e:
    print(f"[TEST] ❌ Import Error: {e}")
    print(
        "     Ensure you're running from project root with virtual environment activated"
    )
    sys.exit(1)


def filter_girls_events_only(df: pd.DataFrame) -> pd.DataFrame:
    """
    Filter DataFrame to include only girls events (no diving, no relays).
    """
    print(f"\n[FILTER] Starting with {len(df)} total entries")

    # Filter for girls only
    df_girls = df[df["gender"] == "F"].copy()
    print(f"[FILTER] After gender filter (F only): {len(df_girls)} entries")

    # Filter out relays
    df_no_relays = df_girls[~df_girls["is_relay"]].copy()
    print(f"[FILTER] After removing relays: {len(df_no_relays)} entries")

    # Filter out diving events
    df_no_diving = df_no_relays[
        ~df_no_relays["event"].str.contains("Diving|Dives", case=False, na=False)
    ].copy()
    print(f"[FILTER] After removing diving: {len(df_no_diving)} entries")

    # Show unique events
    unique_events = df_no_diving["event"].unique()
    print(f"[FILTER] Unique girls events found: {len(unique_events)}")
    for event in sorted(unique_events):
        count = len(df_no_diving[df_no_diving["event"] == event])
        print(f"  - {event}: {count} entries")

    return df_no_diving


async def run_e2e_gurobi():
    """
    Run end-to-end test with Seton and Trinity PDFs, girls events only, using GUROBI.
    """
    print("\n" + "=" * 80)
    print("🏊‍♀️ E2E TEST: Seton vs Trinity - Girls Events Only (GUROBI)")
    print("(No Diving, No Relays)")
    print("=" * 80)

    # Define PDF paths - updated structure
    base_path = Path(__file__).parent / "uploads"
    seton_pdf = (
        base_path / "seton swimming individual times-no manipulation-nov23,25.pdf"
    )
    trinity_pdf = (
        base_path
        / "Trinity Christian swimming individual times-no manipulation-nov23,25.pdf"
    )

    # Verify files exist
    if not seton_pdf.exists():
        print(f"[ERROR] ❌ Seton PDF not found: {seton_pdf}")
        return
    if not trinity_pdf.exists():
        print(f"[ERROR] ❌ Trinity PDF not found: {trinity_pdf}")
        return

    print("\n[STEP 1] 📄 Parsing PDFs...")
    print(f"  Seton: {seton_pdf.name}")
    print(f"  Trinity: {trinity_pdf.name}")

    # Parse PDFs
    try:
        seton_df = await asyncio.to_thread(parse_hytek_pdf, str(seton_pdf))
        print(f"[PARSE] ✅ Seton parsed: {len(seton_df)} total entries")
    except Exception as e:
        print(f"[ERROR] ❌ Failed to parse Seton PDF: {e}")
        return

    try:
        trinity_df = await asyncio.to_thread(parse_hytek_pdf, str(trinity_pdf))
        print(f"[PARSE] ✅ Trinity parsed: {len(trinity_df)} total entries")
    except Exception as e:
        print(f"[ERROR] ❌ Failed to parse Trinity PDF: {e}")
        return

    # Filter for girls events only (no diving, no relays)
    print("\n[STEP 2] 🔍 Filtering for Girls Events Only...")
    print("\n--- SETON FILTERING ---")
    seton_girls = filter_girls_events_only(seton_df)

    print("\n--- TRINITY FILTERING ---")
    trinity_girls = filter_girls_events_only(trinity_df)

    # Check if we have data
    if len(seton_girls) == 0:
        print("\n[ERROR] ❌ No Seton girls events found after filtering!")
        return
    if len(trinity_girls) == 0:
        print("\n[ERROR] ❌ No Trinity girls events found after filtering!")
        return

    # Show swimmer counts
    seton_swimmers = seton_girls["swimmer"].nunique()
    trinity_swimmers = trinity_girls["swimmer"].nunique()
    print("\n[DATA SUMMARY]")
    print(
        f"  Seton: {seton_swimmers} unique swimmers, {len(seton_girls)} event entries"
    )
    print(
        f"  Trinity: {trinity_swimmers} unique swimmers, {len(trinity_girls)} event entries"
    )

    # Run optimization with GUROBI
    print("\n[STEP 3] 🚀 Running Optimization (GUROBI)...")
    print("  Strategy: Best on Best (Trinity lineup will be optimized)")
    print("  Note: Gurobi should be much faster than heuristic...")

    try:
        result = await optimization_service.predict_best_lineups(
            seton_roster=seton_girls,
            opponent_roster=trinity_girls,
            method="gurobi",  # Using Gurobi instead of heuristic
            max_iters=1000,  # Not used by Gurobi but required param
            enforce_fatigue=False,
            scoring_type="visaa_top7",  # New parameter
            robust_mode=False,  # New parameter
            use_cache=False,  # Don't use cache for this test
            retry_on_failure=True,  # New parameter
            max_retries=2,  # New parameter
        )
    except Exception as e:
        print(f"[ERROR] ❌ Optimization failed: {e}")
        import traceback

        traceback.print_exc()
        return

    # Check result - new service returns success field differently
    if "success" in result and not result["success"]:
        print(
            f"\n[FAIL] ❌ Optimization Error: {result.get('message')} - {result.get('error')}"
        )
        return

    if "error" in result:
        print(f"\n[FAIL] ❌ Optimization Error: {result['error']}")
        return

    # Extract data - new service returns data directly or wrapped
    if "data" in result:
        data = result["data"]
    else:
        data = result

    seton_score = data.get("seton_score", 0)
    trinity_score = data.get("opponent_score", 0)
    details = data.get("details", [])

    # Check for from_cache flag
    if data.get("from_cache"):
        print("ℹ️  Results retrieved from cache")

    print("\n[STEP 4] 📊 RESULTS")
    print("=" * 80)
    print("\n🏆 FINAL SCORE:")
    print(f"  Seton:    {seton_score}")
    print(f"  Trinity:  {trinity_score}")
    print(f"  Margin:   {abs(seton_score - trinity_score)} points")
    print(
        f"  Winner:   {'Seton' if seton_score > trinity_score else 'Trinity' if trinity_score > seton_score else 'TIE'}"
    )

    print(f"\n📋 LINEUP DETAILS ({len(details)} events):")
    print("-" * 80)

    # Group by event
    for detail in details:
        event = detail.get("event", "Unknown Event")
        seton_swimmers = detail.get("seton_swimmers", [])
        trinity_swimmers = detail.get("opponent_swimmers", [])
        seton_pts = detail.get("seton_points", 0)
        trinity_pts = detail.get("opponent_points", 0)

        print(f"\n{event}")
        print(f"  Seton ({seton_pts} pts):")
        for i, swimmer in enumerate(seton_swimmers[:4], 1):
            name = swimmer.get("swimmer", "Unknown")
            time = swimmer.get("time", 0)
            print(f"    {i}. {name} - {time:.2f}s")

        print(f"  Trinity ({trinity_pts} pts):")
        for i, swimmer in enumerate(trinity_swimmers[:4], 1):
            name = swimmer.get("swimmer", "Unknown")
            time = swimmer.get("time", 0)
            print(f"    {i}. {name} - {time:.2f}s")

    print("\n" + "=" * 80)
    print("✅ E2E TEST COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(run_e2e_gurobi())
