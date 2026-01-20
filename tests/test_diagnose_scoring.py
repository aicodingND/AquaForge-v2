"""
Diagnostic: Check what's happening with the scoring
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

async def diagnose_scoring():
    print("\n" + "="*80)
    print("DIAGNOSTIC: Scoring Analysis")
    print("="*80)
    
    # Parse PDFs
    base_path = Path(__file__).parent.parent / "uploads"
    seton_pdf = base_path / "seton swimming individual times-no manipulation-nov23,25.pdf"
    trinity_pdf = base_path / "Trinity Christian swimming individual times-no manipulation-nov23,25.pdf"
    
    print("\n[1] Parsing PDFs...")
    seton_df = await asyncio.to_thread(parse_hytek_pdf, str(seton_pdf))
    trinity_df = await asyncio.to_thread(parse_hytek_pdf, str(trinity_pdf))
    
    # Filter for girls senior events (no diving)
    print("\n[2] Filtering for girls events (no diving, no relays)...")
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
    
    print(f"  Seton: {len(seton_girls)} entries")
    print(f"  Trinity: {len(trinity_girls)} entries")
    
    # Create opponent lineup
    print("\n[3] Creating Trinity's best lineup...")
    rules = VISAADualRules()
    trinity_lineup = greedy_opponent_best_lineup(trinity_girls)
    print(f"  Trinity lineup: {len(trinity_lineup)} entries")
    
    # For Seton, use greedy top 4 per event
    print("\n[4] Creating Seton's lineup (greedy)...")
    seton_lineup_parts = []
    for event, grp in seton_girls.groupby('event'):
        top4 = grp.sort_values('time', ascending=True).head(4)
        seton_lineup_parts.append(top4)
    seton_lineup = pd.concat(seton_lineup_parts, ignore_index=True) if seton_lineup_parts else pd.DataFrame()
    
    # Enforce 2 events per swimmer
    seton_final_parts = []
    for swimmer, grp in seton_lineup.groupby('swimmer'):
        if len(grp) <= 2:
            seton_final_parts.append(grp)
        else:
            seton_final_parts.append(grp.sort_values('time', ascending=True).head(2))
    seton_lineup = pd.concat(seton_final_parts, ignore_index=True) if seton_final_parts else pd.DataFrame()
    
    print(f"  Seton lineup: {len(seton_lineup)} entries")
    
    # Combine and score
    print("\n[5] Combining lineups...")
    seton_lineup['team'] = 'seton'
    trinity_lineup['team'] = 'opponent'
    combined = pd.concat([seton_lineup, trinity_lineup], ignore_index=True)
    
    print(f"  Combined entries: {len(combined)}")
    print(f"  Unique events: {combined['event'].nunique()}")
    print(f"  Events list: {sorted(combined['event'].unique())}")
    
    # Check for duplicate events
    print("\n[6] Checking for duplicate event entries...")
    event_counts = combined.groupby(['event', 'team']).size().reset_index(name='count')
    print(event_counts.to_string())
    
    # Score the meet
    print("\n[7] Scoring the meet...")
    scored_df, totals = full_meet_scoring(combined, rules=rules)
    
    print(f"\n  Seton score: {totals['seton']}")
    print(f"  Trinity score: {totals['opponent']}")
    
    # Show scoring breakdown
    print("\n[8] Scoring breakdown by event:")
    for event in sorted(scored_df['event'].unique()):
        event_data = scored_df[scored_df['event'] == event]
        seton_pts = event_data[event_data['team'] == 'seton']['points'].sum()
        trinity_pts = event_data[event_data['team'] == 'opponent']['points'].sum()
        seton_count = len(event_data[event_data['team'] == 'seton'])
        trinity_count = len(event_data[event_data['team'] == 'opponent'])
        print(f"  {event}: Seton {seton_pts} pts ({seton_count} swimmers), Trinity {trinity_pts} pts ({trinity_count} swimmers)")
    
    print("\n" + "="*80)

if __name__ == "__main__":
    asyncio.run(diagnose_scoring())
