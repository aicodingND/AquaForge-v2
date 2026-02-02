"""
Time Distribution Intelligence Module

Provides probabilistic modeling of swimmer times:
- Estimate distributions from historical data
- Calculate probability of one swimmer beating another
- Variance-aware point calculations
"""

import math

import numpy as np
from scipy import stats


def estimate_distribution(times: list[float]) -> tuple[float, float, float]:
    """
    Estimate mean and std_dev from historical times.

    Args:
        times: List of recorded times (in seconds)

    Returns:
        (mean, std_dev, confidence) where confidence is based on sample size
    """
    if not times:
        raise ValueError("Cannot estimate distribution from empty list")

    n = len(times)

    if n == 1:
        # Single time: use default variance
        return times[0], 0.5, 0.5

    mean = sum(times) / n

    # Calculate sample standard deviation
    variance = sum((t - mean) ** 2 for t in times) / (n - 1)
    std_dev = math.sqrt(variance)

    # Minimum std_dev to prevent overconfidence
    std_dev = max(std_dev, 0.3)

    # Confidence based on sample size (asymptotic to 1.0)
    confidence = 1 - (1 / (1 + 0.3 * n))

    return mean, std_dev, confidence


def probability_of_beating(
    swimmer1_mean: float, swimmer1_std: float, swimmer2_mean: float, swimmer2_std: float
) -> float:
    """
    Calculate probability that swimmer1 beats swimmer2.

    Uses the difference of two normal distributions:
    P(T1 < T2) where T1 ~ N(μ1, σ1²) and T2 ~ N(μ2, σ2²)

    The difference D = T2 - T1 ~ N(μ2 - μ1, σ1² + σ2²)
    P(T1 < T2) = P(D > 0) = Φ((μ2 - μ1) / sqrt(σ1² + σ2²))

    Args:
        swimmer1_mean: Swimmer 1's expected time
        swimmer1_std: Swimmer 1's time standard deviation
        swimmer2_mean: Swimmer 2's expected time
        swimmer2_std: Swimmer 2's time standard deviation

    Returns:
        Probability (0-1) that swimmer1 finishes before swimmer2
    """
    # Handle edge cases
    if swimmer1_std == 0 and swimmer2_std == 0:
        return (
            1.0
            if swimmer1_mean < swimmer2_mean
            else (0.5 if swimmer1_mean == swimmer2_mean else 0.0)
        )

    # Combined variance
    combined_std = math.sqrt(swimmer1_std**2 + swimmer2_std**2)

    # Z-score for P(T1 < T2)
    z = (swimmer2_mean - swimmer1_mean) / combined_std

    # CDF gives probability
    return stats.norm.cdf(z)


def expected_points_with_uncertainty(
    swimmer_mean: float,
    swimmer_std: float,
    opponent_times: list[tuple[float, float]],  # List of (mean, std_dev)
    is_relay: bool = False,
    is_exhibition: bool = False,
) -> float:
    """
    Calculate expected points accounting for time uncertainty.

    Instead of deterministic placement, calculates expected value over
    the probability distribution of placements.

    Args:
        swimmer_mean: Our swimmer's expected time
        swimmer_std: Our swimmer's time variance
        opponent_times: List of (mean, std_dev) for opponent swimmers
        is_relay: True if relay event (different point scale)
        is_exhibition: True if exhibition swimmer (0 points)

    Returns:
        Expected points (weighted by probability of each placement)
    """
    if is_exhibition:
        # Exhibition swimmers still have strategic value
        return 0.1

    # Point tables
    if is_relay:
        points = [8, 4, 2]  # 1st, 2nd, 3rd
    else:
        points = [8, 6, 5, 4, 3, 2, 1]  # 1st through 7th

    # Calculate probability of beating each opponent
    beat_probs = []
    for opp_mean, opp_std in opponent_times:
        p = probability_of_beating(swimmer_mean, swimmer_std, opp_mean, opp_std)
        beat_probs.append(p)

    # Calculate expected placement
    # For n opponents, expected placement = 1 + sum(P(loses to each))
    # P(loses) = 1 - P(beats)
    expected_opponents_ahead = sum(1 - p for p in beat_probs)
    expected_placement = 1 + expected_opponents_ahead

    # For more accurate expected points, we'd need the full distribution
    # of placements. This is a reasonable approximation:
    if expected_placement <= 1:
        return points[0]
    elif expected_placement >= len(points):
        return 0
    else:
        # Interpolate between adjacent placement points
        lower = int(expected_placement)
        upper = lower + 1
        frac = expected_placement - lower

        lower_points = points[lower - 1] if lower <= len(points) else 0
        upper_points = points[upper - 1] if upper <= len(points) else 0

        return lower_points * (1 - frac) + upper_points * frac


def calculate_match_confidence(
    swimmer_mean: float, swimmer_std: float, opponent_mean: float, opponent_std: float
) -> tuple[float, str]:
    """
    Calculate confidence level and description for a head-to-head.

    Returns:
        (confidence, description) where confidence is 0-1 and
        description is a human-readable assessment
    """
    prob = probability_of_beating(
        swimmer_mean, swimmer_std, opponent_mean, opponent_std
    )

    if prob >= 0.95:
        return prob, "Near certain win"
    elif prob >= 0.80:
        return prob, "Strong favorite"
    elif prob >= 0.60:
        return prob, "Slight favorite"
    elif prob >= 0.40:
        return prob, "Toss-up"
    elif prob >= 0.20:
        return prob, "Underdog"
    elif prob >= 0.05:
        return prob, "Long shot"
    else:
        return prob, "Near certain loss"


def simulate_race(
    swimmer_times: list[tuple[str, float, float]],  # (name, mean, std)
    n_simulations: int = 1000,
) -> dict:
    """
    Monte Carlo simulation of a race.

    Args:
        swimmer_times: List of (swimmer_name, mean_time, std_dev)
        n_simulations: Number of simulations to run

    Returns:
        Dict with placement probabilities for each swimmer
    """
    results = {
        name: {i: 0 for i in range(1, len(swimmer_times) + 1)}
        for name, _, _ in swimmer_times
    }

    for _ in range(n_simulations):
        # Sample times for each swimmer
        sampled = []
        for name, mean, std in swimmer_times:
            t = np.random.normal(mean, std) if std > 0 else mean
            sampled.append((name, t))

        # Sort by time (fastest first)
        sampled.sort(key=lambda x: x[1])

        # Record placements
        for place, (name, _) in enumerate(sampled, 1):
            results[name][place] += 1

    # Convert to probabilities
    for name in results:
        for place in results[name]:
            results[name][place] /= n_simulations

    return results
