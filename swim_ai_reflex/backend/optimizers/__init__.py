"""
Optimizers package init.

Advanced optimization modules for AquaForge.
"""

from swim_ai_reflex.backend.optimizers.relay_optimizer import (
    RelayOptimizer,
    RelaySwimmer,
    RelayComposition,
    relay_optimizer,
)

from swim_ai_reflex.backend.optimizers.season_planner import (
    SeasonPlanner,
    season_planner,
)

from swim_ai_reflex.backend.optimizers.real_time_adjuster import (
    RealTimeAdjuster,
    ScratchEvent,
    DQEvent,
    AdjustmentRecommendation,
    real_time_adjuster,
)

__all__ = [
    # Relay
    "RelayOptimizer",
    "RelaySwimmer",
    "RelayComposition",
    "relay_optimizer",
    # Season
    "SeasonPlanner",
    "season_planner",
    # Real-time
    "RealTimeAdjuster",
    "ScratchEvent",
    "DQEvent",
    "AdjustmentRecommendation",
    "real_time_adjuster",
]
