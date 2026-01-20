"""
Unified Data Validation Service

Provides consistent validation for all meet types.
Based on 2025 best practices:
- Single source of truth for validation rules
- Clear error messages
- Supports both strict and lenient modes
"""

import logging
from dataclasses import dataclass
from typing import Any, Dict, List

from swim_ai_reflex.backend.pipelines.base import ValidationResult

logger = logging.getLogger(__name__)


# Known events (canonical names)
KNOWN_EVENTS = {
    # Individual events
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
}

# Event aliases for normalization
EVENT_ALIASES = {
    "200 freestyle": "200 Free",
    "200 fr": "200 Free",
    "200 medley": "200 IM",
    "200 individual medley": "200 IM",
    "50 freestyle": "50 Free",
    "50 fr": "50 Free",
    "100 butterfly": "100 Fly",
    "100 fly": "100 Fly",
    "100 freestyle": "100 Free",
    "100 fr": "100 Free",
    "500 freestyle": "500 Free",
    "500 fr": "500 Free",
    "100 backstroke": "100 Back",
    "100 bk": "100 Back",
    "100 breaststroke": "100 Breast",
    "100 br": "100 Breast",
    "1m diving": "Diving",
    "1 meter diving": "Diving",
}


@dataclass
class SwimmerEntry:
    """Validated swimmer entry."""

    swimmer: str
    event: str
    time: float
    grade: int = 12
    team: str = ""
    is_relay: bool = False
    is_diving: bool = False
    is_exhibition: bool = False


