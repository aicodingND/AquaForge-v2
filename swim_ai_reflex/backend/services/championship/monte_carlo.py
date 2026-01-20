"""
Monte Carlo Simulation Engine for Championship Optimization

Provides probabilistic outcome modeling by simulating thousands of
meet scenarios with realistic performance variance.

Features:
- Time variance modeling (swimmers don't always hit seed times)
- Win probability estimation
- Confidence intervals for scores
- Risk assessment
"""

import logging
from collections import defaultdict
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import numpy as np

from swim_ai_reflex.backend.core.rules import get_meet_profile

logger = logging.getLogger(__name__)


@dataclass
class SimulationConfig:
    """Configuration for Monte Carlo simulation."""

    num_simulations: int = 10000
    variance_model: str = "standard"  # "standard", "historical", "conservative"
    confidence_level: float = 0.95
    seed: Optional[int] = None

    # Variance parameters (as percentage of seed time)
    sprint_variance: float = 0.015  # 1.5% for 50/100 events
    distance_variance: float = 0.02  # 2% for 200+ events
    relay_variance: float = 0.01  # 1% for relays (more consistent teams)
    diving_variance: float = 0.05  # 5% for diving (higher variance)


@dataclass
class SimulationResult:
    """Results from Monte Carlo simulation."""

    # Score statistics
    expected_score: float
    score_std: float
    score_min: float
    score_max: float
    confidence_interval: Tuple[float, float]

    # Rank statistics
    expected_rank: float
    win_probability: float  # Probability of 1st place
    podium_probability: float  # Probability of top 3

    # Team-level results
    team_scores: Dict[str, Dict[str, float]]  # {team: {mean, std, ci_low, ci_high}}

    # Event-level insights
    volatile_events: List[Dict]  # Events with highest variance
    stable_events: List[Dict]  # Events with lowest variance

    # Raw data for visualization
    score_distribution: List[float]
    rank_distribution: List[int]

    def to_dict(self) -> Dict:
        return {
            "expected_score": round(self.expected_score, 1),
            "score_std": round(self.score_std, 1),
            "confidence_interval": [round(x, 1) for x in self.confidence_interval],
            "expected_rank": round(self.expected_rank, 2),
            "win_probability": round(self.win_probability * 100, 1),
            "podium_probability": round(self.podium_probability * 100, 1),
            "team_scores": {
                team: {k: round(v, 1) for k, v in scores.items()}
                for team, scores in self.team_scores.items()
            },
            "volatile_events": self.volatile_events[:5],
            "stable_events": self.stable_events[:5],
            "risk_level": self._risk_level(),
            "recommendation": self._recommendation(),
        }

    def _risk_level(self) -> str:
        """Categorize risk based on score variance."""
        cv = self.score_std / self.expected_score if self.expected_score > 0 else 0
        if cv < 0.05:
            return "low"
        elif cv < 0.10:
            return "medium"
        else:
            return "high"

    def _recommendation(self) -> str:
        """Generate recommendation based on results."""
        risk = self._risk_level()
        if self.win_probability > 0.8:
            return "Strong favorite - maintain consistent strategy"
        elif self.win_probability > 0.5:
            if risk == "high":
                return "Slight favorite with high variance - consider conservative approach"
            return "Slight favorite - balanced approach recommended"
        elif self.win_probability > 0.3:
            return "Competitive - aggressive strategy may be needed"
        else:
            return "Underdog - high-risk/high-reward strategies recommended"


