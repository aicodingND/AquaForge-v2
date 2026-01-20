"""
Dual Meet Scoring Service

Handles scoring for head-to-head dual meets.
Key rule: All 232 points MUST be distributed (8 events × 29 points each).
"""

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import pandas as pd

from swim_ai_reflex.backend.services.shared.normalization import (
    is_relay_event,
    normalize_event_name,
    normalize_time,
)

logger = logging.getLogger(__name__)


# Scoring constants
INDIVIDUAL_POINTS = [8, 6, 5, 4, 3, 2, 1]  # Top 7 places
RELAY_POINTS = [10, 5, 3]  # Top 3 relays per team
POINTS_PER_INDIVIDUAL_EVENT = sum(INDIVIDUAL_POINTS)  # 29
POINTS_PER_RELAY_EVENT = sum(RELAY_POINTS)  # 18 (but distributed differently)
STANDARD_EVENTS = 8  # Individual events
TOTAL_MEET_POINTS = 232  # Standard dual meet total


@dataclass
class ScoredEntry:
    """A scored swimmer entry."""

    swimmer: str
    team: str
    event: str
    time: float
    place: int
    points: float
    is_exhibition: bool = False
    grade: Optional[int] = None


@dataclass
class EventResult:
    """Result for a single event."""

    event: str
    entries: List[ScoredEntry]
    our_points: float = 0.0
    opponent_points: float = 0.0

    @property
    def total_points(self) -> float:
        return self.our_points + self.opponent_points


