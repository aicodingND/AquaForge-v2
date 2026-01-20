"""
Direct E2E Test - Bypass service layer to see what's happening
"""
import sys
import os
import pandas as pd
import asyncio
from pathlib import Path

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from swim_ai_reflex.backend.core.hytek_pdf_parser import parse_hytek_pdf
from swim_ai_reflex.backend.core.opponent_model import greedy_opponent_best_lineup
from swim_ai_reflex.backend.core.scoring import full_meet_scoring
from swim_ai_reflex.backend.core.rules import VISAADualRules

async def run_direct_test():
    print("\n" + "="*80)
    print("🏊‍♀️ DIRECT E2E TEST: Seton vs Trinity - Girls Senior Events")
    print("="*80)
    
    # Parse PDFs
    base_path = Path(__file__).parent.parent / "uploads"
    seton_pdf = base_path / "seton swimming individual times-no manipulation-nov23,25.pdf"
    trinity_pdf = base_path / "Trinity Christian swimming individual times-no manipulation-nov23,25.pdf"
    
    print("\n[1] Parsing PDFs...")
    seton_df = await asyncio.to_thread(parse_hytek_pdf, str(seton_pdf))
    trinity_df = await asyncio.to_thread(parse_hytek_pdf, str(trinity_pdf))
    print(f"  Seton: {len(seton_df)} entries")
    print(f"  Trinity: {len(trinity_df)} entries")
    
    # Filter for girls senior events
    print("\n[2] Filtering for girls senior events...")
    seton_girls = seton_df[
        (seton_df['gender'] == 'F') &
        (not seton_df['is_relay']) &
        (seton_df['event'].str.contains('Senior', case=False, na=False)) &
        (~seton_df['event'].str.contains('Diving|Dives|25 ', case=False, na=False))
    ].copy()
    
    trinity_girls = trinity_df[
        (trinity_df['gender'] == 'F') &
        (not trinity_df['is_relay']) &
        (trinity_df['event'].str.contains('Senior', case=False, na=False)) &
        (~trinity_df['event'].str.contains('Diving|Dives|25 ', case=False, na=False))
    ].copy()
    
    print(f"  Seton: {len(seton_girls)} girls senior entries, {seton_girls['swimmer'].nunique()} swimmers")
    print(f"  Trinity: {len(trinity_girls)} girls senior entries, {trinity_girls['swimmer'].nunique()} swimmers")
    
    # Create opponent lineup using greedy model
    print("\n[3] Creating Trinity's best lineup (greedy model)...")
    rules = VISAADualRules()
    trinity_lineup = greedy_opponent_best_lineup(trinity_girls)
    print(f"  Trinity lineup: {len(trinity_lineup)} entries, {trinity_lineup['swimmer'].nunique()} swimmers")
    print(f"  Events: {sorted(trinity_lineup['event'].unique())}")
    
    # For Seton, let's just use their top 4 per event as well (simple greedy)
    print("\n[4] Creating Seton's lineup (simple greedy - top 4 per event)...")
    seton_lineup_parts = []
    for event, grp in seton_girls.groupby('event'):
        top4 = grp.sort_values('time', ascending=True).head(4)
        seton_lineup_parts.append(top4)
    seton_lineup = pd.concat(seton_lineup_parts, ignore_index=True) if seton_lineup_parts else pd.DataFrame()
    
    # Enforce 2 events per swimmer for Seton too
    seton_final_parts = []
    for swimmer, grp in seton_lineup.groupby('swimmer'):
        if len(grp) <= 2:
            seton_final_parts.append(grp)
        else:
            # Keep their 2 fastest events
            seton_final_parts.append(grp.sort_values('time', ascending=True).head(2))
    seton_lineup = pd.concat(seton_final_parts, ignore_index=True) if seton_final_parts else pd.DataFrame()
    
    print(f"  Seton lineup: {len(seton_lineup)} entries, {seton_lineup['swimmer'].nunique()} swimmers")
    print(f"  Events: {sorted(seton_lineup['event'].unique())}")
    
    # Combine lineups
    print("\n[5] Scoring the meet...")
    seton_lineup['team'] = 'seton'
    trinity_lineup['team'] = 'opponent'
    combined = pd.concat([seton_lineup, trinity_lineup], ignore_index=True)
    
    # Score the meet
    scored_df, totals = full_meet_scoring(combined, rules=rules)
    
    seton_score = totals.get('seton', 0)
    trinity_score = totals.get('opponent', 0)
    
    print("\n[6] 📊 RESULTS")
    print("="*80)
    print("\n🏆 FINAL SCORE:")
    print(f"  Seton:    {seton_score}")
    print(f"  Trinity:  {trinity_score}")
    print(f"  Margin:   {abs(seton_score - trinity_score)} points")
    print(f"  Winner:   {'Seton' if seton_score > trinity_score else 'Trinity' if trinity_score > seton_score else 'TIE'}")
    
    # Show event breakdown
    print("\n📋 EVENT BREAKDOWN:")
    print("-"*80)
    for event in sorted(scored_df['event'].unique()):
        event_data = scored_df[scored_df['event'] == event]
        seton_swimmers = event_data[event_data['team'] == 'seton'].sort_values('place')
        trinity_swimmers = event_data[event_data['team'] == 'opponent'].sort_values('place')
        
        seton_pts = seton_swimmers['points'].sum()
        trinity_pts = trinity_swimmers['points'].sum()
        
        print(f"\n{event}")
        print(f"  Seton ({seton_pts} pts):")
        for _, row in seton_swimmers.iterrows():
            print(f"    {int(row['place'])}. {row['swimmer']} - {row['time']:.2f}s ({row['points']} pts)")
        
        print(f"  Trinity ({trinity_pts} pts):")
        for _, row in trinity_swimmers.iterrows():
            print(f"    {int(row['place'])}. {row['swimmer']} - {row['time']:.2f}s ({row['points']} pts)")
    
    print("\n" + "="*80)
    print("✅ DIRECT E2E TEST COMPLETE")
    print("="*80)

if __name__ == "__main__":
    asyncio.run(run_direct_test())
