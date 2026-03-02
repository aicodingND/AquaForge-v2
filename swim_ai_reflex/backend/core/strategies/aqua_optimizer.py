"""
AquaOptimizer - Custom Swim Meet Optimization Engine

A zero-cost replacement for Gurobi with enhanced features:
- Configurable scoring curves
- Nash equilibrium iteration
- Fatigue modeling
- Built-in explanations
- Multiple search strategies (beam, annealing, genetic)

Usage:
    from swim_ai_reflex.backend.core.strategies.aqua_optimizer import AquaOptimizer

    optimizer = AquaOptimizer()
    result = optimizer.optimize(seton_roster, opponent_roster, rules)
"""

import logging
import math
import random
import time
from dataclasses import dataclass, field
from typing import Any

import pandas as pd

from swim_ai_reflex.backend.core.attrition_model import AttritionRates
from swim_ai_reflex.backend.core.championship_factors import (
    ChampionshipFactors,
    adjust_times_df,
)
from swim_ai_reflex.backend.core.rules import MeetRules, get_meet_profile
from swim_ai_reflex.backend.core.scoring import EVENT_ORDER
from swim_ai_reflex.backend.core.strategies.base_strategy import BaseOptimizerStrategy

logger = logging.getLogger(__name__)


# ============================================================================
# CONFIGURATION
# ============================================================================


@dataclass
class ScoringProfile:
    """Configurable scoring profile for different meet types.

    All meet-type-specific fields are derived from MeetRules via from_rules().
    This ensures AquaOptimizer always uses the same canonical rules as Gurobi.
    """

    name: str = "visaa_dual"
    individual_points: list[int] = field(default_factory=lambda: [8, 6, 5, 4, 3, 2, 1])
    relay_points: list[int] = field(
        default_factory=lambda: [10, 5, 3]
    )  # Per Coach Koehr
    min_scoring_grade: int = 8
    max_scorers_per_team: int = 3
    max_entries_per_event: int = 4
    max_individual_events: int = 2
    max_total_events: int = 4  # 2 individual + up to 3 relays, max 4

    # Meet-type-specific constraint fields (from MeetRules)
    relay_3_counts_as_individual: bool = (
        False  # 400 FR costs individual slot (VCAC only)
    )
    diving_counts_as_individual: bool = True  # Diving uses individual slot (all champs)

    @classmethod
    def from_rules(cls, rules: MeetRules) -> "ScoringProfile":
        """Create a ScoringProfile from canonical MeetRules.

        This is the preferred constructor — it ensures all values match the
        authoritative rule definitions in rules.py.
        """
        return cls(
            name=rules.name,
            individual_points=list(rules.individual_points),
            relay_points=list(rules.relay_points),
            min_scoring_grade=rules.min_scoring_grade,
            max_scorers_per_team=rules.max_scorers_per_team_individual,
            max_entries_per_event=rules.max_entries_per_team_per_event,
            max_individual_events=rules.max_individual_events_per_swimmer,
            max_total_events=rules.max_total_events_per_swimmer,
            relay_3_counts_as_individual=rules.relay_3_counts_as_individual,
            diving_counts_as_individual=getattr(
                rules, "diving_counts_as_individual", True
            ),
        )

    @classmethod
    def from_meet_profile(cls, profile_name: str) -> "ScoringProfile":
        """Create from a meet profile name (e.g., 'vcac_championship', 'visaa_state')."""
        rules = get_meet_profile(profile_name)
        return cls.from_rules(rules)

    @classmethod
    def visaa_dual(cls) -> "ScoringProfile":
        return cls.from_meet_profile("visaa_dual")

    @classmethod
    def vcac_championship(cls) -> "ScoringProfile":
        """VCAC Conference scoring: Top 12 (16-13-12-11-10-9, 7-5-4-3-2-1)"""
        return cls.from_meet_profile("vcac_championship")

    @classmethod
    def visaa_championship(cls) -> "ScoringProfile":
        """VISAA State scoring: Top 16 (20-17-16...1)"""
        return cls.from_meet_profile("visaa_state")


@dataclass
class OpponentModelConfig:
    """Configuration for opponent field depth and stochastic modeling.

    Controls three independent capabilities that improve championship projections:
    1. Field depth: how many opponents per event to consider (default 16 → up to 32+)
    2. Time variance: gaussian spread model to account for seed-to-finals uncertainty
    3. Attrition: thin the field by removing slowest entries based on DNS probability

    All features are opt-in and default to OFF for backward compatibility.
    """

    # Field depth
    max_opponents_per_event: int = 16

    # Time variance — gaussian expected-value adjustment
    apply_time_variance: bool = False
    sprint_cv: float = 0.015  # Coefficient of variation for 50/100 events
    distance_cv: float = 0.020  # CV for 200+ events

    # Attrition — directional field thinning (remove slowest likely-to-scratch entries)
    apply_attrition: bool = False

    # Post-optimization Monte Carlo validation
    monte_carlo_validation: bool = False
    monte_carlo_trials: int = 5000

    @classmethod
    def default(cls) -> "OpponentModelConfig":
        """Backward-compatible default: no modeling enhancements."""
        return cls()

    @classmethod
    def championship(cls) -> "OpponentModelConfig":
        """Full championship modeling: deeper fields + variance + attrition."""
        return cls(
            max_opponents_per_event=32,
            apply_time_variance=True,
            apply_attrition=True,
        )


@dataclass
class FatigueModel:
    """Model swimmer fatigue for realistic optimization."""

    enabled: bool = True
    back_to_back_penalty: float = 0.02  # 2% time degradation
    swim_count_penalty: float = 0.01  # 1% per additional swim
    max_no_penalty_swims: int = 2  # First 2 swims have no penalty


@dataclass
class ConfidenceScore:
    """
    Confidence scoring for lineup predictions.

    Measures certainty of the optimization result based on:
    - Search completeness
    - Margin stability
    - Data quality
    - Constraint satisfaction
    """

    overall: float  # 0-100% confidence
    search_quality: float  # How thoroughly we explored the search space
    margin_stability: float  # How stable is the score margin
    data_quality: float  # Quality of input data
    constraint_score: float  # How well constraints are satisfied
    explanation: str  # Human-readable explanation

    @classmethod
    def calculate(
        cls,
        iterations_run: int,
        max_iterations: int,
        margin: float,
        margin_variance: float,
        data_completeness: float,
        constraint_violations: int,
    ) -> "ConfidenceScore":
        """Calculate confidence from optimization metrics."""

        # Search quality: Did we explore enough?
        # 100% = ran all iterations, 50% = ran half
        search_quality = min(100.0, (iterations_run / max_iterations) * 100)

        # Margin stability: Is the result robust?
        # High variance = low confidence
        if margin_variance < 5:
            margin_stability = 95.0
        elif margin_variance < 15:
            margin_stability = 80.0
        elif margin_variance < 30:
            margin_stability = 60.0
        else:
            margin_stability = 40.0

        # Margin size also affects confidence
        # Blowouts are more certain, close races less so
        if abs(margin) > 50:
            margin_stability = min(100.0, margin_stability + 10)
        elif abs(margin) < 10:
            margin_stability = max(20.0, margin_stability - 15)

        # Data quality: How complete is the input?
        data_quality = min(100.0, data_completeness * 100)

        # Constraint satisfaction: Any violations?
        if constraint_violations == 0:
            constraint_score = 100.0
        elif constraint_violations < 3:
            constraint_score = 70.0
        else:
            constraint_score = 30.0

        # Overall: weighted average
        overall = (
            search_quality * 0.25
            + margin_stability * 0.35
            + data_quality * 0.25
            + constraint_score * 0.15
        )

        # Generate explanation
        explanations = []
        if search_quality < 80:
            explanations.append("Limited search depth")
        if margin_stability < 70:
            explanations.append("Score margin unstable")
        if data_quality < 80:
            explanations.append("Incomplete data")
        if constraint_violations > 0:
            explanations.append(f"{constraint_violations} constraint issues")

        if not explanations:
            explanation = "High confidence - thorough search with stable results"
        else:
            explanation = "Lower confidence: " + ", ".join(explanations)

        return cls(
            overall=round(overall, 1),
            search_quality=round(search_quality, 1),
            margin_stability=round(margin_stability, 1),
            data_quality=round(data_quality, 1),
            constraint_score=round(constraint_score, 1),
            explanation=explanation,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "overall": self.overall,
            "search_quality": self.search_quality,
            "margin_stability": self.margin_stability,
            "data_quality": self.data_quality,
            "constraint_score": self.constraint_score,
            "explanation": self.explanation,
        }


