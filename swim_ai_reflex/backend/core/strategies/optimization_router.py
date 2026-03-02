"""
Meet Optimization Router

Routes optimization requests to the appropriate strategy based on meet type
and available resources (e.g., Gurobi license).

Strategies:
- Dual Meet: GurobiStrategy (if available) or AquaOptimizer
- Championship: ChampionshipGurobiStrategy (if available) or AquaOptimizer
- Fallback: HeuristicStrategy

Usage:
    router = MeetOptimizationRouter()
    strategy = router.get_strategy(meet_type="dual")
    result = strategy.optimize(seton_roster, opponent_roster, rules)
"""

import logging
from enum import Enum

from swim_ai_reflex.backend.core.strategies.aqua_optimizer import (
    AquaOptimizer,
    ScoringProfile,
)
from swim_ai_reflex.backend.core.strategies.base_strategy import BaseOptimizerStrategy
from swim_ai_reflex.backend.core.strategies.heuristic_strategy import HeuristicStrategy

logger = logging.getLogger(__name__)


class MeetType(Enum):
    """Types of swim meets with different scoring rules."""

    DUAL = "dual"
    CHAMPIONSHIP = "championship"
    INVITATIONAL = "invitational"


class MeetOptimizationRouter:
    """
    Routes optimization requests to appropriate strategy.

    Priority order (default):
    1. Aqua (zero-cost, high quality) - PRIMARY
    2. Gurobi (if license available) - FALLBACK
    3. Heuristic (fast fallback)

    Design Decision: Aqua is primary to eliminate $10K/year Gurobi dependency.
    Gurobi is available as fallback for edge cases or validation.
    """

    def __init__(self, prefer_gurobi: bool = False):
        """
        Initialize router.

        Args:
            prefer_gurobi: If True, use Gurobi when available (for validation).
                          Default False = Aqua is always used first.
        """
        self.prefer_gurobi = prefer_gurobi
        self._gurobi_available: bool | None = None

    def has_gurobi(self) -> bool:
        """Check if Gurobi is available (cached)."""
        if self._gurobi_available is None:
            try:
                import gurobipy  # noqa: F401

                self._gurobi_available = True
                logger.debug("Gurobi available")
            except ImportError:
                self._gurobi_available = False
                logger.info("Gurobi not available, will use Aqua optimizer")
        return self._gurobi_available

    def get_strategy(
        self,
        meet_type: str = "dual",
        quality_mode: str = "balanced",
        force_strategy: str | None = None,
        meet_profile: str | None = None,
    ) -> BaseOptimizerStrategy:
        """
        Get the appropriate optimization strategy.

        Args:
            meet_type: "dual", "championship", or "invitational"
            quality_mode: For Aqua - "fast", "balanced", or "thorough"
            force_strategy: Override auto-selection with "gurobi", "aqua", or "heuristic"
            meet_profile: Specific meet profile name (e.g., "vcac_championship",
                         "visaa_state"). If None, inferred from meet_type.

        Returns:
            Configured optimizer strategy
        """
        # Handle forced strategy
        if force_strategy:
            return self._get_forced_strategy(
                force_strategy, meet_type, quality_mode, meet_profile
            )

        # Auto-select: Aqua is PRIMARY, Gurobi only if explicitly preferred
        use_gurobi = self.has_gurobi() and self.prefer_gurobi

        if meet_type == MeetType.DUAL.value or meet_type == "dual":
            return self._get_dual_strategy(use_gurobi, quality_mode)

        elif meet_type == MeetType.CHAMPIONSHIP.value or meet_type == "championship":
            return self._get_championship_strategy(
                use_gurobi, quality_mode, meet_profile
            )

        else:
            # Invitational or unknown - use Aqua with championship profile
            logger.info(f"Unknown meet type '{meet_type}', using Aqua optimizer")
            profile_name = meet_profile or "vcac_championship"
            return AquaOptimizer(
                profile=ScoringProfile.from_meet_profile(profile_name),
                quality_mode=quality_mode,
            )

    def _get_dual_strategy(
        self, use_gurobi: bool, quality_mode: str
    ) -> BaseOptimizerStrategy:
        """Get strategy for dual meets."""
        if use_gurobi:
            try:
                from swim_ai_reflex.backend.core.strategies.gurobi_strategy import (
                    GurobiStrategy,
                )

                logger.info("Using GurobiStrategy for dual meet")
                return GurobiStrategy()
            except Exception as e:
                logger.warning(
                    f"Gurobi failed to initialize: {e}, falling back to Aqua"
                )

        logger.info("Using AquaOptimizer for dual meet")
        return AquaOptimizer(
            profile=ScoringProfile.visaa_dual(), quality_mode=quality_mode
        )

    def _get_championship_strategy(
        self, use_gurobi: bool, quality_mode: str, meet_profile: str | None = None
    ) -> BaseOptimizerStrategy:
        """Get strategy for championship meets."""
        profile_name = meet_profile or "vcac_championship"

        if use_gurobi:
            try:
                from swim_ai_reflex.backend.core.strategies.championship_strategy import (
                    ChampionshipGurobiStrategy,
                )

                logger.info(
                    "Using ChampionshipGurobiStrategy for championship (%s)",
                    profile_name,
                )
                return ChampionshipGurobiStrategy(meet_profile=profile_name)
            except Exception as e:
                logger.warning(f"Championship Gurobi failed: {e}, falling back to Aqua")

        logger.info("Using AquaOptimizer (championship profile: %s)", profile_name)
        return AquaOptimizer(
            profile=ScoringProfile.from_meet_profile(profile_name),
            quality_mode=quality_mode,
        )

    def _get_forced_strategy(
        self,
        force_strategy: str,
        meet_type: str,
        quality_mode: str,
        meet_profile: str | None = None,
    ) -> BaseOptimizerStrategy:
        """Get a specific forced strategy."""
        if force_strategy == "gurobi":
            if meet_type == "championship":
                from swim_ai_reflex.backend.core.strategies.championship_strategy import (
                    ChampionshipGurobiStrategy,
                )

                profile_name = meet_profile or "vcac_championship"
                return ChampionshipGurobiStrategy(meet_profile=profile_name)
            else:
                from swim_ai_reflex.backend.core.strategies.gurobi_strategy import (
                    GurobiStrategy,
                )

                return GurobiStrategy()

        elif force_strategy == "aqua":
            if meet_type == "championship":
                profile_name = meet_profile or "vcac_championship"
            else:
                profile_name = meet_profile or "visaa_dual"
            profile = ScoringProfile.from_meet_profile(profile_name)
            return AquaOptimizer(profile=profile, quality_mode=quality_mode)

        elif force_strategy == "heuristic":
            return HeuristicStrategy()

        else:
            raise ValueError(f"Unknown strategy: {force_strategy}")

    def get_available_strategies(self) -> dict[str, bool]:
        """Return available strategies and their status."""
        return {
            "gurobi": self.has_gurobi(),
            "aqua": True,  # Always available
            "heuristic": True,  # Always available
        }


# Convenience function
def get_optimizer(
    meet_type: str = "dual",
    quality_mode: str = "balanced",
    prefer_gurobi: bool = False,
    meet_profile: str | None = None,
) -> BaseOptimizerStrategy:
    """
    Get an optimizer for the given meet type.

    Args:
        meet_type: "dual" or "championship"
        quality_mode: "fast", "balanced", or "thorough"
        prefer_gurobi: If True, use Gurobi instead of Aqua (for validation)
        meet_profile: Specific meet profile (e.g., "visaa_state", "vcac_championship")

    Returns:
        Configured optimizer (Aqua by default)
    """
    router = MeetOptimizationRouter(prefer_gurobi=prefer_gurobi)
    return router.get_strategy(
        meet_type=meet_type, quality_mode=quality_mode, meet_profile=meet_profile
    )


__all__ = ["MeetOptimizationRouter", "MeetType", "get_optimizer"]
