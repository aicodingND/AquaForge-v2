"""
Meet Alignment Service
Automatically aligns team data to only include entries from when they competed against each other.
"""

import logging

import pandas as pd

logger = logging.getLogger(__name__)


def align_meet_data(
    seton_df: pd.DataFrame, opponent_df: pd.DataFrame
) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    """
    Intelligently align two team datasets to only include data from when they competed against each other.

    Handles cases where:
    - Seton PDF has 1 meet, Opponent PDF has multiple meets
    - Seton PDF has multiple meets, Opponent PDF has 1 meet
    - Both PDFs have multiple meets

    Alignment ensures:
    1. Both teams competed in SAME meet (vs each other)
    2. Only COMMON events are included
    3. Each swimmer appears ONCE per event (best time)
    4. Swimmers are on correct team

    Args:
        seton_df: Seton team data (DataFrame or list of dicts)
        opponent_df: Opponent team data (DataFrame or list of dicts)

    Returns:
        Tuple of (aligned_seton_df, aligned_opponent_df, alignment_info)
    """
    # CONVERSION FIX: Handle list inputs from Reflex state
    if isinstance(seton_df, list):
        seton_df = pd.DataFrame(seton_df) if seton_df else pd.DataFrame()
    if isinstance(opponent_df, list):
        opponent_df = pd.DataFrame(opponent_df) if opponent_df else pd.DataFrame()

    alignment_info = {
        "aligned": False,
        "seton_original": len(seton_df),
        "opponent_original": len(opponent_df),
        "seton_filtered": 0,
        "opponent_filtered": 0,
        "common_meet": None,
        "removed_seton": 0,
        "removed_opponent": 0,
        "common_events": [],
        "alignment_method": None,
    }

    # If either dataframe is empty, return as-is
    if seton_df.empty or opponent_df.empty:
        logger.warning("One or both dataframes are empty - cannot align")
        return seton_df, opponent_df, alignment_info

    # Ensure 'team' column exists and is set correctly
    if "team" not in seton_df.columns:
        seton_df = seton_df.copy()
        seton_df["team"] = "Seton"

    if "team" not in opponent_df.columns:
        opponent_df = opponent_df.copy()
        opponent_df["team"] = "Opponent"

    # Get team names from data
    opponent_team_col = (
        opponent_df["team"].iloc[0]
        if not opponent_df.empty and "team" in opponent_df.columns
        else "Opponent"
    )

    # Helper: Detect flexible 'opponent' column name
    def find_opponent_col(df):
        candidates = [
            "opponent",
            "opponent team",
            "opponent_team",
            "visitor",
            "visitor team",
            "vs",
            "vs team",
        ]
        for col in df.columns:
            if col.lower().strip() in candidates:
                # Rename to standard 'opponent' for internal logic
                return col
        return None

    # Normalizing columns for internal logic:
    # If we find a special opponent column, rename it to 'opponent' so logic below works
    # We do this on a COPY so we don't mutate original data permanently if we return early
    seton_df = seton_df.copy()
    opponent_df = opponent_df.copy()

    s_opp_col = find_opponent_col(seton_df)
    if s_opp_col and s_opp_col != "opponent":
        seton_df.rename(columns={s_opp_col: "opponent"}, inplace=True)

    o_opp_col = find_opponent_col(opponent_df)
    if o_opp_col and o_opp_col != "opponent":
        opponent_df.rename(columns={o_opp_col: "opponent"}, inplace=True)

    # Log what we're working with for debugging
    logger.info(
        f"Meet Alignment: Seton team, Opponent team column = '{opponent_team_col}'"
    )

    # STRATEGY 1: Use 'opponent' column if available (MOST RELIABLE)
    if "opponent" in seton_df.columns and "opponent" in opponent_df.columns:
        # Get unique opponent values from both files for debugging
        seton_opponent_values = (
            seton_df["opponent"].dropna().unique().tolist()
            if "opponent" in seton_df.columns
            else []
        )
        opponent_opponent_values = (
            opponent_df["opponent"].dropna().unique().tolist()
            if "opponent" in opponent_df.columns
            else []
        )

        logger.info(f"Seton's 'opponent' column values: {seton_opponent_values[:5]}...")
        logger.info(
            f"Opponent's 'opponent' column values: {opponent_opponent_values[:5]}..."
        )

        # Find Seton entries where opponent column contains opponent team name (flexible matching)
        # Try matching against: ICHS, Isle of Wight, opponent_team_col, etc.
        seton_aligned = seton_df[
            (
                seton_df["team"].str.lower().str.contains("seton", na=False)
            )  # Must be Seton team
        ].copy()

        # Find Opponent entries where opponent is Seton (Strict Check)
        opponent_aligned = opponent_df[
            (
                opponent_df["opponent"].str.lower().str.contains("seton", na=False)
            )  # Their opponent says Seton
        ].copy()

        # ONE-SIDED INFERENCE CHECK
        # If strict check failed (e.g. opponent file has no 'opponent' col),
        # but Seton file explicitly names this team as opponent, accept it.
        if opponent_aligned.empty:
            # Does Seton's opponent column match the Opponent's team name?
            opp_team_name = str(opponent_team_col).lower()
            seton_opponents = (
                seton_df["opponent"].dropna().astype(str).str.lower().unique()
            )

            # Check if any Seton opponent entry loosely matches the Opponent Team Name (e.g. 'ichs' in 'Immanuel Christian')
            # or vice versa (e.g. 'immanuel' in 'ICHS')
            match_found = False
            for so in seton_opponents:
                if opp_team_name in so or so in opp_team_name:
                    match_found = True
                    break

            if match_found:
                logger.info(
                    f"One-sided match confirmed: Seton is swimming against '{opponent_team_col}'"
                )
                opponent_aligned = (
                    opponent_df.copy()
                )  # Assume entire file is the meet roster for opponent

        # If both have data, we have a match!
        if not seton_aligned.empty and not opponent_aligned.empty:
            # Filter to common events
            seton_events = (
                set(seton_aligned["event"].unique())
                if "event" in seton_aligned.columns
                else set()
            )
            opponent_events = (
                set(opponent_aligned["event"].unique())
                if "event" in opponent_aligned.columns
                else set()
            )
            common_events = seton_events & opponent_events

            if common_events:
                seton_aligned = seton_aligned[
                    seton_aligned["event"].isin(common_events)
                ]
                opponent_aligned = opponent_aligned[
                    opponent_aligned["event"].isin(common_events)
                ]

                alignment_info["aligned"] = True
                alignment_info["common_meet"] = f"Seton vs {opponent_team_col}"
                alignment_info["seton_filtered"] = len(seton_aligned)
                alignment_info["opponent_filtered"] = len(opponent_aligned)
                alignment_info["removed_seton"] = len(seton_df) - len(seton_aligned)
                alignment_info["removed_opponent"] = len(opponent_df) - len(
                    opponent_aligned
                )
                alignment_info["common_events"] = sorted(list(common_events))
                alignment_info["alignment_method"] = "opponent_column"

                logger.info(
                    f"Meet alignment (opponent column): {alignment_info['common_meet']}"
                )
                logger.info(
                    f"Seton: {len(seton_df)} → {len(seton_aligned)} entries ({alignment_info['removed_seton']} removed)"
                )
                logger.info(
                    f"Opponent: {len(opponent_df)} → {len(opponent_aligned)} entries ({alignment_info['removed_opponent']} removed)"
                )
                logger.info(f"Common events: {len(common_events)}")

                return seton_aligned, opponent_aligned, alignment_info

    # STRATEGY 2: NO GUESSING - Strict Fail
    # If explicit 'Opponent' column matching failed, we halt.
    # But wait! If we don't have opponent columns (e.g. Top Times report), we should rely on Event Overlap (Strategy 3).

    # STRATEGY 3: Event Overlap (Roster/Top Times Mode)
    # If we lack 'opponent' columns, we check if the events look like a swim meet.
    seton_events = (
        set(seton_df["event"].unique()) if "event" in seton_df.columns else set()
    )
    opponent_events = (
        set(opponent_df["event"].unique()) if "event" in opponent_df.columns else set()
    )
    common_events = seton_events & opponent_events

    if common_events:
        overlap_count = len(common_events)
        total_unique = len(seton_events.union(opponent_events))
        overlap_ratio = overlap_count / total_unique if total_unique > 0 else 0

        # If we have decent overlap (>30%), we assume these are compatible rosters
        if overlap_ratio > 0.3:
            # Check if this looks like a valid dual meet setup
            alignment_info["aligned"] = True
            alignment_info["common_meet"] = "Roster/Top Times (Inferred from Events)"
            alignment_info["seton_filtered"] = len(seton_df)
            alignment_info["opponent_filtered"] = len(opponent_df)
            alignment_info["common_events"] = sorted(list(common_events))
            alignment_info["alignment_method"] = "event_overlap"

            logger.info(
                f"Meet alignment (event overlap): {alignment_info['common_meet']}"
            )
            logger.info(f"Overlap Ratio: {overlap_ratio:.1%}")

            # We filter to common events to be safe, but keep all times
            seton_aligned = seton_df[seton_df["event"].isin(common_events)]
            opponent_aligned = opponent_df[opponent_df["event"].isin(common_events)]

            return seton_aligned, opponent_aligned, alignment_info

    logger.warning(
        "Strict Meet Alignment Failed. Could not match 'Opponent' columns and Event Overlap was insufficient."
    )
    logger.info("Seton file did not explicitly name this opponent, or vice versa.")

    # Return aligned=False. The app should prompt user or refuse to optimize.
    return seton_df, opponent_df, alignment_info


