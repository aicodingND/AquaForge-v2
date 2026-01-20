"""
Dataset Category Validation Service
Analyzes each team's data to detect available categories and ensures alignment.
"""
import pandas as pd
from typing import Dict, Tuple
import logging

logger = logging.getLogger(__name__)


def analyze_dataset_categories(df: pd.DataFrame, team_name: str = "Team") -> Dict:
    """
    Analyze a dataset to detect available categories.
    
    Args:
        df: Team's dataframe
        team_name: Name of team for logging
    
    Returns:
        dict with category analysis
    """
    if df.empty:
        return {
            'team_name': team_name,
            'has_boys': False,
            'has_girls': False,
            'has_individual': False,
            'has_relays': False,
            'has_diving': False,
            'boys_events': [],
            'girls_events': [],
            'individual_events': [],
            'relay_events': [],
            'diving_events': [],
            'all_events': [],
            'entry_count': 0,
            'swimmer_count': 0
        }
    
    # Get all events
    all_events = df['event'].unique().tolist() if 'event' in df.columns else []
    
    # Categorize events
    boys_events = [e for e in all_events if 'boys' in e.lower()]
    girls_events = [e for e in all_events if 'girls' in e.lower()]
    
    # Event types
    individual_events = []
    relay_events = []
    diving_events = []
    
    for event in all_events:
        event_lower = event.lower()
        if 'relay' in event_lower:
            relay_events.append(event)
        elif 'diving' in event_lower or 'dive' in event_lower:
            diving_events.append(event)
        else:
            individual_events.append(event)
    
    # Count unique swimmers
    swimmer_count = len(df['swimmer'].unique()) if 'swimmer' in df.columns else 0
    
    analysis = {
        'team_name': team_name,
        'has_boys': len(boys_events) > 0,
        'has_girls': len(girls_events) > 0,
        'has_individual': len(individual_events) > 0,
        'has_relays': len(relay_events) > 0,
        'has_diving': len(diving_events) > 0,
        'boys_events': sorted(boys_events),
        'girls_events': sorted(girls_events),
        'individual_events': sorted(individual_events),
        'relay_events': sorted(relay_events),
        'diving_events': sorted(diving_events),
        'all_events': sorted(all_events),
        'entry_count': len(df),
        'swimmer_count': swimmer_count,
        'event_count': len(all_events)
    }
    
    logger.info(f"Category analysis for {team_name}:")
    logger.info(f"  Boys: {analysis['has_boys']} ({len(boys_events)} events)")
    logger.info(f"  Girls: {analysis['has_girls']} ({len(girls_events)} events)")
    logger.info(f"  Individual: {analysis['has_individual']} ({len(individual_events)} events)")
    logger.info(f"  Relays: {analysis['has_relays']} ({len(relay_events)} events)")
    logger.info(f"  Diving: {analysis['has_diving']} ({len(diving_events)} events)")
    logger.info(f"  Total: {len(all_events)} events, {len(df)} entries, {swimmer_count} swimmers")
    
    return analysis