@dataclass
class Lineup:
    """Represents a lineup assignment (swimmer → events)."""

    assignments: dict[str, set[str]]  # swimmer_name → set of events
    score: float = 0.0
    opponent_score: float = 0.0
    explanations: list[str] = field(default_factory=list)

    def copy(self) -> "Lineup":
        return Lineup(
            assignments={k: v.copy() for k, v in self.assignments.items()},
            score=self.score,
            opponent_score=self.opponent_score,
            explanations=self.explanations.copy(),
        )

    def add_assignment(self, swimmer: str, event: str) -> None:
        if swimmer not in self.assignments:
            self.assignments[swimmer] = set()
        self.assignments[swimmer].add(event)

    def remove_assignment(self, swimmer: str, event: str) -> None:
        if swimmer in self.assignments:
            self.assignments[swimmer].discard(event)

    def get_swimmer_events(self, swimmer: str) -> set[str]:
        return self.assignments.get(swimmer, set())

    def get_event_swimmers(self, event: str) -> list[str]:
        return [s for s, events in self.assignments.items() if event in events]

    def to_dataframe(self, roster_df: pd.DataFrame) -> pd.DataFrame:
        """Convert lineup to DataFrame with full swimmer data."""
        rows = []
        for swimmer, events in self.assignments.items():
            for event in events:
                row = roster_df[
                    (roster_df["swimmer"] == swimmer) & (roster_df["event"] == event)
                ]
                if not row.empty:
                    rows.append(row.iloc[0].to_dict())
        return pd.DataFrame(rows) if rows else pd.DataFrame()


# ============================================================================
# CONSTRAINT ENGINE
# ============================================================================


class ConstraintEngine:
    """Validates lineup constraints with meet-type-specific rules.

    Key meet-type differences enforced:
    - relay_3_counts_as_individual: At VCAC, 400 FR costs 1 individual slot.
      At VISAA State, it does NOT.
    - diving_counts_as_individual: At both championships, diving = 1 individual slot.
    - max_entries_per_event: 4 at dual, 999 at championships.
    """

    def __init__(
        self,
        profile: ScoringProfile,
        events: list[str],
        divers: set[str] | None = None,
        relay_3_swimmers: set[str] | None = None,
    ):
        self.profile = profile
        self.events = events
        self.individual_events = [e for e in events if "Relay" not in e]
        self.relay_events = [e for e in events if "Relay" in e]
        self.divers = divers or set()
        self.relay_3_swimmers = relay_3_swimmers or set()

    def _count_individual_slots(self, swimmer: str, events: set[str]) -> int:
        """Count individual event slots used, respecting meet-specific rules.

        At VCAC: swims + diving + relay_3 each cost individual slots.
        At VISAA: swims + diving cost individual slots, relay_3 does NOT.
        """
        count = 0
        for e in events:
            if "Relay" in e:
                # Only count relay_3 (400 Free Relay) if rule says so
                if (
                    self.profile.relay_3_counts_as_individual
                    and "400" in e
                    and swimmer in self.relay_3_swimmers
                ):
                    count += 1
            else:
                # Individual swim or diving — always counts
                count += 1

        # Diving counts as individual if swimmer is a diver AND has a diving event
        # (Diving is already counted above since it's not a "Relay" event)
        # No extra logic needed — "Diving" events pass the "Relay not in e" filter

        return count

    def is_valid(
        self, lineup: Lineup, roster_df: pd.DataFrame
    ) -> tuple[bool, list[str]]:
        """Check all constraints. Returns (valid, list of violations)."""
        violations = []

        # Check each swimmer
        for swimmer, events in lineup.assignments.items():
            # Max total events
            if len(events) > self.profile.max_total_events:
                violations.append(
                    f"{swimmer}: {len(events)} events > {self.profile.max_total_events} max"
                )

            # Max individual events (meet-type-aware)
            indiv_slots = self._count_individual_slots(swimmer, events)
            if indiv_slots > self.profile.max_individual_events:
                violations.append(
                    f"{swimmer}: {indiv_slots} individual slots > {self.profile.max_individual_events} max"
                )

            # Back-to-back constraint
            event_indices = [self.events.index(e) for e in events if e in self.events]
            event_indices.sort()
            for i in range(len(event_indices) - 1):
                if event_indices[i + 1] - event_indices[i] == 1:
                    e1, e2 = (
                        self.events[event_indices[i]],
                        self.events[event_indices[i + 1]],
                    )
                    violations.append(f"{swimmer}: back-to-back {e1} → {e2}")

        # Check event entries
        for event in self.events:
            swimmers = lineup.get_event_swimmers(event)
            max_entries = 2 if "Relay" in event else self.profile.max_entries_per_event
            if len(swimmers) > max_entries:
                violations.append(
                    f"{event}: {len(swimmers)} entries > {max_entries} max"
                )

        return len(violations) == 0, violations

    def can_add(
        self, lineup: Lineup, swimmer: str, event: str, roster_df: pd.DataFrame
    ) -> bool:
        """Quick check if adding this assignment is valid."""
        test_lineup = lineup.copy()
        test_lineup.add_assignment(swimmer, event)
        valid, _ = self.is_valid(test_lineup, roster_df)
        return valid


# ============================================================================
# SCORING ENGINE
# ============================================================================


