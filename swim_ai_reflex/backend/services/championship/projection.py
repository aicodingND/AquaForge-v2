"""
Point Projection Service for Championship Meets

Projects points for all teams based on psych sheet seed times.
Used for VCAC, VISAA State, and other multi-team championships.
"""

import logging
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any

from swim_ai_reflex.backend.core.championship_factors import (
    ChampionshipFactors,
    adjust_time,
    get_event_confidence,
)
from swim_ai_reflex.backend.core.rules import get_meet_profile
from swim_ai_reflex.backend.services.shared.normalization import (
    is_diving_event,
    is_relay_event,
    normalize_team_name,
)

logger = logging.getLogger(__name__)


@dataclass
class SwimmerProjection:
    """Projected result for a single swimmer in an event."""

    swimmer: str
    team: str
    event: str
    seed_time: float
    seed_rank: int
    predicted_place: int
    points: float
    is_scoring: bool = True
    confidence: str = "medium"  # "high", "medium", "low" — from empirical flip rates

    def to_dict(self) -> dict[str, Any]:
        return {
            "swimmer": self.swimmer,
            "team": self.team,
            "event": self.event,
            "seed_time": self.seed_time,
            "seed_rank": self.seed_rank,
            "predicted_place": self.predicted_place,
            "points": self.points,
            "is_scoring": self.is_scoring,
            "confidence": self.confidence,
        }


@dataclass
class EventProjection:
    """Projected results for a single event."""

    event: str
    entries: list[SwimmerProjection]
    team_points: dict[str, float] = field(default_factory=dict)

    def calculate_team_points(self) -> dict[str, float]:
        """Calculate total points per team for this event."""
        self.team_points = defaultdict(float)
        for entry in self.entries:
            self.team_points[entry.team] += entry.points
        return dict(self.team_points)

    def to_dict(self) -> dict[str, Any]:
        return {
            "event": self.event,
            "team_points": self.team_points,
            "entries": [e.to_dict() for e in self.entries[:12]],  # Top 12
        }


@dataclass
class SwingEvent:
    """An event where small improvements yield significant point gains."""

    event: str
    swimmer: str
    team: str
    current_place: int
    target_place: int
    current_points: float
    potential_points: float
    point_gain: float
    time_gap: float  # Time needed to improve

    def to_dict(self) -> dict[str, Any]:
        return {
            "event": self.event,
            "swimmer": self.swimmer,
            "team": self.team,
            "current_place": self.current_place,
            "target_place": self.target_place,
            "current_points": self.current_points,
            "potential_points": self.potential_points,
            "point_gain": self.point_gain,
            "time_gap": self.time_gap,
        }


@dataclass
class StandingsProjection:
    """Complete meet standings projection."""

    meet_name: str
    target_team: str
    team_totals: dict[str, float]
    standings: list[tuple[str, float, int]]  # (team, points, rank)
    event_projections: dict[str, EventProjection]
    swing_events: list[SwingEvent]

    @property
    def target_team_total(self) -> float:
        return self.team_totals.get(self.target_team, 0.0)

    @property
    def target_team_rank(self) -> int:
        for team, points, rank in self.standings:
            if team == self.target_team:
                return rank
        return 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "meet_name": self.meet_name,
            "target_team": self.target_team,
            "target_team_total": self.target_team_total,
            "target_team_rank": self.target_team_rank,
            "standings": [
                {"rank": rank, "team": team, "points": points}
                for team, points, rank in self.standings
            ],
            "team_totals": self.team_totals,
            "event_projections": {
                name: proj.to_dict() for name, proj in self.event_projections.items()
            },
            "swing_events": [se.to_dict() for se in self.swing_events[:10]],
        }


