"""
Live Meet Tracker

Real-time tracking of championship meet results.
Updates standings and projections as results come in.

Usage:
    tracker = LiveMeetTracker(meet_profile="vcac_championship")
    tracker.set_psych_sheet(psych_data)  # Initial projections

    # During meet:
    tracker.record_result("Boys 50 Free", 1, "John Smith", "SST", 22.45)
    tracker.record_result("Boys 50 Free", 2, "Mike Jones", "Trinity", 22.89)

    # Get updates:
    standings = tracker.get_current_standings()
    clinch = tracker.get_clinch_scenarios("SST")
    swing = tracker.get_swing_remaining()
"""

import logging
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime

from swim_ai_reflex.backend.core.rules import get_meet_profile
from swim_ai_reflex.backend.services.point_projection_service import (
    MeetProjection,
    PointProjectionEngine,
)

logger = logging.getLogger(__name__)


@dataclass
class RecordedResult:
    """A single recorded result from the meet."""

    event: str
    place: int
    swimmer: str
    team: str
    time: float  # In seconds, or score for diving
    points: float
    timestamp: datetime = field(default_factory=datetime.now)
    is_official: bool = True


@dataclass
class LiveStandings:
    """Current standings with actual + projected points."""

    team_totals: dict[str, float]  # Actual points scored
    projected_remaining: dict[str, float]  # Expected from remaining events
    combined_totals: dict[str, float]  # Actual + projected
    events_completed: int
    events_remaining: int


@dataclass
class ClinchScenario:
    """What's needed to clinch a specific position."""

    target_position: int
    current_position: int
    points_ahead: float
    points_behind: float
    can_clinch: bool
    clinch_requirements: list[str]  # e.g., "Win 200 Free Relay"
    can_be_caught: bool
    danger_scenarios: list[str]  # What could cause us to drop


