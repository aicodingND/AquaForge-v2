"""
Fatigue-Adjusted Performance Model

Models how swimmer performance degrades based on preceding events,
event spacing, and cumulative load during a championship meet.

Features:
- Event-specific fatigue costs
- Back-to-back event penalties
- Rest time recovery modeling
- Cumulative load tracking
"""

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class EventType(Enum):
    """Event type classification for fatigue modeling."""

    SPRINT = "sprint"  # 50, 100
    MIDDLE = "middle"  # 200
    DISTANCE = "distance"  # 500
    IM = "im"  # IM events
    RELAY = "relay"
    DIVING = "diving"


@dataclass
class FatigueParams:
    """Parameters for fatigue model."""

    # Base fatigue costs by event type (as percentage slowdown)
    event_fatigue_cost: Dict[EventType, float] = field(
        default_factory=lambda: {
            EventType.SPRINT: 0.005,  # 0.5% - quick recovery
            EventType.MIDDLE: 0.010,  # 1.0% - moderate
            EventType.DISTANCE: 0.020,  # 2.0% - high fatigue
            EventType.IM: 0.015,  # 1.5% - varied effort
            EventType.RELAY: 0.008,  # 0.8% - team energy
            EventType.DIVING: 0.003,  # 0.3% - mental mostly
        }
    )

    # Back-to-back penalty multiplier
    back_to_back_multiplier: float = 1.5

    # Recovery rate per minute of rest
    recovery_per_minute: float = 0.001  # 0.1% recovery per minute

    # Maximum fatigue cap (performance floor)
    max_fatigue_penalty: float = 0.05  # 5% max slowdown

    # Minimum rest for full recovery (minutes)
    full_recovery_time: float = 45.0


@dataclass
class FatigueState:
    """Tracks current fatigue state for a swimmer."""

    swimmer_name: str
    cumulative_fatigue: float = 0.0  # Current fatigue level
    events_swam: List[str] = field(default_factory=list)
    last_event_time: Optional[float] = None  # Minutes since meet start

    def add_event(self, event: str, event_time: float, fatigue_cost: float):
        """Record a swum event and update fatigue."""
        self.events_swam.append(event)
        self.cumulative_fatigue += fatigue_cost
        self.last_event_time = event_time


@dataclass
class FatigueAdjustedTime:
    """Result of fatigue adjustment calculation."""

    original_time: float
    adjusted_time: float
    fatigue_penalty: float  # As seconds
    fatigue_percentage: float  # As percentage
    is_back_to_back: bool
    rest_time_minutes: Optional[float]

    def to_dict(self) -> Dict:
        return {
            "original_time": round(self.original_time, 2),
            "adjusted_time": round(self.adjusted_time, 2),
            "fatigue_penalty_seconds": round(self.fatigue_penalty, 2),
            "fatigue_percentage": round(self.fatigue_percentage * 100, 2),
            "is_back_to_back": self.is_back_to_back,
            "rest_time_minutes": round(self.rest_time_minutes, 1)
            if self.rest_time_minutes
            else None,
        }


