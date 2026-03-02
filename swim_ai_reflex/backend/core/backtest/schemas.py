"""Data models for backtesting: actual results, predictions, and comparison reports."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class EventResult:
    """Single swimmer's result in an event."""

    place: int
    swimmer: str
    team: str
    time: float | None = None  # Finals time in seconds
    points: float = 0.0
    seed_time: float | None = None
    dq: bool = False
    exhibition: bool = False


@dataclass
class EventResults:
    """All results for one event + gender."""

    event_name: str  # Base name, e.g., "200 Free"
    gender: str  # "Boys" or "Girls"
    event_type: str = "individual"  # "individual", "relay", "diving"
    results: list[EventResult] = field(default_factory=list)

    @property
    def full_event_name(self) -> str:
        """Return gender-prefixed name matching optimizer format: 'Boys 200 Free'."""
        return f"{self.gender} {self.event_name}"


@dataclass
class ActualMeetResults:
    """Complete actual results for a meet."""

    meet_id: str
    meet_name: str
    meet_date: str
    meet_profile: str  # e.g., "visaa_state", "vcac_championship"
    source: str = ""  # e.g., "HyTek results PDF", "manual transcription"
    transcribed_date: str = ""
    events: list[EventResults] = field(default_factory=list)
    team_scores: dict[str, dict[str, float]] = field(default_factory=dict)


@dataclass
class PredictionSnapshot:
    """Saved optimizer prediction for a meet."""

    meet_id: str
    optimizer: str  # "aqua" or "gurobi"
    meet_profile: str
    timestamp: str = ""
    solve_time_ms: float = 0.0
    quality_mode: str = ""
    assignments: dict[str, list[str]] = field(default_factory=dict)
    predicted_scores: dict[str, Any] = field(default_factory=dict)
    event_breakdown: dict[str, Any] = field(default_factory=dict)


@dataclass
class EventComparison:
    """Per-event prediction vs actual comparison."""

    event_name: str  # Full event name (e.g., "Boys 200 Free")
    predicted_seton_points: float
    actual_seton_points: float
    predicted_seton_entries: list[str]  # Swimmer names
    actual_seton_entries: list[str]
    delta: float  # actual - predicted


@dataclass
class SwimmerComparison:
    """Per-swimmer prediction vs actual comparison."""

    swimmer: str
    team: str
    predicted_events: list[str]
    actual_events: list[str]
    actual_points: float
    status: str  # "MATCH", "DIFFER", "predicted_only", "actual_only"


@dataclass
class BacktestReport:
    """Complete comparison report."""

    meet_id: str
    meet_name: str
    optimizer: str
    predicted_seton_total: float
    actual_seton_total: float
    score_delta: float  # actual - predicted
    score_accuracy_pct: float  # 100 - |delta| / actual * 100
    event_comparisons: list[EventComparison] = field(default_factory=list)
    swimmer_comparisons: list[SwimmerComparison] = field(default_factory=list)
    assignment_match_rate: float = 0.0  # % of swimmers with identical events
