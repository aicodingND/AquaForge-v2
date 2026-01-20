"""
E2E Test Script for AquaForge
Tests file parsing for Seton Boys and Immanuel Boys files
"""
import sys
import os

# Add project root to path
sys.path.insert(0, r"c:\Users\Michael\Desktop\AquaForgeFinal")

from swim_ai_reflex.backend.services.data_service import data_service
from swim_ai_reflex.backend.services.data_filter_service import data_filter_service
from swim_ai_reflex.backend.core.rules import VISAADualRules
import asyncio

UPLOAD_DIR = r"c:\Users\Michael\Desktop\AquaForgeFinal\uploads"

async def test_file_parsing():
    print("=" * 60)
    print("E2E FILE PARSING TEST")
    print("=" * 60)
    
    # Test files
    seton_file = os.path.join(UPLOAD_DIR, "Seton Boys v3.1.xlsx")
    immanuel_file = os.path.join(UPLOAD_DIR, "Immanuel Boys V3.xlsx")
    
    print(f"\n1. Testing Seton Boys file: {seton_file}")
    print(f"   Exists: {os.path.exists(seton_file)}")
    
    # Load Seton
    seton_result = await data_service.load_roster_from_path(seton_file)
    print(f"   Load Success: {seton_result['success']}")
    if seton_result['success']:
        df_seton = seton_result['data']
        print(f"   Columns: {list(df_seton.columns)}")
        print(f"   Rows: {len(df_seton)}")
        print(f"   Unique Swimmers: {df_seton['swimmer'].nunique() if 'swimmer' in df_seton.columns else 'N/A'}")
        if 'event' in df_seton.columns:
            print(f"   Events: {df_seton['event'].unique().tolist()[:5]}...")
        if 'gender' in df_seton.columns:
            print(f"   Genders: {df_seton['gender'].unique().tolist()}")
        print("\n   Sample data (first 3 rows):")
        print(df_seton.head(3).to_string())
    else:
        print(f"   ERROR: {seton_result.get('message', 'Unknown error')}")
    
    print(f"\n2. Testing Immanuel Boys file: {immanuel_file}")
    print(f"   Exists: {os.path.exists(immanuel_file)}")
    
    # Load Immanuel
    immanuel_result = await data_service.load_roster_from_path(immanuel_file)
    print(f"   Load Success: {immanuel_result['success']}")
    if immanuel_result['success']:
        df_imm = immanuel_result['data']
        print(f"   Columns: {list(df_imm.columns)}")
        print(f"   Rows: {len(df_imm)}")
        print(f"   Unique Swimmers: {df_imm['swimmer'].nunique() if 'swimmer' in df_imm.columns else 'N/A'}")
        if 'event' in df_imm.columns:
            print(f"   Events: {df_imm['event'].unique().tolist()[:5]}...")
        if 'gender' in df_imm.columns:
            print(f"   Genders: {df_imm['gender'].unique().tolist()}")
        print("\n   Sample data (first 3 rows):")
        print(df_imm.head(3).to_string())
    else:
        print(f"   ERROR: {immanuel_result.get('message', 'Unknown error')}")
    
    # Test filtering for Boys only
    print("\n" + "=" * 60)
    print("3. Testing Data Filtering (Boys Individual)")
    print("=" * 60)
    
    if seton_result['success'] and immanuel_result['success']:
        rules = VISAADualRules()
        
        # Filter Seton
        df_seton_filtered = data_filter_service.filter_for_dual_meet(
            df_seton,
            gender='M',
            include_individual=True,
            include_relay=True,
            include_diving=True,
            grades=[6, 7, 8, 9, 10, 11, 12],
            rules=rules
        )
        print(f"\n   Seton (Boys filtered): {len(df_seton_filtered)} rows, {df_seton_filtered['swimmer'].nunique() if not df_seton_filtered.empty else 0} swimmers")
        
        # Filter Immanuel
        df_imm_filtered = data_filter_service.filter_for_dual_meet(
            df_imm,
            gender='M',
            include_individual=True,
            include_relay=True,
            include_diving=True,
            grades=[6, 7, 8, 9, 10, 11, 12],
            rules=rules
        )
        print(f"   Immanuel (Boys filtered): {len(df_imm_filtered)} rows, {df_imm_filtered['swimmer'].nunique() if not df_imm_filtered.empty else 0} swimmers")
        
        # Show events
        if not df_seton_filtered.empty:
            print(f"\n   Seton Events: {sorted(df_seton_filtered['event'].unique().tolist())}")
        if not df_imm_filtered.empty:
            print(f"   Immanuel Events: {sorted(df_imm_filtered['event'].unique().tolist())}")
    
    print("\n" + "=" * 60)
    print("TEST COMPLETE")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(test_file_parsing())
