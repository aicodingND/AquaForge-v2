# core/dual_meet_scoring.py
"""
Dual meet scoring that ensures ALL 232 points are always awarded.

CRITICAL RULE: In a dual meet, all 232 points MUST be distributed.
- 8 events × 29 points per event = 232 total
- If a team doesn't have a swimmer, opponent gets those points
- If a swimmer is non-scoring (exhibition), their points go to next eligible swimmer
- Seton + Trinity = 232 (always, exactly)
"""

from typing import Dict, Tuple

import pandas as pd

from swim_ai_reflex.backend.core.rules import MeetRules, VISAADualRules

# Standard dual meet scoring
INDIVIDUAL_POINTS = [8, 6, 5, 4, 3, 2, 1]  # Total: 29 points
POINTS_PER_EVENT = sum(INDIVIDUAL_POINTS)  # 29
STANDARD_EVENTS = 8
TOTAL_MEET_POINTS = POINTS_PER_EVENT * STANDARD_EVENTS  # 232


def fill_empty_slots(df_event: pd.DataFrame, max_per_team: int = 4) -> pd.DataFrame:
    """
    Fill empty event slots with placeholder 'NO SWIMMER' entries.

    This ensures:
    - All teams have up to 4 entries per event (or show forfeit)
    - Points are properly distributed when a team has fewer swimmers
    - UI shows where points were forfeited

    Args:
        df_event: Event data for both teams
        max_per_team: Maximum swimmers per team (default 4)

    Returns:
        DataFrame with placeholder entries added
    """
    if df_event.empty:
        return df_event

    # Get unique teams and event
    teams = df_event["team"].unique()
    event = df_event["event"].iloc[0] if "event" in df_event.columns else "Unknown"

    # Check how many swimmers each team has
    placeholders = []

    for team in teams:
        team_swimmers = df_event[df_event["team"] == team]
        count = len(team_swimmers)

        if count < max_per_team:
            # Need to add placeholders
            for i in range(max_per_team - count):
                placeholder = {
                    "swimmer": f"NO SWIMMER #{i + 1} - POINTS FORFEIT",
                    "team": team,
                    "event": event,
                    "time": 9999.99,  # Impossibly slow time
                    "grade": 0,  # Non-scoring
                    "gender": df_event["gender"].iloc[0]
                    if "gender" in df_event.columns
                    else "F",
                    "is_relay": False,
                    "is_diving": False,
                    "scoring_eligible": False,  # Explicitly non-scoring
                    "is_placeholder": True,  # Mark as placeholder
                }
                placeholders.append(placeholder)

    if placeholders:
        placeholder_df = pd.DataFrame(placeholders)
        return pd.concat([df_event, placeholder_df], ignore_index=True)

    return df_event


def score_dual_meet_event(df_event: pd.DataFrame, rules: MeetRules) -> pd.DataFrame:
    """
    Score a single dual meet event ensuring all 29 points are awarded.

    Key rules:
    - Top 7 places score: 8, 6, 5, 4, 3, 2, 1 (total 29)
    - Grades 8-12 are scoring eligible
    - Exhibition swimmers (grades 7 and below, e.g. 6th, 7th) can place but don't score
    - When exhibition swimmer places, next eligible swimmer gets their points
    - All 29 points MUST be awarded
    """
    if df_event.empty:
        return df_event.assign(
            place=pd.Series(dtype=int), points=0.0, scoring_eligible=False
        )

    # Fill empty slots with placeholders
    df_event = fill_empty_slots(df_event, max_per_team=4)

    # Sort by time (ascending = faster is better)
    df_sorted = df_event.sort_values("time", ascending=True).copy()

    # Assign physical places (1st, 2nd, 3rd, etc.)
    df_sorted["place"] = range(1, len(df_sorted) + 1)

    # Determine scoring eligibility
    if "scoring_eligible" not in df_sorted.columns:
        if "grade" in df_sorted.columns:
            df_sorted["scoring_eligible"] = df_sorted["grade"].apply(
                lambda g: (int(g) >= 8 if pd.notna(g) else True) if not isinstance(g, str) else (int(g) >= 8 if g.isdigit() else True)
            )
        else:
            df_sorted["scoring_eligible"] = True

    # Ensure no NaN values in scoring_eligible (fill with True)
    scoring_eligible_filled = df_sorted["scoring_eligible"].fillna(True)
    df_sorted["scoring_eligible"] = scoring_eligible_filled.infer_objects(
        copy=False
    ).astype(bool)

    # Award points to scoring-eligible swimmers only
    scoring_swimmers = df_sorted[df_sorted["scoring_eligible"]].copy()

    # CRITICAL: All 29 points MUST be awarded
    # If there are fewer than 7 scoring swimmers, we still need to distribute all points
    # The way dual meets work: if a team doesn't have swimmers, opponent gets those points

    # Assign points based on scoring place (not physical place)
    points_awarded = []
    for idx, (_, swimmer) in enumerate(scoring_swimmers.iterrows()):
        if idx < len(INDIVIDUAL_POINTS):
            points_awarded.append((swimmer.name, INDIVIDUAL_POINTS[idx]))
        else:
            points_awarded.append((swimmer.name, 0.0))

    # Initialize all points to 0
    df_sorted["points"] = 0.0

    # Assign points to scoring swimmers
    for idx, points in points_awarded:
        df_sorted.at[idx, "points"] = points

    # Calculate how many points were awarded
    points_distributed = sum([p for _, p in points_awarded])
    points_remaining = POINTS_PER_EVENT - points_distributed

    # If there are remaining points (fewer than 7 scoring swimmers),
    # award them to the team that has the most swimmers (they "win by forfeit")
    if points_remaining > 0 and not df_sorted.empty:
        # Count swimmers per team (excluding placeholders)
        if "is_placeholder" in df_sorted.columns:
            # Ensure boolean type before using ~ operator to avoid TypeError
            placeholder_mask = df_sorted["is_placeholder"].fillna(False)
            placeholder_mask = placeholder_mask.infer_objects(copy=False).astype(bool)
            real_swimmers = df_sorted[~placeholder_mask]
        else:
            real_swimmers = df_sorted.copy()

        if not real_swimmers.empty:
            team_counts = real_swimmers.groupby("team").size()
            if len(team_counts) > 0:
                # Give remaining points to the team with more swimmers
                winning_team = team_counts.idxmax()

                # Find the last scoring swimmer from the winning team and add the remaining points
                team_swimmers = df_sorted[
                    (df_sorted["team"] == winning_team) & (df_sorted["points"] > 0)
                ]
                if not team_swimmers.empty:
                    last_scorer_idx = team_swimmers.index[-1]
                    df_sorted.at[last_scorer_idx, "points"] += points_remaining

    return df_sorted


