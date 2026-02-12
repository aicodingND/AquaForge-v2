# core/scoring.py
from __future__ import annotations

import logging

import pandas as pd

from swim_ai_reflex.backend.core.rules import MeetRules, VISAADualRules
from swim_ai_reflex.backend.utils.helpers import normalize_team_name

logger = logging.getLogger(__name__)

# Standard High School Order (Girls then Boys)
BASE_EVENTS = [
    "200 Medley Relay",
    "200 Free",
    "200 IM",
    "50 Free",
    "Diving",
    "100 Fly",
    "100 Free",
    "500 Free",
    "200 Free Relay",
    "100 Back",
    "100 Breast",
    "400 Free Relay",
]

# OPTIMIZED: Use list comprehension instead of loop (faster initialization)
EVENT_ORDER = [
    variant for ev in BASE_EVENTS for variant in [f"Girls {ev}", f"Boys {ev}", ev]
]

# Named constant for clarity (avoiding magic numbers)
UNLIMITED_ENTRIES_THRESHOLD = 100


def is_scoring_grade(grade, min_grade=8) -> bool:
    """Check if a grade is eligible for scoring."""
    try:
        if grade is None:
            return False
        return int(grade) >= min_grade
    except (ValueError, TypeError):
        return False


def score_event_with_rules(df_event: pd.DataFrame, rules: MeetRules) -> pd.DataFrame:
    """
    Scores a single event group based on the provided rules.
    Assumes df_event contains only one event's data.
    """
    if df_event.empty:
        return df_event.assign(
            place=pd.Series(dtype=int), points=0.0, scoring_eligible=False
        )

    is_diving = (
        df_event["is_diving"].any() if "is_diving" in df_event.columns else False
    )

    # Sort
    if is_diving:
        # Descending for diving score
        # Ensure 'dive_score' is used if available, else 'time'
        col = (
            "dive_score"
            if "dive_score" in df_event.columns
            and df_event["dive_score"].notnull().any()
            else "time"
        )
        df_sorted = df_event.sort_values(col, ascending=False).copy()
    else:
        # Ascending for swimming time
        df_sorted = df_event.sort_values("time", ascending=True).copy()

    # Determine scoring eligibility FIRST
    if "grade" in df_sorted.columns:
        df_sorted["scoring_eligible"] = df_sorted["grade"].apply(
            lambda g: is_scoring_grade(g, min_grade=rules.min_scoring_grade)
        )
    else:
        logger.warning(
            "Grade column missing from event data — grade eligibility cannot be enforced. "
            "All swimmers defaulting to scoring-eligible. Upload grade data to enforce "
            "VISAA exhibition rules for grades 7-8."
        )
        df_sorted["scoring_eligible"] = True

    # Separate scoring and non-scoring entries
    scoring_entries = df_sorted[df_sorted["scoring_eligible"]].copy()
    non_scoring_entries = df_sorted[~df_sorted["scoring_eligible"]].copy()

    # Assign places ONLY to scoring entries
    # This ensures non-scoring swimmers do not displace score-eligible swimmers
    # (Effectively treating them as forfeits for scoring purposes)
    scoring_entries["place"] = range(1, len(scoring_entries) + 1)

    # Calculate points for scoring entries
    is_relay = df_sorted["is_relay"].any()
    points_map = rules.relay_points if is_relay else rules.individual_points

    def get_points(place):
        if place <= len(points_map):
            return points_map[place - 1]
        return 0.0

    scoring_entries["points"] = scoring_entries["place"].apply(get_points).astype(float)

    # Apply penalties
    if "penalty" in scoring_entries.columns:
        scoring_entries["points"] = scoring_entries["points"] - scoring_entries[
            "penalty"
        ].fillna(0)

    # Enforce Max Scorers Per Team (e.g. only top 3 score)
    # PERFORMANCE FIX: Vectorized operations instead of .iterrows() (ported from Windows)
    if "team" in scoring_entries.columns:
        scorer_limit = (
            rules.max_scorers_per_team_relay
            if is_relay
            else rules.max_scorers_per_team_individual
        )

        # Normalize team names once for all rows
        scoring_entries["_team_norm"] = scoring_entries["team"].apply(
            normalize_team_name
        )

        # Create cumulative count per team (only for rows with points > 0)
        scoring_entries["_team_rank"] = (
            scoring_entries[scoring_entries["points"] > 0]
            .groupby("_team_norm")
            .cumcount()
            + 1
        )

        # Zero out points for swimmers beyond the limit
        scoring_entries.loc[scoring_entries["_team_rank"] > scorer_limit, "points"] = (
            0.0
        )

        # Clean up temporary columns
        scoring_entries.drop(
            columns=["_team_norm", "_team_rank"], inplace=True, errors="ignore"
        )

    # Handle non-scoring entries (Assign 0 points and 'Exh' place)
    non_scoring_entries["place"] = (
        999  # Or 'Exh' if string allowed, but keeping int for safety
    )
    non_scoring_entries["points"] = 0.0

    # Combine back
    df_result = pd.concat([scoring_entries, non_scoring_entries])

    # Handle ties (Average points) for scoring entries only
    sort_col = (
        "dive_score" if is_diving and "dive_score" in df_result.columns else "time"
    )

    # Re-sort combined result
    if is_diving:
        df_result = df_result.sort_values(sort_col, ascending=False)
    else:
        df_result = df_result.sort_values(sort_col, ascending=True)

    return df_result


