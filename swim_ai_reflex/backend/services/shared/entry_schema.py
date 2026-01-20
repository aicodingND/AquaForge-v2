"""
Standard Entry Schema and Column Normalization

This module defines the canonical column names for swim entries and provides
functions to normalize data from various sources (CSV, JSON, different formats).

CANONICAL SCHEMA:
-----------------
| Field        | Type      | Required | Description                      |
|--------------|-----------|----------|----------------------------------|
| swimmer      | str       | Yes      | Swimmer name (First Last)        |
| team         | str       | Yes      | Team code (e.g., "SST")          |
| event        | str       | Yes      | Event name with gender prefix    |
| time         | float     | Yes      | Seed time in seconds             |
| gender       | str       | No       | "M" or "F"                       |
| grade        | int|None  | No       | Grade level (7-12)               |
| is_diver     | bool      | No       | True if diving event             |
| is_relay     | bool      | No       | True if relay event              |

COLUMN ALIASES:
---------------
Different data sources use different column names. This module maps them all
to the canonical schema above.
"""

import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from swim_ai_reflex.backend.services.shared.normalization import (
    normalize_event_name_with_gender,
    normalize_swimmer_name,
    normalize_time,
)

logger = logging.getLogger(__name__)


# =============================================================================
# COLUMN NAME MAPPINGS - All known aliases for each canonical field
# =============================================================================

COLUMN_ALIASES = {
    "swimmer": [
        "swimmer",
        "swimmer_name",
        "name",
        "athlete",
        "athlete_name",
        "swimmer name",
        "contestant",
    ],
    "team": [
        "team",
        "team_code",
        "team code",
        "school",
        "club",
        "organization",
    ],
    "team_name": [
        "team_name",
        "team name",
        "school_name",
        "school name",
        "full_team_name",
    ],
    "event": [
        "event",
        "event_name",
        "event name",
        "race",
        "distance",
    ],
    "time": [
        "time",
        "seed_time",
        "seed time",
        "entry_time",
        "entry time",
        "best_time",
        "best time",
        "result",
    ],
    "gender": [
        "gender",
        "sex",
        "m/f",
        "category",
    ],
    "grade": [
        "grade",
        "year",
        "class",
        "class_year",
    ],
    "is_diver": [
        "is_diver",
        "diver",
        "diving",
    ],
    "is_relay": [
        "is_relay",
        "relay",
    ],
    "is_varsity": [
        "is_varsity",
        "varsity",
        "level",
    ],
}


# =============================================================================
# TEAM CODE MAPPINGS - Standard three-letter codes
# =============================================================================

TEAM_CODE_MAP = {
    # VCAC Conference
    "seton": "SST",
    "seton school": "SST",
    "seton swimming": "SST",
    "sst": "SST",
    "trinity": "TCS",
    "trinity christian": "TCS",
    "trinity christian school": "TCS",
    "tcs": "TCS",
    "immanuel": "ICS",
    "immanuel christian": "ICS",
    "immanuel christian high school": "ICS",
    "ics": "ICS",
    "oakcrest": "OAK",
    "oakcrest school": "OAK",
    "oak": "OAK",
    "fredericksburg": "FCS",
    "fredericksburg christian": "FCS",
    "fcs": "FCS",
    "bishop o'connell": "DJO",
    "o'connell": "DJO",
    "djo": "DJO",
    "bishop ireton": "BI",
    "ireton": "BI",
    "bi": "BI",
    "paul vi": "PVI",
    "paul 6": "PVI",
    "pvi": "PVI",
    "st. john paul": "JPII",
    "john paul": "JPII",
    "jpii": "JPII",
    "jp2": "JPII",
}

# Reverse mapping: code -> display name
TEAM_DISPLAY_NAMES = {
    "SST": "Seton",
    "TCS": "Trinity",
    "ICS": "Immanuel Christian",
    "OAK": "Oakcrest",
    "FCS": "Fredericksburg Christian",
    "DJO": "Bishop O'Connell",
    "BI": "Bishop Ireton",
    "PVI": "Paul VI",
    "JPII": "St. John Paul",
}


# =============================================================================
# GENDER NORMALIZATION
# =============================================================================

GENDER_MAP = {
    "m": "M",
    "male": "M",
    "boy": "M",
    "boys": "M",
    "men": "M",
    "mens": "M",
    "f": "F",
    "female": "F",
    "girl": "F",
    "girls": "F",
    "women": "F",
    "womens": "F",
}


# =============================================================================
# STANDARD ENTRY DATACLASS
# =============================================================================


