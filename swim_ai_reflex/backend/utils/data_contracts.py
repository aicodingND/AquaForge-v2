"""
Data Contracts - Input/Output Validation for AquaForge Pipeline

This module provides:
1. Typed data structures with validation
2. Centralized normalization functions
3. Clear error messages for invalid input
4. Validation result objects with warnings and errors

Usage:
    from swim_ai_reflex.backend.utils.data_contracts import (
        validate_team_entries,
        normalize_roster,
        ValidationResult,
    )

    result = validate_team_entries(raw_data, team_type="seton")
    if result.has_errors:
        return result.error_response()

    roster = normalize_roster(result.entries)
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

# ==================== Constants ====================

REQUIRED_ENTRY_FIELDS = {"swimmer", "event", "time"}
OPTIONAL_ENTRY_FIELDS = {"grade", "team", "gender", "seed_time", "age"}
FIELD_ALIASES = {
    "name": "swimmer",
    "athlete": "swimmer",
    "student": "swimmer",
    "race": "event",
    "stroke": "event",
    "entry_time": "time",
    "best_time": "time",
}

# Valid dual meet events (base names without gender prefix)
STANDARD_EVENTS = [
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

# Time patterns
TIME_PATTERN_MMSS = re.compile(r"^(\d+):(\d+(?:\.\d+)?)$")
TIME_PATTERN_SECONDS = re.compile(r"^\d+(?:\.\d+)?$")
INVALID_TIME_MARKERS = {"dnf", "dns", "dq", "nt", "ns", "scr", "x", "-"}


# ==================== Validation Result ====================


@dataclass
class ValidationIssue:
    """Single validation issue (error or warning)."""

    field: str
    message: str
    entry_index: Optional[int] = None
    severity: str = "error"  # "error" or "warning"
    suggestion: Optional[str] = None


@dataclass
class ValidationResult:
    """Result of validating input data."""

    entries: List[Dict[str, Any]] = field(default_factory=list)
    errors: List[ValidationIssue] = field(default_factory=list)
    warnings: List[ValidationIssue] = field(default_factory=list)
    stats: Dict[str, Any] = field(default_factory=dict)

    @property
    def has_errors(self) -> bool:
        return len(self.errors) > 0

    @property
    def has_warnings(self) -> bool:
        return len(self.warnings) > 0

    @property
    def is_valid(self) -> bool:
        return not self.has_errors

    def error_messages(self) -> List[str]:
        """Get all error messages as strings."""
        return [
            f"[{e.field}] {e.message}"
            + (f" (suggestion: {e.suggestion})" if e.suggestion else "")
            for e in self.errors
        ]

    def warning_messages(self) -> List[str]:
        """Get all warning messages as strings."""
        return [
            f"[{w.field}] {w.message}"
            + (f" (suggestion: {w.suggestion})" if w.suggestion else "")
            for w in self.warnings
        ]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API response."""
        return {
            "valid": self.is_valid,
            "errors": self.error_messages(),
            "warnings": self.warning_messages(),
            "stats": self.stats,
        }


# ==================== Time Conversion ====================


def parse_time(value: Any) -> Tuple[Optional[float], Optional[str]]:
    """
    Parse a time value to seconds.

    Returns:
        Tuple of (time_in_seconds, warning_message)
        - If valid: (float, None)
        - If invalid but recoverable: (9999.0, "warning message")
        - If invalid and unrecoverable: (None, "error message")
    """
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return 9999.0, "Missing time value, treated as forfeit"

    # Already numeric
    if isinstance(value, (int, float)):
        if value <= 0:
            return 9999.0, f"Invalid time {value}, treated as forfeit"
        return float(value), None

    # String conversion
    time_str = str(value).strip().lower()

    # Check for known invalid markers
    if time_str in INVALID_TIME_MARKERS:
        return 9999.0, f"'{value}' is not a valid time, treated as forfeit"

    # Remove common suffixes (Y for yards, S for short course, etc.)
    time_str = re.sub(r"[yslm]$", "", time_str, flags=re.IGNORECASE).strip()

    # Try MM:SS.ss format
    match = TIME_PATTERN_MMSS.match(time_str)
    if match:
        minutes = int(match.group(1))
        seconds = float(match.group(2))
        return minutes * 60 + seconds, None

    # Try seconds only
    match = TIME_PATTERN_SECONDS.match(time_str)
    if match:
        return float(time_str), None

    # Couldn't parse
    return 9999.0, f"Could not parse time '{value}', treated as forfeit"


def parse_grade(value: Any) -> Tuple[Optional[int], Optional[str]]:
    """
    Parse a grade value.

    Returns:
        Tuple of (grade, warning_message)
    """
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None, None  # Grade is optional

    try:
        grade = int(float(str(value).strip()))
        if grade < 1 or grade > 12:
            return None, f"Grade {grade} out of range (1-12)"
        return grade, None
    except (ValueError, TypeError):
        return None, f"Could not parse grade '{value}'"