def apply_event_entry_limits(df: pd.DataFrame, rules: MeetRules) -> pd.DataFrame:
    """
    Enforces max entries per team per event.
    """
    out_parts = []
    limit = rules.max_entries_per_team_per_event
    relay_limit = rules.max_relays_per_team_per_event

    # Pre-calculate limits to avoid repeated checks
    is_unlimited = limit > UNLIMITED_ENTRIES_THRESHOLD

    for ev, grp in df.groupby("event"):
        is_relay = grp["is_relay"].any()
        is_diving = grp["is_diving"].any() if "is_diving" in grp.columns else False

        current_limit = relay_limit if is_relay else limit

        # If unlimited and not a relay (or relay limit is also high?), just keep all
        if is_unlimited and not is_relay:
            out_parts.append(grp)
            continue

        kept = []
        # Normalize team names to properly group variants (e.g. "Seton" vs "Seton School")
        # Add temporary normalized column
        grp = grp.copy()
        grp["team_norm"] = grp["team"].apply(normalize_team_name)

        for team_norm in grp["team_norm"].unique():
            team_rows = grp[grp["team_norm"] == team_norm]

            # Sort best first
            sort_col = (
                "dive_score"
                if is_diving and "dive_score" in team_rows.columns
                else "time"
            )
            ascending = not is_diving

            # Handle sorting with NaNs explicitly if needed, but default usually okay
            team_rows = team_rows.sort_values(sort_col, ascending=ascending)
            kept.append(team_rows.head(current_limit))

        if kept:
            out_parts.append(pd.concat(kept, ignore_index=True))

    if out_parts:
        return pd.concat(out_parts, ignore_index=True)
    return pd.DataFrame(columns=df.columns)


def enforce_max_events_per_swimmer(df: pd.DataFrame, rules: MeetRules) -> pd.DataFrame:
    """
    Enforces max events per swimmer by capping individual and total events.

    For each swimmer who exceeds the limits:
    - Individual limit: keep only their best individual events (lowest time
      for swimming, highest dive_score for diving).
    - Total limit: after applying individual caps, keep best events overall
      (individual + relay) up to the total cap.

    Relay events do NOT count toward the individual limit but DO count toward
    the total limit.
    """
    if df.empty:
        return df

    # Ensure required columns
    if "is_relay" not in df.columns:
        if "event" in df.columns:
            df = df.copy()
            df["is_relay"] = df["event"].str.lower().str.contains("relay", na=False)
        else:
            return df

    if "is_diving" not in df.columns:
        if "event" in df.columns:
            df = df.copy()
            df["is_diving"] = (
                df["event"]
                .str.lower()
                .str.contains("diving|dive", regex=True, na=False)
            )
        else:
            df = df.copy()
            df["is_diving"] = False

    max_individual = rules.max_individual_events_per_swimmer
    max_total = rules.max_total_events_per_swimmer

    rows_to_keep = []

    for swimmer, swimmer_df in df.groupby("swimmer"):
        individual_entries = swimmer_df[~swimmer_df["is_relay"]].copy()
        relay_entries = swimmer_df[swimmer_df["is_relay"]].copy()

        # --- Step 1: Cap individual events ---
        if len(individual_entries) > max_individual:
            diving = individual_entries[individual_entries["is_diving"]].copy()
            swimming = individual_entries[~individual_entries["is_diving"]].copy()

            if not swimming.empty:
                swimming = swimming.sort_values("time", ascending=True)
            if not diving.empty:
                sort_col = (
                    "dive_score"
                    if "dive_score" in diving.columns
                    and diving["dive_score"].notnull().any()
                    else "time"
                )
                diving = diving.sort_values(sort_col, ascending=(sort_col == "time"))

            combined = []
            if not swimming.empty:
                swimming = swimming.copy()
                swimming["_sort_key"] = swimming["time"]
                combined.append(swimming)
            if not diving.empty:
                diving = diving.copy()
                if (
                    "dive_score" in diving.columns
                    and diving["dive_score"].notnull().any()
                ):
                    diving["_sort_key"] = -diving["dive_score"]
                else:
                    diving["_sort_key"] = diving["time"]
                combined.append(diving)

            if combined:
                all_individual = pd.concat(combined)
                all_individual = all_individual.sort_values("_sort_key", ascending=True)
                individual_entries = all_individual.head(max_individual).drop(
                    columns=["_sort_key"]
                )
            else:
                individual_entries = individual_entries.head(max_individual)

        # --- Step 2: Cap total events (individual + relay) ---
        capped = pd.concat([individual_entries, relay_entries], ignore_index=True)

        if len(capped) > max_total:
            remaining_slots = max_total - len(individual_entries)
            if remaining_slots > 0:
                relay_entries = relay_entries.sort_values("time", ascending=True).head(
                    remaining_slots
                )
                capped = pd.concat(
                    [individual_entries, relay_entries], ignore_index=True
                )
            else:
                capped = individual_entries.head(max_total)

        rows_to_keep.append(capped)

    if rows_to_keep:
        return pd.concat(rows_to_keep, ignore_index=True)
    return pd.DataFrame(columns=df.columns)