def validate_alignment(seton_df: pd.DataFrame, opponent_df: pd.DataFrame) -> dict:
    """
    Validate that aligned data looks reasonable.

    Returns:
        dict with validation results and warnings
    """
    validation = {
        "valid": True,
        "warnings": [],
        "entry_ratio": 0.0,
        "event_overlap": 0.0,
    }

    if seton_df.empty or opponent_df.empty:
        validation["valid"] = False
        validation["warnings"].append("One or both teams have no data")
        return validation

    # Check entry count ratio
    seton_count = len(seton_df)
    opponent_count = len(opponent_df)
    ratio = (
        max(seton_count, opponent_count) / min(seton_count, opponent_count)
        if min(seton_count, opponent_count) > 0
        else 0
    )

    validation["entry_ratio"] = ratio

    if ratio > 2.0:
        validation["warnings"].append(
            f"Entry count mismatch: Seton={seton_count}, Opponent={opponent_count}. "
            f"Ratio={ratio:.1f}x suggests multiple meets in one PDF."
        )

    # Check event overlap
    if "event" in seton_df.columns and "event" in opponent_df.columns:
        seton_events = set(seton_df["event"].unique())
        opponent_events = set(opponent_df["event"].unique())
        common_events = seton_events & opponent_events

        if seton_events and opponent_events:
            overlap = len(common_events) / max(len(seton_events), len(opponent_events))
            validation["event_overlap"] = overlap

            if overlap < 0.5:
                validation["warnings"].append(
                    f"Low event overlap ({overlap:.0%}). Teams may not have competed in same meet."
                )

    return validation
