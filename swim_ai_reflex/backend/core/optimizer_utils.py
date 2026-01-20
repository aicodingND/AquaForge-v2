import pandas as pd
from typing import Tuple, List, Dict, Optional


def count_swimmer_events(
    lineup_df: pd.DataFrame, include_relays: bool = True
) -> Dict[str, int]:
    """
    Count how many events each swimmer is in.

    Args:
        lineup_df: DataFrame with swimmer assignments
        include_relays: Whether to count relay events

    Returns:
        Dictionary mapping swimmer name to event count
    """
    if lineup_df.empty:
        return {}

    # Ensure is_relay column exists (infer from event name if missing)
    if "is_relay" not in lineup_df.columns:
        lineup_df = lineup_df.copy()
        if "event" in lineup_df.columns:
            lineup_df["is_relay"] = (
                lineup_df["event"].str.lower().str.contains("relay", na=False)
            )
        else:
            lineup_df["is_relay"] = False

    if include_relays:
        counts = lineup_df["swimmer"].value_counts().to_dict()
    else:
        # Only count individual events (not relays)
        individual = lineup_df[~lineup_df["is_relay"]]
        counts = individual["swimmer"].value_counts().to_dict()
    return counts


def validate_lineup_constraints(
    lineup_df: pd.DataFrame, rules, min_grade: Optional[int] = None
) -> Tuple[bool, List[str]]:
    """
    Validate that a lineup meets all VISAA constraints.

    IMPORTANT: This validates MAXIMUM constraints only.
    - Swimmers are NOT required to swim any minimum number of events
    - A swimmer may strategically swim 0, 1, or 2 individual events
    - The optimizer determines optimal assignment per swimmer

    Args:
        lineup_df: DataFrame containing the lineup to validate
        rules: MeetRules object with constraint definitions
        min_grade: Minimum grade for scoring eligibility

    Returns:
        Tuple of (is_valid, list_of_violations)
    """
    violations = []

    if min_grade is None:
        min_grade = getattr(rules, "min_scoring_grade", 8)

    if lineup_df.empty:
        return True, []

    # Ensure is_relay column exists (infer from event name if missing)
    if "is_relay" not in lineup_df.columns:
        lineup_df = lineup_df.copy()
        if "event" in lineup_df.columns:
            lineup_df["is_relay"] = (
                lineup_df["event"].str.lower().str.contains("relay", na=False)
            )
        else:
            lineup_df["is_relay"] = False

    # 1. Check max total events per swimmer
    event_counts = count_swimmer_events(lineup_df, include_relays=True)
    for swimmer, count in event_counts.items():
        if count > rules.max_total_events_per_swimmer:
            violations.append(
                f"{swimmer} in {count} events (max {rules.max_total_events_per_swimmer})"
            )

    # 2. Check max individual events per swimmer
    individual_counts = count_swimmer_events(lineup_df, include_relays=False)
    for swimmer, count in individual_counts.items():
        if count > rules.max_individual_events_per_swimmer:
            violations.append(
                f"{swimmer} in {count} individual events (max {rules.max_individual_events_per_swimmer})"
            )

    # 3. Grade eligibility is NOT checked here - 7th graders can compete (blocking strategy)
    #    They just won't score points (handled in scoring engine)

    # 4. Check max entries per team per event
    if "event" in lineup_df.columns:
        for event in lineup_df["event"].unique():
            event_entries = lineup_df[lineup_df["event"] == event]
            relay_entries = event_entries[event_entries["is_relay"]]
            individual_entries = event_entries[~event_entries["is_relay"]]

            if len(relay_entries) > rules.max_relays_per_team_per_event:
                violations.append(
                    f"Event '{event}' has {len(relay_entries)} relays (max {rules.max_relays_per_team_per_event})"
                )

            if len(individual_entries) > rules.max_entries_per_team_per_event:
                violations.append(
                    f"Event '{event}' has {len(individual_entries)} entries (max {rules.max_entries_per_team_per_event})"
                )

    # 5. Check for duplicate (swimmer, event) pairs
    if "swimmer" in lineup_df.columns and "event" in lineup_df.columns:
        swimmer_event_pairs = lineup_df.groupby(["swimmer", "event"]).size()
        duplicates = swimmer_event_pairs[swimmer_event_pairs > 1]
        for (swimmer, event), count in duplicates.items():
            violations.append(f"{swimmer} appears {count} times in {event}")

    # 6. Check for back-to-back events (Hard Constraint)
    b2b_penalty = count_back_to_back_events(lineup_df)
    if b2b_penalty > 0:
        violations.append(
            f"Lineup contains {b2b_penalty} back-to-back event assignments"
        )

    return len(violations) == 0, violations


