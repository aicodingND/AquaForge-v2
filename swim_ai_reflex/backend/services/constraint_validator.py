"""
Constraint Validator Service

Validates swimmer assignments for relay and diving constraints.
Enforces back-to-back constraints (including relay legs blocking next event).

CRITICAL RULE: A swimmer who swims a leg of a relay CANNOT swim the immediately
following event. This is a STANDARD RULE, not an optional fatigue toggle.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Set, Tuple, Optional
from swim_ai_reflex.backend.core.rules import get_meet_profile


# Standard event order for all high school swim meets
EVENT_ORDER = [
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

# Pre-computed: which events are blocked by each event
# Key: event that swimmer is in
# Value: event(s) immediately following that are blocked
BACK_TO_BACK_BLOCKS = {
    "200 Medley Relay": ["200 Free"],
    "200 Free": ["200 IM"],
    "200 IM": ["50 Free"],
    "50 Free": ["Diving"],
    "Diving": ["100 Fly"],
    "100 Fly": ["100 Free"],
    "100 Free": ["500 Free"],
    "500 Free": ["200 Free Relay"],
    "200 Free Relay": ["100 Back"],
    "100 Back": ["100 Breast"],
    "100 Breast": ["400 Free Relay"],
    "400 Free Relay": [],  # End of meet
}


@dataclass
class SwimmerEvent:
    """Represents a swimmer's participation in an event."""

    swimmer_name: str
    event: str
    is_relay: bool = False
    is_diving: bool = False
    relay_leg: Optional[str] = None  # 'back', 'breast', 'fly', 'free' for medley


@dataclass
class ConstraintViolation:
    """Represents a constraint violation."""

    swimmer: str
    violation_type: str  # 'back_to_back', 'max_events', 'invalid_entry'
    message: str
    events_involved: List[str] = field(default_factory=list)
    severity: str = "error"  # 'error' or 'warning'


@dataclass
class ValidationResult:
    """Result of constraint validation."""

    is_valid: bool
    violations: List[ConstraintViolation] = field(default_factory=list)
    warnings: List[ConstraintViolation] = field(default_factory=list)

    def add_error(self, violation: ConstraintViolation):
        self.violations.append(violation)
        self.is_valid = False

    def add_warning(self, violation: ConstraintViolation):
        violation.severity = "warning"
        self.warnings.append(violation)


def normalize_event_name(event: str) -> str:
    """Normalize event name for comparison."""
    if not event:
        return ""

    n = event.lower().strip()

    # Handle relay variations
    if "medley" in n and "relay" in n:
        return "200 Medley Relay"
    if "200 free relay" in n or ("200" in n and "free" in n and "relay" in n):
        return "200 Free Relay"
    if "400 free relay" in n or ("400" in n and "free" in n and "relay" in n):
        return "400 Free Relay"

    # Handle individual events (check longer patterns first!)
    if "diving" in n or "dive" in n:
        return "Diving"
    if "fly" in n or "butterfly" in n:
        return "100 Fly"
    if "back" in n:
        return "100 Back"
    if "breast" in n:
        return "100 Breast"
    if "im" in n or "individual medley" in n:
        return "200 IM"
    # Check 500 Free BEFORE 50 Free (longer match first)
    if "500 free" in n or ("500" in n and "free" in n):
        return "500 Free"
    if "50 free" in n or ("50" in n and "free" in n):
        return "50 Free"
    if "100 free" in n or ("100" in n and "free" in n and "relay" not in n):
        return "100 Free"
    if "200 free" in n and "relay" not in n:
        return "200 Free"

    return event  # Return original if no match


def get_event_index(event: str) -> int:
    """Get the index of an event in the standard order."""
    normalized = normalize_event_name(event)
    try:
        return EVENT_ORDER.index(normalized)
    except ValueError:
        return -1


def is_back_to_back(event1: str, event2: str) -> bool:
    """
    Check if two events are consecutive in standard order.

    Returns True if event2 immediately follows event1.
    """
    e1 = normalize_event_name(event1)
    e2 = normalize_event_name(event2)

    if not e1 or not e2:
        return False

    # Check if e2 is in the blocked list for e1
    blocked = BACK_TO_BACK_BLOCKS.get(e1, [])
    return e2 in blocked


def get_blocked_events(event: str) -> List[str]:
    """Get list of events that are blocked if swimmer participates in given event."""
    normalized = normalize_event_name(event)
    return BACK_TO_BACK_BLOCKS.get(normalized, [])


def is_relay_event(event: str) -> bool:
    """Check if event is a relay."""
    return "relay" in event.lower()


