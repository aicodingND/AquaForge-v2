"""
Normalization Service

Provides consistent normalization for:
- Event names
- Swimmer names
- Times (string to float conversion)
- Team names

This is the single source of truth for data normalization.
"""

import logging
import re
from typing import Optional, Union

logger = logging.getLogger(__name__)


# =============================================================================
# EVENT NAME NORMALIZATION
# =============================================================================

# Canonical event names in meet order
CANONICAL_EVENTS = [
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

# Comprehensive event aliases
EVENT_NORMALIZATION_MAP = {
    # 200 Free
    "200 freestyle": "200 Free",
    "200 fr": "200 Free",
    "200 free": "200 Free",
    "200 yard freestyle": "200 Free",
    "200 yd free": "200 Free",
    "boys 200 free": "200 Free",
    "girls 200 free": "200 Free",
    # 200 IM
    "200 im": "200 IM",
    "200 individual medley": "200 IM",
    "200 medley": "200 IM",
    "200 i.m.": "200 IM",
    "boys 200 im": "200 IM",
    "girls 200 im": "200 IM",
    # 50 Free
    "50 freestyle": "50 Free",
    "50 fr": "50 Free",
    "50 free": "50 Free",
    "50 yard freestyle": "50 Free",
    "boys 50 free": "50 Free",
    "girls 50 free": "50 Free",
    # Diving
    "diving": "Diving",
    "1m diving": "1 Meter Diving",
    "1 meter diving": "1 Meter Diving",
    "1-meter diving": "1 Meter Diving",
    "1m": "1 Meter Diving",
    "boys diving": "Diving",
    "girls diving": "Diving",
    "boys 1m diving": "1 Meter Diving",
    "girls 1m diving": "1 Meter Diving",
    # 100 Fly
    "100 fly": "100 Fly",
    "100 butterfly": "100 Fly",
    "100 fl": "100 Fly",
    "boys 100 fly": "100 Fly",
    "girls 100 fly": "100 Fly",
    # 100 Free
    "100 freestyle": "100 Free",
    "100 fr": "100 Free",
    "100 free": "100 Free",
    "100 yard freestyle": "100 Free",
    "boys 100 free": "100 Free",
    "girls 100 free": "100 Free",
    # 500 Free
    "500 freestyle": "500 Free",
    "500 fr": "500 Free",
    "500 free": "500 Free",
    "500 yard freestyle": "500 Free",
    "boys 500 free": "500 Free",
    "girls 500 free": "500 Free",
    # 100 Back
    "100 backstroke": "100 Back",
    "100 bk": "100 Back",
    "100 back": "100 Back",
    "boys 100 back": "100 Back",
    "girls 100 back": "100 Back",
    # 100 Breast
    "100 breaststroke": "100 Breast",
    "100 br": "100 Breast",
    "100 breast": "100 Breast",
    "boys 100 breast": "100 Breast",
    "girls 100 breast": "100 Breast",
    # Relays
    "200 medley relay": "200 Medley Relay",
    "200 med relay": "200 Medley Relay",
    "200 mr": "200 Medley Relay",
    "boys 200 medley relay": "200 Medley Relay",
    "girls 200 medley relay": "200 Medley Relay",
    "200 free relay": "200 Free Relay",
    "200 freestyle relay": "200 Free Relay",
    "200 fr relay": "200 Free Relay",
    "boys 200 free relay": "200 Free Relay",
    "girls 200 free relay": "200 Free Relay",
    "400 free relay": "400 Free Relay",
    "400 freestyle relay": "400 Free Relay",
    "400 fr relay": "400 Free Relay",
    "4x100 free relay": "400 Free Relay",
    "4x100 freestyle relay": "400 Free Relay",
    "4 x 100 free relay": "400 Free Relay",
    "boys 400 free relay": "400 Free Relay",
    "girls 400 free relay": "400 Free Relay",
}


def normalize_event_name(event: str) -> str:
    """
    Normalize an event name to its canonical form.
    NOTE: This STRIPS gender prefix. For championship meets where boys/girls
    are scored separately, use normalize_event_name_with_gender() instead.

    Args:
        event: Raw event name (may have various formats)

    Returns:
        Canonical event name (e.g., "100 Free", "200 Medley Relay")

    Examples:
        >>> normalize_event_name("100 Freestyle")
        '100 Free'
        >>> normalize_event_name("boys 200 IM")
        '200 IM'
        >>> normalize_event_name("100 butterfly")
        '100 Fly'
    """
    if not event:
        return ""

    # Clean and lowercase
    cleaned = event.strip().lower()

    # Remove common prefixes
    cleaned = re.sub(r"^(boys?|girls?|mens?|womans?|m|f)\s+", "", cleaned)

    # Direct lookup
    if cleaned in EVENT_NORMALIZATION_MAP:
        return EVENT_NORMALIZATION_MAP[cleaned]

    # Check if already canonical (case-insensitive)
    for canonical in CANONICAL_EVENTS:
        if cleaned == canonical.lower():
            return canonical

    # Try partial matching for edge cases
    for key, value in EVENT_NORMALIZATION_MAP.items():
        if key in cleaned or cleaned in key:
            return value

    # Return title case as fallback
    logger.debug(f"Event not recognized, using as-is: {event}")
    return event.strip().title()


def normalize_event_name_with_gender(event: str) -> str:
    """
    Normalize an event name while PRESERVING the gender prefix.
    Use this for championship meets where Boys and Girls events are scored separately.

    Args:
        event: Raw event name (may have gender prefix)

    Returns:
        Normalized event with gender prefix (e.g., "Boys 100 Free", "Girls 200 IM")

    Examples:
        >>> normalize_event_name_with_gender("M 50 Free")
        'Boys 50 Free'
        >>> normalize_event_name_with_gender("F 100 butterfly")
        'Girls 100 Fly'
        >>> normalize_event_name_with_gender("girls 200 IM")
        'Girls 200 IM'
    """
    if not event:
        return ""

    cleaned = event.strip().lower()

    # Extract gender prefix
    gender = None
    gender_match = re.match(r"^(boys?|girls?|mens?|womans?|m|f)\s+", cleaned)
    if gender_match:
        prefix = gender_match.group(1)
        if prefix in ("boy", "boys", "m", "men", "mens"):
            gender = "Boys"
        elif prefix in ("girl", "girls", "f", "women", "womens"):
            gender = "Girls"
        cleaned = cleaned[gender_match.end() :]

    # Normalize the event part
    normalized_event = normalize_event_name(cleaned)

    # Recombine with gender prefix
    if gender:
        return f"{gender} {normalized_event}"
    return normalized_event


def get_event_order() -> list:
    """Get the canonical event order."""
    return CANONICAL_EVENTS.copy()


def is_relay_event(event: str) -> bool:
    """Check if an event is a relay."""
    return "relay" in event.lower()


def is_diving_event(event: str) -> bool:
    """Check if an event is diving."""
    normalized = normalize_event_name(event)
    return normalized == "Diving"


def is_individual_event(event: str) -> bool:
    """Check if an event is an individual swimming event."""
    return not is_relay_event(event) and not is_diving_event(event)


# =============================================================================
# TIME NORMALIZATION
# =============================================================================


def normalize_time(time_value: Union[str, float, int, None]) -> Optional[float]:
    """
    Normalize a time value to seconds (float).

    Handles:
    - Float/int: Return as-is
    - String "MM:SS.ss": Convert to seconds
    - String "SS.ss": Return as float
    - "NT", "NS", "DQ", None: Return infinity or None

    Args:
        time_value: Time in various formats

    Returns:
        Time in seconds as float, or None/inf for special cases

    Examples:
        >>> normalize_time("1:23.45")
        83.45
        >>> normalize_time(52.34)
        52.34
        >>> normalize_time("NT")
        inf
    """
    if time_value is None:
        return None

    # Already numeric
    if isinstance(time_value, (int, float)):
        return float(time_value)

    # Handle string
    if isinstance(time_value, str):
        time_str = time_value.strip().upper()

        # Special values
        if time_str in ("NT", "NS", "DQ", "SCR", ""):
            return float("inf")

        # MM:SS.ss format
        if ":" in time_str:
            try:
                parts = time_str.split(":")
                if len(parts) == 2:
                    minutes = float(parts[0])
                    seconds = float(parts[1])
                    return minutes * 60 + seconds
                elif len(parts) == 3:
                    # HH:MM:SS.ss (very long events)
                    hours = float(parts[0])
                    minutes = float(parts[1])
                    seconds = float(parts[2])
                    return hours * 3600 + minutes * 60 + seconds
            except ValueError:
                pass

        # SS.ss format
        try:
            return float(time_str)
        except ValueError:
            pass

    logger.warning(f"Could not parse time: {time_value}")
    return None


def format_time(seconds: Optional[float]) -> str:
    """
    Format seconds as time string.

    Args:
        seconds: Time in seconds

    Returns:
        Formatted time string (MM:SS.ss or SS.ss)

    Examples:
        >>> format_time(83.45)
        '1:23.45'
        >>> format_time(52.34)
        '52.34'
    """
    if seconds is None or seconds == float("inf"):
        return "NT"

    if seconds >= 60:
        minutes = int(seconds // 60)
        secs = seconds % 60
        return f"{minutes}:{secs:05.2f}"

    return f"{seconds:.2f}"


# =============================================================================
# SWIMMER NAME NORMALIZATION
# =============================================================================


def normalize_swimmer_name(name: str) -> str:
    """
    Normalize a swimmer's name.

    Handles:
    - Extra whitespace
    - Case normalization (Title Case)
    - "Last, First" to "First Last" conversion

    Args:
        name: Raw swimmer name

    Returns:
        Normalized name

    Examples:
        >>> normalize_swimmer_name("  SMITH, JOHN  ")
        'John Smith'
        >>> normalize_swimmer_name("jane doe")
        'Jane Doe'
    """
    if not name:
        return ""

    # Clean whitespace
    cleaned = " ".join(name.strip().split())

    # Handle "Last, First" format
    if "," in cleaned:
        parts = cleaned.split(",", 1)
        if len(parts) == 2:
            last = parts[0].strip()
            first = parts[1].strip()
            cleaned = f"{first} {last}"

    # Title case
    return cleaned.title()


# =============================================================================
# TEAM NAME NORMALIZATION
# =============================================================================

# Team name mappings
TEAM_ALIASES = {
    # Seton School
    "sst": "Seton",
    "seton school": "Seton",
    "seton": "Seton",
    "seton swimming": "Seton",
    # Trinity Christian
    "tcs": "Trinity",
    "trinity": "Trinity",
    "trinity christian": "Trinity",
    "trinity christian school": "Trinity",
    # Oakcrest
    "oak": "Oakcrest",
    "oakcrest": "Oakcrest",
    "oakcrest school": "Oakcrest",
    # Fredericksburg Christian
    "fcs": "Fredericksburg Christian",
    "fredericksburg": "Fredericksburg Christian",
    "fredericksburg christian": "Fredericksburg Christian",
    # Immanuel Christian
    "ics": "Immanuel Christian",
    "immanuel": "Immanuel Christian",
    "immanuel christian": "Immanuel Christian",
    # St. John Paul the Great
    "ppi": "JPII",
    "jp2": "JPII",
    "john paul": "JPII",
    "st. john paul": "JPII",
    "st john paul the great": "JPII",
}


def normalize_team_name(team: str) -> str:
    """
    Normalize a team name to its canonical form.

    Args:
        team: Raw team name

    Returns:
        Canonical team name

    Examples:
        >>> normalize_team_name("SST")
        'Seton'
        >>> normalize_team_name("TRINITY CHRISTIAN SCHOOL")
        'Trinity'
    """
    if not team:
        return ""

    cleaned = team.strip().lower()

    if cleaned in TEAM_ALIASES:
        return TEAM_ALIASES[cleaned]

    # Return title case as fallback
    return team.strip().title()


# =============================================================================
# GRADE NORMALIZATION
# =============================================================================


def normalize_grade(grade: Union[str, int, None]) -> Optional[int]:
    """
    Normalize grade to integer.

    Args:
        grade: Grade value (12, "12th", "Senior", etc.)

    Returns:
        Integer grade or None
    """
    if grade is None:
        return None

    if isinstance(grade, int):
        return grade

    if isinstance(grade, str):
        # Remove common suffixes
        cleaned = grade.strip().lower()
        cleaned = re.sub(r"(st|nd|rd|th)$", "", cleaned)

        # Grade name mapping
        grade_names = {
            "freshman": 9,
            "sophomore": 10,
            "junior": 11,
            "senior": 12,
            "7th": 7,
            "8th": 8,
        }

        if cleaned in grade_names:
            return grade_names[cleaned]

        try:
            return int(cleaned)
        except ValueError:
            pass

    return None


def is_scoring_eligible(grade: Union[str, int, None], min_grade: int = 9) -> bool:
    """
    Check if a swimmer is scoring eligible based on grade.

    Args:
        grade: Swimmer's grade
        min_grade: Minimum grade for scoring (default 9 for varsity)

    Returns:
        True if eligible to score
    """
    normalized = normalize_grade(grade)
    if normalized is None:
        return True  # Assume eligible if unknown

    return normalized >= min_grade