class MonteCarloSimulator:
    """
    Monte Carlo simulation engine for swim meet outcomes.

    Simulates thousands of meet scenarios to estimate:
    - Expected scores and confidence intervals
    - Win probabilities
    - Risk assessment
    - Event volatility
    """

    def __init__(
        self,
        meet_profile: str = "vcac_championship",
        config: Optional[SimulationConfig] = None,
    ):
        self.meet_profile = meet_profile
        self.rules = get_meet_profile(meet_profile)
        self.config = config or SimulationConfig()

        if self.config.seed is not None:
            np.random.seed(self.config.seed)

    def simulate_meet(
        self,
        entries: List[Dict],
        target_team: str = "SST",
    ) -> SimulationResult:
        """
        Run Monte Carlo simulation of championship meet.

        Args:
            entries: List of all entries (all teams, all events)
                     Each entry: {swimmer, team, event, time, gender}
            target_team: Team to focus analysis on

        Returns:
            SimulationResult with full statistical analysis
        """
        logger.info(
            f"Starting Monte Carlo simulation: {self.config.num_simulations} runs"
        )

        # Organize entries by event
        events = self._organize_by_event(entries)
        teams = list(set(e["team"] for e in entries))

        # Run simulations
        all_team_scores = {team: [] for team in teams}
        all_ranks = []
        event_variances = defaultdict(list)

        for sim in range(self.config.num_simulations):
            # Simulate each event
            team_points = {team: 0.0 for team in teams}

            for event_name, event_entries in events.items():
                # Sample times with variance
                simulated_entries = self._simulate_event(event_entries)

                # Score the event
                event_points = self._score_event(simulated_entries, event_name)

                for team, points in event_points.items():
                    team_points[team] += points

                # Track variance for this event
                if sim < 1000:  # Only track for subset to save memory
                    event_variances[event_name].append(event_points.get(target_team, 0))

            # Record team scores
            for team, score in team_points.items():
                all_team_scores[team].append(score)

            # Calculate rank for target team
            sorted_teams = sorted(team_points.items(), key=lambda x: -x[1])
            rank = next(
                i + 1 for i, (t, _) in enumerate(sorted_teams) if t == target_team
            )
            all_ranks.append(rank)

        # Analyze results
        target_scores = np.array(all_team_scores[target_team])
        ranks = np.array(all_ranks)

        # Confidence interval
        alpha = 1 - self.config.confidence_level
        ci_low = np.percentile(target_scores, alpha / 2 * 100)
        ci_high = np.percentile(target_scores, (1 - alpha / 2) * 100)

        # Team score summaries
        team_score_summary = {}
        for team, scores in all_team_scores.items():
            scores_arr = np.array(scores)
            team_score_summary[team] = {
                "mean": float(np.mean(scores_arr)),
                "std": float(np.std(scores_arr)),
                "ci_low": float(np.percentile(scores_arr, 2.5)),
                "ci_high": float(np.percentile(scores_arr, 97.5)),
            }

        # Event volatility
        volatile_events = []
        stable_events = []
        for event_name, point_samples in event_variances.items():
            if len(point_samples) > 0:
                std = float(np.std(point_samples))
                mean = float(np.mean(point_samples))
                volatile_events.append(
                    {
                        "event": event_name,
                        "mean_points": round(mean, 1),
                        "std_points": round(std, 1),
                        "volatility": round(std, 2),
                    }
                )

        volatile_events.sort(key=lambda x: -x["volatility"])
        stable_events = sorted(volatile_events, key=lambda x: x["volatility"])

        result = SimulationResult(
            expected_score=float(np.mean(target_scores)),
            score_std=float(np.std(target_scores)),
            score_min=float(np.min(target_scores)),
            score_max=float(np.max(target_scores)),
            confidence_interval=(ci_low, ci_high),
            expected_rank=float(np.mean(ranks)),
            win_probability=float(np.mean(ranks == 1)),
            podium_probability=float(np.mean(ranks <= 3)),
            team_scores=team_score_summary,
            volatile_events=volatile_events,
            stable_events=stable_events,
            score_distribution=target_scores.tolist(),
            rank_distribution=ranks.tolist(),
        )

        logger.info(
            f"Simulation complete: {result.expected_score:.1f} ± {result.score_std:.1f}"
        )

        return result

    def _organize_by_event(self, entries: List[Dict]) -> Dict[str, List[Dict]]:
        """Group entries by event."""
        events = defaultdict(list)
        for entry in entries:
            event = entry.get("event", "Unknown")
            events[event].append(entry)
        return dict(events)

    def _simulate_event(self, entries: List[Dict]) -> List[Dict]:
        """Simulate times for all entries in an event with variance."""
        simulated = []

        for entry in entries:
            seed_time = entry.get("time", 9999)
            if isinstance(seed_time, str):
                try:
                    seed_time = float(seed_time)
                except ValueError:
                    seed_time = 9999

            # Determine variance based on event type
            event = entry.get("event", "").lower()
            if "diving" in event:
                variance_pct = self.config.diving_variance
            elif "relay" in event:
                variance_pct = self.config.relay_variance
            elif any(x in event for x in ["50", "100"]):
                variance_pct = self.config.sprint_variance
            else:
                variance_pct = self.config.distance_variance

            # Sample time from normal distribution
            # Times can vary ± variance_pct around seed
            std_time = seed_time * variance_pct
            simulated_time = np.random.normal(seed_time, std_time)

            # Ensure positive time
            simulated_time = max(simulated_time, seed_time * 0.95)

            simulated.append(
                {
                    **entry,
                    "simulated_time": simulated_time,
                }
            )

        return simulated

    def _score_event(
        self,
        entries: List[Dict],
        event_name: str,
    ) -> Dict[str, float]:
        """Score an event based on simulated times."""
        # Sort by simulated time
        sorted_entries = sorted(entries, key=lambda x: x["simulated_time"])

        # Get points table
        is_relay = "relay" in event_name.lower()
        points_table = (
            self.rules.relay_points if is_relay else self.rules.individual_points
        )
        max_scorers = (
            self.rules.max_scorers_per_team_relay
            if is_relay
            else self.rules.max_scorers_per_team_individual
        )

        # Track scorers per team
        team_scorer_count = defaultdict(int)
        team_points = defaultdict(float)

        for place, entry in enumerate(sorted_entries):
            team = entry.get("team", "Unknown")

            # Check if team can still score
            if team_scorer_count[team] >= max_scorers:
                continue

            # Award points
            if place < len(points_table):
                points = points_table[place]
                team_points[team] += points
                team_scorer_count[team] += 1

        return dict(team_points)

    def quick_simulation(
        self,
        entries: List[Dict],
        target_team: str = "SST",
        num_simulations: int = 1000,
    ) -> Dict:
        """
        Run a quick simulation for UI responsiveness.

        Args:
            entries: All entries
            target_team: Team to analyze
            num_simulations: Number of runs (default 1000 for speed)

        Returns:
            Quick summary dict
        """
        # Override config for quick run
        original_sims = self.config.num_simulations
        self.config.num_simulations = num_simulations

        try:
            result = self.simulate_meet(entries, target_team)
            return {
                "expected_score": round(result.expected_score, 1),
                "confidence_interval": [
                    round(x, 1) for x in result.confidence_interval
                ],
                "win_probability": round(result.win_probability * 100, 1),
                "risk_level": result._risk_level(),
            }
        finally:
            self.config.num_simulations = original_sims


# Convenience function for API
def run_monte_carlo(
    entries: List[Dict],
    target_team: str = "SST",
    meet_profile: str = "vcac_championship",
    num_simulations: int = 10000,
) -> Dict:
    """
    Convenience function to run Monte Carlo simulation.

    Args:
        entries: All psych sheet entries
        target_team: Team to analyze
        meet_profile: Meet rules profile
        num_simulations: Number of simulations

    Returns:
        Simulation results as dict
    """
    config = SimulationConfig(num_simulations=num_simulations)
    simulator = MonteCarloSimulator(meet_profile=meet_profile, config=config)
    result = simulator.simulate_meet(entries, target_team)
    return result.to_dict()