def is_diving_event(event: str) -> bool:
    """Check if event is diving."""
    n = event.lower()
    return "diving" in n or "dive" in n


class ConstraintValidator:
    """
    Validates swimmer assignments against meet rules.

    Enforces:
    - Back-to-back constraint (including relay legs)
    - Max individual events per swimmer
    - Max total events per swimmer
    - Diving counts as individual event
    - 400 Free Relay counts as individual event (VCAC)
    """

    def __init__(
        self,
        meet_profile: str = "seton_dual",
        allow_back_to_back_override: bool = False,
    ):
        """
        Initialize validator.

        Args:
            meet_profile: Name of meet profile for rules
            allow_back_to_back_override: If True, back-to-back violations
                                         become warnings instead of errors.
                                         Should ONLY be used in extraordinary cases.
        """
        self.rules = get_meet_profile(meet_profile)
        self.allow_back_to_back_override = allow_back_to_back_override
        self.meet_profile = meet_profile

    def validate_assignments(
        self,
        assignments: Dict[str, List[str]],
        divers: Set[str] = None,
        relay_assignments: Dict[str, Dict[str, List[str]]] = None,
    ) -> ValidationResult:
        """
        Validate all swimmer assignments.

        Args:
            assignments: {swimmer_name: [event1, event2, ...]}
            divers: Set of swimmer names who are divers
            relay_assignments: {relay_name: {leg: [swimmers]}} or
                             {relay_name: [swimmers]} (for free relays)

        Returns:
            ValidationResult with any violations found
        """
        result = ValidationResult(is_valid=True)
        divers = divers or set()
        relay_assignments = relay_assignments or {}

        # Build complete picture of each swimmer's events
        swimmer_events = self._build_swimmer_events(
            assignments, divers, relay_assignments
        )

        # Validate each swimmer
        for swimmer, events in swimmer_events.items():
            # Check back-to-back constraint
            self._check_back_to_back(swimmer, events, result)

            # Check max events constraint
            self._check_max_events(swimmer, events, divers, result)

        return result

    def _build_swimmer_events(
        self,
        assignments: Dict[str, List[str]],
        divers: Set[str],
        relay_assignments: Dict[str, Dict[str, List[str]]],
    ) -> Dict[str, List[SwimmerEvent]]:
        """Build list of SwimmerEvent objects for each swimmer."""
        swimmer_events: Dict[str, List[SwimmerEvent]] = {}

        # Individual event assignments
        for swimmer, events in assignments.items():
            if swimmer not in swimmer_events:
                swimmer_events[swimmer] = []

            for event in events:
                swimmer_events[swimmer].append(
                    SwimmerEvent(
                        swimmer_name=swimmer,
                        event=normalize_event_name(event),
                        is_relay=is_relay_event(event),
                        is_diving=is_diving_event(event),
                    )
                )

        # Relay assignments
        for relay_name, legs_or_swimmers in relay_assignments.items():
            normalized_relay = normalize_event_name(relay_name)

            if isinstance(legs_or_swimmers, dict):
                # Medley relay: {leg: [swimmers]}
                for leg, swimmers in legs_or_swimmers.items():
                    for swimmer in swimmers:
                        if swimmer not in swimmer_events:
                            swimmer_events[swimmer] = []
                        swimmer_events[swimmer].append(
                            SwimmerEvent(
                                swimmer_name=swimmer,
                                event=normalized_relay,
                                is_relay=True,
                                relay_leg=leg,
                            )
                        )
            else:
                # Free relay: [swimmers]
                for swimmer in legs_or_swimmers:
                    if swimmer not in swimmer_events:
                        swimmer_events[swimmer] = []
                    swimmer_events[swimmer].append(
                        SwimmerEvent(
                            swimmer_name=swimmer, event=normalized_relay, is_relay=True
                        )
                    )

        # Add diving events for divers
        for swimmer in divers:
            if swimmer not in swimmer_events:
                swimmer_events[swimmer] = []
            # Check if diving already added
            has_diving = any(e.is_diving for e in swimmer_events[swimmer])
            if not has_diving:
                swimmer_events[swimmer].append(
                    SwimmerEvent(swimmer_name=swimmer, event="Diving", is_diving=True)
                )

        return swimmer_events

    def _check_back_to_back(
        self, swimmer: str, events: List[SwimmerEvent], result: ValidationResult
    ):
        """Check for back-to-back constraint violations."""
        # Sort events by meet order
        sorted_events = sorted(events, key=lambda e: get_event_index(e.event))

        for i, event1 in enumerate(sorted_events):
            blocked_events = get_blocked_events(event1.event)

            for event2 in sorted_events[i + 1 :]:
                if event2.event in blocked_events:
                    violation = ConstraintViolation(
                        swimmer=swimmer,
                        violation_type="back_to_back",
                        message=(
                            f"{swimmer} cannot swim {event2.event} immediately after "
                            f"{event1.event} (back-to-back constraint)"
                        ),
                        events_involved=[event1.event, event2.event],
                    )

                    if self.allow_back_to_back_override:
                        result.add_warning(violation)
                    else:
                        result.add_error(violation)

    def _check_max_events(
        self,
        swimmer: str,
        events: List[SwimmerEvent],
        divers: Set[str],
        result: ValidationResult,
    ):
        """Check max events per swimmer constraints."""
        is_diver = swimmer in divers

        # Count individual events
        individual_count = sum(1 for e in events if not e.is_relay and not e.is_diving)

        # Count relays
        relay_events = [e for e in events if e.is_relay]
        relay_count = len(set(e.event for e in relay_events))  # Unique relays

        # Apply VCAC 400 Free Relay penalty if applicable
        has_400_free_relay = any(e.event == "400 Free Relay" for e in relay_events)
        relay_3_penalty = 0
        if self.meet_profile == "vcac_championship" and has_400_free_relay:
            relay_3_penalty = 1

        # Calculate effective individual count
        effective_individual = (
            individual_count + (1 if is_diver else 0) + relay_3_penalty
        )

        # Check constraint
        max_individual = self.rules.max_individual_events_per_swimmer
        if effective_individual > max_individual:
            result.add_error(
                ConstraintViolation(
                    swimmer=swimmer,
                    violation_type="max_events",
                    message=(
                        f"{swimmer} has {effective_individual} effective individual events "
                        f"(max {max_individual}). "
                        f"Breakdown: {individual_count} swim + "
                        f"{'1 diving + ' if is_diver else ''}"
                        f"{'1 relay-3 penalty' if relay_3_penalty else ''}"
                    ),
                    events_involved=[e.event for e in events if not e.is_relay],
                )
            )

        # Check relay count
        if relay_count > 3:
            result.add_error(
                ConstraintViolation(
                    swimmer=swimmer,
                    violation_type="max_relays",
                    message=f"{swimmer} is on {relay_count} relays (max 3)",
                    events_involved=[e.event for e in relay_events],
                )
            )


