"""
Relay Configuration Optimizer Service

Optimizes A and B relay compositions for maximum team points.
Uses Hungarian algorithm for optimal stroke assignments in medley relays.

VCAC Relay Rules:
- 3 relays: 200 Medley Relay, 200 Free Relay, 400 Free Relay
- Both A and B relays score
- Relay 3 (400 Free) counts as 1 individual event slot

NOTE: Uses scipy.optimize.linear_sum_assignment for accurate optimization.
No approximation algorithms - we want correct results.
"""

from dataclasses import dataclass
from typing import List, Dict, Set, Optional, Tuple
from collections import defaultdict
import numpy as np

from swim_ai_reflex.backend.core.rules import get_meet_profile
from swim_ai_reflex.backend.models.championship import MeetPsychSheet


@dataclass
class RelayLeg:
    """A single leg of a relay."""

    swimmer: str
    stroke: str  # 'back', 'breast', 'fly', 'free'
    split_time: float  # Expected split time in seconds


@dataclass
class RelayConfiguration:
    """Complete configuration for one relay."""

    relay_name: str  # '200 Medley Relay', '200 Free Relay', '400 Free Relay'
    team_designation: str  # 'A' or 'B'
    legs: List[RelayLeg]
    predicted_time: float  # Total relay time
    predicted_place: int  # Expected finish position
    predicted_points: int  # Points based on placement

    @property
    def swimmer_names(self) -> List[str]:
        """Get list of swimmer names on this relay."""
        return [leg.swimmer for leg in self.legs]

    @property
    def is_complete(self) -> bool:
        """Check if relay has all 4 legs filled."""
        return len(self.legs) == 4


@dataclass
class RelayOptimizationResult:
    """Result of relay optimization for all relays."""

    configurations: Dict[str, List[RelayConfiguration]]  # {relay_name: [A, B]}
    total_points: float
    relay_400_recommendation: str  # 'swim', 'skip', or 'optional'
    relay_400_net_value: float  # Points gained/lost by swimming 400
    solve_time_ms: float = 0.0