class FatigueModel:
    """
    Models performance degradation from fatigue during meets.

    Accounts for:
    - Event type (distance events more fatiguing)
    - Back-to-back events (additional penalty)
    - Rest time between events (recovery)
    - Cumulative load (multiple events in meet)
    """

    # Standard event order with approximate times (minutes from meet start)
    # Based on typical VCAC Championship timeline
    STANDARD_EVENT_TIMES: Dict[str, float] = {
        "200 Medley Relay": 0,
        "200 Free": 10,
        "200 IM": 25,
        "50 Free": 40,
        "Diving": 55,
        "100 Fly": 80,
        "100 Free": 95,
        "500 Free": 110,
        "200 Free Relay": 140,
        "100 Back": 155,
        "100 Breast": 170,
        "400 Free Relay": 185,
    }

    # Back-to-back event pairs (events too close together)
    BACK_TO_BACK_PAIRS = [
        ("50 Free", "100 Fly"),
        ("100 Fly", "100 Free"),
        ("100 Free", "500 Free"),
        ("500 Free", "200 Free Relay"),
        ("100 Back", "100 Breast"),
    ]

    def __init__(self, params: Optional[FatigueParams] = None):
        self.params = params or FatigueParams()
        self.swimmer_states: Dict[str, FatigueState] = {}

    def classify_event(self, event_name: str) -> EventType:
        """Classify event for fatigue calculation."""
        event_lower = event_name.lower()

        if "diving" in event_lower:
            return EventType.DIVING
        if "relay" in event_lower:
            return EventType.RELAY
        if (
            "im" in event_lower
            or "medley" in event_lower
            and "relay" not in event_lower
        ):
            return EventType.IM
        if "500" in event_lower or "1000" in event_lower or "1650" in event_lower:
            return EventType.DISTANCE
        if "200" in event_lower:
            return EventType.MIDDLE
        return EventType.SPRINT

    def is_back_to_back(self, event1: str, event2: str) -> bool:
        """Check if two events are back-to-back."""
        # Normalize event names
        e1 = self._normalize_event(event1)
        e2 = self._normalize_event(event2)

        for pair in self.BACK_TO_BACK_PAIRS:
            p1, p2 = self._normalize_event(pair[0]), self._normalize_event(pair[1])
            if (e1 == p1 and e2 == p2) or (e1 == p2 and e2 == p1):
                return True
        return False

    def _normalize_event(self, event: str) -> str:
        """Normalize event name for comparison."""
        # Remove gender prefix
        event = event.lower()
        for prefix in ["boys ", "girls ", "mens ", "womens ", "m ", "f "]:
            if event.startswith(prefix):
                event = event[len(prefix) :]
        return event.strip()

    def get_event_time(self, event_name: str) -> float:
        """Get approximate time of event in meet timeline (minutes)."""
        normalized = self._normalize_event(event_name)

        # Try exact match first
        for event, time in self.STANDARD_EVENT_TIMES.items():
            if self._normalize_event(event) == normalized:
                return time

        # Try partial match
        for event, time in self.STANDARD_EVENT_TIMES.items():
            if normalized in self._normalize_event(event):
                return time

        # Default to middle of meet
        return 90.0

    def calculate_rest_time(self, previous_event: str, current_event: str) -> float:
        """Calculate rest time between two events in minutes."""
        prev_time = self.get_event_time(previous_event)
        curr_time = self.get_event_time(current_event)

        # Events are in order, so current should be after previous
        rest = curr_time - prev_time

        # Account for warm-up/cool-down (subtract ~5 mins each)
        effective_rest = max(0, rest - 10)

        return effective_rest

    def calculate_fatigue_penalty(
        self,
        swimmer: str,
        current_event: str,
        previous_events: List[str],
        seed_time: float,
    ) -> FatigueAdjustedTime:
        """
        Calculate fatigue-adjusted performance.

        Args:
            swimmer: Swimmer name
            current_event: Event being predicted
            previous_events: Events already swum (in order)
            seed_time: Original seed time in seconds

        Returns:
            FatigueAdjustedTime with adjusted prediction
        """
        total_penalty_pct = 0.0
        is_b2b = False
        rest_time = None

        if previous_events:
            # Check for back-to-back with immediately previous event
            last_event = previous_events[-1]
            is_b2b = self.is_back_to_back(last_event, current_event)
            rest_time = self.calculate_rest_time(last_event, current_event)

            # Calculate cumulative fatigue from ALL previous events
            for prev_event in previous_events:
                event_type = self.classify_event(prev_event)
                base_cost = self.params.event_fatigue_cost.get(event_type, 0.01)
                total_penalty_pct += base_cost

            # Additional back-to-back penalty
            if is_b2b:
                total_penalty_pct *= self.params.back_to_back_multiplier

            # Recovery from rest time
            if rest_time is not None and rest_time > 0:
                recovery = min(
                    rest_time * self.params.recovery_per_minute,
                    total_penalty_pct,  # Can't recover more than fatigued
                )
                total_penalty_pct -= recovery

        # Cap at maximum penalty
        total_penalty_pct = min(total_penalty_pct, self.params.max_fatigue_penalty)
        total_penalty_pct = max(0, total_penalty_pct)  # Ensure non-negative

        # Calculate adjusted time
        penalty_seconds = seed_time * total_penalty_pct
        adjusted_time = seed_time + penalty_seconds

        return FatigueAdjustedTime(
            original_time=seed_time,
            adjusted_time=adjusted_time,
            fatigue_penalty=penalty_seconds,
            fatigue_percentage=total_penalty_pct,
            is_back_to_back=is_b2b,
            rest_time_minutes=rest_time,
        )

    def get_fatigue_report(
        self,
        swimmer: str,
        event_assignments: List[str],
    ) -> Dict:
        """
        Generate fatigue report for a swimmer's lineup.

        Args:
            swimmer: Swimmer name
            event_assignments: Ordered list of assigned events

        Returns:
            Report with fatigue analysis per event
        """
        report = {
            "swimmer": swimmer,
            "total_events": len(event_assignments),
            "events": [],
            "total_fatigue_cost": 0.0,
            "back_to_back_count": 0,
            "risk_assessment": "",
        }

        for i, event in enumerate(event_assignments):
            previous = event_assignments[:i]

            # Need a sample time - use 60 seconds as baseline
            # In real usage, pass actual seed time
            sample_time = 60.0
            fatigue = self.calculate_fatigue_penalty(
                swimmer, event, previous, sample_time
            )

            report["events"].append(
                {
                    "event": event,
                    "order": i + 1,
                    "fatigue_percentage": round(fatigue.fatigue_percentage * 100, 2),
                    "is_back_to_back": fatigue.is_back_to_back,
                    "rest_time": fatigue.rest_time_minutes,
                }
            )

            report["total_fatigue_cost"] += fatigue.fatigue_percentage
            if fatigue.is_back_to_back:
                report["back_to_back_count"] += 1

        # Risk assessment
        total = report["total_fatigue_cost"]
        b2b = report["back_to_back_count"]

        if total > 0.03 or b2b >= 2:
            report["risk_assessment"] = "high"
        elif total > 0.015 or b2b >= 1:
            report["risk_assessment"] = "medium"
        else:
            report["risk_assessment"] = "low"

        report["total_fatigue_cost"] = round(total * 100, 2)

        return report


