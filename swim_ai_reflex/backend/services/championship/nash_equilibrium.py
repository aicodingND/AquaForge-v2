"""
Nash Equilibrium Strategy for Multi-Team Championship Optimization

Implements game-theoretic optimization where each team's strategy
accounts for what other teams might do.

Features:
- Best-response iteration algorithm
- Convergence detection
- Multi-team competitive dynamics
- Strategic recommendations
"""

import copy
import logging
from collections import defaultdict
from dataclasses import dataclass

from swim_ai_reflex.backend.core.rules import get_meet_profile

logger = logging.getLogger(__name__)


@dataclass
class TeamStrategy:
    """Represents a team's event assignment strategy."""

    team: str
    assignments: dict[str, list[str]]  # {event: [swimmers]}
    projected_points: float = 0.0

    def copy(self) -> "TeamStrategy":
        return TeamStrategy(
            team=self.team,
            assignments=copy.deepcopy(self.assignments),
            projected_points=self.projected_points,
        )


@dataclass
class NashResult:
    """Result of Nash Equilibrium computation."""

    equilibrium_found: bool
    iterations_used: int
    final_strategies: dict[str, TeamStrategy]
    team_rankings: list[tuple[str, float]]  # [(team, points), ...]
    stability_score: float  # 0-1, higher = more stable
    strategic_insights: list[str]
    convergence_history: list[dict[str, float]]

    def to_dict(self) -> dict:
        return {
            "equilibrium_found": self.equilibrium_found,
            "iterations": self.iterations_used,
            "rankings": [
                {"rank": i + 1, "team": team, "points": round(pts, 1)}
                for i, (team, pts) in enumerate(self.team_rankings)
            ],
            "stability_score": round(self.stability_score, 2),
            "insights": self.strategic_insights,
            "target_team_points": self._get_target_points(),
            "target_team_rank": self._get_target_rank(),
        }

    def _get_target_points(self) -> float:
        for team, pts in self.team_rankings:
            if team in ["SST", "Seton"]:
                return round(pts, 1)
        return 0.0

    def _get_target_rank(self) -> int:
        for i, (team, _) in enumerate(self.team_rankings):
            if team in ["SST", "Seton"]:
                return i + 1
        return 0