class PointProjectionService:
    """
    Service for projecting championship meet standings.

    Uses psych sheet seed times to predict placements and calculate
    expected points for each team.
    """

    def __init__(
        self,
        meet_profile: str = "vcac_championship",
        championship_factors: ChampionshipFactors | None = None,
    ):
        """
        Initialize projection service.

        Args:
            meet_profile: Meet rules profile to use
            championship_factors: Optional factors for seed time adjustment.
                Defaults to global singleton (enabled for championship profiles).
        """
        self.rules = get_meet_profile(meet_profile)
        self.meet_profile = meet_profile
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

        # Enable championship factors for championship meet profiles
        if championship_factors is not None:
            self.factors = championship_factors
        elif "championship" in meet_profile or "state" in meet_profile:
            self.factors = ChampionshipFactors()
        else:
            self.factors = ChampionshipFactors.disabled()

    def project_standings(
        self,
        entries: list[dict[str, Any]],
        target_team: str = "Seton",
        meet_name: str = "Championship",
    ) -> StandingsProjection:
        """
        Project complete meet standings.

        Args:
            entries: List of all entries (all teams, all events)
            target_team: Team to focus on for swing events
            meet_name: Name of the meet

        Returns:
            StandingsProjection with full breakdown
        """
        # Normalize entries
        normalized = self._normalize_entries(entries)

        # Group by event
        events: dict[str, list[dict]] = defaultdict(list)
        for entry in normalized:
            events[entry["event"]].append(entry)

        # Project each event
        event_projections: dict[str, EventProjection] = {}
        team_totals: dict[str, float] = defaultdict(float)
        all_swing_events: list[SwingEvent] = []

        for event_name, event_entries in events.items():
            projection = self._project_event(event_name, event_entries)
            event_projections[event_name] = projection

            # Accumulate team totals
            for team, points in projection.team_points.items():
                team_totals[team] += points

            # Find swing events for target team
            swing = self._find_swing_events(projection, target_team)
            all_swing_events.extend(swing)

        # Sort swing events by point gain
        all_swing_events.sort(key=lambda x: -x.point_gain)

        # Calculate standings
        standings = sorted(team_totals.items(), key=lambda x: -x[1])
        standings_with_rank = [
            (team, points, rank + 1) for rank, (team, points) in enumerate(standings)
        ]

        return StandingsProjection(
            meet_name=meet_name,
            target_team=normalize_team_name(target_team),
            team_totals=dict(team_totals),
            standings=standings_with_rank,
            event_projections=event_projections,
            swing_events=all_swing_events[:10],
        )

    def project_event(
        self,
        event_name: str,
        entries: list[dict[str, Any]],
    ) -> EventProjection:
        """Project a single event."""
        normalized = self._normalize_entries(entries)
        return self._project_event(event_name, normalized)

    def _normalize_entries(self, entries: list[dict]) -> list[dict]:
        """
        Normalize entry data using centralized entry schema.

        Handles all known column name variations (swimmer/swimmer_name,
        team/team_code, time/seed_time, etc.)
        """
        from swim_ai_reflex.backend.services.shared.entry_schema import (
            normalize_entry_dict,
        )

        normalized = []
        for entry in entries:
            norm = normalize_entry_dict(entry)
            # Map to internal field names used by this service
            normalized.append(
                {
                    "swimmer": norm["swimmer"],
                    "team": norm.get("team_name") or norm["team"],  # Use display name
                    "event": norm["event"],
                    "seed_time": norm["time"],
                    "grade": norm.get("grade", 12),
                    "is_diving": norm.get("is_diver", False),
                    "dive_score": entry.get("dive_score"),  # Pass through
                }
            )
        return normalized

    def _project_event(
        self,
        event_name: str,
        entries: list[dict],
    ) -> EventProjection:
        """Project results for a single event."""
        is_relay = is_relay_event(event_name)
        is_diving = is_diving_event(event_name)

        # Get points table
        points_table = (
            self.rules.relay_points if is_relay else self.rules.individual_points
        )

        # Get max scorers per team
        max_scorers = (
            self.rules.max_scorers_per_team_relay
            if is_relay
            else self.rules.max_scorers_per_team_individual
        )

        # Sort entries by championship-adjusted time (or dive score for diving)
        if is_diving:
            sorted_entries = sorted(
                entries,
                key=lambda e: -(e.get("dive_score") or 0),
            )
        else:
            sorted_entries = sorted(
                entries,
                key=lambda e: adjust_time(
                    e.get("seed_time") or float("inf"),
                    event_name,
                    self.factors,
                ),
            )

        # Assign places and points
        projections = []
        team_scorer_count: dict[str, int] = defaultdict(int)

        for seed_rank, entry in enumerate(sorted_entries, 1):
            team = entry["team"]

            # Check if team can still score
            is_scoring = team_scorer_count[team] < max_scorers
            if is_scoring:
                team_scorer_count[team] += 1

            # Calculate predicted place (based on scoring position, not seed)
            predicted_place = seed_rank

            # Calculate points
            points = 0.0
            if is_scoring and predicted_place <= len(points_table):
                points = points_table[predicted_place - 1]

            projections.append(
                SwimmerProjection(
                    swimmer=entry["swimmer"],
                    team=team,
                    event=event_name,
                    seed_time=entry.get("seed_time") or 0.0,
                    seed_rank=seed_rank,
                    predicted_place=predicted_place,
                    points=points,
                    is_scoring=is_scoring,
                    confidence=get_event_confidence(event_name, self.factors),
                )
            )

        event_proj = EventProjection(
            event=event_name,
            entries=projections,
        )
        event_proj.calculate_team_points()

        return event_proj

    def _find_swing_events(
        self,
        projection: EventProjection,
        target_team: str,
    ) -> list[SwingEvent]:
        """Find swing events for target team."""
        swing_events = []
        target = normalize_team_name(target_team)

        # Get points table for this event
        is_relay = is_relay_event(projection.event)
        points_table = (
            self.rules.relay_points if is_relay else self.rules.individual_points
        )

        for entry in projection.entries:
            if entry.team != target:
                continue

            if not entry.is_scoring:
                continue

            current_place = entry.predicted_place
            current_points = entry.points

            if current_place <= 1:
                continue  # Already first

            # Check improvement potential
            target_place = current_place - 1
            if target_place <= len(points_table):
                potential_points = points_table[target_place - 1]
            else:
                potential_points = 0.0

            point_gain = potential_points - current_points

            # Only include significant gains
            if point_gain >= 2:
                # Calculate time gap to next swimmer
                prev_entry = projection.entries[target_place - 1]
                time_gap = entry.seed_time - prev_entry.seed_time

                swing_events.append(
                    SwingEvent(
                        event=projection.event,
                        swimmer=entry.swimmer,
                        team=entry.team,
                        current_place=current_place,
                        target_place=target_place,
                        current_points=current_points,
                        potential_points=potential_points,
                        point_gain=point_gain,
                        time_gap=time_gap,
                    )
                )

        return swing_events


# Convenience function
def project_standings(
    entries: list[dict[str, Any]],
    target_team: str = "Seton",
    meet_profile: str = "vcac_championship",
    meet_name: str = "Championship",
) -> StandingsProjection:
    """
    Project meet standings.

    Args:
        entries: All swimmer entries
        target_team: Team to focus analysis on
        meet_profile: Rules profile to use
        meet_name: Name of the meet

    Returns:
        StandingsProjection
    """
    service = PointProjectionService(meet_profile)
    return service.project_standings(entries, target_team, meet_name)


# Singleton instance
point_projection_service = PointProjectionService()
