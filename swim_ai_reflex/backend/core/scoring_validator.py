# core/scoring_validator.py
"""
Validation utilities to ensure scoring follows standard dual meet rules.

STANDARD DUAL MEET RULES:
- 8 individual events per gender (Girls/Boys)
- 29 points per event maximum (8+6+5+4+3+2+1 for top 7 places)
- Total: 232 points maximum per gender (29 × 8 = 232)
- 4 swimmers per team per event (or forfeit points)
"""
from typing import Dict, List, Any, Optional
import pandas as pd

# Standard dual meet individual events (per gender)
STANDARD_INDIVIDUAL_EVENTS = [
    '200 Free',
    '200 IM', 
    '50 Free',
    '100 Fly',
    '100 Free',
    '500 Free',
    '100 Back',
    '100 Breast'
]

# Points per place for individual events
INDIVIDUAL_POINTS = [8, 6, 5, 4, 3, 2, 1]  # Total: 29 points per event

# Maximum points per event
MAX_POINTS_PER_EVENT = sum(INDIVIDUAL_POINTS)  # 29

# Maximum total points for 8 individual events
MAX_TOTAL_POINTS = MAX_POINTS_PER_EVENT * len(STANDARD_INDIVIDUAL_EVENTS)  # 232


def validate_event_list(events: List[str], gender: Optional[str] = None) -> Dict[str, Any]:
    """
    Validate that events match standard dual meet format.
    
    Returns:
        dict with validation results and warnings
    """
    results = {
        'valid': True,
        'warnings': [],
        'errors': [],
        'event_count': len(events),
        'expected_count': len(STANDARD_INDIVIDUAL_EVENTS),
        'events': events
    }
    
    # Check event count
    if len(events) != len(STANDARD_INDIVIDUAL_EVENTS):
        results['warnings'].append(
            f"Expected {len(STANDARD_INDIVIDUAL_EVENTS)} individual events, found {len(events)}"
        )
    
    # Check for non-standard events
    gender_prefix = f"{gender} " if gender else ""
    [f"{gender_prefix}{e}" for e in STANDARD_INDIVIDUAL_EVENTS]
    
    for event in events:
        # Remove gender prefix for comparison
        event_base = event.replace("Girls ", "").replace("Boys ", "")
        if event_base not in STANDARD_INDIVIDUAL_EVENTS:
            results['warnings'].append(f"Non-standard event: {event}")
    
    # Check for missing standard events
    for std_event in STANDARD_INDIVIDUAL_EVENTS:
        full_event = f"{gender_prefix}{std_event}"
        if full_event not in events and std_event not in events:
            results['warnings'].append(f"Missing standard event: {std_event}")
    
    return results


def validate_event_scoring(scored_df: pd.DataFrame, event: str) -> Dict[str, Any]:
    """
    Validate scoring for a single event.
    
    Returns:
        dict with validation results
    """
    event_data = scored_df[scored_df['event'] == event]
    
    total_points = event_data['points'].sum()
    max_place = event_data['place'].max() if len(event_data) > 0 else 0
    
    results = {
        'event': event,
        'valid': True,
        'total_points': total_points,
        'max_points': MAX_POINTS_PER_EVENT,
        'swimmers': len(event_data),
        'max_place': max_place,
        'warnings': []
    }
    
    # Check if total points exceed maximum
    if total_points > MAX_POINTS_PER_EVENT:
        results['valid'] = False
        results['warnings'].append(
            f"Total points ({total_points}) exceeds maximum ({MAX_POINTS_PER_EVENT})"
        )
    
    # Check if we have the expected number of swimmers (should be up to 8 total, 4 per team)
    if len(event_data) > 8:
        results['warnings'].append(
            f"More than 8 swimmers in event ({len(event_data)})"
        )
    
    return results


def validate_meet_scoring(
    scored_df: pd.DataFrame,
    totals: Dict[str, float],
    gender: Optional[str] = None
) -> Dict[str, Any]:
    """
    Validate overall meet scoring.
    
    Returns:
        dict with comprehensive validation results
    """
    # Get unique events
    events = scored_df['event'].unique().tolist()
    
    # Validate event list
    event_validation = validate_event_list(events, gender)
    
    # Validate each event
    event_results = []
    for event in events:
        event_result = validate_event_scoring(scored_df, event)
        event_results.append(event_result)
    
    # Calculate totals
    combined_total = sum(totals.values())
    
    results = {
        'valid': True,
        'event_validation': event_validation,
        'event_results': event_results,
        'totals': totals,
        'combined_total': combined_total,
        'max_combined_total': MAX_TOTAL_POINTS,
        'warnings': [],
        'summary': {}
    }
    
    # Check combined total
    if combined_total > MAX_TOTAL_POINTS:
        results['valid'] = False
        results['warnings'].append(
            f"⚠️ CRITICAL: Combined total ({combined_total}) exceeds maximum ({MAX_TOTAL_POINTS})"
        )
        results['warnings'].append(
            f"   Expected: {len(STANDARD_INDIVIDUAL_EVENTS)} events × {MAX_POINTS_PER_EVENT} points = {MAX_TOTAL_POINTS} max"
        )
        results['warnings'].append(
            f"   Actual: {len(events)} events scored"
        )
    
    # Add summary
    results['summary'] = {
        'events_scored': len(events),
        'expected_events': len(STANDARD_INDIVIDUAL_EVENTS),
        'points_awarded': combined_total,
        'max_possible': MAX_TOTAL_POINTS,
        'percentage_of_max': (combined_total / MAX_TOTAL_POINTS * 100) if MAX_TOTAL_POINTS > 0 else 0
    }
    
    return results


def print_validation_report(validation: Dict[str, Any]):
    """
    Print a formatted validation report.
    """
    print("\n" + "="*80)
    print("📊 DUAL MEET SCORING VALIDATION REPORT")
    print("="*80)
    
    # Summary
    summary = validation['summary']
    print(f"\n✓ Events Scored: {summary['events_scored']} (expected: {summary['expected_events']})")
    print(f"✓ Points Awarded: {summary['points_awarded']:.1f} / {summary['max_possible']} max")
    print(f"✓ Percentage: {summary['percentage_of_max']:.1f}%")
    
    # Team scores
    totals = validation['totals']
    print("\n📈 Team Scores:")
    for team, score in totals.items():
        print(f"   {team.capitalize()}: {score:.1f}")
    
    # Warnings
    if validation['warnings']:
        print(f"\n⚠️  WARNINGS ({len(validation['warnings'])}):")
        for warning in validation['warnings']:
            print(f"   {warning}")
    
    # Event validation warnings
    event_val = validation['event_validation']
    if event_val['warnings']:
        print("\n⚠️  EVENT LIST WARNINGS:")
        for warning in event_val['warnings']:
            print(f"   {warning}")
    
    # Event-specific issues
    problem_events = [e for e in validation['event_results'] if e['warnings']]
    if problem_events:
        print("\n⚠️  EVENT-SPECIFIC ISSUES:")
        for event in problem_events:
            print(f"   {event['event']}:")
            for warning in event['warnings']:
                print(f"      - {warning}")
    
    # Status
    status = "✅ VALID" if validation['valid'] else "❌ INVALID"
    print(f"\n{status}")
    print("="*80 + "\n")


def get_standard_events_for_gender(gender: str) -> List[str]:
    """
    Get list of standard individual events for a specific gender.
    
    Args:
        gender: 'Girls' or 'Boys'
    
    Returns:
        List of event names with gender prefix
    """
    return [f"{gender} {event}" for event in STANDARD_INDIVIDUAL_EVENTS]
