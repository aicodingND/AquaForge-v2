"""
Entry Selection Optimizer Service

Determines optimal event assignments for each swimmer to maximize team points.
Uses Mixed Integer Linear Programming (MILP) for accurate, optimal solutions.

This solves a Generalized Assignment Problem (GAP):
    MAXIMIZE: Σ (expected_points[swimmer, event] × assigned[swimmer, event])
    SUBJECT TO:
      - Each swimmer assigned ≤ 2 individual events
      - Each swimmer assigned ≤ 3 relays
      - Diving counts as 1 individual event
      - Relay 3 counts as 1 individual event (VCAC rule)
      - Each event has ≤ max_scorers Seton swimmers scoring

NOTE: No greedy fallback - MILP provides accurate results.
If MILP fails, we raise an error so the issue can be debugged and fixed.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Set
from collections import defaultdict
import numpy as np

from swim_ai_reflex.backend.core.rules import get_meet_profile
from swim_ai_reflex.backend.models.championship import MeetPsychSheet, PsychSheetEntry
from swim_ai_reflex.backend.services.point_projection_service import (
    PointProjectionEngine,
)
from swim_ai_reflex.backend.utils.helpers import normalize_team_name


@dataclass
class SwimmerAssignment:
    """Assignment of events to a single swimmer."""

    swimmer_name: str
    team: str
    individual_events: List[str] = field(default_factory=list)
    relay_events: List[str] = field(default_factory=list)
    is_diver: bool = False
    expected_points: float = 0.0

    @property
    def total_events(self) -> int:
        """Total number of events assigned."""
        return len(self.individual_events) + len(self.relay_events)

    @property
    def effective_individual_count(self) -> int:
        """
        Calculate effective individual count per VCAC rules.

        - Diving counts as 1 individual
        - First 2 relays are free
        - Relay 3+ counts as individual
        """
        individual_used = len(self.individual_events) + (1 if self.is_diver else 0)
        relay_penalty = max(0, len(self.relay_events) - 2)
        return individual_used + relay_penalty

    @property
    def is_valid(self) -> bool:
        """Check if assignment is valid per VCAC rules."""
        return self.effective_individual_count <= 2


@dataclass
class OptimizationResult:
    """Result of entry optimization."""

    assignments: Dict[str, SwimmerAssignment]  # {swimmer_name: assignment}
    total_points: float
    current_points: float  # Points with current/default assignments
    improvement: float  # total_points - current_points
    status: str  # 'optimal', 'heuristic', 'failed'
    solve_time_ms: float = 0.0
    message: str = ""


class EntrySelectionOptimizer:
    """
    Optimize swimmer event assignments for maximum team points.
    Uses Mixed Integer Linear Programming (MILP) for optimal solution.
    """

    def __init__(self, meet_profile: str = "vcac_championship"):
        """
        Initialize optimizer with meet rules.

        Args:
            meet_profile: Name of meet profile for scoring rules
        """
        self.rules = get_meet_profile(meet_profile)
        self.projection_engine = PointProjectionEngine(meet_profile)

    def optimize(
        self, psych: MeetPsychSheet, team: str = "Seton", divers: Set[str] = None
    ) -> OptimizationResult:
        """
        Find optimal event assignments for team swimmers.

        Args:
            psych: Meet psych sheet with all entries
            team: Target team to optimize for
            divers: Set of swimmer names who are divers

        Returns:
            OptimizationResult with optimal assignments
        """
        import time

        start_time = time.time()

        divers = divers or set()
        normalize_team_name(team)

        # Get team swimmers and their individual events
        team_entries = psych.get_team_entries(team)
        individual_entries = [e for e in team_entries if "relay" not in e.event.lower()]

        # Get unique swimmers and events
        swimmers = sorted(set(e.swimmer_name for e in individual_entries))
        events = sorted(set(e.event for e in individual_entries))

        n_swimmers = len(swimmers)
        n_events = len(events)

        if n_swimmers == 0 or n_events == 0:
            return OptimizationResult(
                assignments={},
                total_points=0,
                current_points=0,
                improvement=0,
                status="failed",
                message="No swimmers or events found",
            )

        # Build swimmer-event lookup for seed times/ranks
        swimmer_events: Dict[str, Dict[str, PsychSheetEntry]] = defaultdict(dict)
        for entry in individual_entries:
            swimmer_events[entry.swimmer_name][entry.event] = entry

        # Calculate expected points for each (swimmer, event) pair
        # This considers all competitors, not just our team
        point_matrix = self._build_point_matrix(psych, swimmers, events, team)

        # Solve using MILP (no fallback - we want accurate results)
        result = self._solve_milp(swimmers, events, point_matrix, divers, team)
        result.solve_time_ms = (time.time() - start_time) * 1000

        # Calculate improvement over current assignment
        current_points = self._calculate_current_points(
            psych, swimmers, events, swimmer_events, team
        )
        result.current_points = current_points
        result.improvement = result.total_points - current_points

        return result

    def _build_point_matrix(
        self, psych: MeetPsychSheet, swimmers: List[str], events: List[str], team: str
    ) -> np.ndarray:
        """
        Build matrix of expected points for each (swimmer, event) pair.

        Args:
            psych: Meet psych sheet
            swimmers: List of swimmer names
            events: List of event names
            team: Target team name

        Returns:
            2D numpy array [n_swimmers × n_events] of expected points
        """
        n_swimmers = len(swimmers)
        n_events = len(events)
        points = np.zeros((n_swimmers, n_events))

        team_normalized = normalize_team_name(team)

        for i, swimmer in enumerate(swimmers):
            for j, event in enumerate(events):
                points[i, j] = self._get_expected_points(
                    psych, swimmer, event, team_normalized
                )

        return points

    def _get_expected_points(
        self, psych: MeetPsychSheet, swimmer: str, event: str, team: str
    ) -> float:
        """
        Calculate expected points for swimmer in event.

        Uses seed rank to predict placement and applies scoring rules.
        """
        entries = psych.get_event_entries(event)

        # Find swimmer's entry
        swimmer_entry = None
        for e in entries:
            if e.swimmer_name == swimmer and normalize_team_name(e.team) == team:
                swimmer_entry = e
                break

        if not swimmer_entry:
            return 0.0  # Swimmer not entered in this event

        # Get placement considering team max scorers
        # For now, use seed rank directly (assumes seed order = final order)
        place = swimmer_entry.seed_rank

        # Check if swimmer would score (max 4 per team at VCAC)
        max_scorers = getattr(self.rules, "max_scorers_per_team_individual", 4)

        # Count how many teammates are ahead
        teammates_ahead = sum(
            1
            for e in entries
            if normalize_team_name(e.team) == team
            and e.seed_rank < swimmer_entry.seed_rank
        )

        if teammates_ahead >= max_scorers:
            return 0.0  # Won't score (exhibition)

        # Get points for this placement
        points_table = self.rules.individual_points
        if place <= len(points_table):
            return float(points_table[place - 1])

        return 0.0

    def _solve_milp(
        self,
        swimmers: List[str],
        events: List[str],
        point_matrix: np.ndarray,
        divers: Set[str],
        team: str,
    ) -> OptimizationResult:
        """
        Solve optimization using Mixed Integer Linear Programming.

        Decision variables: x[i,j] = 1 if swimmer i is assigned to event j
        Objective: maximize sum of expected points
        Constraints:
          - Each swimmer ≤ 2 individual events (adjusted for diving)
        """
        from scipy.optimize import milp, LinearConstraint, Bounds

        n_swimmers = len(swimmers)
        n_events = len(events)
        n_vars = n_swimmers * n_events

        # Flatten point matrix to objective vector
        # We want to MAXIMIZE, but milp MINIMIZES, so negate
        c = -point_matrix.flatten()

        # Build constraints
        constraint_matrices = []
        constraint_lb = []
        constraint_ub = []

        # Constraint 1: Each swimmer ≤ 2 individual events (adjusted for diving)
        for i, swimmer in enumerate(swimmers):
            # Sum of x[i, :] <= 2 (or 1 if diver)
            A_row = np.zeros(n_vars)
            for j in range(n_events):
                A_row[i * n_events + j] = 1

            # Divers get 1 fewer slot (since diving counts as 1 individual)
            max_events = 1 if swimmer in divers else 2

            constraint_matrices.append(A_row)
            constraint_lb.append(-np.inf)
            constraint_ub.append(max_events)

        # Convert to matrix form
        if constraint_matrices:
            A = np.vstack(constraint_matrices)
            constraints = LinearConstraint(A, lb=constraint_lb, ub=constraint_ub)
        else:
            constraints = []

        # Variable bounds: binary (0 or 1)
        bounds = Bounds(lb=0, ub=1)

        # All variables are binary integers
        integrality = np.ones(n_vars, dtype=int)

        # Solve
        result = milp(
            c=c,
            constraints=constraints if constraint_matrices else None,
            bounds=bounds,
            integrality=integrality,
        )

        if result.success:
            # Parse solution
            x = result.x.round().astype(int)
            assignments = {}

            for i, swimmer in enumerate(swimmers):
                assigned_events = []
                for j, event in enumerate(events):
                    if x[i * n_events + j] > 0.5:
                        assigned_events.append(event)

                if assigned_events or swimmer in divers:
                    assignment = SwimmerAssignment(
                        swimmer_name=swimmer,
                        team=team,
                        individual_events=assigned_events,
                        is_diver=swimmer in divers,
                    )
                    # Calculate expected points for this swimmer
                    assignment.expected_points = sum(
                        point_matrix[i, events.index(e)] for e in assigned_events
                    )
                    assignments[swimmer] = assignment

            return OptimizationResult(
                assignments=assignments,
                total_points=-result.fun,  # Negate back since we minimized -objective
                current_points=0,  # Filled in later
                improvement=0,
                status="optimal",
            )
        else:
            raise RuntimeError(f"MILP solver failed: {result.message}")

    def _calculate_current_points(
        self,
        psych: MeetPsychSheet,
        swimmers: List[str],
        events: List[str],
        swimmer_events: Dict[str, Dict[str, PsychSheetEntry]],
        team: str,
    ) -> float:
        """
        Calculate points with current psych sheet assignments.

        Assumes all entered events are swum (up to 2 best per swimmer).
        """
        total = 0.0
        team_normalized = normalize_team_name(team)

        for swimmer in swimmers:
            # Get swimmer's entries sorted by expected points
            entries_with_points = []
            for event, entry in swimmer_events.get(swimmer, {}).items():
                points = self._get_expected_points(
                    psych, swimmer, event, team_normalized
                )
                entries_with_points.append((points, event))

            # Take top 2 by points
            entries_with_points.sort(key=lambda x: -x[0])
            for points, event in entries_with_points[:2]:
                total += points

        return total


def compare_assignments(
    psych: MeetPsychSheet,
    current: Dict[str, List[str]],
    optimized: OptimizationResult,
    team: str = "Seton",
) -> Dict:
    """
    Compare current assignments to optimized assignments.

    Args:
        psych: Meet psych sheet
        current: Current assignments {swimmer: [events]}
        optimized: Optimized result
        team: Team name

    Returns:
        Comparison dict with changes and impact
    """
    changes = []

    for swimmer, assignment in optimized.assignments.items():
        current_events = set(current.get(swimmer, []))
        new_events = set(assignment.individual_events)

        added = new_events - current_events
        removed = current_events - new_events

        if added or removed:
            changes.append(
                {
                    "swimmer": swimmer,
                    "added": list(added),
                    "removed": list(removed),
                    "expected_points": assignment.expected_points,
                }
            )

    return {
        "changes": changes,
        "total_changes": len(changes),
        "current_points": optimized.current_points,
        "optimized_points": optimized.total_points,
        "improvement": optimized.improvement,
        "status": optimized.status,
    }