def find_common_categories(seton_analysis: Dict, opponent_analysis: Dict) -> Dict:
    """
    Find common categories between two teams.
    
    Args:
        seton_analysis: Seton's category analysis
        opponent_analysis: Opponent's category analysis
    
    Returns:
        dict with common categories and recommendations
    """
    # Find common event types
    common_boys = seton_analysis['has_boys'] and opponent_analysis['has_boys']
    common_girls = seton_analysis['has_girls'] and opponent_analysis['has_girls']
    common_individual = seton_analysis['has_individual'] and opponent_analysis['has_individual']
    common_relays = seton_analysis['has_relays'] and opponent_analysis['has_relays']
    common_diving = seton_analysis['has_diving'] and opponent_analysis['has_diving']
    
    # Find common events
    seton_events = set(seton_analysis['all_events'])
    opponent_events = set(opponent_analysis['all_events'])
    common_events = sorted(list(seton_events & opponent_events))
    
    # Events only in one team
    seton_only = sorted(list(seton_events - opponent_events))
    opponent_only = sorted(list(opponent_events - seton_events))
    
    # Generate warnings
    warnings = []
    recommendations = []
    
    if not common_boys and (seton_analysis['has_boys'] or opponent_analysis['has_boys']):
        if seton_analysis['has_boys'] and not opponent_analysis['has_boys']:
            warnings.append("Seton has boys events but opponent doesn't")
            recommendations.append("Remove boys events from Seton data or add to opponent")
        else:
            warnings.append("Opponent has boys events but Seton doesn't")
            recommendations.append("Remove boys events from opponent data or add to Seton")
    
    if not common_girls and (seton_analysis['has_girls'] or opponent_analysis['has_girls']):
        if seton_analysis['has_girls'] and not opponent_analysis['has_girls']:
            warnings.append("Seton has girls events but opponent doesn't")
            recommendations.append("Remove girls events from Seton data or add to opponent")
        else:
            warnings.append("Opponent has girls events but Seton doesn't")
            recommendations.append("Remove girls events from opponent data or add to Seton")
    
    if not common_relays and (seton_analysis['has_relays'] or opponent_analysis['has_relays']):
        warnings.append("Relay events not present in both teams")
        recommendations.append("Ensure both teams have relay data or remove relays from both")
    
    if not common_diving and (seton_analysis['has_diving'] or opponent_analysis['has_diving']):
        warnings.append("Diving events not present in both teams")
        recommendations.append("Ensure both teams have diving data or remove diving from both")
    
    if len(common_events) < len(seton_events) * 0.5 or len(common_events) < len(opponent_events) * 0.5:
        warnings.append(f"Low event overlap: Only {len(common_events)} common events")
        recommendations.append("Verify both teams competed in same meet")
    
    # Calculate alignment score (0-100)
    if seton_events or opponent_events:
        alignment_score = (len(common_events) / max(len(seton_events), len(opponent_events))) * 100
    else:
        alignment_score = 0
    
    result = {
        'common_boys': common_boys,
        'common_girls': common_girls,
        'common_individual': common_individual,
        'common_relays': common_relays,
        'common_diving': common_diving,
        'common_events': common_events,
        'common_event_count': len(common_events),
        'seton_only_events': seton_only,
        'opponent_only_events': opponent_only,
        'alignment_score': alignment_score,
        'warnings': warnings,
        'recommendations': recommendations,
        'is_aligned': alignment_score >= 80 and len(warnings) == 0
    }
    
    logger.info("Common category analysis:")
    logger.info(f"  Boys: {common_boys}")
    logger.info(f"  Girls: {common_girls}")
    logger.info(f"  Individual: {common_individual}")
    logger.info(f"  Relays: {common_relays}")
    logger.info(f"  Diving: {common_diving}")
    logger.info(f"  Common events: {len(common_events)}")
    logger.info(f"  Alignment score: {alignment_score:.1f}%")
    
    if warnings:
        logger.warning("Category alignment warnings:")
        for warning in warnings:
            logger.warning(f"  - {warning}")
    
    return result


def filter_to_common_categories(
    seton_df: pd.DataFrame,
    opponent_df: pd.DataFrame,
    common_analysis: Dict
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Filter both datasets to only include common categories.
    
    Args:
        seton_df: Seton's dataframe
        opponent_df: Opponent's dataframe
        common_analysis: Result from find_common_categories()
    
    Returns:
        (filtered_seton_df, filtered_opponent_df)
    """
    if seton_df.empty or opponent_df.empty:
        return seton_df, opponent_df
    
    common_events = set(common_analysis['common_events'])
    
    if not common_events:
        logger.warning("No common events found - returning empty dataframes")
        return pd.DataFrame(), pd.DataFrame()
    
    # Filter to common events
    seton_filtered = seton_df[seton_df['event'].isin(common_events)].copy()
    opponent_filtered = opponent_df[opponent_df['event'].isin(common_events)].copy()
    
    logger.info("Filtered to common categories:")
    logger.info(f"  Seton: {len(seton_df)} → {len(seton_filtered)} entries")
    logger.info(f"  Opponent: {len(opponent_df)} → {len(opponent_filtered)} entries")
    
    return seton_filtered, opponent_filtered


def validate_category_alignment(seton_df: pd.DataFrame, opponent_df: pd.DataFrame) -> Dict:
    """
    Complete category validation workflow.
    
    Args:
        seton_df: Seton's dataframe
        opponent_df: Opponent's dataframe
    
    Returns:
        dict with validation results and filtered dataframes
    """
    # Analyze each dataset
    seton_analysis = analyze_dataset_categories(seton_df, "Seton")
    opponent_analysis = analyze_dataset_categories(opponent_df, "Opponent")
    
    # Find common categories
    common_analysis = find_common_categories(seton_analysis, opponent_analysis)
    
    # Filter to common categories
    seton_filtered, opponent_filtered = filter_to_common_categories(
        seton_df, opponent_df, common_analysis
    )
    
    return {
        'seton_analysis': seton_analysis,
        'opponent_analysis': opponent_analysis,
        'common_analysis': common_analysis,
        'seton_filtered': seton_filtered,
        'opponent_filtered': opponent_filtered,
        'is_valid': common_analysis['is_aligned'],
        'warnings': common_analysis['warnings'],
        'recommendations': common_analysis['recommendations']
    }
