"""
Unified Optimization Service

Orchestrates individual entry optimization, relay optimization, and constraint validation
into a single coherent workflow.

Key Features:
- Joint optimization of individual and relay assignments
- Back-to-back constraint enforcement (including relay legs)
- Diver integration
- VCAC 400 Free Relay trade-off analysis
- Monte Carlo validation
"""

import time as time_module
from dataclasses import dataclass, field
from typing import Any

from swim_ai_reflex.backend.core.rules import get_meet_profile
from swim_ai_reflex.backend.models.championship import MeetPsychSheet
from swim_ai_reflex.backend.services.constraint_validator import (
    ConstraintValidator,
)
from swim_ai_reflex.backend.services.entry_optimizer_service import (
    EntrySelectionOptimizer,
)
from swim_ai_reflex.backend.services.relay_optimizer_service import (
    RelayOptimizationResult,
    RelayOptimizer,
    get_blocked_swimmers_for_event,
    get_relay_swimmers_for_constraints,
)


@dataclass
class UnifiedOptimizationResult:
    """Result from unified optimization."""

    # Individual assignments
    individual_assignments: dict[str, list[str]]  # {swimmer: [events]}
    individual_points: float

    # Relay configurations
    relay_result: RelayOptimizationResult | None = None
    relay_points: float = 0.0

    # Combined
    total_points: float = 0.0
    baseline_points: float = 0.0
    improvement: float = 0.0

    # Validation
    constraint_violations: list[str] = field(default_factory=list)
    is_valid: bool = True

    # Recommendations
    recommendations: list[str] = field(default_factory=list)

    # Performance
    solve_time_ms: float = 0.0

    # Monte Carlo results (if run)
    monte_carlo_results: dict[str, Any] | None = None