class LiveMeetTracker:
    """
    Track live results during a championship meet.

    Combines actual results with projections for remaining events
    to provide real-time standings and coaching insights.
    """

    # Standard championship event order (VCAC/VISAA)
    EVENT_ORDER = [
        "Girls 200 Medley Relay",
        "Boys 200 Medley Relay",
        "Girls 200 Free",
        "Boys 200 Free",
        "Girls 200 IM",
        "Boys 200 IM",
        "Girls 50 Free",
        "Boys 50 Free",
        "Girls Diving",
        "Boys Diving",
        "Girls 100 Fly",
        "Boys 100 Fly",
        "Girls 100 Free",
        "Boys 100 Free",
        "Girls 500 Free",
        "Boys 500 Free",
        "Girls 200 Free Relay",
        "Boys 200 Free Relay",
        "Girls 100 Back",
        "Boys 100 Back",
        "Girls 100 Breast",
        "Boys 100 Breast",
        "Girls 400 Free Relay",
        "Boys 400 Free Relay",
    ]

    def __init__(self, meet_profile: str = "vcac_championship"):
        self.meet_profile = meet_profile
        self.rules = get_meet_profile(meet_profile)
        self.projection_engine = PointProjectionEngine(meet_profile)

        # State
        self.results: dict[str, list[RecordedResult]] = defaultdict(list)
        self.teams: set[str] = set()
        self.psych_projection: MeetProjection | None = None
        self.completed_events: set[str] = set()
        self._meet_name: str = "Championship"

    def set_psych_sheet(
        self,
        entries: list[dict],
        target_team: str = "SST",
        meet_name: str = "Championship",
    ) -> None:
        """
        Initialize with psych sheet for projections.

        Args:
            entries: List of entry dicts with swimmer, team, event, seed_time
            target_team: Team to focus analysis on
            meet_name: Name of the meet
        """
        from swim_ai_reflex.backend.models.championship import (
            MeetPsychSheet,
            PsychSheetEntry,
        )

        self._meet_name = meet_name

        # Extract teams
        self.teams = set(e.get("team", "") for e in entries)

        # Convert dicts to PsychSheetEntry objects
        psych_entries = []
        for e in entries:
            entry = PsychSheetEntry(
                swimmer_name=e.get("swimmer", e.get("swimmer_name", "Unknown")),
                team=e.get("team", ""),
                event=e.get("event", ""),
                seed_time=e.get("seed_time", float("inf")),
                grade=e.get("grade", 12),
                gender=e.get("gender", "M"),
                is_diving=e.get("is_diving", False),
                dive_score=e.get("dive_score"),
            )
            psych_entries.append(entry)

        # Build psych sheet model
        psych = MeetPsychSheet(
            meet_name=meet_name,
            meet_date=datetime.now().date(),
            teams=list(self.teams),
            entries=psych_entries,
        )

        # Get initial projection
        self.psych_projection = self.projection_engine.project_full_meet(
            psych, target_team
        )

        logger.info(f"Initialized tracker for {meet_name} with {len(entries)} entries")

    def record_result(
        self,
        event: str,
        place: int,
        swimmer: str,
        team: str,
        time: float,
        is_official: bool = True,
    ) -> RecordedResult:
        """
        Record a single result.

        Args:
            event: Event name (e.g., "Boys 50 Free")
            place: Finishing place (1-16 typically)
            swimmer: Swimmer name
            team: Team code/name
            time: Time in seconds or diving score
            is_official: Whether this is an official (scoring) result

        Returns:
            The recorded result with calculated points
        """
        # Calculate points for this place
        points = self._get_points_for_place(event, place)

        result = RecordedResult(
            event=event,
            place=place,
            swimmer=swimmer,
            team=team,
            time=time,
            points=points,
            is_official=is_official,
        )

        self.results[event].append(result)
        self.teams.add(team)

        # Check if event is complete (all scoring places recorded)
        if self._is_event_complete(event):
            self.completed_events.add(event)
            logger.info(f"Event complete: {event}")

        logger.debug(
            f"Recorded: {swimmer} ({team}) {place}th in {event} = {points} pts"
        )
        return result

    def record_event_results(
        self, event: str, results: list[dict]
    ) -> list[RecordedResult]:
        """
        Record all results for an event at once.

        Args:
            event: Event name
            results: List of dicts with place, swimmer, team, time

        Returns:
            List of recorded results
        """
        recorded = []
        for r in results:
            result = self.record_result(
                event=event,
                place=r["place"],
                swimmer=r["swimmer"],
                team=r["team"],
                time=r.get("time", 0),
                is_official=r.get("is_official", True),
            )
            recorded.append(result)

        self.completed_events.add(event)
        return recorded

    def get_current_standings(self) -> LiveStandings:
        """
        Get current standings combining actual and projected points.

        Returns:
            LiveStandings with team totals, projections, and event counts
        """
        # Actual points from recorded results
        actual = defaultdict(float)
        for event, event_results in self.results.items():
            for r in event_results:
                if r.is_official:
                    actual[r.team] += r.points

        # Projected points for remaining events
        projected = defaultdict(float)
        if self.psych_projection:
            for event, event_proj in self.psych_projection.event_projections.items():
                if event not in self.completed_events:
                    for team in self.teams:
                        projected[team] += event_proj.get_team_points(team)

        # Combined
        combined = {}
        all_teams = set(actual.keys()) | set(projected.keys()) | self.teams
        for team in all_teams:
            combined[team] = actual.get(team, 0) + projected.get(team, 0)

        return LiveStandings(
            team_totals=dict(actual),
            projected_remaining=dict(projected),
            combined_totals=combined,
            events_completed=len(self.completed_events),
            events_remaining=len(self.EVENT_ORDER) - len(self.completed_events),
        )

    def get_remaining_points(self) -> dict[str, dict]:
        """
        Get points still available in remaining events.

        Returns:
            Dict mapping team -> {max_possible, projected, events: [...]}
        """
        remaining = {}

        for team in self.teams:
            team_events = []
            total_projected = 0.0
            total_max = 0.0

            for event in self.EVENT_ORDER:
                if event not in self.completed_events:
                    # Get projected points for this team in this event
                    proj_pts = 0.0
                    if (
                        self.psych_projection
                        and event in self.psych_projection.event_projections
                    ):
                        proj_pts = self.psych_projection.event_projections[
                            event
                        ].get_team_points(team)

                    # Max possible (4 scoring positions)
                    max_pts = self._get_max_event_points(event)

                    if proj_pts > 0 or team in self.teams:
                        team_events.append(
                            {
                                "event": event,
                                "projected": proj_pts,
                                "max_possible": max_pts,
                            }
                        )
                        total_projected += proj_pts
                        total_max += max_pts

            remaining[team] = {
                "projected": total_projected,
                "max_possible": total_max,
                "events": team_events,
            }

        return remaining

    def get_clinch_scenarios(self, target_team: str) -> list[ClinchScenario]:
        """
        Determine what's needed to clinch each position.

        Args:
            target_team: Team to analyze

        Returns:
            List of ClinchScenario for each attainable position
        """
        standings = self.get_current_standings()
        remaining = self.get_remaining_points()

        # Sort teams by combined total
        sorted_teams = sorted(
            standings.combined_totals.items(), key=lambda x: x[1], reverse=True
        )

        # Find target team's position
        target_total = standings.combined_totals.get(target_team, 0)
        target_remaining = remaining.get(target_team, {}).get("max_possible", 0)
        current_pos = 1
        for i, (team, total) in enumerate(sorted_teams):
            if team == target_team:
                current_pos = i + 1
                break

        scenarios = []

        # Analyze each position
        for pos, (team, total) in enumerate(sorted_teams, 1):
            if team == target_team:
                # Our current position - can we be caught?
                teams_behind = sorted_teams[pos:]
                danger = []
                for behind_team, behind_total in teams_behind:
                    behind_max = behind_total + remaining.get(behind_team, {}).get(
                        "max_possible", 0
                    )
                    if behind_max > target_total:
                        danger.append(f"{behind_team} can still catch us")

                scenarios.append(
                    ClinchScenario(
                        target_position=pos,
                        current_position=current_pos,
                        points_ahead=0,
                        points_behind=0,
                        can_clinch=len(danger) == 0,
                        clinch_requirements=["Hold current position"]
                        if len(danger) == 0
                        else [],
                        can_be_caught=len(danger) > 0,
                        danger_scenarios=danger,
                    )
                )
            else:
                # Can we catch this position?
                points_behind = total - target_total
                max_we_can_score = target_remaining

                can_clinch = max_we_can_score > points_behind
                requirements = []

                if can_clinch and points_behind > 0:
                    # What do we need to do?
                    remaining_events = [
                        e for e in self.EVENT_ORDER if e not in self.completed_events
                    ]
                    # Find high-point opportunities
                    for event in remaining_events[:5]:  # Look at next 5 events
                        if "Relay" in event:
                            requirements.append(f"Win {event} (+32 potential)")

                scenarios.append(
                    ClinchScenario(
                        target_position=pos,
                        current_position=current_pos,
                        points_ahead=-points_behind if points_behind < 0 else 0,
                        points_behind=points_behind if points_behind > 0 else 0,
                        can_clinch=can_clinch,
                        clinch_requirements=requirements,
                        can_be_caught=False,
                        danger_scenarios=[],
                    )
                )

        return scenarios

    def get_swing_remaining(self, target_team: str = "SST") -> list[dict]:
        """
        Find remaining events where we can gain ground.

        Returns:
            List of swing events with potential gains
        """
        remaining_events = [
            e for e in self.EVENT_ORDER if e not in self.completed_events
        ]
        swing = []

        for event in remaining_events:
            if (
                not self.psych_projection
                or event not in self.psych_projection.event_projections
            ):
                continue

            event_proj = self.psych_projection.event_projections[event]
            our_pts = event_proj.get_team_points(target_team)

            # Find max competitor points
            max_other = 0
            top_competitor = ""
            for team in self.teams:
                if team != target_team:
                    other_pts = event_proj.get_team_points(team)
                    if other_pts > max_other:
                        max_other = other_pts
                        top_competitor = team

            # Calculate potential swing
            potential_gain = self._get_max_event_points(event) - our_pts

            if potential_gain > 10:  # Significant swing potential
                swing.append(
                    {
                        "event": event,
                        "projected_points": our_pts,
                        "max_possible": self._get_max_event_points(event),
                        "potential_gain": potential_gain,
                        "top_competitor": top_competitor,
                        "competitor_projected": max_other,
                        "is_relay": "Relay" in event,
                    }
                )

        # Sort by potential gain
        swing.sort(key=lambda x: x["potential_gain"], reverse=True)
        return swing

    def get_event_status(self) -> dict[str, str]:
        """
        Get status of all events.

        Returns:
            Dict mapping event -> status ("completed", "in_progress", "upcoming")
        """
        status = {}
        for event in self.EVENT_ORDER:
            if event in self.completed_events:
                status[event] = "completed"
            elif event in self.results and len(self.results[event]) > 0:
                status[event] = "in_progress"
            else:
                status[event] = "upcoming"
        return status

    def generate_coach_summary(self, target_team: str = "SST") -> str:
        """
        Generate a text summary for coaches.

        Returns:
            Formatted text summary of current standings and recommendations
        """
        standings = self.get_current_standings()
        clinch = self.get_clinch_scenarios(target_team)
        swing = self.get_swing_remaining(target_team)

        lines = [
            f"=== {self._meet_name} Live Summary ===",
            f"Events: {standings.events_completed}/{len(self.EVENT_ORDER)} complete",
            "",
            "Current Standings (Actual + Projected):",
        ]

        # Standings
        sorted_standings = sorted(
            standings.combined_totals.items(), key=lambda x: x[1], reverse=True
        )
        for i, (team, total) in enumerate(sorted_standings, 1):
            actual = standings.team_totals.get(team, 0)
            marker = " <--" if team == target_team else ""
            lines.append(
                f"  {i}. {team}: {total:.0f} pts ({actual:.0f} actual){marker}"
            )

        # Clinch info
        lines.append("")
        lines.append(f"Clinch Analysis for {target_team}:")
        for scenario in clinch[:3]:
            if scenario.can_clinch:
                lines.append(
                    f"  Position {scenario.target_position}: CLINCHED"
                    if scenario.target_position == scenario.current_position
                    else f"  Position {scenario.target_position}: Attainable"
                )
            elif scenario.points_behind > 0:
                lines.append(
                    f"  Position {scenario.target_position}: {scenario.points_behind:.0f} pts behind"
                )

        # Swing events
        if swing:
            lines.append("")
            lines.append("Key Remaining Events:")
            for s in swing[:3]:
                lines.append(f"  {s['event']}: +{s['potential_gain']:.0f} potential")

        return "\n".join(lines)

    # -------------------------------------------------------------------------
    # Private Methods
    # -------------------------------------------------------------------------

    def _get_points_for_place(self, event: str, place: int) -> float:
        """Get points for a specific place in an event."""
        is_relay = "Relay" in event

        if is_relay:
            points_table = self.rules.relay_points
        else:
            points_table = self.rules.individual_points

        if place <= 0 or place > len(points_table):
            return 0.0

        return points_table[place - 1]

    def _get_max_event_points(self, event: str) -> float:
        """Get maximum points possible in an event (top 4 scorers)."""
        is_relay = "Relay" in event

        if is_relay:
            # One relay team = just 1st place points
            return self.rules.relay_points[0] if self.rules.relay_points else 0
        else:
            # Top 4 individual scorers
            return (
                sum(self.rules.individual_points[:4])
                if len(self.rules.individual_points) >= 4
                else 0
            )

    def _is_event_complete(self, event: str) -> bool:
        """Check if all scoring positions have been recorded."""
        event_results = self.results.get(event, [])

        # For relays, usually 8 teams = 8 relays
        if "Relay" in event:
            return len(event_results) >= 6  # Most places that score

        # For individuals, typically top 12-16 score
        return len(event_results) >= 12


# Factory function
def create_live_tracker(meet_profile: str = "vcac_championship") -> LiveMeetTracker:
    """Create a new live meet tracker."""
    return LiveMeetTracker(meet_profile=meet_profile)


__all__ = [
    "LiveMeetTracker",
    "RecordedResult",
    "LiveStandings",
    "ClinchScenario",
    "create_live_tracker",
]