def validate_lineup(
    seton_assignments: Dict[str, List[str]],
    divers: Set[str] = None,
    relay_assignments: Dict[str, Dict[str, List[str]]] = None,
    meet_profile: str = "seton_dual",
    allow_override: bool = False,
) -> ValidationResult:
    """
    Convenience function to validate a lineup.

    Args:
        seton_assignments: {swimmer: [events]}
        divers: Set of diver names
        relay_assignments: Relay leg assignments
        meet_profile: Meet profile name
        allow_override: Allow back-to-back override (extraordinary cases only)

    Returns:
        ValidationResult
    """
    validator = ConstraintValidator(
        meet_profile=meet_profile, allow_back_to_back_override=allow_override
    )
    return validator.validate_assignments(
        assignments=seton_assignments,
        divers=divers,
        relay_assignments=relay_assignments,
    )


# =============================================================================
# GUROBI CONSTRAINT GENERATION
# =============================================================================


def generate_back_to_back_constraints_for_gurobi(
    swimmers: List[str], events: List[str], relay_swimmers: Dict[str, Set[str]] = None
) -> List[Tuple[str, str, str]]:
    """
    Generate list of back-to-back constraints for Gurobi.

    Returns list of (swimmer, event1, event2) tuples where
    swimmer cannot do both event1 and event2.

    Args:
        swimmers: List of swimmer names
        events: List of event names
        relay_swimmers: {relay_name: set(swimmers on that relay)}

    Returns:
        List of constraint tuples
    """
    constraints = []
    relay_swimmers = relay_swimmers or {}

    # Normalize events
    normalized_events = [normalize_event_name(e) for e in events]

    for event1 in normalized_events:
        blocked = get_blocked_events(event1)

        for event2 in blocked:
            if event2 in normalized_events:
                # For individual events, apply to all swimmers
                if not is_relay_event(event1):
                    for swimmer in swimmers:
                        constraints.append((swimmer, event1, event2))
                else:
                    # For relays, only apply to swimmers on that relay
                    relay_swimmers_set = relay_swimmers.get(event1, set())
                    for swimmer in relay_swimmers_set:
                        if swimmer in swimmers:
                            constraints.append((swimmer, event1, event2))

    return constraints