@dataclass
class StandardEntry:
    """A normalized swim entry with standard field names."""

    swimmer: str
    team: str  # Team code (e.g., "SST")
    event: str  # Full event name with gender (e.g., "Boys 100 Free")
    time: float  # Time in seconds
    gender: str = ""  # "M" or "F"
    grade: Optional[int] = None
    is_diver: bool = False
    is_relay: bool = False
    team_name: str = ""  # Full team name for display

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "swimmer": self.swimmer,
            "team": self.team,
            "event": self.event,
            "time": self.time,
            "gender": self.gender,
            "grade": self.grade,
            "is_diver": self.is_diver,
            "is_relay": self.is_relay,
            "team_name": self.team_name,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StandardEntry":
        """Create from dictionary with any column name format."""
        normalized = normalize_entry_dict(data)
        return cls(
            swimmer=normalized.get("swimmer", ""),
            team=normalized.get("team", ""),
            event=normalized.get("event", ""),
            time=normalized.get("time", float("inf")),
            gender=normalized.get("gender", ""),
            grade=normalized.get("grade"),
            is_diver=normalized.get("is_diver", False),
            is_relay=normalized.get("is_relay", False),
            team_name=normalized.get("team_name", ""),
        )


# =============================================================================
# NORMALIZATION FUNCTIONS
# =============================================================================


def find_column_value(
    data: Dict[str, Any], canonical_name: str, default: Any = None
) -> Any:
    """
    Find a value in a dictionary using canonical name or its aliases.

    Args:
        data: Source dictionary
        canonical_name: The canonical field name (e.g., "swimmer")
        default: Default value if not found

    Returns:
        The value found, or default
    """
    # Try exact match first
    if canonical_name in data:
        return data[canonical_name]

    # Try aliases
    aliases = COLUMN_ALIASES.get(canonical_name, [])
    for alias in aliases:
        # Try exact match
        if alias in data:
            return data[alias]
        # Try case-insensitive
        for key in data.keys():
            if key.lower() == alias.lower():
                return data[key]
            # Try with underscores replaced by spaces and vice versa
            if key.lower().replace("_", " ") == alias.lower():
                return data[key]
            if key.lower().replace(" ", "_") == alias.lower():
                return data[key]

    return default


def normalize_team_code(team: str) -> str:
    """
    Normalize a team name to its standard three-letter code.

    Args:
        team: Any form of team name

    Returns:
        Standard team code (e.g., "SST")

    Examples:
        >>> normalize_team_code("Seton Swimming")
        'SST'
        >>> normalize_team_code("sst")
        'SST'
        >>> normalize_team_code("Trinity Christian School")
        'TCS'
    """
    if not team:
        return ""

    cleaned = team.strip().lower()

    # Check if already a code (3 uppercase letters)
    if len(team.strip()) <= 4 and team.strip().isupper():
        return team.strip()

    # Look up in mapping
    if cleaned in TEAM_CODE_MAP:
        return TEAM_CODE_MAP[cleaned]

    # Partial match
    for key, code in TEAM_CODE_MAP.items():
        if key in cleaned or cleaned in key:
            return code

    # Return uppercase as fallback
    return team.strip().upper()[:4]


def normalize_gender(gender: str) -> str:
    """
    Normalize a gender value to "M" or "F".

    Args:
        gender: Any form of gender designation

    Returns:
        "M", "F", or "" if unknown
    """
    if not gender:
        return ""

    cleaned = str(gender).strip().lower()
    return GENDER_MAP.get(cleaned, "")


def normalize_grade(grade: Any) -> Optional[int]:
    """
    Normalize a grade value to an integer.

    Args:
        grade: Grade in various formats

    Returns:
        Integer grade (7-12) or None
    """
    if grade is None:
        return None

    if isinstance(grade, int):
        return grade if 6 <= grade <= 12 else None

    if isinstance(grade, float):
        return int(grade) if 6 <= grade <= 12 else None

    if isinstance(grade, str):
        cleaned = grade.strip().lower()

        # Remove suffixes
        cleaned = re.sub(r"(st|nd|rd|th)$", "", cleaned)

        # Grade names
        grade_names = {
            "freshman": 9,
            "fr": 9,
            "sophomore": 10,
            "so": 10,
            "junior": 11,
            "jr": 11,
            "senior": 12,
            "sr": 12,
            "7th": 7,
            "7": 7,
            "8th": 8,
            "8": 8,
        }

        if cleaned in grade_names:
            return grade_names[cleaned]

        try:
            val = int(cleaned)
            return val if 6 <= val <= 12 else None
        except ValueError:
            return None

    return None