def count_back_to_back_events(
    lineup_df: pd.DataFrame, event_order: Optional[List[str]] = None
) -> int:
    """
    Count the number of back-to-back event assignments for swimmers.
    Uses fuzzy matching to handle event name variations.

    Args:
        lineup_df: DataFrame with 'swimmer' and 'event' columns
        event_order: List of event names in meet order (optional)

    Returns:
        Penalty score (0 = no back-to-back, higher = more back-to-back)
    """
    if (
        lineup_df.empty
        or "swimmer" not in lineup_df.columns
        or "event" not in lineup_df.columns
    ):
        return 0

    if event_order is None:
        # Use default VISAA event order
        event_order = [
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

    def normalize_event_name(event_name: str) -> int:
        """Convert event name to standard order index using fuzzy matching."""
        if not event_name:
            return 999

        name_lower = event_name.lower()

        # Check for each event type
        if "medley" in name_lower and "relay" in name_lower:
            return 0  # 200 Medley Relay
        elif "200" in name_lower and "free" in name_lower and "relay" not in name_lower:
            return 1  # 200 Free
        elif "im" in name_lower or ("200" in name_lower and "individual" in name_lower):
            return 2  # 200 IM
        elif "50" in name_lower and "free" in name_lower:
            return 3  # 50 Free
        elif "diving" in name_lower or "dive" in name_lower:
            return 4  # Diving
        elif "fly" in name_lower or "butterfly" in name_lower:
            return 5  # 100 Fly
        elif "100" in name_lower and "free" in name_lower and "relay" not in name_lower:
            return 6  # 100 Free
        elif "500" in name_lower and "free" in name_lower:
            return 7  # 500 Free
        elif "200" in name_lower and "free" in name_lower and "relay" in name_lower:
            return 8  # 200 Free Relay
        elif "back" in name_lower:
            return 9  # 100 Back
        elif "breast" in name_lower:
            return 10  # 100 Breast
        elif "400" in name_lower and "relay" in name_lower:
            return 11  # 400 Free Relay
        else:
            # Fallback checks for weird formatting
            if (
                "free" in name_lower and "200" in name_lower
            ):  # Catch-all for 200 free variations
                if "relay" in name_lower:
                    return 8
                return 1
            if "free" in name_lower and "100" in name_lower:  # Catch-all for 100 free
                if "relay" in name_lower:
                    return 11  # Assume 400 relay if not specified? No, unsafe.
                return 6

            # Log warning for unidentified event if possible (need to import logger first)
            # print(f"WARNING: Unrecognized event for back-to-back check: {event_name}")
            return 999  # Unknown event

    # Group by swimmer and check for back-to-back
    penalty = 0

    # Only check Seton swimmers (we control their lineup)
    seton_mask = (
        lineup_df["team"].str.lower().str.contains("seton", na=False)
        if "team" in lineup_df.columns
        else pd.Series([True] * len(lineup_df))
    )
    seton_df = lineup_df[seton_mask]

    for swimmer in seton_df["swimmer"].unique():
        swimmer_events = seton_df[seton_df["swimmer"] == swimmer]["event"].tolist()

        if len(swimmer_events) < 2:
            continue

        # Get indices and sort
        indices = sorted([normalize_event_name(e) for e in swimmer_events])

        # SAFETY CHECK: If any event is unrecognized (999) and swimmer has multiple events,
        # we must assume potential back-to-back to be safe.
        if 999 in indices:
            penalty += 1  # Strict penalty for unknown event ordering
            continue

        # Count consecutive events (index difference of 1)
        for i in range(len(indices) - 1):
            if indices[i + 1] - indices[i] == 1:
                # Back-to-back events detected!
                penalty += 1

    return penalty


def standardize_dataframe_events(df: pd.DataFrame) -> pd.DataFrame:
    """
    Standardize event names in a DataFrame to the official VISAA format.
    Run this on roster load to ensure all logic handles events correctly.
    """
    if df.empty or "event" not in df.columns:
        return df

    rules = [
        (
            "200 Medley Relay",
            [
                "200 medley relay",
                "boys 200 medley",
                "girls 200 medley",
                "mens 200 medley",
                "womens 200 medley",
            ],
        ),
        (
            "200 Yard Freestyle",
            [
                "200 free",
                "200 freestyle",
                "boys 200 free",
                "girls 200 free",
                "mens 200 free",
                "womens 200 free",
            ],
        ),
        (
            "200 Yard IM",
            [
                "200 im",
                "200 individual medley",
                "boys 200 im",
                "girls 200 im",
                "mens 200 im",
                "womens 200 im",
            ],
        ),
        (
            "50 Yard Freestyle",
            [
                "50 free",
                "50 freestyle",
                "boys 50 free",
                "girls 50 free",
                "mens 50 free",
                "womens 50 free",
            ],
        ),
        (
            "Diving",
            [
                "diving",
                "dive",
                "1 meter diving",
                "boys diving",
                "girls diving",
                "mens diving",
                "womens diving",
            ],
        ),
        (
            "100 Yard Butterfly",
            [
                "100 fly",
                "100 butterfly",
                "boys 100 fly",
                "girls 100 fly",
                "mens 100 fly",
                "womens 100 fly",
            ],
        ),
        (
            "100 Yard Freestyle",
            [
                "100 free",
                "100 freestyle",
                "boys 100 free",
                "girls 100 free",
                "mens 100 free",
                "womens 100 free",
            ],
        ),
        (
            "500 Yard Freestyle",
            [
                "500 free",
                "500 freestyle",
                "400 free",
                "400 freestyle",
                "boys 500 free",
                "girls 500 free",
            ],
        ),
        (
            "200 Free Relay",
            [
                "200 free relay",
                "200 freestyle relay",
                "boys 200 free relay",
                "girls 200 free relay",
            ],
        ),
        (
            "100 Yard Backstroke",
            [
                "100 back",
                "100 backstroke",
                "boys 100 back",
                "girls 100 back",
                "mens 100 back",
                "womens 100 back",
            ],
        ),
        (
            "100 Yard Breaststroke",
            [
                "100 breast",
                "100 breaststroke",
                "boys 100 breast",
                "girls 100 breast",
                "mens 100 breast",
                "womens 100 breast",
            ],
        ),
        (
            "400 Free Relay",
            [
                "400 free relay",
                "400 freestyle relay",
                "boys 400 free relay",
                "girls 400 free relay",
            ],
        ),
    ]

    def get_standard_name(raw_name):
        if not isinstance(raw_name, str):
            return raw_name
        norm = raw_name.lower().strip()

        # Exact/Partial match check
        for std_name, variations in rules:
            # Check basic variations
            for v in variations:
                if v in norm:
                    # Specific relay check to prevent "200 Free" matching "200 Free Relay" incorrectly
                    if "relay" in std_name.lower() and "relay" not in norm:
                        continue
                    if "relay" in norm and "relay" not in std_name.lower():
                        continue
                    return std_name

        return raw_name  # Return original if no match found

    df = df.copy()

    # Safety: Backfill gender from event name if missing
    if "gender" not in df.columns:
        df["gender"] = None

    def backfill_gender(row):
        ev = str(row.get("event", "")).lower()
        g = row.get("gender")
        # Only backfill if gender is missing
        if not g or pd.isna(g) or str(g).lower() == "none" or str(g).strip() == "":
            if "boys" in ev or "men" in ev:
                return "M"
            if "girls" in ev or "women" in ev:
                return "F"
        return g

    df["gender"] = df.apply(backfill_gender, axis=1)

    df["event"] = df["event"].apply(get_standard_name)
    return df


def check_event_names(df: pd.DataFrame) -> List[str]:
    """
    Check for non-standard event names in the DataFrame.
    Returns a list of issues/warnings describing what will be changed.
    """
    if df.empty or "event" not in df.columns:
        return []

    issues = []

    # Expanded rules for checking (includes Men/Women)
    rules = [
        (
            "200 Medley Relay",
            [
                "200 medley relay",
                "boys 200 medley",
                "girls 200 medley",
                "mens 200 medley",
                "womens 200 medley",
            ],
        ),
        (
            "200 Yard Freestyle",
            [
                "200 free",
                "200 freestyle",
                "boys 200 free",
                "girls 200 free",
                "mens 200 free",
                "womens 200 free",
            ],
        ),
        (
            "200 Yard IM",
            [
                "200 im",
                "200 individual medley",
                "boys 200 im",
                "girls 200 im",
                "mens 200 im",
                "womens 200 im",
            ],
        ),
        (
            "50 Yard Freestyle",
            [
                "50 free",
                "50 freestyle",
                "boys 50 free",
                "girls 50 free",
                "mens 50 free",
                "womens 50 free",
            ],
        ),
        (
            "Diving",
            [
                "diving",
                "dive",
                "1 meter diving",
                "boys diving",
                "girls diving",
                "mens diving",
                "womens diving",
            ],
        ),
        (
            "100 Yard Butterfly",
            [
                "100 fly",
                "100 butterfly",
                "boys 100 fly",
                "girls 100 fly",
                "mens 100 fly",
                "womens 100 fly",
            ],
        ),
        (
            "100 Yard Freestyle",
            [
                "100 free",
                "100 freestyle",
                "boys 100 free",
                "girls 100 free",
                "mens 100 free",
                "womens 100 free",
            ],
        ),
        (
            "500 Yard Freestyle",
            [
                "500 free",
                "500 freestyle",
                "400 free",
                "400 freestyle",
                "boys 500 free",
                "girls 500 free",
            ],
        ),
        (
            "200 Free Relay",
            [
                "200 free relay",
                "200 freestyle relay",
                "boys 200 free relay",
                "girls 200 free relay",
            ],
        ),
        (
            "100 Yard Backstroke",
            [
                "100 back",
                "100 backstroke",
                "boys 100 back",
                "girls 100 back",
                "mens 100 back",
                "womens 100 back",
            ],
        ),
        (
            "100 Yard Breaststroke",
            [
                "100 breast",
                "100 breaststroke",
                "boys 100 breast",
                "girls 100 breast",
                "mens 100 breast",
                "womens 100 breast",
            ],
        ),
        (
            "400 Free Relay",
            [
                "400 free relay",
                "400 freestyle relay",
                "boys 400 free relay",
                "girls 400 free relay",
            ],
        ),
    ]

    # Check unique events
    unique_events = df["event"].dropna().unique()

    for event in unique_events:
        if not isinstance(event, str):
            continue
        norm = event.lower().strip()
        matched = False

        for std_name, variations in rules:
            if event == std_name:  # Already standard
                matched = True
                break

            for v in variations:
                if v in norm:
                    # Relay safety check
                    if "relay" in std_name.lower() and "relay" not in norm:
                        continue
                    if "relay" in norm and "relay" not in std_name.lower():
                        continue

                    issues.append(f"Event '{event}' will be renamed to '{std_name}'")
                    matched = True
                    break
            if matched:
                break

        if not matched:
            issues.append(f"Unknown Event format: '{event}' (May need manual fix)")

    return sorted(issues)


def evaluate_seton_vs_opponent(
    seton_df: pd.DataFrame, opponent_df: pd.DataFrame, scoring_fn, alpha: float = 1.0
) -> Tuple[float, Dict[str, float], pd.DataFrame]:
    """
    Evaluate lineup objective: Seton_points - alpha * Opponent_points.

    Args:
        seton_df: Seton team lineup DataFrame
        opponent_df: Opponent team lineup DataFrame
        scoring_fn: Scoring function to apply
        alpha: Weight for opponent score in objective

    Returns:
        Tuple of (net_score, totals_dict, scored_dataframe)
    """
    if seton_df.empty:
        # Handle empty case
        return -9999.0, {"seton": 0.0, "opponent": 0.0}, pd.DataFrame()

    combined = pd.concat([seton_df, opponent_df], ignore_index=True)
    scored, totals = scoring_fn(combined)
    net = totals["seton"] - alpha * totals["opponent"]
    return net, totals, scored
