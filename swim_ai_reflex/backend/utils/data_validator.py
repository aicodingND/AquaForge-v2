# utils/data_validator.py

import pandas as pd


def validate_roster_data(
    df: pd.DataFrame, meet_type: str = "dual"
) -> dict[str, list[str]]:
    """
    Validate uploaded roster data and return warnings/errors.

    Returns:
        Dict with 'warnings' and 'errors' lists
    """
    warnings = []
    errors = []

    # Standard dual meet events
    STANDARD_DUAL_EVENTS = {
        "50 Free",
        "100 Free",
        "200 Free",
        "500 Free",
        "100 Back",
        "100 Breast",
        "100 Fly",
        "200 IM",
    }

    # Championship event patterns
    CHAMPIONSHIP_PATTERNS = [
        "13-14",
        "15-16",
        "17-18",
        "Senior",
        "Junior",
        "11-12",
        "8 & Under",
        "9-10",
        "Age Group",
    ]

    if df is None or df.empty:
        errors.append("No data found in uploaded file")
        return {"warnings": warnings, "errors": errors}

    # Check 0: Missing Gender column
    if "gender" not in df.columns:
        warnings.append(
            "⚠️ 'Gender' column not found. Please ensure your file has a column named 'Gender' or 'Sex' to correctly separate Boys/Girls events."
        )

    # Check 1: Non-standard event names (championship format)
    if "event" in df.columns:
        events = df["event"].dropna().unique()
        non_standard_events = [e for e in events if e not in STANDARD_DUAL_EVENTS]

        # Check for championship event patterns
        championship_events = []
        for event in non_standard_events:
            if any(pattern in str(event) for pattern in CHAMPIONSHIP_PATTERNS):
                championship_events.append(event)

        if championship_events:
            warnings.append(
                f"⚠️ Data appears to be from a CHAMPIONSHIP or INVITATIONAL meet (found age group events: {', '.join(championship_events[:3])}). "
                f"This optimizer is designed for DUAL MEETS with standard events only."
            )

        # Warn about non-standard but not championship events
        other_non_standard = [
            e for e in non_standard_events if e not in championship_events
        ]
        if other_non_standard:
            warnings.append(
                f"Found non-standard event names: {', '.join(other_non_standard[:5])}. "
                f"Expected: 50/100/200/500 Free, 100 Back/Breast/Fly, 200 IM"
            )

    # Check 2: Mixed genders
    if "gender" in df.columns:
        genders = df["gender"].dropna().unique()
        if len(genders) > 1:
            warnings.append(
                f"⚠️ Mixed genders detected ({', '.join([str(g) for g in genders])}). "
                f"Dual meets typically separate boys and girls. Consider uploading separate rosters."
            )

    # Check 3: Missing swimmer names (after filtering should be caught)
    if "swimmer" in df.columns:
        empty_names = df[
            df["swimmer"].isna() | (df["swimmer"].str.strip() == "")
        ].shape[0]
        if empty_names > 0:
            warnings.append(
                f"Found {empty_names} entries with missing swimmer names (these will be filtered out)"
            )

    # Check 4: Missing grades
    if "grade" in df.columns:
        missing_grades = df["grade"].isna().sum()
        if missing_grades > 5:
            warnings.append(
                f"⚠️ {missing_grades} swimmers missing grade information. "
                f"Grades are needed to determine scoring eligibility (8th grade and up)."
            )

    # Check 5: Insufficient swimmers for competitive meet
    if "swimmer" in df.columns:
        num_swimmers = df["swimmer"].nunique()
        if num_swimmers < 8:
            warnings.append(
                f"⚠️ Only {num_swimmers} unique swimmers found. "
                f"A competitive dual meet typically requires 15-30 swimmers to fill all events."
            )

    # Check 6: Relay events (if present, warn they're not fully supported)
    if "is_relay" in df.columns:
        relay_count = df["is_relay"].sum()
        if relay_count > 0:
            warnings.append(
                f"Found {relay_count} relay entries. Note: Relay optimization is limited in current version."
            )

    # Check 7: Very large dataset (might be multi-meet data)
    if len(df) > 500:
        warnings.append(
            f"⚠️ Dataset contains {len(df)} entries (very large). "
            f"This may be data from multiple meets or a championship. Dual meet rosters are typically 100-200 entries."
        )

    return {"warnings": warnings, "errors": errors}
