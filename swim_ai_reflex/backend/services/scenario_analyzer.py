"""
Scenario Analyzer

What-if analysis for championship line-up decisions.
Compare alternative configurations before committing to a line-up.

Usage:
    analyzer = ScenarioAnalyzer(psych_sheet)

    # Compare two line-up scenarios
    comparison = analyzer.compare_scenarios(
        base_lineup=current_assignments,
        alternative=proposed_changes
    )

    # Find best swap for a swimmer
    swaps = analyzer.find_best_swap(
        swimmer="John Smith",
        from_event="Boys 100 Free"
    )
"""

import logging
from dataclasses import dataclass, field

from swim_ai_reflex.backend.core.rules import get_meet_profile
from swim_ai_reflex.backend.models.championship import MeetPsychSheet
from swim_ai_reflex.backend.services.point_projection_service import (
    PointProjectionEngine,
)

logger = logging.getLogger(__name__)


@dataclass
class SwapOption:
    """A potential event swap for a swimmer."""

    swimmer: str
    from_event: str
    to_event: str
    from_points: float  # Points in current event
    to_points: float  # Projected points in new event
    net_change: float  # Difference (positive = better)
    feasible: bool  # Meets constraints
    notes: list[str] = field(default_factory=list)


@dataclass
class ScenarioComparison:
    """Comparison between two line-up scenarios."""

    base_total: float
    alternative_total: float
    net_change: float
    changes_made: list[dict]
    event_impacts: dict[str, float]  # Event -> point change
    recommendation: str
    detailed_breakdown: list[str]


@dataclass
class RelayAnalysis:
    """Analysis of a relay configuration."""

    relay_event: str
    swimmers: list[str]
    projected_place: int
    projected_points: float
    alternative_configs: list[dict]  # Other possible configurations
    optimization_notes: list[str]


