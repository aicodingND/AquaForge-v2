"""
Relay 400 Free Trade-off Analyzer

Analyze the trade-off of swimming the 400 Free Relay at VCAC.
VCAC Rule: Relay 3 (400 Free) counts as 1 individual event.
"""

from typing import Any

from swim_ai_reflex.backend.core.rules import get_meet_profile
from swim_ai_reflex.backend.core.strategies.championship_strategy import (
    ChampionshipEntry,
    ChampionshipGurobiStrategy,
)


class Relay400TradeoffAnalyzer:
    """
    Analyze the trade-off of swimming the 400 Free Relay at VCAC.

    VCAC Rule: Relay 3 (400 Free) counts as 1 individual event.

    This means swimmers on the 400FR lose an individual slot, so we need
    to compare:
    - Points gained from faster 400FR
    - Points lost from giving up an individual event
    """

    def __init__(self, meet_profile: str = "vcac_championship"):
        self.rules = get_meet_profile(meet_profile)
        self.optimizer = ChampionshipGurobiStrategy(meet_profile)

    def analyze_400fr_decision(
        self,
        all_entries: list[ChampionshipEntry],
        target_team: str,
        potential_400fr_swimmers: list[str],
        split_times: dict[str, float],  # swimmer -> 100 free split time
    ) -> dict[str, Any]:
        """
        Analyze whether to swim the 400 Free Relay and who should be on it.

        Args:
            all_entries: All meet entries
            target_team: Team to analyze
            potential_400fr_swimmers: Swimmers being considered for 400FR
            split_times: Each swimmer's projected 100 free split

        Returns:
            Analysis with recommendation
        """
        # Calculate points WITHOUT 400FR (swimmers keep individual slots)
        result_without_400 = self.optimizer.optimize_entries(
            all_entries,
            target_team,
            relay_3_swimmers=set(),  # No one loses a slot
        )

        # Calculate points WITH 400FR (swimmers lose individual slots)
        result_with_400 = self.optimizer.optimize_entries(
            all_entries, target_team, relay_3_swimmers=set(potential_400fr_swimmers)
        )

        # Estimate 400FR relay points (simplified - based on total time)
        total_split = sum(
            split_times.get(s, 60.0) for s in potential_400fr_swimmers[:4]
        )
        estimated_400fr_points = self._estimate_relay_points(total_split)

        # Net analysis
        individual_cost = result_without_400.total_points - result_with_400.total_points
        net_gain = estimated_400fr_points - individual_cost

        # Per-swimmer analysis
        swimmer_analysis = []
        for swimmer in potential_400fr_swimmers:
            # What individual points does this swimmer lose?
            with_swimmer = self.optimizer.optimize_entries(
                all_entries, target_team, relay_3_swimmers=set()
            )
            without_swimmer = self.optimizer.optimize_entries(
                all_entries, target_team, relay_3_swimmers={swimmer}
            )
            individual_loss = with_swimmer.total_points - without_swimmer.total_points

            swimmer_analysis.append(
                {
                    "swimmer": swimmer,
                    "split_time": split_times.get(swimmer, 0),
                    "individual_points_lost": individual_loss,
                    "value_for_relay": "HIGH"
                    if individual_loss < 10
                    else "MEDIUM"
                    if individual_loss < 20
                    else "LOW",
                }
            )

        # Sort by value (lower individual loss = better for relay)
        swimmer_analysis.sort(key=lambda x: x["individual_points_lost"])

        return {
            "points_without_400fr": result_without_400.total_points,
            "points_with_400fr": result_with_400.total_points,
            "estimated_400fr_relay_points": estimated_400fr_points,
            "individual_cost": individual_cost,
            "net_gain": net_gain,
            "recommendation": " ✓ SWIM 400FR" if net_gain > 0 else " SKIP 400FR",
            "swimmer_analysis": swimmer_analysis,
            "suggested_lineup": [s["swimmer"] for s in swimmer_analysis[:4]],
        }

    def _estimate_relay_points(self, total_time: float) -> float:
        """Estimate relay points based on time. Placeholder - needs real opponent data."""
        # Simplified: assume ~3:30 is 1st place, ~4:00 is 8th
        if total_time < 210:  # 3:30
            return self.rules.relay_points[0]  # 1st
        elif total_time < 220:  # 3:40
            return self.rules.relay_points[1]  # 2nd
        elif total_time < 230:  # 3:50
            return self.rules.relay_points[3]  # 4th
        elif total_time < 240:  # 4:00
            return self.rules.relay_points[5]  # 6th
        else:
            return self.rules.relay_points[7] if len(self.rules.relay_points) > 7 else 0