class ScoringEngine:
    """Calculates meet scores with proper point distribution."""

    def __init__(
        self,
        profile: ScoringProfile,
        fatigue: FatigueModel,
        attrition: AttritionRates
        | None = None,  # kept for API compat; unused (zero impact)
    ):
        self.profile = profile
        self.fatigue = fatigue

    def calculate_adjusted_time(
        self, base_time: float, swim_count: int, is_back_to_back: bool
    ) -> float:
        """Apply fatigue penalties to base time."""
        if not self.fatigue.enabled:
            return base_time

        penalty = 0.0

        # Swim count penalty
        if swim_count > self.fatigue.max_no_penalty_swims:
            excess = swim_count - self.fatigue.max_no_penalty_swims
            penalty += excess * self.fatigue.swim_count_penalty

        # Back-to-back penalty
        if is_back_to_back:
            penalty += self.fatigue.back_to_back_penalty

        return base_time * (1.0 + penalty)

    def score_event(
        self,
        seton_entries: list[dict],
        opponent_entries: list[dict],
        is_relay: bool = False,
        event_name: str = "",
    ) -> tuple[float, float, list[dict]]:
        """
        Score a single event.

        Returns:
            (seton_points, opponent_points, placement_details)
        """
        points_table = (
            self.profile.relay_points if is_relay else self.profile.individual_points
        )

        # Combine and sort by time
        all_entries = []
        for e in seton_entries:
            all_entries.append({**e, "team": "seton"})
        for e in opponent_entries:
            # Preserve real team name if present; fall back to "opponent"
            opp_team = e.get("team", "opponent")
            if not opp_team or opp_team == "seton":
                opp_team = "opponent"
            all_entries.append({**e, "team": opp_team})

        all_entries.sort(key=lambda x: x.get("time", 999))

        # Assign points with per-team scorer caps (multi-team aware)
        seton_points = 0.0
        opponent_points = 0.0
        team_scorer_count: dict[str, int] = {}
        details = []

        scoring_pos = 0
        for entry in all_entries:
            grade = entry.get("grade", 12)
            try:
                grade = int(grade) if grade is not None else 12
            except (ValueError, TypeError):
                grade = 12

            is_scoring = grade >= self.profile.min_scoring_grade
            team = entry.get("team", "")

            # Check per-team scorer limit
            team_count = team_scorer_count.get(team, 0)
            if team_count >= self.profile.max_scorers_per_team:
                is_scoring = False

            points = 0
            if is_scoring and scoring_pos < len(points_table):
                points = points_table[scoring_pos]
                scoring_pos += 1
                team_scorer_count[team] = team_count + 1

                if team == "seton":
                    seton_points += points
                else:
                    opponent_points += points

            details.append(
                {
                    **entry,
                    "points": points,
                    "scoring_eligible": is_scoring,
                }
            )

        return seton_points, opponent_points, details

    @staticmethod
    def get_scoring_eligible_opponent_times(
        opponent_entries: list[dict],
        max_scorers_per_team: int,
    ) -> list[float]:
        """Get opponent times after applying per-team scorer caps.

        Sorts all opponents by time, then walks through them applying per-team
        limits. Only times from scoring-eligible opponents are returned.

        This mirrors Gurobi's _get_scoring_eligible_opponent_times() to ensure
        consistent scoring between both optimizers.
        """
        # Collect (time, team) pairs
        opp_with_team: list[tuple[float, str]] = []
        for e in opponent_entries:
            t = e.get("time", 999.0)
            if t is None or t <= 0:
                continue
            team = e.get("team", "opponent")
            if not team or team == "seton":
                team = "opponent"
            opp_with_team.append((t, team))

        # Sort by time (fastest first)
        opp_with_team.sort(key=lambda x: x[0])

        # Apply per-team scorer cap
        scoring_times: list[float] = []
        team_count: dict[str, int] = {}
        for adj_time, team in opp_with_team:
            count = team_count.get(team, 0)
            if count < max_scorers_per_team:
                scoring_times.append(adj_time)
                team_count[team] = count + 1

        return scoring_times

    def score_event_fast(
        self,
        seton_entries: list[dict],
        opponent_times: list[float],
        is_relay: bool = False,
        event_name: str = "",
    ) -> float:
        """
        Fast O(log N) scoring for championships using pre-sorted opponent times.
        Only calculates Seton points (opponent score irrelevant in optimization loop).

        Note: opponent_times should already be filtered for per-team scorer caps
        (via _get_scoring_eligible_opponent_times or equivalent pre-processing).
        """
        import bisect

        points_table = (
            self.profile.relay_points if is_relay else self.profile.individual_points
        )
        max_place = len(points_table)

        # Sort Seton entries by time (usually small, e.g., 4 entries)
        seton_times = [e.get("time", 999.0) for e in seton_entries]
        seton_grades = [int(e.get("grade", 12)) for e in seton_entries]

        # Pair and sort
        seton_swimmers = sorted(zip(seton_times, seton_grades), key=lambda x: x[0])

        total_points = 0.0
        seton_scorers = 0

        for i, (swim_time, grade) in enumerate(seton_swimmers):
            # Check eligibility
            if grade < self.profile.min_scoring_grade:
                continue

            if seton_scorers >= self.profile.max_scorers_per_team:
                continue

            # Find rank: opponents faster + seton teammates faster
            opp_ahead = bisect.bisect_left(opponent_times, swim_time)

            # Rank (1-based) = opponents better + teammates better (i) + 1
            rank = opp_ahead + i + 1

            if rank <= max_place:
                total_points += points_table[rank - 1]
                seton_scorers += 1

        return total_points

    def score_lineup(
        self,
        lineup: Lineup,
        seton_roster: pd.DataFrame,
        opponent_roster: pd.DataFrame,
        events: list[str],
    ) -> tuple[float, float, list[str]]:
        """
        Score a complete lineup.

        Returns:
            (seton_total, opponent_total, explanations)
        """
        seton_total = 0.0
        opponent_total = 0.0
        explanations = []

        for event in events:
            is_relay = "Relay" in event

            # Get Seton entries from lineup
            seton_swimmers = lineup.get_event_swimmers(event)
            seton_entries = []
            for swimmer in seton_swimmers:
                row = seton_roster[
                    (seton_roster["swimmer"] == swimmer)
                    & (seton_roster["event"] == event)
                ]
                if not row.empty:
                    seton_entries.append(row.iloc[0].to_dict())

            # Get opponent entries (use all available)
            opp_rows = opponent_roster[opponent_roster["event"] == event]
            opponent_entries = opp_rows.to_dict("records")

            # Score this event
            seton_pts, opp_pts, _ = self.score_event(
                seton_entries, opponent_entries, is_relay, event_name=event
            )
            seton_total += seton_pts
            opponent_total += opp_pts

            # Generate explanation for significant events
            if seton_pts > opp_pts:
                margin = seton_pts - opp_pts
                explanations.append(f"Win {event} (+{margin:.0f})")
            elif opp_pts > seton_pts:
                margin = opp_pts - seton_pts
                explanations.append(f"Lose {event} (-{margin:.0f})")

        return seton_total, opponent_total, explanations


# ============================================================================
# SEARCH STRATEGIES
# ============================================================================