# ==================== Field Normalization ====================


def normalize_field_name(field_name: str) -> str:
    """Normalize a field name using aliases."""
    normalized = field_name.lower().strip().replace(" ", "_")
    return FIELD_ALIASES.get(normalized, normalized)


def normalize_event_name(event: str) -> str:
    """Normalize event name to standard format."""
    if not isinstance(event, str):
        return str(event)

    # Strip and normalize whitespace
    event = " ".join(event.split())

    # Common abbreviation replacements
    replacements = {
        "Freestyle": "Free",
        "Butterfly": "Fly",
        "Backstroke": "Back",
        "Breaststroke": "Breast",
        "Individual Medley": "IM",
        "Indiv Medley": "IM",
        "Ind Medley": "IM",
        "Med Relay": "Medley Relay",
        "Fr Relay": "Free Relay",
    }

    for old, new in replacements.items():
        event = event.replace(old, new)

    return event


def normalize_swimmer_name(name: str) -> str:
    """Normalize swimmer name for matching."""
    if not isinstance(name, str):
        return str(name)

    # Strip and normalize whitespace
    name = " ".join(name.split())

    # Handle "Last, First" format
    if "," in name:
        parts = name.split(",", 1)
        name = f"{parts[1].strip()} {parts[0].strip()}"

    return name.strip()


# ==================== Entry Validation ====================


def validate_entry(
    entry: Dict[str, Any], index: int
) -> Tuple[Dict[str, Any], List[ValidationIssue]]:
    """
    Validate and normalize a single entry.

    Returns:
        Tuple of (normalized_entry, list_of_issues)
    """
    issues: List[ValidationIssue] = []
    normalized: Dict[str, Any] = {}

    # Normalize field names
    entry_normalized_keys = {normalize_field_name(k): v for k, v in entry.items()}

    # Check required fields
    for required in REQUIRED_ENTRY_FIELDS:
        if (
            required not in entry_normalized_keys
            or entry_normalized_keys.get(required) is None
        ):
            # Check if an alias was provided
            found_alias = None
            for alias, canonical in FIELD_ALIASES.items():
                if canonical == required and alias in entry:
                    found_alias = alias
                    break

            if found_alias:
                issues.append(
                    ValidationIssue(
                        field=required,
                        message=f"Missing required field '{required}'",
                        entry_index=index,
                        severity="error",
                        suggestion=f"Use '{required}' instead of '{found_alias}'",
                    )
                )
            else:
                issues.append(
                    ValidationIssue(
                        field=required,
                        message=f"Missing required field '{required}'",
                        entry_index=index,
                        severity="error",
                    )
                )

    if any(i.severity == "error" for i in issues):
        return {}, issues

    # Normalize swimmer name
    normalized["swimmer"] = normalize_swimmer_name(
        entry_normalized_keys.get("swimmer", "")
    )

    # Normalize event name
    normalized["event"] = normalize_event_name(entry_normalized_keys.get("event", ""))

    # Parse time
    time_val, time_warning = parse_time(entry_normalized_keys.get("time"))
    normalized["time"] = time_val
    if time_warning:
        issues.append(
            ValidationIssue(
                field="time",
                message=time_warning,
                entry_index=index,
                severity="warning",
            )
        )

    # Parse grade (optional)
    if "grade" in entry_normalized_keys:
        grade_val, grade_warning = parse_grade(entry_normalized_keys.get("grade"))
        normalized["grade"] = grade_val
        if grade_warning:
            issues.append(
                ValidationIssue(
                    field="grade",
                    message=grade_warning,
                    entry_index=index,
                    severity="warning",
                )
            )

    # Copy optional fields
    for opt_field in ["gender", "team", "seed_time", "age"]:
        if opt_field in entry_normalized_keys:
            normalized[opt_field] = entry_normalized_keys[opt_field]

    return normalized, issues


# ==================== Main Validation Function ====================


