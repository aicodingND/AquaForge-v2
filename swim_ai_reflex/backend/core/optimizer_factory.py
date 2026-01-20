from typing import Dict, Type

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
    """

    _strategies: Dict[str, Type[BaseOptimizerStrategy]] = {
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
            strategy_name: Name of strategy ('heuristic', 'gurobi')

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
    def register_strategy(cls, name: str, strategy_class: Type[BaseOptimizerStrategy]):
        """Register a new strategy dynamically."""
        cls._strategies[name.lower()] = strategy_class