class MeetDataValidator:
    """
    Unified validation for all meet types.

    Validates:
    - Swimmer entries (required fields, valid types)
    - Event names (recognized, normalized)
    - Times (parseable, reasonable range)
    - Constraints (event limits, back-to-back)
    """

    def __init__(self, strict: bool = False):
        """
        Initialize validator.

        Args:
            strict: If True, treat warnings as errors
        """
        self.strict = strict
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    def validate_swimmer_entry(
        self,
        entry: Dict[str, Any],
        require_team: bool = False,
    ) -> ValidationResult:
        """
        Validate a single swimmer entry.

        Args:
            entry: Dictionary with swimmer, event, time, etc.
            require_team: Whether team field is required

        Returns:
            ValidationResult
        """
        result = ValidationResult(valid=True)

        # Check required fields - accept both "swimmer" and "swimmer_name"
        swimmer = entry.get("swimmer") or entry.get("swimmer_name")
        if not swimmer:
            result.add_error("Missing swimmer name")
        elif not isinstance(swimmer, str):
            result.add_error(f"Swimmer name must be string, got {type(swimmer)}")

        if "event" not in entry:
            result.add_error("Missing event")
        elif not entry.get("event"):
            result.add_error("Event cannot be empty")

        if require_team and ("team" not in entry or not entry.get("team")):
            result.add_error("Missing team name")

        # Validate time (optional for diving)
        if "time" in entry:
            time_val = entry["time"]
            if time_val is not None:
                try:
                    float_time = float(time_val)
                    if float_time < 0:
                        result.add_error(f"Time cannot be negative: {time_val}")
                    elif float_time > 7200:  # 2 hours
                        result.add_warning(f"Unusually long time: {time_val}")
                except (ValueError, TypeError):
                    # Could be a time string like "1:23.45" - that's okay
                    if isinstance(time_val, str) and ":" in time_val:
                        pass  # Time string, will be parsed later
                    elif time_val not in ("NT", "NS", "DQ", None):
                        result.add_error(f"Invalid time format: {time_val}")

        # Validate grade if present
        if "grade" in entry:
            grade = entry.get("grade")
            if grade is not None:
                try:
                    int_grade = int(grade)
                    if int_grade < 6 or int_grade > 12:
                        result.add_warning(f"Unusual grade: {grade}")
                except (ValueError, TypeError):
                    result.add_error(f"Invalid grade: {grade}")

        return result

    def validate_event_name(self, event_name: str) -> ValidationResult:
        """
        Validate that an event name is recognized.

        Args:
            event_name: Event name to validate

        Returns:
            ValidationResult
        """
        result = ValidationResult(valid=True)

        if not event_name or not isinstance(event_name, str):
            result.add_error("Event name must be non-empty string")
            return result

        # Normalize and check
        normalized = self._normalize_event(event_name)

        if normalized not in KNOWN_EVENTS:
            result.add_warning(f"Unrecognized event: '{event_name}' -> '{normalized}'")

        return result

    def validate_swimmer_constraints(
        self,
        swimmer_events: Dict[str, List[str]],
        max_individual: int = 2,
        max_total: int = 4,
        check_back_to_back: bool = True,
    ) -> ValidationResult:
        """
        Validate swimmer event assignment constraints.

        Args:
            swimmer_events: Mapping of swimmer name to list of events
            max_individual: Maximum individual events per swimmer
            max_total: Maximum total events per swimmer
            check_back_to_back: Whether to check back-to-back constraint

        Returns:
            ValidationResult
        """
        result = ValidationResult(valid=True)

        for swimmer, events in swimmer_events.items():
            # Count individual vs relay events
            individual_events = [e for e in events if "relay" not in e.lower()]
            _relay_events = [e for e in events if "relay" in e.lower()]

            # Check individual limit
            if len(individual_events) > max_individual:
                result.add_error(
                    f"{swimmer}: {len(individual_events)} individual events "
                    f"exceeds limit of {max_individual}"
                )

            # Check total limit
            if len(events) > max_total:
                result.add_error(
                    f"{swimmer}: {len(events)} total events exceeds limit of {max_total}"
                )

            # Check back-to-back
            if check_back_to_back and len(individual_events) >= 2:
                b2b_violations = self._check_back_to_back(individual_events)
                for violation in b2b_violations:
                    result.add_error(f"{swimmer}: {violation}")

        return result

    def validate_team_entries(
        self,
        entries: List[Dict[str, Any]],
        max_per_event: int = 4,
    ) -> ValidationResult:
        """
        Validate team entry constraints.

        Args:
            entries: List of swimmer entries for a team
            max_per_event: Maximum entries per event

        Returns:
            ValidationResult with per-event validation
        """
        result = ValidationResult(valid=True)

        # Group by event
        event_counts: Dict[str, int] = {}
        for entry in entries:
            event = entry.get("event", "")
            event_counts[event] = event_counts.get(event, 0) + 1

        # Check per-event limits (warning only, not error)
        for event, count in event_counts.items():
            if count > max_per_event:
                result.add_warning(
                    f"Event '{event}' has {count} entries, only top {max_per_event} will score"
                )

        return result

    def validate_full_roster(
        self,
        entries: List[Dict[str, Any]],
        require_team: bool = False,
    ) -> ValidationResult:
        """
        Validate a complete roster of entries.

        Args:
            entries: List of all entries
            require_team: Whether team field is required

        Returns:
            Combined ValidationResult
        """
        result = ValidationResult(valid=True)

        if not entries:
            result.add_error("No entries provided")
            return result

        # Validate each entry
        for i, entry in enumerate(entries):
            entry_result = self.validate_swimmer_entry(entry, require_team)
            if not entry_result.valid:
                for error in entry_result.errors:
                    result.add_error(f"Entry {i + 1}: {error}")
            result.warnings.extend(entry_result.warnings)

        # Collect swimmer events
        swimmer_events: Dict[str, List[str]] = {}
        for entry in entries:
            swimmer = entry.get("swimmer") or entry.get("swimmer_name", "")
            event = entry.get("event", "")
            if swimmer and event:
                if swimmer not in swimmer_events:
                    swimmer_events[swimmer] = []
                swimmer_events[swimmer].append(event)

        # Validate constraints
        constraint_result = self.validate_swimmer_constraints(swimmer_events)
        result = result.merge(constraint_result)

        return result

    def _normalize_event(self, event_name: str) -> str:
        """Normalize event name to canonical form."""
        # Basic normalization
        normalized = event_name.strip().lower()

        # Check aliases
        if normalized in EVENT_ALIASES:
            return EVENT_ALIASES[normalized]

        # Try to match known events (case insensitive)
        for known in KNOWN_EVENTS:
            if normalized == known.lower():
                return known

        # Return title case as best effort
        return event_name.strip().title()

    def _check_back_to_back(self, events: List[str]) -> List[str]:
        """Check for back-to-back event violations."""
        violations = []

        # Event order (simplified)
        event_order = [
            "200 Free",
            "200 IM",
            "50 Free",
            "100 Fly",
            "100 Free",
            "500 Free",
            "100 Back",
            "100 Breast",
        ]

        # Normalize events
        normalized = [self._normalize_event(e) for e in events]

        # Get indices
        indices = []
        for event in normalized:
            if event in event_order:
                indices.append(event_order.index(event))

        # Check for consecutive indices
        indices.sort()
        for i in range(len(indices) - 1):
            if indices[i + 1] - indices[i] == 1:
                event1 = event_order[indices[i]]
                event2 = event_order[indices[i + 1]]
                violations.append(f"Back-to-back: {event1} → {event2}")

        return violations


# Singleton instance for dependency injection
meet_data_validator = MeetDataValidator()