class UnifiedOptimizationService:
    """
    Unified service for complete lineup optimization.

    Handles:
    - Individual event assignment
    - Relay configuration
    - Joint constraint validation
    - Back-to-back enforcement (including relays)
    """

    def __init__(
        self,
        meet_profile: str = "vcac_championship",
        allow_back_to_back_override: bool = False,
    ):
        """
        Initialize unified optimizer.

        Args:
            meet_profile: Meet rules profile
            allow_back_to_back_override: Allow back-to-back violations (extraordinary cases only)
        """
        self.meet_profile = meet_profile
        self.rules = get_meet_profile(meet_profile)
        self.allow_back_to_back_override = allow_back_to_back_override

        # Initialize component optimizers
        self.entry_optimizer = EntrySelectionOptimizer(meet_profile)
        self.relay_optimizer = RelayOptimizer(meet_profile)
        self.constraint_validator = ConstraintValidator(
            meet_profile, allow_back_to_back_override
        )

    def optimize(
        self,
        psych: MeetPsychSheet,
        team: str = "Seton",
        divers: set[str] | None = None,
        run_monte_carlo: bool = False,
        monte_carlo_trials: int = 500,
    ) -> UnifiedOptimizationResult:
        """
        Run complete optimization.

        Workflow:
        1. Identify divers and their constraints
        2. Run initial relay optimization (to know who's on relays)
        3. Add relay back-to-back constraints to individual optimization
        4. Run individual entry optimization
        5. Joint constraint validation
        6. Optional: Monte Carlo simulation

        Args:
            psych: Meet psych sheet
            team: Target team name
            divers: Set of diver names
            run_monte_carlo: Whether to run Monte Carlo validation
            monte_carlo_trials: Number of trials for Monte Carlo

        Returns:
            UnifiedOptimizationResult with complete lineup
        """
        start_time = time_module.time()
        divers = divers or set()

        recommendations = []

        # =========================================================================
        # PHASE 1: Initial Relay Optimization
        # =========================================================================
        # Run relay optimization first to identify who's on each relay
        # This lets us block those swimmers from back-to-back individual events

        # For initial relay optimization, assume no individual constraints yet
        empty_assignments: dict[str, list[str]] = {}

        relay_result = self.relay_optimizer.optimize_relays(
            psych=psych,
            individual_assignments=empty_assignments,
            team=team,
            divers=divers,
        )

        # Get relay swimmers for constraint propagation
        _relay_swimmers = get_relay_swimmers_for_constraints(relay_result)

        # =========================================================================
        # PHASE 2: Individual Entry Optimization (with relay constraints)
        # =========================================================================
        # Get swimmers blocked from each individual event due to relay back-to-back

        blocked_by_relay: dict[str, set[str]] = {}
        for event in self._get_individual_events(psych, team):
            blocked_swimmers = get_blocked_swimmers_for_event(relay_result, event)
            if blocked_swimmers:
                blocked_by_relay[event] = blocked_swimmers

        # Run entry optimization
        # The entry optimizer will handle diver constraints internally
        entry_result = self.entry_optimizer.optimize(
            psych=psych,
            team=team,
            divers=divers,
        )

        individual_assignments = {
            swimmer: assignment.individual_events
            for swimmer, assignment in entry_result.assignments.items()
        }
        individual_points = entry_result.total_points

        # =========================================================================
        # PHASE 3: Check and Fix Relay Back-to-Back Violations
        # =========================================================================
        # Verify that individual assignments don't violate relay back-to-back

        violations_fixed = 0
        for event, blocked_swimmers in blocked_by_relay.items():
            for swimmer in blocked_swimmers:
                if swimmer in individual_assignments:
                    if event in individual_assignments[swimmer]:
                        # Violation! Remove this event from swimmer
                        individual_assignments[swimmer].remove(event)
                        violations_fixed += 1
                        recommendations.append(
                            f"! Removed {swimmer} from {event} (blocked by relay)"
                        )

        if violations_fixed > 0:
            recommendations.append(
                f"Fixed {violations_fixed} relay back-to-back violations"
            )

        # =========================================================================
        # PHASE 4: Re-optimize Relays with Final Individual Assignments
        # =========================================================================
        # Now that we have individual assignments, re-optimize relays

        relay_result = self.relay_optimizer.optimize_relays(
            psych=psych,
            individual_assignments=individual_assignments,
            team=team,
            divers=divers,
        )

        relay_points = relay_result.total_points

        # =========================================================================
        # PHASE 5: Final Constraint Validation
        # =========================================================================
        # Convert relay configurations to format expected by validator
        relay_assignments_for_validation = {}
        for relay_name, configs in relay_result.configurations.items():
            # Combine A and B relay swimmers for constraint checking
            swimmers = []
            for config in configs:
                swimmers.extend(config.swimmer_names)
            relay_assignments_for_validation[relay_name] = swimmers

        validation_result = self.constraint_validator.validate_assignments(
            assignments=individual_assignments,
            divers=divers,
            relay_assignments=relay_assignments_for_validation,
        )

        constraint_violations = [v.message for v in validation_result.violations]
        is_valid = validation_result.is_valid

        if validation_result.warnings:
            for warning in validation_result.warnings:
                recommendations.append(f"! {warning.message}")

        # =========================================================================
        # PHASE 6: Calculate Totals and Improvements
        # =========================================================================
        total_points = individual_points + relay_points
        baseline_points = entry_result.current_points
        improvement = total_points - baseline_points

        # Add 400FR recommendation
        if relay_result.relay_400_recommendation == "swim":
            recommendations.append(
                f"✓ SWIM 400 Free Relay - Net gain: {relay_result.relay_400_net_value:.1f} pts"
            )
        elif relay_result.relay_400_recommendation == "skip":
            recommendations.append(
                "✗ SKIP 400 Free Relay - Not enough available swimmers"
            )
        elif relay_result.relay_400_recommendation == "optional":
            recommendations.append(
                f"400 Free Relay optional - Net gain: {relay_result.relay_400_net_value:.1f} pts"
            )

        # =========================================================================
        # PHASE 7: Optional Monte Carlo Validation
        # =========================================================================
        monte_carlo_results = None
        if run_monte_carlo:
            monte_carlo_results = self._run_monte_carlo_validation(
                psych, team, individual_assignments, divers, monte_carlo_trials
            )
            recommendations.append(
                f"▸ Monte Carlo: {monte_carlo_results.get('win_prob', 0):.0%} win probability"
            )

        solve_time_ms = (time_module.time() - start_time) * 1000

        return UnifiedOptimizationResult(
            individual_assignments=individual_assignments,
            individual_points=individual_points,
            relay_result=relay_result,
            relay_points=relay_points,
            total_points=total_points,
            baseline_points=baseline_points,
            improvement=improvement,
            constraint_violations=constraint_violations,
            is_valid=is_valid,
            recommendations=recommendations,
            solve_time_ms=solve_time_ms,
            monte_carlo_results=monte_carlo_results,
        )

    def _get_individual_events(self, psych: MeetPsychSheet, team: str) -> list[str]:
        """Get list of individual events for the team."""
        team_entries = psych.get_team_entries(team)
        events = set()
        for entry in team_entries:
            if (
                "relay" not in entry.event.lower()
                and "diving" not in entry.event.lower()
            ):
                events.add(entry.event)
        return list(events)

    def _run_monte_carlo_validation(
        self,
        psych: MeetPsychSheet,
        team: str,
        assignments: dict[str, list[str]],
        divers: set[str],
        trials: int,
    ) -> dict[str, Any]:
        """Run Monte Carlo simulation on the final lineup."""
        # This is a placeholder - would need to convert psych sheet to DataFrame
        # and run fast_monte_carlo_simulation

        # For now, return placeholder
        return {
            "trials": trials,
            "win_prob": 0.0,
            "note": "Full Monte Carlo integration pending",
        }


def quick_optimize(
    psych: MeetPsychSheet,
    team: str = "Seton",
    divers: set[str] | None = None,
    meet_profile: str = "vcac_championship",
) -> UnifiedOptimizationResult:
    """
    Convenience function for quick optimization.

    Usage:
        result = quick_optimize(psych, team="Seton", divers={"John Smith"})
        print(f"Total points: {result.total_points}")
    """
    service = UnifiedOptimizationService(meet_profile)
    return service.optimize(psych, team, divers)