def validate_team_entries(
    raw_entries: List[Dict[str, Any]],
    team_type: str = "seton",
    remove_duplicates: bool = True,
) -> ValidationResult:
    """
    Validate and normalize a list of team entries.

    Args:
        raw_entries: List of dictionaries with swimmer/event/time data
        team_type: "seton" or "opponent"
        remove_duplicates: If True, keep only best time for duplicate swimmer+event

    Returns:
        ValidationResult with normalized entries, errors, and warnings
    """
    result = ValidationResult()

    if not raw_entries:
        result.errors.append(
            ValidationIssue(
                field="entries",
                message=f"No entries provided for {team_type} team",
                severity="error",
            )
        )
        return result

    normalized_entries: List[Dict[str, Any]] = []
    seen_swimmer_events: Dict[
        str, Tuple[int, float]
    ] = {}  # (swimmer+event) -> (index, time)

    for i, entry in enumerate(raw_entries):
        normalized, issues = validate_entry(entry, i)

        for issue in issues:
            if issue.severity == "error":
                result.errors.append(issue)
            else:
                result.warnings.append(issue)

        if not normalized:
            continue

        # Check for duplicates
        key = f"{normalized['swimmer'].lower()}|{normalized['event'].lower()}"

        if key in seen_swimmer_events:
            prev_index, prev_time = seen_swimmer_events[key]
            if remove_duplicates:
                if normalized["time"] < prev_time:
                    # New entry is faster, replace previous
                    result.warnings.append(
                        ValidationIssue(
                            field="duplicate",
                            message=f"Duplicate entry for {normalized['swimmer']} in {normalized['event']} - keeping faster time ({normalized['time']:.2f}s)",
                            entry_index=i,
                            severity="warning",
                        )
                    )
                    # Remove previous entry
                    normalized_entries = [
                        e for j, e in enumerate(normalized_entries) if j != prev_index
                    ]
                    normalized["team"] = team_type
                    normalized_entries.append(normalized)
                    seen_swimmer_events[key] = (
                        len(normalized_entries) - 1,
                        normalized["time"],
                    )
                else:
                    # Previous entry is faster or equal, skip this one
                    result.warnings.append(
                        ValidationIssue(
                            field="duplicate",
                            message=f"Duplicate entry for {normalized['swimmer']} in {normalized['event']} - keeping faster time ({prev_time:.2f}s)",
                            entry_index=i,
                            severity="warning",
                        )
                    )
            else:
                # Keep both but warn
                result.warnings.append(
                    ValidationIssue(
                        field="duplicate",
                        message=f"Duplicate entry for {normalized['swimmer']} in {normalized['event']}",
                        entry_index=i,
                        severity="warning",
                    )
                )
                normalized["team"] = team_type
                normalized_entries.append(normalized)
        else:
            normalized["team"] = team_type
            normalized_entries.append(normalized)
            seen_swimmer_events[key] = (len(normalized_entries) - 1, normalized["time"])

    result.entries = normalized_entries

    # Compute stats
    swimmers = set(e["swimmer"] for e in normalized_entries)
    events = set(e["event"] for e in normalized_entries)

    result.stats = {
        "total_entries": len(normalized_entries),
        "unique_swimmers": len(swimmers),
        "unique_events": len(events),
        "entries_with_warnings": len(
            set(w.entry_index for w in result.warnings if w.entry_index is not None)
        ),
        "forfeit_times": sum(1 for e in normalized_entries if e["time"] >= 9999),
    }

    return result


def normalize_roster(
    entries: List[Dict[str, Any]], team: str = "seton"
) -> pd.DataFrame:
    """
    Convert validated entries to a DataFrame with guaranteed schema.

    Args:
        entries: List of validated entry dictionaries
        team: Team name to use

    Returns:
        DataFrame with columns: swimmer, event, time, grade, team, is_relay, is_diving
    """
    if not entries:
        return pd.DataFrame(
            columns=[
                "swimmer",
                "event",
                "time",
                "grade",
                "team",
                "is_relay",
                "is_diving",
            ]
        )

    df = pd.DataFrame(entries)

    # Ensure required columns
    df["team"] = team

    # Add derived columns
    df["is_relay"] = df["event"].str.lower().str.contains("relay", na=False)
    df["is_diving"] = (
        df["event"].str.lower().str.contains("diving|dive", regex=True, na=False)
    )

    # Ensure grade exists (default None)
    if "grade" not in df.columns:
        df["grade"] = None

    return df


# ==================== Scoring Validation ====================


def validate_scoring_result(
    scored_df: pd.DataFrame,
    totals: Dict[str, float],
    num_events: int = 8,
    points_per_event: int = 29,
) -> ValidationResult:
    """
    Validate that scoring results are consistent.

    Checks:
    1. Total points sum to expected (232 for 8 events)
    2. No negative points
    3. Points per event match expected breakdown
    """
    result = ValidationResult()

    expected_total = num_events * points_per_event
    actual_total = totals.get("seton", 0) + totals.get("opponent", 0)

    if abs(actual_total - expected_total) > 0.1:
        result.warnings.append(
            ValidationIssue(
                field="total_points",
                message=f"Point total {actual_total:.1f} does not match expected {expected_total}",
                severity="warning",
            )
        )

    # Check for negative points
    if "points" in scored_df.columns:
        negative_points = scored_df[scored_df["points"] < 0]
        if not negative_points.empty:
            result.errors.append(
                ValidationIssue(
                    field="points",
                    message=f"Found {len(negative_points)} entries with negative points",
                    severity="error",
                )
            )

    result.stats = {
        "seton_score": totals.get("seton", 0),
        "opponent_score": totals.get("opponent", 0),
        "total_points": actual_total,
        "expected_total": expected_total,
        "point_difference": actual_total - expected_total,
    }

    return result
