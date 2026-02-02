"""
Scenario Simulator for Championship Strategy

Run what-if scenarios for championship strategy decisions.
"""

from typing import Any

from swim_ai_reflex.backend.core.strategies.championship_strategy import (
    ChampionshipEntry,
    ChampionshipGurobiStrategy,
)


class ScenarioSimulator:
    """
    Run what-if scenarios for championship strategy.
    """

    def __init__(self, optimizer: ChampionshipGurobiStrategy):
        self.optimizer = optimizer

    def simulate_entry_change(
        self,
        all_entries: list[ChampionshipEntry],
        target_team: str,
        swimmer: str,
        old_events: list[str],
        new_events: list[str],
        **kwargs,
    ) -> dict[str, Any]:
        """
        Simulate moving a swimmer from one set of events to another.

        Returns comparison showing point impact.
        """
        # Create modified entries
        modified_entries = []

        for entry in all_entries:
            if (
                entry.swimmer_name == swimmer
                and entry.team.upper() == target_team.upper()
            ):
                # Check if this event should be included
                if entry.event in new_events:
                    modified_entries.append(entry)
                # Skip events being removed
            else:
                modified_entries.append(entry)

        # Run both optimizations
        original_result = self.optimizer.optimize_entries(
            all_entries, target_team, **kwargs
        )
        modified_result = self.optimizer.optimize_entries(
            modified_entries, target_team, **kwargs
        )

        return {
            "swimmer": swimmer,
            "old_events": old_events,
            "new_events": new_events,
            "original_points": original_result.total_points,
            "modified_points": modified_result.total_points,
            "delta": modified_result.total_points - original_result.total_points,
            "recommendation": "✅ MAKE CHANGE"
            if modified_result.total_points > original_result.total_points
            else "❌ KEEP CURRENT",
        }

    def simulate_scratch(
        self,
        all_entries: list[ChampionshipEntry],
        target_team: str,
        swimmer: str,
        **kwargs,
    ) -> dict[str, Any]:
        """
        Simulate a swimmer scratching from the meet entirely.

        Useful for injury/illness scenarios.
        """
        # Remove swimmer from entries
        modified_entries = [
            e
            for e in all_entries
            if not (e.swimmer_name == swimmer and e.team.upper() == target_team.upper())
        ]

        original_result = self.optimizer.optimize_entries(
            all_entries, target_team, **kwargs
        )
        modified_result = self.optimizer.optimize_entries(
            modified_entries, target_team, **kwargs
        )

        return {
            "swimmer": swimmer,
            "scenario": "SCRATCHED",
            "original_points": original_result.total_points,
            "modified_points": modified_result.total_points,
            "point_loss": original_result.total_points - modified_result.total_points,
            "impact": "HIGH"
            if (original_result.total_points - modified_result.total_points) > 20
            else "MEDIUM"
            if (original_result.total_points - modified_result.total_points) > 10
            else "LOW",
        }

    def simulate_time_improvement(
        self,
        all_entries: list[ChampionshipEntry],
        target_team: str,
        swimmer: str,
        event: str,
        new_time: float,
        **kwargs,
    ) -> dict[str, Any]:
        """
        Simulate a swimmer dropping time in an event.
        """
        original_time = None
        modified_entries = []

        for entry in all_entries:
            if (
                entry.swimmer_name == swimmer
                and entry.event == event
                and entry.team.upper() == target_team.upper()
            ):
                original_time = entry.seed_time
                # Create modified entry
                modified_entries.append(
                    ChampionshipEntry(
                        swimmer_name=entry.swimmer_name,
                        team=entry.team,
                        event=entry.event,
                        seed_time=new_time,
                        gender=entry.gender,
                        grade=entry.grade,
                        source="simulation",
                    )
                )
            else:
                modified_entries.append(entry)

        original_result = self.optimizer.optimize_entries(
            all_entries, target_team, **kwargs
        )
        modified_result = self.optimizer.optimize_entries(
            modified_entries, target_team, **kwargs
        )

        return {
            "swimmer": swimmer,
            "event": event,
            "original_time": original_time,
            "new_time": new_time,
            "time_drop": original_time - new_time if original_time else 0,
            "original_points": original_result.total_points,
            "modified_points": modified_result.total_points,
            "point_gain": modified_result.total_points - original_result.total_points,
        }
