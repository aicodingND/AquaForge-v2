"""
E2E Test: Seton vs Trinity - Girls STANDARD DUAL MEET Events Only
Uses event mapper to filter to 8 standard individual events (232 max points)
"""
import sys
import os
import asyncio
from pathlib import Path

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

try:
    from swim_ai_reflex.backend.core.hytek_pdf_parser import parse_hytek_pdf
    from swim_ai_reflex.backend.services.optimization_service import optimization_service
    from swim_ai_reflex.backend.core.event_mapper import filter_to_standard_events, print_event_summary
    print("[TEST] ✅ Imports successful.")
except ImportError as e:
    print(f"[TEST] ❌ Import Error: {e}")
    sys.exit(1)


async def run_e2e_standard_events():
    """
    Run E2E test with STANDARD dual meet events only (8 events, 232 max points).
    """
    print("\n" + "="*80)
    print("🏊‍♀️ E2E TEST: Seton vs Trinity - STANDARD Dual Meet (Girls)")
    print("8 Individual Events × 29 Points = 232 Maximum Points")
    print("="*80)
    
    # Define PDF paths
    base_path = Path(__file__).parent.parent / "uploads"
    seton_pdf = base_path / "seton swimming individual times-no manipulation-nov23,25.pdf"
    trinity_pdf = base_path / "Trinity Christian swimming individual times-no manipulation-nov23,25.pdf"
    
    if not seton_pdf.exists() or not trinity_pdf.exists():
        print("[ERROR] ❌ PDFs not found")
        return
    
    print("\n[STEP 1] 📄 Parsing PDFs...")
    
    # Parse PDFs
    try:
        seton_df = await asyncio.to_thread(parse_hytek_pdf, str(seton_pdf))
        trinity_df = await asyncio.to_thread(parse_hytek_pdf, str(trinity_pdf))
        print(f"[PARSE] ✅ Seton: {len(seton_df)} entries, Trinity: {len(trinity_df)} entries")
    except Exception as e:
        print(f"[ERROR] ❌ Failed to parse PDFs: {e}")
        return
    
    # Filter for girls only (no diving, no relays)
    print("\n[STEP 2] 🔍 Filtering for Girls Events...")
    seton_girls = seton_df[
        (seton_df['gender'] == 'F') &
        (not seton_df['is_relay']) &
        (~seton_df['event'].str.contains('Diving|Dives', case=False, na=False))
    ].copy()
    
    trinity_girls = trinity_df[
        (trinity_df['gender'] == 'F') &
        (not trinity_df['is_relay']) &
        (~trinity_df['event'].str.contains('Diving|Dives', case=False, na=False))
    ].copy()
    
    print("  After gender/relay/diving filter:")
    print(f"    Seton: {len(seton_girls)} entries")
    print(f"    Trinity: {len(trinity_girls)} entries")
    
    # Filter to STANDARD dual meet events
    print("\n[STEP 3] 📋 Mapping to STANDARD Dual Meet Events...")
    seton_standard = filter_to_standard_events(seton_girls, gender='F')
    trinity_standard = filter_to_standard_events(trinity_girls, gender='F')
    
    print_event_summary(seton_standard, "SETON - Standard Events")
    print_event_summary(trinity_standard, "TRINITY - Standard Events")
    
    # Check if we have data
    if len(seton_standard) == 0:
        print("\n[ERROR] ❌ No Seton standard events found!")
        return
    if len(trinity_standard) == 0:
        print("\n[ERROR] ❌ No Trinity standard events found!")
        return
    
    # Show swimmer counts
    seton_swimmers = seton_standard['swimmer'].nunique()
    trinity_swimmers = trinity_standard['swimmer'].nunique()
    print("\n[DATA SUMMARY]")
    print(f"  Seton: {seton_swimmers} unique swimmers, {len(seton_standard)} event entries")
    print(f"  Trinity: {trinity_swimmers} unique swimmers, {len(trinity_standard)} event entries")
    
    # Run optimization with GUROBI
    print("\n[STEP 4] 🚀 Running Optimization (GUROBI)...")
    print("  Strategy: Best on Best (Trinity lineup will be optimized)")
    print("  Expected: Seton 128-135, Trinity 70-110, Combined ≤ 232")
    
    try:
        result = await optimization_service.predict_best_lineups(
            seton_roster=seton_standard,
            opponent_roster=trinity_standard,
            method="gurobi",
            max_iters=1000,
            enforce_fatigue=False,
            use_cache=False
        )
    except Exception as e:
        print(f"[ERROR] ❌ Optimization failed: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Check result
    if not result.get("success", False):
        print(f"\n[FAIL] ❌ Optimization Error: {result.get('message')} - {result.get('error')}")
        return
    
    # Extract data
    data = result['data']
    seton_score = data['seton_score']
    trinity_score = data['opponent_score']
    combined_score = seton_score + trinity_score
    
    print("\n[STEP 5] 📊 RESULTS")
    print("="*80)
    print("\n🏆 FINAL SCORE:")
    print(f"  Seton:    {seton_score:.1f}")
    print(f"  Trinity:  {trinity_score:.1f}")
    print(f"  Combined: {combined_score:.1f} / 232 max ({combined_score/232*100:.1f}%)")
    print(f"  Margin:   {abs(seton_score - trinity_score):.1f} points")
    print(f"  Winner:   {'Seton' if seton_score > trinity_score else 'Trinity' if trinity_score > seton_score else 'TIE'}")
    
    # Validation
    print("\n✅ VALIDATION:")
    in_range_seton = 128 <= seton_score <= 135
    in_range_trinity = 70 <= trinity_score <= 110
    under_max = combined_score <= 232
    
    print(f"  Seton in range (128-135): {'✅' if in_range_seton else '❌'} {seton_score:.1f}")
    print(f"  Trinity in range (70-110): {'✅' if in_range_trinity else '❌'} {trinity_score:.1f}")
    print(f"  Combined ≤ 232: {'✅' if under_max else '❌'} {combined_score:.1f}")
    
    if in_range_seton and in_range_trinity and under_max:
        print("\n  🎉 ALL VALIDATIONS PASSED!")
    else:
        print("\n  ⚠️  Some validations failed - check scoring logic")
    
    print("\n" + "="*80)
    print("✅ E2E TEST COMPLETE")
    print("="*80)


if __name__ == "__main__":
    asyncio.run(run_e2e_standard_events())