def adjust_times_for_fatigue(
    entries: List[Dict],
    assignments: Dict[str, List[str]],  # {swimmer: [events]}
) -> List[Dict]:
    """
    Adjust all entry times for fatigue based on assignments.

    Args:
        entries: Original entry list
        assignments: Event assignments per swimmer

    Returns:
        Entries with adjusted times
    """
    model = FatigueModel()
    adjusted_entries = []

    # Group entries by swimmer for efficient lookup
    swimmer_entries = {}
    for entry in entries:
        swimmer = entry.get("swimmer", "")
        if swimmer not in swimmer_entries:
            swimmer_entries[swimmer] = []
        swimmer_entries[swimmer].append(entry)

    for entry in entries:
        swimmer = entry.get("swimmer", "")
        event = entry.get("event", "")
        time = entry.get("time", 9999)

        if isinstance(time, str):
            try:
                time = float(time)
            except ValueError:
                time = 9999

        # Get this swimmer's assigned events
        swimmer_events = assignments.get(swimmer, [])

        # Find previous events relative to current
        if event in swimmer_events:
            event_idx = swimmer_events.index(event)
            previous_events = swimmer_events[:event_idx]
        else:
            previous_events = []

        # Calculate fatigue adjustment
        fatigue = model.calculate_fatigue_penalty(swimmer, event, previous_events, time)

        adjusted_entries.append(
            {
                **entry,
                "original_time": time,
                "time": fatigue.adjusted_time,
                "fatigue_penalty": fatigue.fatigue_penalty,
                "fatigue_pct": fatigue.fatigue_percentage,
                "is_back_to_back": fatigue.is_back_to_back,
            }
        )

    return adjusted_entries
