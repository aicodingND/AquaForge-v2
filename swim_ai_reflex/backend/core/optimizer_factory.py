from swim_ai_reflex.backend.core.strategies.aqua_optimizer import AquaOptimizer
from swim_ai_reflex.backend.core.strategies.base_strategy import BaseOptimizerStrategy
from swim_ai_reflex.backend.core.strategies.gurobi_strategy import GurobiStrategy
from swim_ai_reflex.backend.core.strategies.heuristic_strategy import HeuristicStrategy
from swim_ai_reflex.backend.core.strategies.highs_strategy import HiGHSStrategy
from swim_ai_reflex.backend.core.strategies.stackelberg_strategy import (
    StackelbergStrategy,
)


class OptimizerFactory:
    """
    Factory for creating optimizer strategies.

    Available strategies:
    - heuristic: Fast greedy approach
    - gurobi: Commercial MIP solver ($10K license)
    - aqua: Custom hybrid optimizer (recommended)
    - highs: Free MIP solver (exact solutions, no license)
    - stackelberg: Game-theoretic bilevel optimization

    For meet-type-aware selection, use `get_strategy_for_meet()`.
    """

    _strategies: dict[str, type[BaseOptimizerStrategy]] = {
        "heuristic": HeuristicStrategy,
        "gurobi": GurobiStrategy,
        "stackelberg": StackelbergStrategy,  # Bilevel game-theoretic optimization
        "aqua": AquaOptimizer,  # License-free custom optimizer (recommended)
        "highs": HiGHSStrategy,  # Free MIP solver (exact optimal solutions)
    }

    @classmethod
    def get_strategy(cls, strategy_name: str) -> BaseOptimizerStrategy:
        """
        Get an instance of the requested strategy.

        Args:
            strategy_name: Name of strategy ('heuristic', 'gurobi', etc.)

        Returns:
            Instance of the requested strategy class

        Raises:
            ValueError: If strategy not found
        """
        strategy_class = cls._strategies.get(strategy_name.lower())

        if not strategy_class:
            valid = ", ".join(cls._strategies.keys())
            raise ValueError(
                f"Unknown strategy '{strategy_name}'. Valid options: {valid}"
            )

        return strategy_class()

    @classmethod
    def get_strategy_for_meet(
        cls,
        meet_type: str = "dual",
        quality_mode: str = "balanced",
        prefer_aqua: bool = False,
        force_strategy: str | None = None,
    ) -> BaseOptimizerStrategy:
        """
        Get the optimal strategy for a given meet type.

        Uses MeetOptimizationRouter for intelligent selection:
        - Dual meets: Gurobi (if available) → Aqua
        - Championship: ChampionshipGurobi (if available) → Aqua

        Args:
            meet_type: "dual" or "championship"
            quality_mode: "fast", "balanced", or "thorough" (for Aqua)
            prefer_aqua: Use Aqua even when Gurobi available
            force_strategy: Override with "gurobi", "aqua", or "heuristic"

        Returns:
            Configured optimizer strategy
        """
        from swim_ai_reflex.backend.core.strategies.optimization_router import (
            MeetOptimizationRouter,
        )

        router = MeetOptimizationRouter(prefer_aqua=prefer_aqua)
        return router.get_strategy(
            meet_type=meet_type,
            quality_mode=quality_mode,
            force_strategy=force_strategy,
        )

    @classmethod
    def register_strategy(cls, name: str, strategy_class: type[BaseOptimizerStrategy]):
        """Register a new strategy dynamically."""
        cls._strategies[name.lower()] = strategy_class

    @classmethod
    def list_strategies(cls) -> list[str]:
        """Return list of available strategy names."""
        return list(cls._strategies.keys())
