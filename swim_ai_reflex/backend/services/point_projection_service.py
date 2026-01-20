"""
Point Projection Service

Calculates expected team standings and individual points from psych sheet data.
Used for championship meet planning and strategy.
"""

from dataclasses import dataclass
from typing import List, Dict, Tuple
from collections import defaultdict

from swim_ai_reflex.backend.core.rules import get_meet_profile, MeetRules
from swim_ai_reflex.backend.models.championship import MeetPsychSheet
from swim_ai_reflex.backend.utils.helpers import normalize_team_name


@dataclass
class EventProjection:
    """Projection results for a single event."""

    event: str
    team_results: Dict[str, List[Dict]]  # team -> list of swimmer results

    def get_team_points(self, team: str) -> int:
        """Get total points scored by a team in this event."""
        team_norm = normalize_team_name(team)
        if team_norm in self.team_results:
            return sum(r["points"] for r in self.team_results[team_norm])
        return 0


@dataclass
class MeetProjection:
    """Complete meet projection with standings and analysis."""

    meet_name: str
    team_totals: Dict[str, float]  # team -> total points
    standings: List[Tuple[str, float]]  # [(team, points), ...] sorted by points desc
    event_projections: Dict[str, EventProjection]  # event -> projection
    swing_events: List[Dict]  # opportunities for improvement
    target_team: str
    target_team_total: float