def normalize_entry_dict(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize a dictionary entry to use canonical column names and values.

    This is the main entry point for normalizing swim entry data from any source.

    Args:
        data: Dictionary with any column naming convention

    Returns:
        Dictionary with canonical column names and normalized values
    """
    # Extract raw values using aliases
    raw_swimmer = find_column_value(data, "swimmer", "")
    raw_team = find_column_value(data, "team", "")
    raw_team_name = find_column_value(data, "team_name", "")
    raw_event = find_column_value(data, "event", "")
    raw_time = find_column_value(data, "time", None)
    raw_gender = find_column_value(data, "gender", "")
    raw_grade = find_column_value(data, "grade", None)
    raw_is_diver = find_column_value(data, "is_diver", False)
    raw_is_relay = find_column_value(data, "is_relay", False)

    # Normalize each field
    swimmer = normalize_swimmer_name(str(raw_swimmer)) if raw_swimmer else ""
    team_code = normalize_team_code(str(raw_team)) if raw_team else ""
    team_name = raw_team_name or TEAM_DISPLAY_NAMES.get(team_code, "")
    gender = normalize_gender(str(raw_gender)) if raw_gender else ""
    grade = normalize_grade(raw_grade)

    # Normalize event - try to extract gender from event name if not provided
    event_str = str(raw_event) if raw_event else ""

    # If gender not in data but is in event name, extract it
    if not gender and event_str:
        event_lower = event_str.lower()
        if event_lower.startswith(("m ", "boys ", "men ")):
            gender = "M"
        elif event_lower.startswith(("f ", "girls ", "women ")):
            gender = "F"

    # Build event with gender prefix
    if gender and not event_str.lower().startswith(("boys", "girls", "m ", "f ")):
        prefix = "Boys" if gender == "M" else "Girls"
        event = normalize_event_name_with_gender(f"{prefix} {event_str}")
    else:
        event = normalize_event_name_with_gender(event_str)

    # Normalize time
    time = normalize_time(raw_time)
    if time is None:
        time = float("inf")

    # Determine if relay/diving from event name
    is_relay = "relay" in event.lower() if event else bool(raw_is_relay)
    is_diver = "diving" in event.lower() if event else bool(raw_is_diver)

    return {
        "swimmer": swimmer,
        "team": team_code,
        "team_name": team_name,
        "event": event,
        "time": time,
        "gender": gender,
        "grade": grade,
        "is_diver": is_diver,
        "is_relay": is_relay,
    }


def normalize_entries(entries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Normalize a list of entry dictionaries.

    Args:
        entries: List of raw entry dictionaries

    Returns:
        List of normalized entry dictionaries
    """
    return [normalize_entry_dict(e) for e in entries]


def normalize_entries_to_standard(entries: List[Dict[str, Any]]) -> List[StandardEntry]:
    """
    Convert a list of entry dictionaries to StandardEntry objects.

    Args:
        entries: List of raw entry dictionaries

    Returns:
        List of StandardEntry objects
    """
    return [StandardEntry.from_dict(e) for e in entries]


# =============================================================================
# VALIDATION
# =============================================================================


@dataclass
class ValidationResult:
    """Result of entry validation."""

    is_valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


def validate_entry(entry: Dict[str, Any]) -> ValidationResult:
    """
    Validate a normalized entry dictionary.

    Args:
        entry: Normalized entry dictionary

    Returns:
        ValidationResult with status and any issues
    """
    errors = []
    warnings = []

    # Required fields
    if not entry.get("swimmer"):
        errors.append("Missing swimmer name")

    if not entry.get("team"):
        errors.append("Missing team")

    if not entry.get("event"):
        errors.append("Missing event")

    # Time validation
    time = entry.get("time")
    if time is None or time == float("inf"):
        warnings.append("Missing or invalid time (will sort to end)")
    elif time <= 0:
        errors.append(f"Invalid time: {time}")
    elif time < 10:
        warnings.append(f"Unusually fast time: {time}s - verify data")
    elif time > 1000:
        warnings.append(f"Unusually slow time: {time}s - verify format")

    # Gender validation
    gender = entry.get("gender", "")
    if gender and gender not in ("M", "F"):
        warnings.append(f"Unexpected gender value: {gender}")

    # Grade validation
    grade = entry.get("grade")
    if grade is not None and (grade < 6 or grade > 12):
        warnings.append(f"Grade out of range: {grade}")

    return ValidationResult(
        is_valid=len(errors) == 0,
        errors=errors,
        warnings=warnings,
    )


def validate_entries(entries: List[Dict[str, Any]]) -> Tuple[List[Dict], List[str]]:
    """
    Validate a list of entries and return valid ones with error summary.

    Args:
        entries: List of normalized entry dictionaries

    Returns:
        Tuple of (valid_entries, error_messages)
    """
    valid_entries = []
    all_errors = []

    for i, entry in enumerate(entries):
        result = validate_entry(entry)

        if result.is_valid:
            valid_entries.append(entry)
        else:
            for error in result.errors:
                all_errors.append(f"Entry {i + 1}: {error}")

        for warning in result.warnings:
            logger.warning(f"Entry {i + 1}: {warning}")

    return valid_entries, all_errors
