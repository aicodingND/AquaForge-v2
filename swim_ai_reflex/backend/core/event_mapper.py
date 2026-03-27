# core/event_mapper.py
"""
Maps non-standard event names from PDFs to standard dual meet format.

STANDARD DUAL MEET INDIVIDUAL EVENTS (per gender):
1. 200 Free
2. 200 IM
3. 50 Free
4. 100 Fly
5. 100 Free
6. 500 Free
7. 100 Back
8. 100 Breast

Total: 8 events × 29 points = 232 maximum points
"""

import logging

import pandas as pd

logger = logging.getLogger(__name__)

# Standard event names (without gender prefix)
STANDARD_EVENTS = [
    "200 Free",
    "200 IM",
    "50 Free",
    "100 Fly",
    "100 Free",
    "500 Free",
    "100 Back",
    "100 Breast",
]


def normalize_event_name(event: str) -> str | None:
    """
    Normalize event name to standard dual meet format.

    Examples:
        "Senior 100 Free" -> "100 Free"
        "13-14 50 Free" -> "50 Free"
        "Girls 200 IM" -> "200 IM"

    Returns:
        Normalized event name, or None if not a standard event
    """
    if not isinstance(event, str):
        return None
    # Remove age group prefixes
    event = event.replace("Senior ", "")
    event = event.replace("13-14 ", "")
    event = event.replace("15-16 ", "")
    event = event.replace("11-12 ", "")

    # Remove gender prefixes
    event = event.replace("Girls ", "")
    event = event.replace("Boys ", "")

    # Remove extra spaces
    event = " ".join(event.split())

    # Check if it's a standard event
    if event in STANDARD_EVENTS:
        return event

    # Try to map non-standard distances to standard
    # 400 Free -> 500 Free (closest standard distance)
    if "400 Free" in event:
        return "500 Free"

    # 25 yard events -> not standard, return None
    if event.startswith("25 "):
        return None

    # If we can't map it, return None
    return None


def filter_to_standard_events(
    df: pd.DataFrame, gender: str | None = None
) -> pd.DataFrame:
    """
    Filter DataFrame to only include standard dual meet events.

    Args:
        df: DataFrame with 'event' column
        gender: Optional gender filter ('F' or 'M')

    Returns:
        Filtered DataFrame with only standard events
    """
    if df.empty:
        return df

    # Apply gender filter if specified
    if gender and "gender" in df.columns:
        df = df[df["gender"] == gender].copy()

    # Normalize event names
    df["event_normalized"] = df["event"].apply(normalize_event_name)

    # Filter out non-standard events (where normalize returned None)
    df_filtered = df[df["event_normalized"].notna()].copy()

    # Replace event column with normalized names
    df_filtered["event"] = df_filtered["event_normalized"]
    df_filtered = df_filtered.drop(columns=["event_normalized"])

    # Keep only one entry per swimmer per event (in case of duplicates)
    if "swimmer" in df_filtered.columns:
        df_filtered = df_filtered.drop_duplicates(
            subset=["swimmer", "event"], keep="first"
        )

    return df_filtered


def add_gender_prefix(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add gender prefix to event names (e.g., "100 Free" -> "Girls 100 Free").

    Args:
        df: DataFrame with 'event' and 'gender' columns

    Returns:
        DataFrame with gender-prefixed event names
    """
    if df.empty or "gender" not in df.columns:
        return df

    df = df.copy()

    def prefix_event(row):
        gender_prefix = (
            "Girls" if row["gender"] == "F" else "Boys" if row["gender"] == "M" else ""
        )
        if gender_prefix and not row["event"].startswith(gender_prefix):
            return f"{gender_prefix} {row['event']}"
        return row["event"]

    df["event"] = df.apply(prefix_event, axis=1)

    return df


def get_event_summary(df: pd.DataFrame) -> dict:
    """
    Get summary of events in the DataFrame.

    Returns:
        Dictionary with event statistics
    """
    if df.empty:
        return {"total_events": 0, "events": []}

    events = df["event"].unique().tolist()

    summary = {
        "total_events": len(events),
        "events": sorted(events),
        "is_standard": len(events) == len(STANDARD_EVENTS),
        "standard_events": STANDARD_EVENTS,
        "missing_events": [
            e
            for e in STANDARD_EVENTS
            if e not in [ev.replace("Girls ", "").replace("Boys ", "") for ev in events]
        ],
        "extra_events": [
            e
            for e in events
            if e.replace("Girls ", "").replace("Boys ", "") not in STANDARD_EVENTS
        ],
    }

    return summary


def print_event_summary(df: pd.DataFrame, title: str = "Event Summary"):
    """
    Print a formatted event summary.
    """
    summary = get_event_summary(df)

    logger.info(f"\n{'=' * 60}")
    logger.info(f"{title}")
    logger.info(f"{'=' * 60}")
    logger.info(
        f"Total Events: {summary['total_events']} (standard: {len(STANDARD_EVENTS)})"
    )
    logger.info(f"Standard Format: {' ✓ YES' if summary['is_standard'] else ' NO'}")

    if summary["events"]:
        logger.info("\nEvents Included:")
        for event in summary["events"]:
            count = len(df[df["event"] == event])
            logger.info(f"• {event}: {count} entries")

    if summary["missing_events"]:
        logger.warning("\nMissing Standard Events:")
        for event in summary["missing_events"]:
            logger.warning(f"• {event}")

    if summary["extra_events"]:
        logger.warning("\nNon-Standard Events:")
        for event in summary["extra_events"]:
            logger.warning(f"• {event}")

    logger.info(f"{'=' * 60}\n")