def score_dual_meet(
    seton_df: pd.DataFrame, opponent_df: pd.DataFrame, rules: MeetRules = None
) -> Tuple[pd.DataFrame, Dict[str, float]]:
    """
    Score a complete dual meet ensuring exactly 232 points are awarded.

    Returns:
        Tuple of (scored_dataframe, totals_dict)
        totals_dict['seton'] + totals_dict['opponent'] = 232 (always)
    """
    if rules is None:
        rules = VISAADualRules()

    # Combine rosters
    seton_df = seton_df.copy()
    opponent_df = opponent_df.copy()
    seton_df["team"] = "seton"
    opponent_df["team"] = "opponent"

    combined = pd.concat([seton_df, opponent_df], ignore_index=True)

    if combined.empty:
        return combined, {"seton": 0.0, "opponent": 0.0}

    # Score each event
    scored_parts = []
    event_totals = {}

    for event in combined["event"].unique():
        event_data = combined[combined["event"] == event]
        scored_event = score_dual_meet_event(event_data, rules)
        scored_parts.append(scored_event)

        # Track points per event
        event_totals[event] = scored_event["points"].sum()

    # Combine all scored events
    full_scored = (
        pd.concat(scored_parts, ignore_index=True) if scored_parts else pd.DataFrame()
    )

    # Calculate team totals
    seton_total = full_scored[full_scored["team"] == "seton"]["points"].sum()
    opponent_total = full_scored[full_scored["team"] == "opponent"]["points"].sum()

    totals = {"seton": float(seton_total), "opponent": float(opponent_total)}

    # CRITICAL VALIDATION: Ensure total = 232
    combined_total = seton_total + opponent_total
    expected_total = len(event_totals) * POINTS_PER_EVENT

    if abs(combined_total - expected_total) > 0.1:  # Allow tiny floating point errors
        print("\n⚠️  WARNING: Point total mismatch!")
        print(
            f"   Expected: {expected_total} points ({len(event_totals)} events × {POINTS_PER_EVENT})"
        )
        print(f"   Actual: {combined_total} points")
        print(f"   Seton: {seton_total}, Opponent: {opponent_total}")
        print("\n   Event breakdown:")
        for event, points in event_totals.items():
            print(f"     {event}: {points} points (expected {POINTS_PER_EVENT})")

    return full_scored, totals


def validate_dual_meet_total(totals: Dict[str, float], num_events: int = 8) -> bool:
    """
    Validate that total points equal expected maximum.

    Args:
        totals: Dictionary with 'seton' and 'opponent' scores
        num_events: Number of events (default 8 for standard dual meet)

    Returns:
        True if totals sum to expected value
    """
    expected = num_events * POINTS_PER_EVENT
    actual = sum(totals.values())
    return abs(actual - expected) < 0.1  # Allow tiny floating point errors


def print_dual_meet_summary(totals: Dict[str, float], num_events: int = 8):
    """
    Print a summary of dual meet scoring.
    """
    expected = num_events * POINTS_PER_EVENT
    actual = sum(totals.values())
    is_valid = abs(actual - expected) < 0.1

    print(f"\n{'=' * 60}")
    print("DUAL MEET SCORING SUMMARY")
    print(f"{'=' * 60}")
    print(f"Events: {num_events}")
    print(f"Points per event: {POINTS_PER_EVENT}")
    print(f"Expected total: {expected}")
    print("\nTeam Scores:")
    print(f"  Seton:    {totals.get('seton', 0):.1f}")
    print(f"  Opponent: {totals.get('opponent', 0):.1f}")
    print(f"  Total:    {actual:.1f}")
    print(f"\nValidation: {'✅ VALID' if is_valid else '❌ INVALID'}")
    if not is_valid:
        print(f"  Difference: {actual - expected:.1f} points")
    print(f"{'=' * 60}\n")