class RelayOptimizer:
    """
    Optimize relay configurations for maximum team points.

    Uses Hungarian algorithm for medley relays (stroke assignment)
    and greedy assignment for free relays.
    """

    def __init__(self, meet_profile: str = "vcac_championship"):
        """
        Initialize with meet rules.

        Args:
            meet_profile: Name of meet profile for scoring rules
        """
        self.rules = get_meet_profile(meet_profile)

    def optimize_relays(
        self,
        psych: MeetPsychSheet,
        individual_assignments: Dict[str, List[str]],
        team: str = "Seton",
        divers: Set[str] = None,
    ) -> RelayOptimizationResult:
        """
        Optimize all relay configurations.

        Args:
            psych: Meet psych sheet with all entries
            individual_assignments: {swimmer: [events]} from entry optimizer
            team: Target team name
            divers: Set of swimmer names who are divers

        Returns:
            RelayOptimizationResult with optimal configurations
        """
        import time

        start_time = time.time()

        divers = divers or set()

        # Get all team swimmers and their times by stroke
        swimmer_times = self._get_swimmer_times(psych, team)

        # Track who's available for each relay
        # For relays 1-2: everyone is available
        # For relay 3: check individual slot usage
        available_relay_12 = set(swimmer_times.keys())
        available_relay_3 = self._get_relay_3_availability(
            swimmer_times.keys(), individual_assignments, divers
        )

        # Track swimmers used in each relay
        swimmers_used_per_relay: Dict[str, Set[str]] = {}

        # Optimize 200 Medley Relay
        medley_configs = self._optimize_medley_relay(
            swimmer_times, available_relay_12, psych, "200 Medley Relay"
        )
        swimmers_used_per_relay["200 Medley Relay"] = {
            leg.swimmer for cfg in medley_configs for leg in cfg.legs
        }

        # Optimize 200 Free Relay (50 Free splits)
        free200_configs = self._optimize_free_relay(
            swimmer_times, available_relay_12, psych, "200 Free Relay", 50
        )
        swimmers_used_per_relay["200 Free Relay"] = {
            leg.swimmer for cfg in free200_configs for leg in cfg.legs
        }

        # Optimize 400 Free Relay with trade-off analysis
        relay_400_recommendation, relay_400_net_value, free400_configs = (
            self._optimize_400_free_with_analysis(
                swimmer_times, available_relay_3, individual_assignments, psych, divers
            )
        )

        configurations = {
            "200 Medley Relay": medley_configs,
            "200 Free Relay": free200_configs,
        }

        if free400_configs:
            configurations["400 Free Relay"] = free400_configs

        # Calculate total points
        total_points = sum(
            cfg.predicted_points
            for configs in configurations.values()
            for cfg in configs
        )

        return RelayOptimizationResult(
            configurations=configurations,
            total_points=total_points,
            relay_400_recommendation=relay_400_recommendation,
            relay_400_net_value=relay_400_net_value,
            solve_time_ms=(time.time() - start_time) * 1000,
        )

    def _get_swimmer_times(
        self, psych: MeetPsychSheet, team: str
    ) -> Dict[str, Dict[str, float]]:
        """
        Extract swimmer times by stroke from psych sheet.

        Returns: {swimmer_name: {'50 Free': 23.4, '100 Back': 58.2, ...}}
        """
        team_entries = psych.get_team_entries(team)
        swimmer_times: Dict[str, Dict[str, float]] = defaultdict(dict)

        for entry in team_entries:
            if "relay" not in entry.event.lower():
                # Extract the stroke/distance from event name
                event_key = self._normalize_event(entry.event)
                if event_key:
                    swimmer_times[entry.swimmer_name][event_key] = entry.seed_time

        return dict(swimmer_times)

    def _normalize_event(self, event: str) -> Optional[str]:
        """Normalize event name to standard form (e.g., '50 Free', '100 Back')."""
        event_lower = event.lower()

        # Remove gender prefix
        for prefix in ["boys ", "girls ", "men's ", "women's "]:
            if event_lower.startswith(prefix):
                event_lower = event_lower[len(prefix) :]
                break

        # Map to standard names
        stroke_map = {
            "free": "Free",
            "freestyle": "Free",
            "back": "Back",
            "backstroke": "Back",
            "breast": "Breast",
            "breaststroke": "Breast",
            "fly": "Fly",
            "butterfly": "Fly",
            "im": "IM",
        }

        # Try to parse distance and stroke
        parts = event_lower.strip().split()
        if len(parts) >= 2:
            distance = parts[0]
            stroke_raw = parts[1] if len(parts) > 1 else ""
            stroke = stroke_map.get(stroke_raw, stroke_raw.title())

            if distance.isdigit():
                return f"{distance} {stroke}"

        return None

    def _get_relay_3_availability(
        self,
        all_swimmers: Set[str],
        individual_assignments: Dict[str, List[str]],
        divers: Set[str],
    ) -> Set[str]:
        """
        Determine who can swim relay 3 (400 Free).

        Relay 3 counts as 1 individual event, so swimmers with
        2 individual events already cannot swim it.
        """
        available = set()

        for swimmer in all_swimmers:
            events = individual_assignments.get(swimmer, [])
            is_diver = swimmer in divers

            # Effective individual count
            individual_count = len(events) + (1 if is_diver else 0)

            # Can swim relay 3 if individual_count + 1 <= 2
            if individual_count < 2:
                available.add(swimmer)

        return available

    def _optimize_medley_relay(
        self,
        swimmer_times: Dict[str, Dict[str, float]],
        available: Set[str],
        psych: MeetPsychSheet,
        relay_name: str,
    ) -> List[RelayConfiguration]:
        """
        Optimize medley relay using Hungarian algorithm.

        Medley order: Back → Breast → Fly → Free
        Uses 100-yard times for split prediction.
        """
        from scipy.optimize import linear_sum_assignment

        strokes = ["100 Back", "100 Breast", "100 Fly", "100 Free"]
        stroke_names = ["back", "breast", "fly", "free"]
        available_list = list(available)
        n_swimmers = len(available_list)

        if n_swimmers < 4:
            # Not enough swimmers for a full relay
            return self._build_incomplete_relays(
                available_list, swimmer_times, strokes, stroke_names, relay_name, psych
            )

        # Build cost matrix: cost[swimmer][stroke] = time (lower is better)
        cost_matrix = np.full((n_swimmers, 4), np.inf)

        for i, swimmer in enumerate(available_list):
            for j, stroke in enumerate(strokes):
                if stroke in swimmer_times.get(swimmer, {}):
                    cost_matrix[i, j] = swimmer_times[swimmer][stroke]

        # Check if assignment is feasible (each column has at least one finite value)
        # and we have enough swimmers with times
        col_has_finite = [np.any(np.isfinite(cost_matrix[:, j])) for j in range(4)]

        if not all(col_has_finite):
            # Can't fill all legs - fall back to greedy assignment
            return self._build_incomplete_relays(
                available_list, swimmer_times, strokes, stroke_names, relay_name, psych
            )

        # Build A relay using Hungarian algorithm
        try:
            row_ind, col_ind = linear_sum_assignment(cost_matrix)
        except ValueError:
            # Infeasible assignment - fall back to greedy
            return self._build_incomplete_relays(
                available_list, swimmer_times, strokes, stroke_names, relay_name, psych
            )

        a_legs = []
        a_swimmers_used = set()

        # Sort by column index to maintain stroke order
        assignments = sorted(zip(row_ind, col_ind), key=lambda x: x[1])

        for i, j in assignments:
            if cost_matrix[i, j] < np.inf and len(a_legs) < 4:
                a_legs.append(
                    RelayLeg(
                        swimmer=available_list[i],
                        stroke=stroke_names[j],
                        split_time=cost_matrix[i, j],
                    )
                )
                a_swimmers_used.add(available_list[i])

        # If we don't have 4 legs, try to fill with available swimmers
        if len(a_legs) < 4:
            a_legs = self._fill_missing_legs(
                a_legs, available_list, swimmer_times, strokes, stroke_names
            )

        a_time = (
            sum(leg.split_time for leg in a_legs) if len(a_legs) == 4 else float("inf")
        )
        a_place, a_points = self._predict_relay_placement(psych, relay_name, a_time)

        a_config = RelayConfiguration(
            relay_name=relay_name,
            team_designation="A",
            legs=a_legs,
            predicted_time=a_time,
            predicted_place=a_place,
            predicted_points=a_points,
        )

        # Build B relay with remaining swimmers
        remaining = [s for s in available_list if s not in a_swimmers_used]
        b_config = self._build_b_medley_relay(
            remaining, swimmer_times, strokes, stroke_names, relay_name, psych
        )

        return [a_config, b_config]

    def _fill_missing_legs(
        self,
        current_legs: List[RelayLeg],
        swimmers: List[str],
        swimmer_times: Dict[str, Dict[str, float]],
        strokes: List[str],
        stroke_names: List[str],
    ) -> List[RelayLeg]:
        """Try to fill missing relay legs with remaining swimmers."""
        used_swimmers = {leg.swimmer for leg in current_legs}
        used_strokes = {leg.stroke for leg in current_legs}

        for j, (stroke, stroke_name) in enumerate(zip(strokes, stroke_names)):
            if stroke_name in used_strokes:
                continue

            # Find best available swimmer for this stroke
            best_swimmer = None
            best_time = float("inf")

            for swimmer in swimmers:
                if swimmer in used_swimmers:
                    continue

                time_val = swimmer_times.get(swimmer, {}).get(stroke)
                if time_val and time_val < best_time:
                    best_swimmer = swimmer
                    best_time = time_val

            if best_swimmer:
                current_legs.append(
                    RelayLeg(
                        swimmer=best_swimmer, stroke=stroke_name, split_time=best_time
                    )
                )
                used_swimmers.add(best_swimmer)

        # Sort legs by stroke order
        stroke_order = {name: i for i, name in enumerate(stroke_names)}
        current_legs.sort(key=lambda x: stroke_order.get(x.stroke, 99))

        return current_legs

    def _build_b_medley_relay(
        self,
        remaining_swimmers: List[str],
        swimmer_times: Dict[str, Dict[str, float]],
        strokes: List[str],
        stroke_names: List[str],
        relay_name: str,
        psych: MeetPsychSheet,
    ) -> RelayConfiguration:
        """Build B medley relay with remaining swimmers."""
        from scipy.optimize import linear_sum_assignment

        n = len(remaining_swimmers)

        if n < 4:
            # Not enough for complete B relay
            b_legs = []
            used = set()

            for j, (stroke, stroke_name) in enumerate(zip(strokes, stroke_names)):
                best = None
                best_time = float("inf")

                for swimmer in remaining_swimmers:
                    if swimmer in used:
                        continue
                    time_val = swimmer_times.get(swimmer, {}).get(stroke)
                    if time_val and time_val < best_time:
                        best = swimmer
                        best_time = time_val

                if best:
                    b_legs.append(
                        RelayLeg(swimmer=best, stroke=stroke_name, split_time=best_time)
                    )
                    used.add(best)

            b_time = sum(leg.split_time for leg in b_legs) if b_legs else float("inf")
            b_place, b_points = self._predict_relay_placement(psych, relay_name, b_time)

            return RelayConfiguration(
                relay_name=relay_name,
                team_designation="B",
                legs=b_legs,
                predicted_time=b_time,
                predicted_place=b_place,
                predicted_points=b_points,
            )

        # Use Hungarian for B relay too
        cost_matrix = np.full((n, 4), np.inf)

        for i, swimmer in enumerate(remaining_swimmers):
            for j, stroke in enumerate(strokes):
                if stroke in swimmer_times.get(swimmer, {}):
                    cost_matrix[i, j] = swimmer_times[swimmer][stroke]

        # Handle infeasible cases
        col_has_finite = [np.any(np.isfinite(cost_matrix[:, j])) for j in range(4)]
        if not all(col_has_finite):
            # Fall back to greedy - some strokes have no swimmers
            b_legs = []
            used = set()
            for stroke, stroke_name in zip(strokes, stroke_names):
                best, best_time = None, float("inf")
                for swimmer in remaining_swimmers:
                    if swimmer in used:
                        continue
                    time_val = swimmer_times.get(swimmer, {}).get(stroke)
                    if time_val and time_val < best_time:
                        best, best_time = swimmer, time_val
                if best:
                    b_legs.append(
                        RelayLeg(swimmer=best, stroke=stroke_name, split_time=best_time)
                    )
                    used.add(best)
            b_time = (
                sum(leg.split_time for leg in b_legs)
                if len(b_legs) == 4
                else float("inf")
            )
            b_place, b_points = self._predict_relay_placement(psych, relay_name, b_time)
            return RelayConfiguration(
                relay_name=relay_name,
                team_designation="B",
                legs=b_legs,
                predicted_time=b_time,
                predicted_place=b_place,
                predicted_points=b_points,
            )

        try:
            row_ind, col_ind = linear_sum_assignment(cost_matrix)
        except ValueError:
            # Fallback to greedy
            b_legs = []
            used = set()
            for stroke, stroke_name in zip(strokes, stroke_names):
                best, best_time = None, float("inf")
                for swimmer in remaining_swimmers:
                    if swimmer in used:
                        continue
                    time_val = swimmer_times.get(swimmer, {}).get(stroke)
                    if time_val and time_val < best_time:
                        best, best_time = swimmer, time_val
                if best:
                    b_legs.append(
                        RelayLeg(swimmer=best, stroke=stroke_name, split_time=best_time)
                    )
                    used.add(best)
            b_time = (
                sum(leg.split_time for leg in b_legs)
                if len(b_legs) == 4
                else float("inf")
            )
            b_place, b_points = self._predict_relay_placement(psych, relay_name, b_time)
            return RelayConfiguration(
                relay_name=relay_name,
                team_designation="B",
                legs=b_legs,
                predicted_time=b_time,
                predicted_place=b_place,
                predicted_points=b_points,
            )

        b_legs = []
        for i, j in sorted(zip(row_ind, col_ind), key=lambda x: x[1]):
            if cost_matrix[i, j] < np.inf and len(b_legs) < 4:
                b_legs.append(
                    RelayLeg(
                        swimmer=remaining_swimmers[i],
                        stroke=stroke_names[j],
                        split_time=cost_matrix[i, j],
                    )
                )

        b_time = (
            sum(leg.split_time for leg in b_legs) if len(b_legs) == 4 else float("inf")
        )
        b_place, b_points = self._predict_relay_placement(psych, relay_name, b_time)

        return RelayConfiguration(
            relay_name=relay_name,
            team_designation="B",
            legs=b_legs,
            predicted_time=b_time,
            predicted_place=b_place,
            predicted_points=b_points,
        )

    def _build_incomplete_relays(
        self,
        swimmers: List[str],
        swimmer_times: Dict[str, Dict[str, float]],
        strokes: List[str],
        stroke_names: List[str],
        relay_name: str,
        psych: MeetPsychSheet,
    ) -> List[RelayConfiguration]:
        """Handle case where we don't have enough swimmers for full relays."""
        a_legs = []
        used = set()

        for j, (stroke, stroke_name) in enumerate(zip(strokes, stroke_names)):
            best = None
            best_time = float("inf")

            for swimmer in swimmers:
                if swimmer in used:
                    continue
                time_val = swimmer_times.get(swimmer, {}).get(stroke)
                if time_val and time_val < best_time:
                    best = swimmer
                    best_time = time_val

            if best:
                a_legs.append(
                    RelayLeg(swimmer=best, stroke=stroke_name, split_time=best_time)
                )
                used.add(best)

        a_time = sum(leg.split_time for leg in a_legs) if a_legs else float("inf")
        a_place, a_points = self._predict_relay_placement(psych, relay_name, a_time)

        a_config = RelayConfiguration(
            relay_name=relay_name,
            team_designation="A",
            legs=a_legs,
            predicted_time=a_time,
            predicted_place=a_place,
            predicted_points=a_points,
        )

        # Empty B relay
        b_config = RelayConfiguration(
            relay_name=relay_name,
            team_designation="B",
            legs=[],
            predicted_time=float("inf"),
            predicted_place=0,
            predicted_points=0,
        )

        return [a_config, b_config]

    def _optimize_free_relay(
        self,
        swimmer_times: Dict[str, Dict[str, float]],
        available: Set[str],
        psych: MeetPsychSheet,
        relay_name: str,
        split_distance: int,  # 50 for 200 Free Relay, 100 for 400 Free Relay
    ) -> List[RelayConfiguration]:
        """
        Optimize free relay by selecting fastest swimmers.

        Simply pick the 4 fastest for A, next 4 for B.
        """
        stroke_key = f"{split_distance} Free"

        # Get swimmers sorted by free time
        swimmers_with_times = []
        for swimmer in available:
            time_val = swimmer_times.get(swimmer, {}).get(stroke_key)
            if time_val:
                swimmers_with_times.append((swimmer, time_val))

        swimmers_with_times.sort(key=lambda x: x[1])

        # A relay: fastest 4
        a_legs = []
        for swimmer, time_val in swimmers_with_times[:4]:
            a_legs.append(RelayLeg(swimmer=swimmer, stroke="free", split_time=time_val))

        a_time = (
            sum(leg.split_time for leg in a_legs) if len(a_legs) == 4 else float("inf")
        )
        a_place, a_points = self._predict_relay_placement(psych, relay_name, a_time)

        a_config = RelayConfiguration(
            relay_name=relay_name,
            team_designation="A",
            legs=a_legs,
            predicted_time=a_time,
            predicted_place=a_place,
            predicted_points=a_points,
        )

        # B relay: next 4
        b_legs = []
        for swimmer, time_val in swimmers_with_times[4:8]:
            b_legs.append(RelayLeg(swimmer=swimmer, stroke="free", split_time=time_val))

        b_time = (
            sum(leg.split_time for leg in b_legs) if len(b_legs) == 4 else float("inf")
        )
        b_place, b_points = self._predict_relay_placement(psych, relay_name, b_time)

        b_config = RelayConfiguration(
            relay_name=relay_name,
            team_designation="B",
            legs=b_legs,
            predicted_time=b_time,
            predicted_place=b_place,
            predicted_points=b_points,
        )

        return [a_config, b_config]

    def _optimize_400_free_with_analysis(
        self,
        swimmer_times: Dict[str, Dict[str, float]],
        available: Set[str],
        individual_assignments: Dict[str, List[str]],
        psych: MeetPsychSheet,
        divers: Set[str],
    ) -> Tuple[str, float, Optional[List[RelayConfiguration]]]:
        """
        Analyze whether swimming 400 Free Relay is worth it.

        VCAC Rule: Relay 3 counts as 1 individual event slot!

        Returns:
            (recommendation, net_value, configurations or None)
        """
        # If no one is available for relay 3, skip it
        if len(available) < 4:
            return ("skip", 0.0, None)

        # Calculate potential relay points
        configs = self._optimize_free_relay(
            swimmer_times, available, psych, "400 Free Relay", 100
        )

        relay_points = sum(cfg.predicted_points for cfg in configs)

        if relay_points == 0:
            return ("skip", 0.0, None)

        # For now, assume the opportunity cost is low since we already
        # filtered for swimmers who have <2 individual events
        # A more sophisticated analysis would calculate exact trade-offs

        net_value = (
            relay_points  # Simplified - full points since swimmers are available
        )

        if net_value > 5:  # More than 5 points gained
            return ("swim", net_value, configs)
        elif net_value > 0:
            return ("optional", net_value, configs)
        else:
            return ("skip", net_value, None)

    def _predict_relay_placement(
        self, psych: MeetPsychSheet, relay_name: str, relay_time: float
    ) -> Tuple[int, int]:
        """
        Predict relay placement based on psych sheet data.

        Returns: (predicted_place, points)
        """
        if relay_time == float("inf"):
            return (0, 0)

        # Get all relay entries for this event
        entries = psych.get_event_entries(relay_name)

        if not entries:
            # No other teams - assume 1st place
            return (1, self.rules.relay_points[0] if self.rules.relay_points else 0)

        # Count how many teams are faster
        faster_teams = 0
        for entry in entries:
            if entry.seed_time < relay_time:
                faster_teams += 1

        place = faster_teams + 1

        # Get points for this placement
        points_table = self.rules.relay_points
        if place <= len(points_table):
            return (place, points_table[place - 1])

        return (place, 0)


