"""
E2E Test Script - Full Flow with Exports
Tests Loading -> Filtering -> Aligning -> Optimizing -> Exporting
using 'Seton Boys v3.1.xlsx' and 'Immanuel Boys V3.xlsx'
"""
import sys
import os
import asyncio

sys.path.insert(0, r"c:\Users\Michael\Desktop\AquaForgeFinal")

from swim_ai_reflex.backend.services.data_service import data_service
from swim_ai_reflex.backend.services.data_filter_service import data_filter_service
from swim_ai_reflex.backend.services.optimization_service import optimization_service
from swim_ai_reflex.backend.services.meet_alignment_service import align_meet_data
from swim_ai_reflex.backend.services.export_service import export_service
from swim_ai_reflex.backend.core.rules import VISAADualRules

UPLOAD_DIR = r"c:\Users\Michael\Desktop\AquaForgeFinal\uploads"
OUTPUT_DIR = r"c:\Users\Michael\Desktop\AquaForgeFinal\test_outputs"

if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

async def test_full_chain():
    print("=" * 60)
    print("FULL CHAIN VERIFICATION (LOAD -> OPTIMIZE -> EXPORT)")
    print("=" * 60)
    
    # 1. Load
    print("\n1. Loading files...")
    seton_file = os.path.join(UPLOAD_DIR, "Seton Boys v3.1.xlsx")
    immanuel_file = os.path.join(UPLOAD_DIR, "Immanuel Boys V3.xlsx")
    
    seton_res = await data_service.load_roster_from_path(seton_file)
    imm_res = await data_service.load_roster_from_path(immanuel_file)
    
    if not seton_res['success'] or not imm_res['success']:
        print("❌ LOAD FAILED")
        return

    # 2. Filter
    print("\n2. Filtering...")
    rules = VISAADualRules()
    df_seton = data_filter_service.filter_for_dual_meet(seton_res['data'], gender='M', grades=[8,9,10,11,12], rules=rules)
    df_seton['team'] = 'seton'
    df_imm = data_filter_service.filter_for_dual_meet(imm_res['data'], gender='M', grades=[8,9,10,11,12], rules=rules)
    df_imm['team'] = 'opponent'
    
    # 3. Align
    print("\n3. Aligning...")
    seton_aligned, imm_aligned, _ = align_meet_data(df_seton, df_imm)
    
    # 4. Optimize
    print("\n4. Optimizing...")
    opt_res = await optimization_service.predict_best_lineups(
        seton_aligned, imm_aligned, method="gurobi", max_iters=50, scoring_type="individual"
    )
    
    if not opt_res['success']:
        print("❌ OPTIMIZATION FAILED")
        return
        
    lineup = opt_res['data']['details']
    s_score = opt_res['data']['seton_score']
    o_score = opt_res['data']['opponent_score']
    print(f"   Lineup generated: {len(lineup)} entries. Score: {s_score}-{o_score}")
    
    # 5. Export
    print("\n5. Testing Exports...")
    
    try:
        # CSV
        csv_data = export_service.to_csv(lineup, s_score, o_score)
        with open(os.path.join(OUTPUT_DIR, "test_export.csv"), "w", newline="") as f:
            f.write(csv_data)
        print("   ✅ CSV Export success")
        
        # HTML/PDF
        html_data = export_service.to_html_table(lineup, s_score, o_score)
        with open(os.path.join(OUTPUT_DIR, "test_export.html"), "w", encoding="utf-8") as f:
            f.write(html_data)
        print("   ✅ HTML Export success")
        
        # XLSX
        xlsx_data = export_service.to_xlsx(lineup, s_score, o_score)
        with open(os.path.join(OUTPUT_DIR, "test_export.xlsx"), "wb") as f:
            f.write(xlsx_data)
        print("   ✅ XLSX Export success")
        
    except Exception as e:
        print(f"❌ EXPORT FAILED: {e}")
        import traceback
        traceback.print_exc()

    print("\n✅ FULL CHAIN COMPLETE.")

if __name__ == "__main__":
    asyncio.run(test_full_chain())