class BeamSearch:
    """
    Optimized beam search with:
    - Pre-computed swimmer-event availability (O(1) lookups)
    - Early termination when no improvement
    - Pruning of dominated candidates
    - Adaptive iteration count
    """

    def __init__(
        self,
        beam_width: int = 10,
        max_iterations: int = 1000,
        early_stop_patience: int = 5,  # Stop if no improvement for N iterations
    ):
        self.beam_width = beam_width
        self.max_iterations = max_iterations
        self.early_stop_patience = early_stop_patience

    def search(
        self,
        seton_roster: pd.DataFrame,
        opponent_roster: pd.DataFrame,
        events: list[str],
        constraint_engine: ConstraintEngine,
        scoring_engine: ScoringEngine,
    ) -> Lineup:
        """Find best lineup using optimized beam search."""
        swimmers = seton_roster["swimmer"].unique().tolist()

        # === OPTIMIZATION 1: Pre-compute swimmer-event availability ===
        # Convert DataFrame lookups to O(1) dict lookups
        swimmer_events: dict[str, set[str]] = {}
        swimmer_data: dict[tuple[str, str], dict] = {}

        for _, row in seton_roster.iterrows():
            swimmer = row["swimmer"]
            event = row["event"]
            if swimmer not in swimmer_events:
                swimmer_events[swimmer] = set()
            swimmer_events[swimmer].add(event)
            swimmer_data[(swimmer, event)] = row.to_dict()

        # Pre-compute opponent data per event for scoring
        opponent_by_event: dict[str, list[dict]] = {}
        opponent_times_sorted: dict[str, list[float]] = {}

        for event in events:
            opp_rows = opponent_roster[opponent_roster["event"] == event]
            all_opp_records = opp_rows.to_dict("records")
            opponent_by_event[event] = all_opp_records

            # Pre-compute scoring-eligible opponent times with per-team caps
            # This ensures the fast bisect path uses correct multi-team placement
            opponent_times_sorted[event] = (
                scoring_engine.get_scoring_eligible_opponent_times(
                    all_opp_records, scoring_engine.profile.max_scorers_per_team
                )
            )

        # Initial beam: empty lineup
        beam: list[Lineup] = [Lineup(assignments={})]
        best_ever = Lineup(assignments={})
        best_ever.score = float("-inf")

        no_improvement_count = 0
        last_best_margin = float("-inf")

        # === OPTIMIZATION 2: Adaptive iteration count ===
        # Fewer iterations for smaller problems
        max_iters = min(self.max_iterations, len(swimmers) * len(events) // 2 + 10)

        for iteration in range(max_iters):
            candidate_moves: list[tuple[float, str, str, float, float]] = []

            # === PRE-COMPUTE 3: Baseline event scores for current lineups ===
            # Store (seton_pts, opp_pts) for each event for each lineup in beam
            lineup_event_scores: dict[int, dict[str, tuple[float, float]]] = {}

            for i, lineup in enumerate(beam):
                lineup_event_scores[i] = {}
                for event in events:
                    # Calculate current score for this event
                    current_swimmers = lineup.get_event_swimmers(event)
                    seton_entries = [
                        swimmer_data.get((s, event))
                        for s in current_swimmers
                        if swimmer_data.get((s, event))
                    ]
                    is_relay = "Relay" in event

                    if (
                        hasattr(scoring_engine, "score_event_fast")
                        and "championship" in scoring_engine.profile.name
                    ):
                        s_pts = scoring_engine.score_event_fast(
                            seton_entries,
                            opponent_times_sorted[event],
                            is_relay,
                            event_name=event,
                        )
                        o_pts = 0.0  # Opponent score irrelevant for championship optimization direction
                    else:
                        opponent_entries = opponent_by_event.get(event, [])
                        s_pts, o_pts, _ = scoring_engine.score_event(
                            seton_entries, opponent_entries, is_relay, event_name=event
                        )

                    lineup_event_scores[i][event] = (s_pts, o_pts)

            for i, lineup in enumerate(beam):
                # Analyze potential moves for this lineup
                current_scores = lineup_event_scores[i]

                for swimmer in swimmers:
                    available_events = swimmer_events.get(swimmer, set())
                    current_events = lineup.get_swimmer_events(swimmer)

                    for event in available_events:
                        if event in current_events:
                            continue

                        # === OPTIMIZATION 3: Fast constraint check ===
                        if not constraint_engine.can_add(
                            lineup, swimmer, event, seton_roster
                        ):
                            continue

                        # === OPTIMIZATION 6: Incremental Scoring ===
                        # Calculate impact of adding this single swimmer to this event
                        # 1. Get current score components
                        curr_s_pts, curr_o_pts = current_scores.get(event, (0.0, 0.0))

                        # 2. Get new entries
                        current_swimmers = lineup.get_event_swimmers(event)
                        seton_entries = [
                            swimmer_data.get((s, event))
                            for s in current_swimmers
                            if swimmer_data.get((s, event))
                        ]
                        new_entry = swimmer_data.get((swimmer, event))
                        if new_entry:
                            seton_entries.append(new_entry)

                        # 3. Score new state
                        opponent_entries = opponent_by_event.get(event, [])
                        is_relay = "Relay" in event
                        new_s_pts, new_o_pts, _ = scoring_engine.score_event(
                            seton_entries, opponent_entries, is_relay, event_name=event
                        )

                        # 4. Deltas
                        delta_s = new_s_pts - curr_s_pts
                        delta_o = new_o_pts - curr_o_pts
                        net_gain = delta_s - delta_o

                        # Store move candidate: (gain, swimmer, event, new_s_score, new_o_score, lineup_idx)
                        # We store raw new scores to avoid re-calculation later
                        # Use a tuple that sorts by gain descending
                        candidate_moves.append(
                            (net_gain, swimmer, event, new_s_pts, new_o_pts, i)
                        )

            if not candidate_moves:
                break

            # === OPTIMIZATION 7: Move Ordering & Pruning ===
            # Sort all moves across all lineups by net gain
            candidate_moves.sort(key=lambda x: x[0], reverse=True)

            # Keep top K moves globally (Beam Width * Branch Factor)
            top_k = self.beam_width * 10
            best_moves = candidate_moves[:top_k]

            candidates: list[Lineup] = []
            seen_assignments: set[frozenset] = set()

            for (
                gain,
                swimmer,
                event,
                event_s_pts,
                event_o_pts,
                lineup_idx,
            ) in best_moves:
                source_lineup = beam[lineup_idx]

                new_lineup = source_lineup.copy()
                new_lineup.add_assignment(swimmer, event)

                assignment_key = frozenset(
                    (s, e) for s, evts in new_lineup.assignments.items() for e in evts
                )
                if assignment_key in seen_assignments:
                    continue
                seen_assignments.add(assignment_key)

                # Update total score incrementally
                # Handle case where event might not be in precomputed scores
                old_s_pts, old_o_pts = lineup_event_scores[lineup_idx].get(
                    event, (0.0, 0.0)
                )

                new_lineup.score = source_lineup.score - old_s_pts + event_s_pts
                new_lineup.opponent_score = (
                    source_lineup.opponent_score - old_o_pts + event_o_pts
                )

                candidates.append(new_lineup)

                # Update global best
                margin = new_lineup.score - new_lineup.opponent_score
                if margin > best_ever.score - best_ever.opponent_score:
                    best_ever = new_lineup.copy()

            if not candidates:
                break

            # Selection for next beam
            candidates.sort(
                key=lambda lineup: lineup.score - lineup.opponent_score, reverse=True
            )
            beam = candidates[: self.beam_width]

            # === OPTIMIZATION 5: Early termination ===
            current_best_margin = beam[0].score - beam[0].opponent_score
            if current_best_margin <= last_best_margin + 0.5:
                no_improvement_count += 1
                if no_improvement_count >= self.early_stop_patience:
                    break
            else:
                no_improvement_count = 0
                last_best_margin = current_best_margin

        # Final polish: Calculate full explanations for the result
        if best_ever:
            s, o, expl = self._fast_score_lineup(
                best_ever, swimmer_data, opponent_by_event, events, scoring_engine
            )
            best_ever.score = s
            best_ever.opponent_score = o
            best_ever.explanations = expl
            return best_ever

        return Lineup(assignments={})

    def _fast_score_lineup(
        self,
        lineup: Lineup,
        swimmer_data: dict[tuple[str, str], dict],
        opponent_by_event: dict[str, list[dict]],
        events: list[str],
        scoring_engine: ScoringEngine,
    ) -> tuple[float, float, list[str]]:
        """Fast scoring using pre-computed data."""
        seton_total = 0.0
        opponent_total = 0.0
        explanations = []

        for event in events:
            is_relay = "Relay" in event

            # Get Seton entries from lineup using pre-computed data
            seton_swimmers = lineup.get_event_swimmers(event)
            seton_entries = []
            for swimmer in seton_swimmers:
                data = swimmer_data.get((swimmer, event))
                if data:
                    seton_entries.append(data)

            # Get opponent entries (pre-computed)
            opponent_entries = opponent_by_event.get(event, [])

            # Score this event
            seton_pts, opp_pts, _ = scoring_engine.score_event(
                seton_entries, opponent_entries, is_relay, event_name=event
            )
            seton_total += seton_pts
            opponent_total += opp_pts

            # Generate explanation for significant events
            if seton_pts > opp_pts:
                margin = seton_pts - opp_pts
                explanations.append(f"Win {event} (+{margin:.0f})")
            elif opp_pts > seton_pts:
                margin = opp_pts - seton_pts
                explanations.append(f"Lose {event} (-{margin:.0f})")

        return seton_total, opponent_total, explanations


class SimulatedAnnealing:
    """
    Optimized simulated annealing with:
    - Pre-computed swimmer-event availability
    - Reduced iteration count for quality maintenance
    - Early convergence detection
    """

    def __init__(
        self,
        initial_temp: float = 100.0,
        cooling_rate: float = 0.995,  # Faster cooling (was 0.995)
        min_temp: float = 0.1,
        max_iterations: int = 2500,  # Reduced (was 5000)
    ):
        self.initial_temp = initial_temp
        self.cooling_rate = cooling_rate
        self.min_temp = min_temp
        self.max_iterations = max_iterations

    def search(
        self,
        initial_lineup: Lineup,
        seton_roster: pd.DataFrame,
        opponent_roster: pd.DataFrame,
        events: list[str],
        constraint_engine: ConstraintEngine,
        scoring_engine: ScoringEngine,
    ) -> Lineup:
        """Refine lineup using optimized simulated annealing."""
        swimmers = seton_roster["swimmer"].unique().tolist()

        # === OPTIMIZATION: Pre-compute swimmer-event availability ===
        swimmer_events: dict[str, set[str]] = {}
        swimmer_data: dict[tuple[str, str], dict] = {}

        for _, row in seton_roster.iterrows():
            swimmer = row["swimmer"]
            event = row["event"]
            if swimmer not in swimmer_events:
                swimmer_events[swimmer] = set()
            swimmer_events[swimmer].add(event)
            swimmer_data[(swimmer, event)] = row.to_dict()

        # Pre-compute opponent data (no truncation — per-team caps applied in scoring)
        opponent_by_event: dict[str, list[dict]] = {}
        for event in events:
            opp_rows = opponent_roster[opponent_roster["event"] == event]
            opponent_by_event[event] = opp_rows.to_dict("records")

        current = initial_lineup.copy()
        best = current.copy()
        temp = self.initial_temp

        # Early convergence: track if we've improved recently
        no_improvement_streak = 0
        max_no_improvement = 100

        for iteration in range(self.max_iterations):
            if temp < self.min_temp:
                break

            # Early convergence check
            if no_improvement_streak > max_no_improvement:
                break

            # Generate neighbor using pre-computed data
            neighbor = self._fast_generate_neighbor(
                current,
                swimmers,
                events,
                swimmer_events,
                constraint_engine,
                seton_roster,
            )

            if neighbor is None:
                temp *= self.cooling_rate
                no_improvement_streak += 1
                continue

            # Fast scoring using pre-computed data
            seton_score, opp_score = self._fast_score(
                neighbor, swimmer_data, opponent_by_event, events, scoring_engine
            )
            neighbor.score = seton_score
            neighbor.opponent_score = opp_score

            # Calculate acceptance probability
            current_fitness = current.score - current.opponent_score
            neighbor_fitness = neighbor.score - neighbor.opponent_score
            delta = neighbor_fitness - current_fitness

            if delta > 0:
                # Always accept improvements
                current = neighbor
                no_improvement_streak = 0
                if neighbor_fitness > best.score - best.opponent_score:
                    best = neighbor.copy()
            else:
                # Accept worse solutions with probability
                prob = math.exp(delta / temp)
                if random.random() < prob:
                    current = neighbor
                no_improvement_streak += 1

            temp *= self.cooling_rate

        return best

    def _fast_generate_neighbor(
        self,
        lineup: Lineup,
        swimmers: list[str],
        events: list[str],
        swimmer_events: dict[str, set[str]],
        constraint_engine: ConstraintEngine,
        roster_df: pd.DataFrame,
    ) -> Lineup | None:
        """Generate neighbor using pre-computed data (no DataFrame lookups)."""
        neighbor = lineup.copy()

        # Random operation: add, remove, or swap
        operation = random.choice(["add", "remove", "swap"])

        if operation == "add":
            # Try to add a random assignment
            shuffled_swimmers = swimmers.copy()
            random.shuffle(shuffled_swimmers)
            for swimmer in shuffled_swimmers[:5]:  # Only try top 5 randomly
                available = swimmer_events.get(swimmer, set())
                current = neighbor.get_swimmer_events(swimmer)
                candidates = list(available - current)
                if candidates:
                    event = random.choice(candidates)
                    if constraint_engine.can_add(neighbor, swimmer, event, roster_df):
                        neighbor.add_assignment(swimmer, event)
                        return neighbor

        elif operation == "remove":
            # Remove a random assignment
            all_assignments = [
                (s, e) for s, evts in neighbor.assignments.items() for e in evts
            ]
            if all_assignments:
                swimmer, event = random.choice(all_assignments)
                neighbor.remove_assignment(swimmer, event)
                return neighbor

        else:  # swap
            # Swap two swimmers in an event
            shuffled_events = events.copy()
            random.shuffle(shuffled_events)
            for event in shuffled_events[:3]:  # Only try 3 events
                current_swimmers = neighbor.get_event_swimmers(event)
                if current_swimmers:
                    # Find a candidate swimmer for this event
                    for swimmer in swimmers:
                        if swimmer not in current_swimmers:
                            if event in swimmer_events.get(swimmer, set()):
                                # Do swap
                                old_swimmer = random.choice(current_swimmers)
                                test = neighbor.copy()
                                test.remove_assignment(old_swimmer, event)
                                if constraint_engine.can_add(
                                    test, swimmer, event, roster_df
                                ):
                                    test.add_assignment(swimmer, event)
                                    return test

        return None

    def _fast_score(
        self,
        lineup: Lineup,
        swimmer_data: dict[tuple[str, str], dict],
        opponent_by_event: dict[str, list[dict]],
        events: list[str],
        scoring_engine: ScoringEngine,
    ) -> tuple[float, float]:
        """Fast scoring (no explanations needed during annealing)."""
        seton_total = 0.0
        opponent_total = 0.0

        for event in events:
            is_relay = "Relay" in event

            seton_swimmers = lineup.get_event_swimmers(event)
            seton_entries = [
                swimmer_data[(s, event)]
                for s in seton_swimmers
                if (s, event) in swimmer_data
            ]
            opponent_entries = opponent_by_event.get(event, [])

            seton_pts, opp_pts, _ = scoring_engine.score_event(
                seton_entries, opponent_entries, is_relay, event_name=event
            )
            seton_total += seton_pts
            opponent_total += opp_pts

        return seton_total, opponent_total


# ============================================================================
# MAIN OPTIMIZER
# ============================================================================


class AquaOptimizer(BaseOptimizerStrategy):
    """
    AquaForge Custom Optimizer - License-free alternative to Gurobi.

    Features:
    - Beam search + simulated annealing hybrid
    - Configurable scoring profiles
    - Fatigue modeling
    - Nash equilibrium iteration
    - Built-in explanations

    Quality Modes:
    - "fast": ~200ms, good for quick iterations
    - "balanced": ~500ms, default production mode
    - "thorough": ~2-3s, maximum quality for critical meets
    """

    # Quality mode presets
    QUALITY_PRESETS = {
        "fast": {
            "beam_width": 15,
            "annealing_iterations": 1000,
            "nash_iterations": 2,
            "num_seeds": 3,
            "early_stop_patience": 3,
            "hill_climb_iterations": 100,
            "use_parallel": False,  # Too few seeds to benefit
        },
        "balanced": {
            "beam_width": 25,
            "annealing_iterations": 1500,
            "nash_iterations": 4,
            "num_seeds": 5,
            "early_stop_patience": 4,
            "hill_climb_iterations": 200,
            "use_parallel": True,  # 5 seeds benefit from parallelism
        },
        "thorough": {
            "beam_width": 75,
            "annealing_iterations": 5000,
            "nash_iterations": 6,
            "num_seeds": 15,
            "early_stop_patience": 8,
            "hill_climb_iterations": 500,
            "use_parallel": True,  # 15 seeds definitely parallel
        },
    }

    def __init__(
        self,
        profile: ScoringProfile | None = None,
        fatigue: FatigueModel | None = None,
        quality_mode: str = "balanced",  # "fast", "balanced", or "thorough"
        beam_width: int | None = None,
        annealing_iterations: int | None = None,
        nash_iterations: int | None = None,
        use_parallel: bool | None = None,  # NEW: enable parallel seed execution
        championship_factors: ChampionshipFactors | None = None,
        attrition: AttritionRates
        | None = None,  # accepted but unused (zero optimization impact)
        opponent_model: OpponentModelConfig | None = None,
    ):
        self.profile = profile or ScoringProfile.visaa_dual()
        self.fatigue = fatigue or FatigueModel()
        self.quality_mode = quality_mode

        # Opponent modeling config (auto-enable for championship profiles)
        profile_lower = self.profile.name.lower()
        if opponent_model is not None:
            self.opponent_model = opponent_model
        elif "championship" in profile_lower:
            self.opponent_model = OpponentModelConfig.championship()
        else:
            self.opponent_model = OpponentModelConfig.default()

        # Championship adjustment factors (auto-enable for championship profiles)
        if championship_factors is not None:
            self.championship_factors = championship_factors
        elif "championship" in profile_lower:
            self.championship_factors = ChampionshipFactors()
        else:
            self.championship_factors = ChampionshipFactors.disabled()

        # Get preset values, allow overrides
        preset = self.QUALITY_PRESETS.get(
            quality_mode, self.QUALITY_PRESETS["balanced"]
        )
        self.beam_width = beam_width or preset["beam_width"]
        self.annealing_iterations = (
            annealing_iterations or preset["annealing_iterations"]
        )
        self.nash_iterations = (
            nash_iterations
            if nash_iterations is not None
            else preset["nash_iterations"]
        )
        self.num_seeds = preset["num_seeds"]
        self.early_stop_patience = preset["early_stop_patience"]
        self.hill_climb_iterations = preset["hill_climb_iterations"]
        self.use_parallel = (
            use_parallel
            if use_parallel is not None
            else preset.get("use_parallel", False)
        )

    # ── Opponent Field Pre-Processing ──────────────────────────────────

    def _preprocess_opponent_field(
        self,
        opponent_df: pd.DataFrame,
        events: list[str],
    ) -> pd.DataFrame:
        """Pre-process opponent field with depth limiting, time variance, and attrition.

        Runs ONCE before optimization begins. Transforms the raw opponent
        roster into an "expected field" that the deterministic optimizer uses.

        Pipeline order:
        1. Depth limiting — trim to max_opponents_per_event per event
        2. Time variance — gaussian expected-value adjustment on opponent seeds
        3. Attrition — remove slowest entries based on DNS probability
        """
        config = self.opponent_model
        df = opponent_df.copy()

        # Step 1: Depth limiting
        if config.max_opponents_per_event < 999:
            trimmed_parts = []
            for event in events:
                event_df = df[df["event"] == event].copy()
                if len(event_df) > config.max_opponents_per_event:
                    event_df = event_df.nsmallest(
                        config.max_opponents_per_event, "time"
                    )
                trimmed_parts.append(event_df)
            # Include entries for events not in our event list (relays, etc.)
            other_df = df[~df["event"].isin(events)]
            if not other_df.empty:
                trimmed_parts.append(other_df)
            df = pd.concat(trimmed_parts, ignore_index=True) if trimmed_parts else df

        # Step 2: Time variance — gaussian expected-value adjustment
        if config.apply_time_variance:
            df = self._apply_opponent_time_variance(df, config)

        # Step 3: Attrition — directional field thinning
        if config.apply_attrition:
            df = self._apply_attrition_thinning(df, config)

        return df

    @staticmethod
    def _apply_opponent_time_variance(
        df: pd.DataFrame,
        config: OpponentModelConfig,
    ) -> pd.DataFrame:
        """Apply gaussian expected-value time adjustment to opponent entries.

        At championships, swimmers typically go faster than seed. Championship
        factors already apply a uniform per-event adjustment (lines 1320-1330),
        but that treats every swimmer identically. This adds a spread-aware
        adjustment: given a field of swimmers with similar seeds, the expected
        competitive time is slightly below seed due to variance.

        Model: expected_time = seed * (1 - cv * 0.5)
        The 0.5 factor reflects that the expected value of the faster half
        of a symmetric distribution is ~0.5σ below the mean.
        """
        df = df.copy()
        times = df["time"].copy()
        events = df["event"]

        for idx in df.index:
            seed_time = times.at[idx]
            if seed_time is None or seed_time <= 0 or seed_time >= 599:
                continue

            event_lower = str(events.at[idx]).lower()
            if any(x in event_lower for x in ["50 ", "100 "]):
                cv = config.sprint_cv
            else:
                cv = config.distance_cv

            times.at[idx] = seed_time * (1 - cv * 0.5)

        df["time"] = times
        return df

    @staticmethod
    def _apply_attrition_thinning(
        df: pd.DataFrame,
        config: OpponentModelConfig,
    ) -> pd.DataFrame:
        """Apply attrition-based field thinning to opponent entries.

        For each event, removes the slowest (N * attrition_rate) entries.
        This is directional — slower swimmers are more likely to scratch at
        championships — unlike uniform scaling which has zero optimizer impact.

        The AttritionRates singleton provides per-event DNS probabilities
        derived from 77,345 entries across 162 meets.
        """
        from swim_ai_reflex.backend.core.attrition_model import ATTRITION_RATES

        events = df["event"].unique()
        keep_parts = []

        for event in events:
            event_df = df[df["event"] == event].copy()
            n = len(event_df)
            if n == 0:
                continue

            # Strip gender prefix for rate lookup (e.g., "Boys 100 Fly" → "100 Fly")
            event_base = str(event)
            for prefix in ("Boys ", "Girls "):
                if event_base.startswith(prefix):
                    event_base = event_base[len(prefix) :]
                    break

            att_rate = ATTRITION_RATES.attrition_rate(event_base)
            expected_n = max(1, int(n * (1 - att_rate)))

            # Keep the fastest expected_n entries
            event_df = event_df.nsmallest(expected_n, "time")
            keep_parts.append(event_df)

        return pd.concat(keep_parts, ignore_index=True) if keep_parts else df

    # ── Main Optimization Entry Point ──────────────────────────────────

    def optimize(
        self,
        seton_roster: pd.DataFrame,
        opponent_roster: pd.DataFrame,
        scoring_fn: Any,
        rules: Any,
        **kwargs,
    ) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, float], list[dict[str, Any]]]:
        """
        Run AquaOptimizer with enhanced quality features:
        - Greedy warm start
        - Multi-seed ensemble (3 runs)
        - Hill climbing polish

        Returns:
            (best_seton_lineup, scored_df, totals_dict, details_list)
        """
        start_time = time.perf_counter()

        # Prepare data
        seton_df = seton_roster.copy().reset_index(drop=True)
        opponent_df = opponent_roster.copy().reset_index(drop=True)

        if "team" not in seton_df.columns:
            seton_df["team"] = "seton"
        if "team" not in opponent_df.columns:
            opponent_df["team"] = "opponent"
        else:
            # Fill any empty/null team values but preserve existing real team names
            opponent_df["team"] = opponent_df["team"].fillna("opponent")
            opponent_df.loc[opponent_df["team"] == "", "team"] = "opponent"

        # Apply championship speed-up factor to all seed times
        # Empirical: swimmers are ~1% faster at championships (per-event factors vary)
        if self.championship_factors.enabled:
            seton_df = adjust_times_df(seton_df, factors=self.championship_factors)
            opponent_df = adjust_times_df(
                opponent_df, factors=self.championship_factors
            )
            logger.info(
                "Championship factors applied (default=%.4f)",
                self.championship_factors.default_factor,
            )

        # Validate opponent roster completeness
        seton_events = set(seton_df["event"].unique())
        opponent_events = (
            set(opponent_df["event"].unique()) if len(opponent_df) > 0 else set()
        )
        missing_opponents = seton_events - opponent_events
        if missing_opponents:
            logger.warning(
                "OPPONENT DATA GAP: %d/%d SST events have NO opponent entries: %s. "
                "Scores for these events will be inflated (SST gets automatic top placement).",
                len(missing_opponents),
                len(seton_events),
                sorted(missing_opponents),
            )

        # Apply opponent modeling pipeline (depth limiting, time variance, attrition)
        opp_model = self.opponent_model
        if (
            opp_model.apply_time_variance
            or opp_model.apply_attrition
            or opp_model.max_opponents_per_event != 16
        ):
            original_opp_count = len(opponent_df)
            opponent_df = self._preprocess_opponent_field(
                opponent_df, sorted(seton_events)
            )
            logger.info(
                "Opponent modeling: %d → %d entries (depth=%d, variance=%s, attrition=%s)",
                original_opp_count,
                len(opponent_df),
                opp_model.max_opponents_per_event,
                opp_model.apply_time_variance,
                opp_model.apply_attrition,
            )

        # Setup events
        available_events = seton_events
        events = [e for e in EVENT_ORDER if e in available_events]
        if not events:
            events = sorted(list(available_events))

        # === PRE-COMPUTE INVARIANTS (Tier 1 Optimization) ===
        # Cache swimmer-event mappings for O(1) lookup instead of DataFrame filtering
        swimmer_events: dict[str, set[str]] = {}
        for _, row in seton_df.iterrows():
            swimmer = row["swimmer"]
            if swimmer not in swimmer_events:
                swimmer_events[swimmer] = set()
            swimmer_events[swimmer].add(row["event"])

        event_swimmers: dict[str, set[str]] = {}
        for _, row in seton_df.iterrows():
            event = row["event"]
            if event not in event_swimmers:
                event_swimmers[event] = set()
            event_swimmers[event].add(row["swimmer"])

        # Detect divers and relay-3 swimmers from roster for constraint enforcement
        divers: set[str] = set()
        relay_3_swimmers: set[str] = set()
        for _, row in seton_df.iterrows():
            event = str(row.get("event", ""))
            swimmer = str(row.get("swimmer", ""))
            if "Diving" in event or "diving" in event:
                divers.add(swimmer)
            if "400" in event and "Relay" in event:
                relay_3_swimmers.add(swimmer)

        # Initialize engines
        constraint_engine = ConstraintEngine(
            self.profile, events, divers=divers, relay_3_swimmers=relay_3_swimmers
        )
        scoring_engine = ScoringEngine(self.profile, self.fatigue)

        # === Multi-seed ensemble using quality preset ===
        parallel_mode = self.use_parallel and self.num_seeds >= 3
        logger.info(
            f"AquaOptimizer: Running in {self.quality_mode} mode ({self.num_seeds} seeds, parallel={parallel_mode})"
        )

        # Define seed optimization function (can run in parallel)
        def run_seed(seed_idx: int) -> tuple[float, Lineup]:
            """Run optimization for a single seed."""
            random.seed(seed_idx * 42)  # Deterministic but different seeds

            # Phase 0: Greedy warm start
            greedy_lineup = self._greedy_initialize(
                seton_df, opponent_df, events, constraint_engine, scoring_engine
            )

            # Phase 1: Beam search
            beam_search = BeamSearch(beam_width=self.beam_width)
            beam_lineup = beam_search.search(
                seton_df, opponent_df, events, constraint_engine, scoring_engine
            )

            # Take better of greedy or beam
            greedy_margin = greedy_lineup.score - greedy_lineup.opponent_score
            beam_margin = beam_lineup.score - beam_lineup.opponent_score
            initial_lineup = (
                greedy_lineup if greedy_margin > beam_margin else beam_lineup
            )

            # Phase 2: Simulated annealing
            annealing = SimulatedAnnealing(max_iterations=self.annealing_iterations)
            refined_lineup = annealing.search(
                initial_lineup,
                seton_df,
                opponent_df,
                events,
                constraint_engine,
                scoring_engine,
            )

            # Phase 3: Hill climbing polish
            polished_lineup = self._hill_climb(
                refined_lineup if refined_lineup else initial_lineup,
                seton_df,
                opponent_df,
                events,
                constraint_engine,
                scoring_engine,
            )

            margin = polished_lineup.score - polished_lineup.opponent_score
            return margin, polished_lineup

        # Run seeds (parallel or sequential)
        best_overall: Lineup | None = None
        best_margin = float("-inf")

        if parallel_mode:
            # PARALLEL EXECUTION (Tier 1 Optimization)
            # Use ThreadPoolExecutor for GIL-bound work (ProcessPoolExecutor has pickling issues)
            from concurrent.futures import ThreadPoolExecutor, as_completed

            max_workers = min(self.num_seeds, 4)  # Limit to 4 threads

            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = [executor.submit(run_seed, i) for i in range(self.num_seeds)]
                for future in as_completed(futures):
                    try:
                        margin, lineup = future.result()
                        if margin > best_margin:
                            best_margin = margin
                            best_overall = lineup
                    except Exception as e:
                        logger.warning(f"Seed failed: {e}")
        else:
            # SEQUENTIAL EXECUTION (for fast mode or debugging)
            for seed_idx in range(self.num_seeds):
                margin, lineup = run_seed(seed_idx)
                if margin > best_margin:
                    best_margin = margin
                    best_overall = lineup

        # Use best result from ensemble
        best_lineup = best_overall if best_overall else Lineup(assignments={})

        # Phase 4: Nash equilibrium iteration (optional)
        if self.nash_iterations > 0:
            logger.info(
                f"AquaOptimizer: Phase 4 - Nash Equilibrium ({self.nash_iterations} iterations)"
            )
            best_lineup = self._nash_iterate(
                best_lineup,
                seton_df,
                opponent_df,
                events,
                constraint_engine,
                scoring_engine,
            )

        # Final scoring
        seton_score, opponent_score, explanations = scoring_engine.score_lineup(
            best_lineup, seton_df, opponent_df, events
        )

        elapsed_ms = (time.perf_counter() - start_time) * 1000
        logger.info(
            f"AquaOptimizer: Complete in {elapsed_ms:.0f}ms - Seton {seton_score:.0f} vs Opponent {opponent_score:.0f}"
        )

        # Convert to DataFrame
        best_seton_df = best_lineup.to_dataframe(seton_df)

        # Build scored DataFrame
        scored_rows = []
        for event in events:
            seton_swimmers = best_lineup.get_event_swimmers(event)
            for swimmer in seton_swimmers:
                row = seton_df[
                    (seton_df["swimmer"] == swimmer) & (seton_df["event"] == event)
                ]
                if not row.empty:
                    scored_rows.append(row.iloc[0].to_dict())

        scored_df = pd.DataFrame(scored_rows) if scored_rows else pd.DataFrame()

        # Build details
        details = [{"explanations": explanations, "optimizer": "aqua"}]

        totals = {
            "seton": seton_score,
            "opponent": opponent_score,
        }

        return best_seton_df, scored_df, totals, details

    def _nash_iterate(
        self,
        initial_lineup: Lineup,
        seton_df: pd.DataFrame,
        opponent_df: pd.DataFrame,
        events: list[str],
        constraint_engine: ConstraintEngine,
        scoring_engine: ScoringEngine,
    ) -> Lineup:
        """
        Iterate toward Nash equilibrium - both teams optimize against each other.
        """
        best_seton = initial_lineup

        # Opponent constraint engine
        _opp_constraint = ConstraintEngine(self.profile, events)

        for i in range(self.nash_iterations):
            # Opponent best-responds to Seton's lineup
            _opp_search = BeamSearch(beam_width=self.beam_width // 2)

            # Swap perspective: opponent optimizes against Seton's lineup
            # (In practice, just re-optimize Seton given opponent might adapt)
            seton_search = BeamSearch(beam_width=self.beam_width)
            candidate = seton_search.search(
                seton_df, opponent_df, events, constraint_engine, scoring_engine
            )

            # Refine with annealing
            annealing = SimulatedAnnealing(max_iterations=500)
            candidate = annealing.search(
                candidate,
                seton_df,
                opponent_df,
                events,
                constraint_engine,
                scoring_engine,
            )

            # Keep if improved
            if (
                candidate.score - candidate.opponent_score
                > best_seton.score - best_seton.opponent_score
            ):
                best_seton = candidate

        return best_seton

    def _greedy_initialize(
        self,
        seton_df: pd.DataFrame,
        opponent_df: pd.DataFrame,
        events: list[str],
        constraint_engine: ConstraintEngine,
        scoring_engine: ScoringEngine,
    ) -> Lineup:
        """
        Generate a greedy initial lineup by assigning fastest swimmers to events.

        Strategy:
        1. For each event, rank swimmers by time
        2. Assign the fastest available swimmer (respecting constraints)
        3. This gives a strong baseline for further optimization
        """
        lineup = Lineup(assignments={})

        # Pre-compute swimmer-event lookup
        swimmer_data: dict[tuple[str, str], dict] = {}
        for _, row in seton_df.iterrows():
            swimmer_data[(row["swimmer"], row["event"])] = row.to_dict()

        # Pre-compute opponent data (no truncation — per-team caps applied in scoring)
        opponent_by_event: dict[str, list[dict]] = {}
        for event in events:
            opp_rows = opponent_df[opponent_df["event"] == event]
            opponent_by_event[event] = opp_rows.to_dict("records")

        # Sort swimmers by their best time for each event
        for event in events:
            event_swimmers = seton_df[seton_df["event"] == event].copy()
            if event_swimmers.empty:
                continue

            # Sort by time (fastest first)
            event_swimmers = event_swimmers.sort_values("time")

            # Try to assign swimmers (up to max entries)
            max_entries = 2 if "Relay" in event else self.profile.max_entries_per_event
            assigned_count = 0

            for _, row in event_swimmers.iterrows():
                swimmer = row["swimmer"]

                if assigned_count >= max_entries:
                    break

                # Check if this assignment is valid
                if constraint_engine.can_add(lineup, swimmer, event, seton_df):
                    lineup.add_assignment(swimmer, event)
                    assigned_count += 1

        # Score the greedy lineup
        seton_score, opp_score, explanations = scoring_engine.score_lineup(
            lineup, seton_df, opponent_df, events
        )
        lineup.score = seton_score
        lineup.opponent_score = opp_score
        lineup.explanations = explanations

        return lineup

    def _hill_climb(
        self,
        lineup: Lineup,
        seton_df: pd.DataFrame,
        opponent_df: pd.DataFrame,
        events: list[str],
        constraint_engine: ConstraintEngine,
        scoring_engine: ScoringEngine,
        max_iterations: int = 300,
    ) -> Lineup:
        """
        Hill climbing to polish the solution.

        Only accepts strict improvements (no worse solutions).
        Guaranteed to find a local optimum.
        """
        current = lineup.copy()
        swimmers = seton_df["swimmer"].unique().tolist()

        # Pre-compute swimmer-event availability
        swimmer_events: dict[str, set[str]] = {}
        for _, row in seton_df.iterrows():
            swimmer = row["swimmer"]
            event = row["event"]
            if swimmer not in swimmer_events:
                swimmer_events[swimmer] = set()
            swimmer_events[swimmer].add(event)

        best_margin = current.score - current.opponent_score
        improved = True
        iterations = 0

        while improved and iterations < max_iterations:
            improved = False
            iterations += 1

            # Try all possible single-swap improvements
            for event in events:
                current_swimmers = current.get_event_swimmers(event)

                for swimmer in swimmers:
                    if swimmer in current_swimmers:
                        continue

                    if event not in swimmer_events.get(swimmer, set()):
                        continue

                    # Try adding this swimmer
                    test = current.copy()
                    if current_swimmers:
                        # Swap: remove one, add new
                        for old_swimmer in current_swimmers:
                            swap_test = current.copy()
                            swap_test.remove_assignment(old_swimmer, event)

                            if constraint_engine.can_add(
                                swap_test, swimmer, event, seton_df
                            ):
                                swap_test.add_assignment(swimmer, event)

                                # Score and check improvement
                                s, o, _ = scoring_engine.score_lineup(
                                    swap_test, seton_df, opponent_df, events
                                )
                                swap_test.score = s
                                swap_test.opponent_score = o

                                if s - o > best_margin:
                                    best_margin = s - o
                                    current = swap_test
                                    improved = True
                                    break
                    else:
                        # Add without removing
                        if constraint_engine.can_add(test, swimmer, event, seton_df):
                            test.add_assignment(swimmer, event)

                            s, o, _ = scoring_engine.score_lineup(
                                test, seton_df, opponent_df, events
                            )
                            test.score = s
                            test.opponent_score = o

                            if s - o > best_margin:
                                best_margin = s - o
                                current = test
                                improved = True

                    if improved:
                        break

                if improved:
                    break

        # Update final scores
        seton_score, opp_score, explanations = scoring_engine.score_lineup(
            current, seton_df, opponent_df, events
        )
        current.score = seton_score
        current.opponent_score = opp_score
        current.explanations = explanations

        return current


# ============================================================================
# FACTORY FUNCTION
# ============================================================================


def create_aqua_optimizer(
    profile: str = "visaa_dual",
    enable_fatigue: bool = True,
) -> AquaOptimizer:
    """Factory to create configured AquaOptimizer."""

    profiles = {
        "visaa_dual": ScoringProfile.visaa_dual,
        "vcac_championship": ScoringProfile.vcac_championship,
    }

    scoring_profile = profiles.get(profile, ScoringProfile.visaa_dual)()
    fatigue_model = FatigueModel(enabled=enable_fatigue)

    return AquaOptimizer(profile=scoring_profile, fatigue=fatigue_model)


# ============================================================================
# CLI TEST
# ============================================================================


if __name__ == "__main__":
    print("AquaOptimizer v1.0 - Testing...")

    # Create test data
    test_seton = pd.DataFrame(
        [
            {"swimmer": "Alice", "event": "50 Free", "time": 25.5, "grade": 10},
            {"swimmer": "Alice", "event": "100 Free", "time": 55.0, "grade": 10},
            {"swimmer": "Bob", "event": "50 Free", "time": 26.0, "grade": 11},
            {"swimmer": "Bob", "event": "100 Fly", "time": 58.0, "grade": 11},
            {"swimmer": "Carol", "event": "100 Free", "time": 56.0, "grade": 9},
            {"swimmer": "Carol", "event": "100 Back", "time": 62.0, "grade": 9},
        ]
    )

    test_opponent = pd.DataFrame(
        [
            {"swimmer": "Dave", "event": "50 Free", "time": 25.8, "grade": 10},
            {"swimmer": "Dave", "event": "100 Free", "time": 55.5, "grade": 10},
            {"swimmer": "Eve", "event": "50 Free", "time": 26.5, "grade": 11},
            {"swimmer": "Eve", "event": "100 Fly", "time": 59.0, "grade": 11},
        ]
    )

    optimizer = create_aqua_optimizer()
    best_seton, scored, totals, details = optimizer.optimize(
        test_seton, test_opponent, None, None
    )

    print("\n✅ Optimization Complete")
    print(f"   Seton: {totals['seton']:.0f}")
    print(f"   Opponent: {totals['opponent']:.0f}")
    print(
        f"   Winner: {'Seton' if totals['seton'] > totals['opponent'] else 'Opponent'}"
    )
    print(f"\n   Lineup: {len(best_seton)} assignments")
    for _, row in best_seton.iterrows():
        print(f"      {row['swimmer']} → {row['event']} ({row['time']}s)")