class ScenarioAnalyzer:
    """
    Analyze alternative line-up scenarios.

    Enables coaches to ask "what if?" questions about swimmer assignments
    before finalizing entries.
    """

    def __init__(
        self,
        psych_sheet: MeetPsychSheet,
        target_team: str = "SST",
        meet_profile: str = "vcac_championship",
    ):
        self.psych = psych_sheet
        self.target_team = target_team
        self.rules = get_meet_profile(meet_profile)
        self.projection_engine = PointProjectionEngine(meet_profile)

        # Get base projection
        self.base_projection = self.projection_engine.project_full_meet(
            psych_sheet, target_team
        )

        # Cache team entries
        self._team_entries = psych_sheet.get_team_entries(target_team)
        self._team_swimmers = set(e.swimmer_name for e in self._team_entries)

    def compare_scenarios(
        self,
        base_lineup: dict[str, list[str]],  # swimmer -> [events]
        alternative: dict[str, list[str]],
    ) -> ScenarioComparison:
        """
        Compare two line-up scenarios.

        Args:
            base_lineup: Current assignments (swimmer -> events)
            alternative: Proposed assignments

        Returns:
            ScenarioComparison with point totals and breakdown
        """
        # Calculate points for base scenario
        base_points = self._calculate_scenario_points(base_lineup)

        # Calculate points for alternative
        alt_points = self._calculate_scenario_points(alternative)

        # Find what changed
        changes = self._find_changes(base_lineup, alternative)

        # Calculate per-event impact
        event_impacts = {}
        for change in changes:
            event = change.get("event")
            if event:
                base_event_pts = self._get_event_points(event, base_lineup)
                alt_event_pts = self._get_event_points(event, alternative)
                event_impacts[event] = alt_event_pts - base_event_pts

        # Generate recommendation
        net_change = alt_points - base_points
        if net_change > 5:
            recommendation = f"RECOMMENDED: +{net_change:.1f} points"
        elif net_change > 0:
            recommendation = f"Slight improvement: +{net_change:.1f} points"
        elif net_change < -5:
            recommendation = f"NOT RECOMMENDED: {net_change:.1f} points"
        else:
            recommendation = f"Neutral change: {net_change:.1f} points"

        # Detailed breakdown
        breakdown = [
            f"Base scenario: {base_points:.1f} points",
            f"Alternative: {alt_points:.1f} points",
            f"Net change: {net_change:+.1f} points",
            "",
            "Changes:",
        ]
        for change in changes:
            breakdown.append(f"  - {change['description']}")

        return ScenarioComparison(
            base_total=base_points,
            alternative_total=alt_points,
            net_change=net_change,
            changes_made=changes,
            event_impacts=event_impacts,
            recommendation=recommendation,
            detailed_breakdown=breakdown,
        )

    def find_best_swap(
        self,
        swimmer: str,
        from_event: str,
        current_lineup: dict[str, list[str]] | None = None,
    ) -> list[SwapOption]:
        """
        Find best alternative events for a swimmer.

        Args:
            swimmer: Swimmer name
            from_event: Current event to swap from
            current_lineup: Current assignments (optional)

        Returns:
            List of swap options sorted by net gain
        """
        swaps = []

        # Get swimmer's entries from psych sheet
        swimmer_entries = self.psych.get_swimmer_entries(swimmer, self.target_team)
        current_events = [e.event for e in swimmer_entries]

        # Get points in current event
        from_points = self._get_swimmer_event_points(swimmer, from_event)

        # Find events swimmer could enter but isn't currently
        all_events = self.psych.get_individual_events()

        for event in all_events:
            if event == from_event:
                continue

            # Check if swimmer has a seed time for this event
            has_seed = any(e.event == event for e in swimmer_entries)

            # Check if swimmer can add this event (max 2 individual)
            individual_count = sum(
                1
                for e in current_events
                if "relay" not in e.lower() and e != from_event
            )
            can_add = individual_count < 2 or has_seed

            # Project points in new event
            to_points = (
                self._get_swimmer_event_points(swimmer, event) if has_seed else 0
            )

            to_points - from_points

            notes = []
            if not has_seed:
                notes.append("No seed time - would need to add entry")
                to_points = self._estimate_points_without_seed(swimmer, event)

            if not can_add:
                notes.append("Would exceed 2 individual event limit")

            swaps.append(
                SwapOption(
                    swimmer=swimmer,
                    from_event=from_event,
                    to_event=event,
                    from_points=from_points,
                    to_points=to_points,
                    net_change=to_points - from_points,
                    feasible=can_add,
                    notes=notes,
                )
            )

        # Sort by net gain (highest first), feasible options first
        swaps.sort(key=lambda x: (x.feasible, x.net_change), reverse=True)

        return swaps

    def evaluate_relay_impact(
        self,
        relay_event: str,
        proposed_swimmers: list[str],
        current_lineup: dict[str, list[str]] | None = None,
    ) -> RelayAnalysis:
        """
        Analyze impact of a relay configuration.

        Args:
            relay_event: Relay event name (e.g., "Boys 200 Medley Relay")
            proposed_swimmers: 4 swimmers for the relay
            current_lineup: Current individual assignments

        Returns:
            RelayAnalysis with projections and alternatives
        """
        # Get relay times for these swimmers
        total_split_time = 0.0
        swimmer_splits = []

        for swimmer in proposed_swimmers:
            # Estimate split from individual events
            split = self._estimate_relay_split(swimmer, relay_event)
            swimmer_splits.append({"swimmer": swimmer, "estimated_split": split})
            total_split_time += split

        # Predict placement against other teams
        projected_place = self._predict_relay_place(relay_event, total_split_time)

        # Get points for this place
        if projected_place <= len(self.rules.relay_points):
            points = self.rules.relay_points[projected_place - 1]
        else:
            points = 0

        # Find alternative configurations
        alternatives = self._find_alternative_relay_configs(
            relay_event, proposed_swimmers
        )

        # Generate notes
        notes = []
        if "400" in relay_event and "Free" in relay_event:
            notes.append("400 FR counts as individual slot at VCAC")

        # Check if any swimmer has individual conflicts
        for swimmer in proposed_swimmers:
            entries = self.psych.get_swimmer_entries(swimmer, self.target_team)
            individual_count = sum(1 for e in entries if "relay" not in e.event.lower())
            if individual_count >= 2:
                notes.append(f"{swimmer} already at 2 individual events")

        return RelayAnalysis(
            relay_event=relay_event,
            swimmers=proposed_swimmers,
            projected_place=projected_place,
            projected_points=points,
            alternative_configs=alternatives,
            optimization_notes=notes,
        )

    def quick_what_if(self, change: str) -> str:
        """
        Natural language what-if query.

        Args:
            change: Description like "move John from 100 Free to 50 Free"

        Returns:
            Text summary of the impact
        """
        # Parse the change (simple pattern matching)
        change_lower = change.lower()

        # Pattern: "move X from Y to Z"
        if "move" in change_lower and "from" in change_lower and "to" in change_lower:
            try:
                # Extract swimmer and events
                parts = change.split("from")
                swimmer_part = parts[0].replace("move", "").strip()
                events_part = parts[1].split("to")
                from_event = events_part[0].strip()
                to_event = events_part[1].strip()

                # Get swap analysis
                swaps = self.find_best_swap(swimmer_part, from_event)

                # Find the requested swap
                for swap in swaps:
                    if to_event.lower() in swap.to_event.lower():
                        impact = swap.net_change
                        if impact > 0:
                            return f"Moving {swimmer_part} from {from_event} to {swap.to_event}: +{impact:.1f} points. RECOMMENDED."
                        else:
                            return f"Moving {swimmer_part} from {from_event} to {swap.to_event}: {impact:.1f} points. NOT RECOMMENDED."

                return f"Could not find {to_event} as an option for {swimmer_part}."
            except Exception:
                return f"Could not parse: {change}. Try: 'move John Smith from Boys 100 Free to Boys 50 Free'"

        return "Unknown query format. Try: 'move [swimmer] from [event] to [event]'"

    # -------------------------------------------------------------------------
    # Private Methods
    # -------------------------------------------------------------------------

    def _calculate_scenario_points(self, lineup: dict[str, list[str]]) -> float:
        """Calculate total projected points for a lineup."""
        total = 0.0

        for swimmer, events in lineup.items():
            for event in events:
                total += self._get_swimmer_event_points(swimmer, event)

        return total

    def _get_swimmer_event_points(self, swimmer: str, event: str) -> float:
        """Get projected points for swimmer in event."""
        # Get from projection
        if event in self.base_projection.event_projections:
            event_proj = self.base_projection.event_projections[event]
            team_results = event_proj.team_results.get(self.target_team, [])
            for result in team_results:
                if result.get("swimmer") == swimmer:
                    return result.get("points", 0)

        return 0.0

    def _get_event_points(self, event: str, lineup: dict[str, list[str]]) -> float:
        """Get total points for an event in a lineup."""
        total = 0.0
        for swimmer, events in lineup.items():
            if event in events:
                total += self._get_swimmer_event_points(swimmer, event)
        return total

    def _find_changes(
        self, base: dict[str, list[str]], alt: dict[str, list[str]]
    ) -> list[dict]:
        """Find differences between two lineups."""
        changes = []

        all_swimmers = set(base.keys()) | set(alt.keys())

        for swimmer in all_swimmers:
            base_events = set(base.get(swimmer, []))
            alt_events = set(alt.get(swimmer, []))

            removed = base_events - alt_events
            added = alt_events - base_events

            for event in removed:
                changes.append(
                    {
                        "type": "removed",
                        "swimmer": swimmer,
                        "event": event,
                        "description": f"Removed {swimmer} from {event}",
                    }
                )

            for event in added:
                changes.append(
                    {
                        "type": "added",
                        "swimmer": swimmer,
                        "event": event,
                        "description": f"Added {swimmer} to {event}",
                    }
                )

        return changes

    def _estimate_points_without_seed(self, swimmer: str, event: str) -> float:
        """Estimate points if swimmer doesn't have a seed."""
        # Conservative: assume middle of scoring positions
        if len(self.rules.individual_points) >= 6:
            return self.rules.individual_points[5]  # 6th place
        return 0

    def _estimate_relay_split(self, swimmer: str, relay_event: str) -> float:
        """Estimate relay split time from individual events."""
        # Map relay to individual event for split estimation
        if "Medley" in relay_event:
            # Depends on leg assignment - use 50 time as approximation
            entries = self.psych.get_swimmer_entries(swimmer, self.target_team)
            for e in entries:
                if "50" in e.event:
                    return e.seed_time
            return 30.0  # Default
        elif "Free" in relay_event:
            entries = self.psych.get_swimmer_entries(swimmer, self.target_team)
            # For 200 FR: use 50 + adjustment
            # For 400 FR: use 100 time
            for e in entries:
                if "100 Free" in e.event and "400" in relay_event:
                    return e.seed_time
                elif "50 Free" in e.event and "200" in relay_event:
                    return e.seed_time
            return 55.0  # Default

        return 60.0

    def _predict_relay_place(self, relay_event: str, total_time: float) -> int:
        """Predict placement based on total relay time."""
        # Get other teams' projected times
        event_entries = self.psych.get_event_entries(relay_event)

        # Sort by time and find our position
        times = sorted(
            [e.seed_time for e in event_entries if e.seed_time < float("inf")]
        )

        place = 1
        for t in times:
            if t < total_time:
                place += 1
            else:
                break

        return min(place, 8)  # Cap at 8th

    def _find_alternative_relay_configs(
        self, relay_event: str, current_swimmers: list[str]
    ) -> list[dict]:
        """Find alternative relay configurations."""
        alternatives = []

        # Get all available swimmers
        team_swimmers = list(self._team_swimmers)

        # Try swapping one swimmer at a time
        for i, current in enumerate(current_swimmers):
            for swap_in in team_swimmers:
                if swap_in not in current_swimmers:
                    new_config = current_swimmers.copy()
                    new_config[i] = swap_in

                    # Estimate time difference
                    current_split = self._estimate_relay_split(current, relay_event)
                    new_split = self._estimate_relay_split(swap_in, relay_event)
                    time_diff = new_split - current_split

                    if time_diff < -0.5:  # Improvement of 0.5s or more
                        alternatives.append(
                            {
                                "swap_out": current,
                                "swap_in": swap_in,
                                "time_improvement": -time_diff,
                                "new_swimmers": new_config,
                            }
                        )

        # Sort by improvement
        alternatives.sort(key=lambda x: x["time_improvement"], reverse=True)

        return alternatives[:5]  # Top 5


# Factory function
def create_scenario_analyzer(
    psych_sheet: MeetPsychSheet,
    target_team: str = "SST",
    meet_profile: str = "vcac_championship",
) -> ScenarioAnalyzer:
    """Create a scenario analyzer."""
    return ScenarioAnalyzer(psych_sheet, target_team, meet_profile)


__all__ = [
    "ScenarioAnalyzer",
    "ScenarioComparison",
    "SwapOption",
    "RelayAnalysis",
    "create_scenario_analyzer",
]