@dataclass
class DualMeetResult:
    """Complete dual meet result."""

    our_team: str
    opponent_team: str
    our_score: float
    opponent_score: float
    event_results: List[EventResult]
    winner: str = ""

    def __post_init__(self):
        if self.our_score > self.opponent_score:
            self.winner = self.our_team
        elif self.opponent_score > self.our_score:
            self.winner = self.opponent_team
        else:
            self.winner = "Tie"

    @property
    def total_points(self) -> float:
        return self.our_score + self.opponent_score

    def is_valid(self, expected_total: int = TOTAL_MEET_POINTS) -> bool:
        """Check if total points match expected."""
        return abs(self.total_points - expected_total) < 0.01

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API response."""
        return {
            "our_team": self.our_team,
            "opponent_team": self.opponent_team,
            "our_score": self.our_score,
            "opponent_score": self.opponent_score,
            "winner": self.winner,
            "total_points": self.total_points,
            "is_valid": self.is_valid(),
            "event_breakdown": [
                {
                    "event": er.event,
                    "our_points": er.our_points,
                    "opponent_points": er.opponent_points,
                    "entries": [
                        {
                            "place": e.place,
                            "swimmer": e.swimmer,
                            "team": e.team,
                            "time": e.time,
                            "points": e.points,
                            "exhibition": e.is_exhibition,
                        }
                        for e in er.entries
                    ],
                }
                for er in self.event_results
            ],
        }


class DualMeetScoringService:
    """
    Service for scoring dual meets.

    Implements VISAA dual meet scoring rules:
    - Individual: Top 7 score [8, 6, 5, 4, 3, 2, 1]
    - Relays: Top 3 score [10, 5, 3]
    - Exhibition swimmers displace but don't score
    - Total must equal 232 points
    """

    def __init__(
        self,
        individual_points: List[int] = None,
        relay_points: List[int] = None,
        min_scoring_grade: int = 9,
    ):
        """
        Initialize scoring service.

        Args:
            individual_points: Points for individual event places
            relay_points: Points for relay places
            min_scoring_grade: Minimum grade for scoring eligibility
        """
        self.individual_points = individual_points or INDIVIDUAL_POINTS
        self.relay_points = relay_points or RELAY_POINTS
        self.min_scoring_grade = min_scoring_grade
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    def score_event(
        self,
        our_entries: List[Dict[str, Any]],
        opponent_entries: List[Dict[str, Any]],
        event_name: str,
        our_team: str = "Seton",
        opponent_team: str = "Opponent",
    ) -> EventResult:
        """
        Score a single event.

        Args:
            our_entries: Our team's entries for this event
            opponent_entries: Opponent's entries for this event
            event_name: Name of the event
            our_team: Our team name
            opponent_team: Opponent team name

        Returns:
            EventResult with scored entries
        """
        is_relay = is_relay_event(event_name)
        points_table = self.relay_points if is_relay else self.individual_points

        # Combine and sort entries by time
        all_entries = []

        for entry in our_entries:
            all_entries.append(
                {
                    **entry,
                    "team": our_team,
                    "is_ours": True,
                }
            )

        for entry in opponent_entries:
            all_entries.append(
                {
                    **entry,
                    "team": opponent_team,
                    "is_ours": False,
                }
            )

        # Sort by time (ascending)
        all_entries.sort(
            key=lambda e: normalize_time(e.get("time", float("inf"))) or float("inf")
        )

        # Score entries
        scored_entries = []
        our_points = 0.0
        opponent_points = 0.0
        scoring_place = 0  # Place for scoring purposes

        for place, entry in enumerate(all_entries, 1):
            time_val = normalize_time(entry.get("time"))
            grade = entry.get("grade")

            # Check exhibition status
            is_exhibition = False
            if grade is not None:
                try:
                    if int(grade) < self.min_scoring_grade:
                        is_exhibition = True
                except (ValueError, TypeError):
                    pass

            # Also check explicit exhibition flag
            if entry.get("is_exhibition") or entry.get("exhibition"):
                is_exhibition = True

            # Calculate points
            points = 0.0
            if not is_exhibition:
                scoring_place += 1
                if scoring_place <= len(points_table):
                    points = points_table[scoring_place - 1]

            # Add to team totals
            if entry["is_ours"]:
                our_points += points
            else:
                opponent_points += points

            scored_entries.append(
                ScoredEntry(
                    swimmer=entry.get("swimmer", "Unknown"),
                    team=entry["team"],
                    event=event_name,
                    time=time_val or 0.0,
                    place=place,
                    points=points,
                    is_exhibition=is_exhibition,
                    grade=grade,
                )
            )

        return EventResult(
            event=event_name,
            entries=scored_entries,
            our_points=our_points,
            opponent_points=opponent_points,
        )

    def score_meet(
        self,
        our_roster: pd.DataFrame,
        opponent_roster: pd.DataFrame,
        our_team: str = "Seton",
        opponent_team: str = "Opponent",
    ) -> DualMeetResult:
        """
        Score a complete dual meet.

        Args:
            our_roster: DataFrame with our team's entries
            opponent_roster: DataFrame with opponent's entries
            our_team: Our team name
            opponent_team: Opponent team name

        Returns:
            DualMeetResult with full scoring
        """
        # Normalize event names
        our_roster = our_roster.copy()
        opponent_roster = opponent_roster.copy()

        if "event" in our_roster.columns:
            our_roster["event"] = our_roster["event"].apply(normalize_event_name)
        if "event" in opponent_roster.columns:
            opponent_roster["event"] = opponent_roster["event"].apply(
                normalize_event_name
            )

        # Get all events
        events = set()
        if "event" in our_roster.columns:
            events.update(our_roster["event"].unique())
        if "event" in opponent_roster.columns:
            events.update(opponent_roster["event"].unique())

        # Score each event
        event_results = []
        total_our_points = 0.0
        total_opponent_points = 0.0

        for event in sorted(events):
            our_entries = (
                our_roster[our_roster["event"] == event].to_dict("records")
                if "event" in our_roster.columns
                else []
            )
            opponent_entries = (
                opponent_roster[opponent_roster["event"] == event].to_dict("records")
                if "event" in opponent_roster.columns
                else []
            )

            result = self.score_event(
                our_entries=our_entries,
                opponent_entries=opponent_entries,
                event_name=event,
                our_team=our_team,
                opponent_team=opponent_team,
            )

            event_results.append(result)
            total_our_points += result.our_points
            total_opponent_points += result.opponent_points

        meet_result = DualMeetResult(
            our_team=our_team,
            opponent_team=opponent_team,
            our_score=total_our_points,
            opponent_score=total_opponent_points,
            event_results=event_results,
        )

        # Validate total
        if not meet_result.is_valid():
            self.logger.warning(
                f"Meet total {meet_result.total_points} != expected {TOTAL_MEET_POINTS}"
            )

        return meet_result

    def score_lineup(
        self,
        combined_lineup: pd.DataFrame,
        our_team: str = "Seton",
    ) -> DualMeetResult:
        """
        Score a combined lineup DataFrame.

        Args:
            combined_lineup: DataFrame with both teams' entries
            our_team: Name of our team

        Returns:
            DualMeetResult
        """
        # Split by team
        if "team" not in combined_lineup.columns:
            raise ValueError("Lineup must have 'team' column")

        our_roster = combined_lineup[
            combined_lineup["team"].str.lower() == our_team.lower()
        ].copy()

        opponent_roster = combined_lineup[
            combined_lineup["team"].str.lower() != our_team.lower()
        ].copy()

        # Get opponent team name
        opponent_teams = opponent_roster["team"].unique()
        opponent_team = opponent_teams[0] if len(opponent_teams) > 0 else "Opponent"

        return self.score_meet(
            our_roster=our_roster,
            opponent_roster=opponent_roster,
            our_team=our_team,
            opponent_team=opponent_team,
        )


# Singleton instance
dual_meet_scoring_service = DualMeetScoringService()