class PointProjectionEngine:
    """
    Calculate expected points from psych sheet data.

    Uses seed times/ranks to predict placements and applies
    meet-specific scoring rules to calculate expected points.
    """

    def __init__(self, meet_profile: str = "vcac_championship"):
        """
        Initialize with a meet profile.

        Args:
            meet_profile: Name of meet profile (e.g., "vcac_championship", "visaa_state")
        """
        self.rules: MeetRules = get_meet_profile(meet_profile)
        self.meet_profile = meet_profile

    def project_event_points(
        self, psych: MeetPsychSheet, event: str
    ) -> EventProjection:
        """
        Project points for a single event.

        Args:
            psych: Meet psych sheet with all entries
            event: Event name (e.g., "Boys 50 Free", "Girls Diving")

        Returns:
            EventProjection with per-team results

        Note:
            For diving events, seed_time contains dive scores (typically 6-dive or 11-dive).
            Higher scores = better placement (opposite of swimming times).
        """
        entries = psych.get_event_entries(event)
        is_relay = "relay" in event.lower()
        _is_diving = "diving" in event.lower() or "dive" in event.lower()

        # Get appropriate scoring table
        points_table = (
            self.rules.relay_points if is_relay else self.rules.individual_points
        )
        max_scorers = (
            self.rules.max_scorers_per_team_relay
            if is_relay
            else self.rules.max_scorers_per_team_individual
        )

        results: Dict[str, List[Dict]] = defaultdict(list)
        team_scorer_count: Dict[str, int] = defaultdict(int)

        for place, entry in enumerate(entries, 1):
            team = normalize_team_name(entry.team)

            # Determine points based on placement and scorer limits
            if team_scorer_count[team] < max_scorers:
                points = points_table[place - 1] if place <= len(points_table) else 0
                scoring = points > 0
                team_scorer_count[team] += 1
            else:
                points = 0
                scoring = False  # Exhibition - exceeds scorer limit

            results[team].append(
                {
                    "swimmer": entry.swimmer_name,
                    "seed_time": entry.seed_time,
                    "formatted_time": entry.formatted_time,
                    "predicted_place": place,
                    "points": points,
                    "scoring": scoring,
                    "is_exhibition": not scoring and place <= len(points_table),
                }
            )

        return EventProjection(event=event, team_results=dict(results))

    def project_full_meet(
        self, psych: MeetPsychSheet, target_team: str = "Seton"
    ) -> MeetProjection:
        """
        Project points for entire meet.

        Args:
            psych: Complete psych sheet
            target_team: Team to focus analysis on

        Returns:
            MeetProjection with standings, event breakdowns, and swing events
        """
        event_projections: Dict[str, EventProjection] = {}
        team_totals: Dict[str, float] = defaultdict(float)

        # Get all events
        all_events = psych.get_all_events()

        # Project each event
        for event in all_events:
            proj = self.project_event_points(psych, event)
            event_projections[event] = proj

            # Accumulate team totals
            for team, swimmers in proj.team_results.items():
                team_totals[team] += sum(s["points"] for s in swimmers)

        # Sort standings
        standings = sorted(team_totals.items(), key=lambda x: -x[1])

        # Identify swing events for target team
        target_norm = normalize_team_name(target_team)
        swing_events = self._identify_swing_events(event_projections, target_norm)

        return MeetProjection(
            meet_name=psych.meet_name,
            team_totals=dict(team_totals),
            standings=standings,
            event_projections=event_projections,
            swing_events=swing_events,
            target_team=target_norm,
            target_team_total=team_totals.get(target_norm, 0),
        )

    def _identify_swing_events(
        self, projections: Dict[str, EventProjection], target_team: str
    ) -> List[Dict]:
        """
        Find events where small improvements yield significant point gains.

        A "swing event" is where:
        - Target team swimmer is close to better placement
        - Moving up 1-2 places gains 4+ points

        Args:
            projections: Event projections from project_full_meet
            target_team: Normalized target team name

        Returns:
            List of swing event opportunities, sorted by potential gain
        """
        swing_events = []

        for event_name, projection in projections.items():
            if target_team not in projection.team_results:
                continue

            # Get scoring table for this event
            is_relay = "relay" in event_name.lower()
            points_table = (
                self.rules.relay_points if is_relay else self.rules.individual_points
            )

            for swimmer in projection.team_results[target_team]:
                place = swimmer["predicted_place"]
                current_points = swimmer["points"]

                # Skip if already scoring maximum (1st place)
                if place <= 1:
                    continue

                # Check potential points at 1 place better
                better_place = place - 1
                potential_points = (
                    points_table[better_place - 1]
                    if better_place <= len(points_table)
                    else 0
                )
                point_gain = potential_points - current_points

                # Only include if gain is significant (4+ points)
                if point_gain >= 4:
                    swing_events.append(
                        {
                            "event": event_name,
                            "swimmer": swimmer["swimmer"],
                            "current_place": place,
                            "target_place": better_place,
                            "current_points": current_points,
                            "potential_points": potential_points,
                            "point_gain": point_gain,
                            "current_time": swimmer["formatted_time"],
                            "priority": "high" if point_gain >= 6 else "medium",
                        }
                    )

        # Sort by point gain (highest first)
        return sorted(swing_events, key=lambda x: -x["point_gain"])

    def get_head_to_head(
        self, projection: MeetProjection, team1: str, team2: str
    ) -> Dict:
        """
        Analyze head-to-head matchup between two teams.

        Args:
            projection: Full meet projection
            team1, team2: Team names to compare

        Returns:
            Comparison with events won/lost, point differential, etc.
        """
        t1 = normalize_team_name(team1)
        t2 = normalize_team_name(team2)

        events_won = {t1: 0, t2: 0}
        point_diff_by_event = []

        for event_name, event_proj in projection.event_projections.items():
            t1_points = event_proj.get_team_points(t1)
            t2_points = event_proj.get_team_points(t2)

            if t1_points > t2_points:
                events_won[t1] += 1
            elif t2_points > t1_points:
                events_won[t2] += 1

            point_diff_by_event.append(
                {
                    "event": event_name,
                    f"{t1}_points": t1_points,
                    f"{t2}_points": t2_points,
                    "differential": t1_points - t2_points,
                }
            )

        return {
            "team1": t1,
            "team2": t2,
            "team1_total": projection.team_totals.get(t1, 0),
            "team2_total": projection.team_totals.get(t2, 0),
            "overall_differential": projection.team_totals.get(t1, 0)
            - projection.team_totals.get(t2, 0),
            "events_won": events_won,
            "event_breakdown": point_diff_by_event,
        }

    def summarize_team(self, projection: MeetProjection, team: str) -> Dict:
        """
        Get detailed summary for a single team.

        Args:
            projection: Full meet projection
            team: Team name

        Returns:
            Summary with top scorers, best events, etc.
        """
        team_norm = normalize_team_name(team)

        # Collect all scoring entries for this team
        all_scorers = []
        event_points = []

        for event_name, event_proj in projection.event_projections.items():
            if team_norm not in event_proj.team_results:
                continue

            team_event_points = 0
            for swimmer in event_proj.team_results[team_norm]:
                if swimmer["scoring"]:
                    all_scorers.append(
                        {
                            "swimmer": swimmer["swimmer"],
                            "event": event_name,
                            "place": swimmer["predicted_place"],
                            "points": swimmer["points"],
                        }
                    )
                    team_event_points += swimmer["points"]

            event_points.append({"event": event_name, "points": team_event_points})

        # Sort scorers by points
        top_scorers = sorted(all_scorers, key=lambda x: -x["points"])[:10]
        best_events = sorted(event_points, key=lambda x: -x["points"])[:5]

        return {
            "team": team_norm,
            "total_points": projection.team_totals.get(team_norm, 0),
            "standing": next(
                (
                    i + 1
                    for i, (t, _) in enumerate(projection.standings)
                    if t == team_norm
                ),
                None,
            ),
            "top_scorers": top_scorers,
            "best_events": best_events,
            "total_scoring_entries": len(all_scorers),
        }