def full_meet_scoring(
    long_roster: pd.DataFrame, rules: MeetRules = None, validate: bool = True
) -> tuple[pd.DataFrame, dict[str, float]]:
    if rules is None:
        rules = VISAADualRules()

    if long_roster is None or long_roster.empty:
        cols = [
            "swimmer",
            "grade",
            "event",
            "time",
            "team",
            "is_relay",
            "place",
            "points",
        ]
        return pd.DataFrame(columns=cols), {"seton": 0.0, "opponent": 0.0}

    # Ensure is_relay and is_diving columns exist (infer from event name if missing)
    long_roster = long_roster.copy()
    if "is_relay" not in long_roster.columns:
        if "event" in long_roster.columns:
            long_roster["is_relay"] = (
                long_roster["event"].str.lower().str.contains("relay", na=False)
            )
        else:
            long_roster["is_relay"] = False
    if "is_diving" not in long_roster.columns:
        if "event" in long_roster.columns:
            long_roster["is_diving"] = (
                long_roster["event"]
                .str.lower()
                .str.contains("diving|dive", regex=True, na=False)
            )
        else:
            long_roster["is_diving"] = False

    # 1. Apply entry limits
    capped = apply_event_entry_limits(long_roster, rules)

    # 2. Enforce max events per swimmer (safety net — optimizer should already respect this)
    if "swimmer" in capped.columns:
        capped = enforce_max_events_per_swimmer(capped, rules)

    # 3. Score each event
    scored_parts = []
    for ev, grp in capped.groupby("event"):
        scored = score_event_with_rules(grp, rules)
        scored_parts.append(scored)

    if scored_parts:
        full_scored = pd.concat(scored_parts, ignore_index=True)
    else:
        full_scored = pd.DataFrame(columns=list(capped.columns) + ["place", "points"])

    # 4. Calculate totals using normalized team names for consistency
    # OPTIMIZED: Use centralized normalize_team_name function
    full_scored["team_norm"] = full_scored["team"].apply(normalize_team_name)

    # Calculate Seton score explicitly
    seton_score = float(
        full_scored.loc[full_scored["team_norm"] == "seton", "points"].sum()
    )

    # Calculate Opponent score (everyone who is NOT Seton)
    # This handles case where opponent team name is "Immanuel" or "Trinity" etc.
    opponent_score = float(
        full_scored.loc[full_scored["team_norm"] != "seton", "points"].sum()
    )

    totals = {
        "seton": seton_score,
        "opponent": opponent_score,
    }

    # 5. VALIDATION: Check if scoring follows standard dual meet rules
    if validate:
        try:
            from swim_ai_reflex.backend.core.scoring_validator import (
                print_validation_report,
                validate_meet_scoring,
            )

            # Determine gender if possible
            gender = None
            if "gender" in full_scored.columns:
                genders = full_scored["gender"].unique()
                if len(genders) == 1:
                    gender = (
                        "Girls"
                        if genders[0] == "F"
                        else "Boys"
                        if genders[0] == "M"
                        else None
                    )

            validation = validate_meet_scoring(full_scored, totals, gender)

            # Print validation report if there are warnings
            if validation["warnings"] or not validation["valid"]:
                print_validation_report(validation)
        except ImportError:
            pass  # Validation module not available

    return full_scored.drop(columns=["team_norm"]), totals