def format_relay_configuration(config: RelayConfiguration) -> str:
    """Format relay configuration for display."""
    lines = [f"{config.relay_name} ({config.team_designation} Relay)"]
    lines.append(
        f"Predicted: {config.predicted_place} place, {config.predicted_points} pts"
    )
    lines.append(f"Total time: {config.predicted_time:.2f}s")
    lines.append("Legs:")

    for i, leg in enumerate(config.legs, 1):
        lines.append(f"  {i}. {leg.swimmer} ({leg.stroke}): {leg.split_time:.2f}s")

    return "\n".join(lines)


def get_relay_swimmers_for_constraints(
    result: RelayOptimizationResult,
) -> Dict[str, Set[str]]:
    """
    Extract relay swimmers for back-to-back constraint validation.

    Returns: {relay_name: set(swimmer_names)}

    Use this with the constraint validator to check that relay swimmers
    are not assigned to the immediately following individual event.
    """
    relay_swimmers: Dict[str, Set[str]] = {}

    for relay_name, configs in result.configurations.items():
        swimmers = set()
        for config in configs:
            swimmers.update(config.swimmer_names)
        relay_swimmers[relay_name] = swimmers

    return relay_swimmers


def get_blocked_swimmers_for_event(
    relay_result: RelayOptimizationResult,
    event: str,
) -> Set[str]:
    """
    Get swimmers who cannot swim a specific event due to relay back-to-back.

    Args:
        relay_result: Result from relay optimization
        event: Event name to check (e.g., '200 Free')

    Returns:
        Set of swimmer names who cannot swim this event
    """
    from swim_ai_reflex.backend.services.constraint_validator import (
        normalize_event_name,
        BACK_TO_BACK_BLOCKS,
    )

    blocked_swimmers = set()
    norm_event = normalize_event_name(event)

    # Check each relay to see if it blocks this event
    for relay_name, configs in relay_result.configurations.items():
        norm_relay = normalize_event_name(relay_name)
        blocked_events = BACK_TO_BACK_BLOCKS.get(norm_relay, [])

        if norm_event in blocked_events:
            # Swimmers on this relay are blocked from this event
            for config in configs:
                blocked_swimmers.update(config.swimmer_names)

    return blocked_swimmers
