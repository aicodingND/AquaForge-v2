"""
Intelligence package init.

Advanced analytics modules for AquaForge optimization.
"""

from swim_ai_reflex.backend.intelligence.time_distribution import (
    estimate_distribution,
    probability_of_beating,
    expected_points_with_uncertainty,
    calculate_match_confidence,
    simulate_race,
)

from swim_ai_reflex.backend.intelligence.coach_tendency import (
    CoachTendencyAnalyzer,
    coach_tendency_analyzer,
)

from swim_ai_reflex.backend.intelligence.trajectory import (
    TrajectoryPredictor,
    SwimmerTrajectory,
    TrajectoryPoint,
    trajectory_predictor,
)

from swim_ai_reflex.backend.intelligence.psychological import (
    PsychologicalProfiler,
    PsychologicalProfile,
    psychological_profiler,
)

__all__ = [
    # Time distribution
    "estimate_distribution",
    "probability_of_beating",
    "expected_points_with_uncertainty",
    "calculate_match_confidence",
    "simulate_race",
    # Coach tendency
    "CoachTendencyAnalyzer",
    "coach_tendency_analyzer",
    # Trajectory
    "TrajectoryPredictor",
    "SwimmerTrajectory",
    "TrajectoryPoint",
    "trajectory_predictor",
    # Psychological
    "PsychologicalProfiler",
    "PsychologicalProfile",
    "psychological_profiler",
]