class NashEquilibriumStrategy:
    """
    Multi-team Nash Equilibrium optimization.

    Finds stable lineup configurations where no team has incentive
    to unilaterally change their assignments.

    Algorithm:
    1. Initialize with seed-time-based strategies
    2. For each team, compute best response to others
    3. Update strategy if improvement found
    4. Repeat until no team wants to change (equilibrium)
    """

    def __init__(
        self,
        meet_profile: str = "vcac_championship",
        max_iterations: int = 100,
        convergence_threshold: float = 0.1,
    ):
        self.meet_profile = meet_profile
        self.rules = get_meet_profile(meet_profile)
        self.max_iterations = max_iterations
        self.convergence_threshold = convergence_threshold

    def find_equilibrium(
        self,
        entries: list[dict],
        target_team: str = "SST",
    ) -> NashResult:
        """
        Find Nash Equilibrium for multi-team championship.

        Args:
            entries: All entries from all teams
            target_team: Team to focus strategic analysis on

        Returns:
            NashResult with equilibrium strategies
        """
        logger.info(f"Computing Nash Equilibrium for {target_team}")

        # Group entries by team
        team_entries = self._group_by_team(entries)
        teams = list(team_entries.keys())

        logger.info(f"Teams in competition: {teams}")

        # Initialize strategies
        strategies = {
            team: self._initialize_strategy(team, team_entries[team]) for team in teams
        }

        # Score initial strategies
        self._score_all_strategies(strategies, entries)

        convergence_history = []

        # Best-response iteration
        for iteration in range(self.max_iterations):
            improved = False
            iteration_scores = {}

            for team in teams:
                # Get other teams' current strategies
                other_strategies = {t: s for t, s in strategies.items() if t != team}

                # Compute best response
                new_strategy = self._best_response(
                    team,
                    team_entries[team],
                    other_strategies,
                    entries,
                )

                # Check if improvement
                if (
                    new_strategy.projected_points
                    > strategies[team].projected_points + self.convergence_threshold
                ):
                    strategies[team] = new_strategy
                    improved = True
                    logger.debug(
                        f"Iteration {iteration}: {team} improved to {new_strategy.projected_points:.1f}"
                    )

                iteration_scores[team] = strategies[team].projected_points

            convergence_history.append(iteration_scores)

            if not improved:
                logger.info(f"Nash Equilibrium reached at iteration {iteration}")
                break

        # Compute final rankings
        team_rankings = sorted(
            [(team, strat.projected_points) for team, strat in strategies.items()],
            key=lambda x: -x[1],
        )

        # Calculate stability score
        stability = self._calculate_stability(strategies, entries)

        # Generate insights
        insights = self._generate_insights(strategies, target_team, entries)

        return NashResult(
            equilibrium_found=(iteration < self.max_iterations - 1),
            iterations_used=iteration + 1,
            final_strategies=strategies,
            team_rankings=team_rankings,
            stability_score=stability,
            strategic_insights=insights,
            convergence_history=convergence_history,
        )

    def _group_by_team(self, entries: list[dict]) -> dict[str, list[dict]]:
        """Group entries by team."""
        team_entries = defaultdict(list)
        for entry in entries:
            team = entry.get("team", "Unknown")
            team_entries[team].append(entry)
        return dict(team_entries)

    def _initialize_strategy(self, team: str, entries: list[dict]) -> TeamStrategy:
        """Initialize strategy based on seed times (best swimmers in each event)."""
        # Group by event
        event_entries = defaultdict(list)
        for entry in entries:
            event = entry.get("event", "Unknown")
            event_entries[event].append(entry)

        # Select top swimmers per event
        assignments = {}
        max_per_event = self.rules.max_scorers_per_team_individual

        for event, event_ents in event_entries.items():
            # Sort by time
            sorted_ents = sorted(event_ents, key=lambda x: x.get("time", 9999))
            # Take top N
            top_swimmers = [
                e.get("swimmer", "Unknown") for e in sorted_ents[:max_per_event]
            ]
            assignments[event] = top_swimmers

        return TeamStrategy(team=team, assignments=assignments)

    def _best_response(
        self,
        team: str,
        team_entries: list[dict],
        other_strategies: dict[str, TeamStrategy],
        all_entries: list[dict],
    ) -> TeamStrategy:
        """
        Compute best response for a team given others' strategies.

        This is a simplified greedy approach - full optimization would use ILP.
        """
        # Current strategy as baseline
        current = self._initialize_strategy(team, team_entries)

        # Try swapping swimmers between events to find improvements
        best_strategy = current.copy()
        best_strategy.projected_points = self._score_strategy(
            best_strategy, other_strategies, all_entries
        )

        # Get all swimmers and their eligible events
        swimmer_events = defaultdict(list)
        for entry in team_entries:
            swimmer = entry.get("swimmer", "")
            event = entry.get("event", "")
            swimmer_events[swimmer].append(entry)

        # Try variations - for each swimmer with multiple events, try different assignments
        for swimmer, entries in swimmer_events.items():
            if len(entries) < 2:
                continue

            # Try focusing swimmer on different events
            for focus_entry in entries:
                test_strategy = best_strategy.copy()
                focus_event = focus_entry.get("event", "")

                # Ensure swimmer is in focus event
                for event, swimmers in test_strategy.assignments.items():
                    if event == focus_event:
                        if swimmer not in swimmers:
                            swimmers.append(swimmer)
                    else:
                        if swimmer in swimmers:
                            swimmers.remove(swimmer)

                # Score this variation
                score = self._score_strategy(
                    test_strategy, other_strategies, all_entries
                )

                if score > best_strategy.projected_points:
                    best_strategy = test_strategy.copy()
                    best_strategy.projected_points = score

        return best_strategy

    def _score_strategy(
        self,
        strategy: TeamStrategy,
        other_strategies: dict[str, TeamStrategy],
        all_entries: list[dict],
    ) -> float:
        """Score a strategy against other teams' strategies."""
        # Combine all strategies
        all_strategies = {**other_strategies, strategy.team: strategy}

        # Score each event
        total_points = 0.0

        # Group all entries by event
        event_entries = defaultdict(list)
        for entry in all_entries:
            event_entries[entry.get("event", "")].append(entry)

        for event, entries in event_entries.items():
            event_points = self._score_event_with_strategies(
                event, entries, all_strategies
            )
            total_points += event_points.get(strategy.team, 0)

        return total_points

    def _score_event_with_strategies(
        self,
        event: str,
        entries: list[dict],
        strategies: dict[str, TeamStrategy],
    ) -> dict[str, float]:
        """Score an event considering all teams' strategies."""
        # Filter to swimmers actually assigned to this event
        active_entries = []
        for entry in entries:
            team = entry.get("team", "")
            swimmer = entry.get("swimmer", "")

            if team in strategies:
                event_swimmers = strategies[team].assignments.get(event, [])
                if swimmer in event_swimmers:
                    active_entries.append(entry)

        # Sort by time
        sorted_entries = sorted(active_entries, key=lambda x: x.get("time", 9999))

        # Get points table
        is_relay = "relay" in event.lower()
        points_table = (
            self.rules.relay_points if is_relay else self.rules.individual_points
        )
        max_scorers = (
            self.rules.max_scorers_per_team_relay
            if is_relay
            else self.rules.max_scorers_per_team_individual
        )

        # Award points
        team_scorer_count = defaultdict(int)
        team_points = defaultdict(float)

        for place, entry in enumerate(sorted_entries):
            team = entry.get("team", "")

            if team_scorer_count[team] >= max_scorers:
                continue

            if place < len(points_table):
                team_points[team] += points_table[place]
                team_scorer_count[team] += 1

        return dict(team_points)

    def _score_all_strategies(
        self,
        strategies: dict[str, TeamStrategy],
        all_entries: list[dict],
    ):
        """Score all strategies and update projected points."""
        for team, strategy in strategies.items():
            other_strategies = {t: s for t, s in strategies.items() if t != team}
            strategy.projected_points = self._score_strategy(
                strategy, other_strategies, all_entries
            )

    def _calculate_stability(
        self,
        strategies: dict[str, TeamStrategy],
        all_entries: list[dict],
    ) -> float:
        """
        Calculate stability score (0-1).

        Higher score = more stable equilibrium.
        """
        total_improvement_possible = 0.0

        for team, strategy in strategies.items():
            other_strategies = {t: s for t, s in strategies.items() if t != team}

            # Get best possible response
            team_entries = [e for e in all_entries if e.get("team") == team]
            best_response = self._best_response(
                team, team_entries, other_strategies, all_entries
            )

            improvement = best_response.projected_points - strategy.projected_points
            total_improvement_possible += max(0, improvement)

        # Stability is inverse of improvement potential
        if total_improvement_possible < 1:
            return 1.0
        else:
            return 1.0 / (1.0 + total_improvement_possible / 10.0)

    def _generate_insights(
        self,
        strategies: dict[str, TeamStrategy],
        target_team: str,
        all_entries: list[dict],
    ) -> list[str]:
        """Generate strategic insights for target team."""
        insights = []

        target_strategy = strategies.get(target_team)
        if not target_strategy:
            return ["Target team not found in competition"]

        # Find target team rank - rankings is list of (team, strategy) tuples
        rankings = sorted(strategies.items(), key=lambda x: -x[1].projected_points)
        target_rank = next(
            i + 1 for i, (team, _) in enumerate(rankings) if team == target_team
        )

        if target_rank == 1:
            insights.append("Team is projected to WIN - maintain current strategy")
        elif target_rank <= 3:
            insights.append(
                f"Team is projected {target_rank}{'nd' if target_rank == 2 else 'rd'} - strong position"
            )
        else:
            insights.append(
                f"▸ Team is projected {target_rank}th - consider aggressive moves"
            )

        # Find closest competitor
        if target_rank > 1:
            ahead_team, ahead_strategy = rankings[target_rank - 2]
            gap = ahead_strategy.projected_points - target_strategy.projected_points
            insights.append(f"Gap to {ahead_team}: {gap:.1f} points")

        if target_rank < len(rankings):
            behind_team, behind_strategy = rankings[target_rank]
            gap = target_strategy.projected_points - behind_strategy.projected_points
            insights.append(f"Lead over {behind_team}: {gap:.1f} points")

        # Identify contested events
        contested = self._find_contested_events(strategies, all_entries)
        if contested:
            top_contested = contested[:3]
            insights.append(f"Key contested events: {', '.join(top_contested)}")

        return insights

    def _find_contested_events(
        self,
        strategies: dict[str, TeamStrategy],
        all_entries: list[dict],
    ) -> list[str]:
        """Find events where multiple teams are competitive."""
        event_entries = defaultdict(list)
        for entry in all_entries:
            event_entries[entry.get("event", "")].append(entry)

        contested = []
        for event, entries in event_entries.items():
            # Get times by team
            team_best_times = {}
            for entry in entries:
                team = entry.get("team", "")
                time = entry.get("time", 9999)
                if team not in team_best_times or time < team_best_times[team]:
                    team_best_times[team] = time

            # Check if multiple teams within 2%
            if len(team_best_times) >= 2:
                times = sorted(team_best_times.values())
                if len(times) >= 2:
                    spread = (times[1] - times[0]) / times[0]
                    if spread < 0.02:  # Within 2%
                        contested.append(event)

        return contested


# Convenience function
def run_nash_equilibrium(
    entries: list[dict],
    target_team: str = "SST",
    meet_profile: str = "vcac_championship",
) -> dict:
    """
    Run Nash Equilibrium optimization.

    Args:
        entries: All psych sheet entries
        target_team: Team to focus on
        meet_profile: Meet rules

    Returns:
        Nash equilibrium results
    """
    strategy = NashEquilibriumStrategy(meet_profile=meet_profile)
    result = strategy.find_equilibrium(entries, target_team)
    return result.to_dict()
