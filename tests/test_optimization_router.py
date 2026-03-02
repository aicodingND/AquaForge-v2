"""
Tests for MeetOptimizationRouter.

Verifies:
- Correct strategy selection by meet type
- Gurobi fallback to Aqua
- Forced strategy override
- Quality mode propagation
"""

from unittest.mock import patch

import pytest

from swim_ai_reflex.backend.core.strategies.aqua_optimizer import AquaOptimizer
from swim_ai_reflex.backend.core.strategies.heuristic_strategy import HeuristicStrategy
from swim_ai_reflex.backend.core.strategies.optimization_router import (
    MeetOptimizationRouter,
    MeetType,
    get_optimizer,
)


class TestMeetOptimizationRouter:
    """Tests for strategy routing logic."""

    def test_meet_type_enum(self):
        """Verify MeetType enum values."""
        assert MeetType.DUAL.value == "dual"
        assert MeetType.CHAMPIONSHIP.value == "championship"
        assert MeetType.INVITATIONAL.value == "invitational"

    def test_router_returns_aqua_when_gurobi_unavailable(self):
        """Router should fallback to Aqua when Gurobi not installed."""
        with patch.dict("sys.modules", {"gurobipy": None}):
            router = MeetOptimizationRouter()
            router._gurobi_available = False  # Force no Gurobi

            strategy = router.get_strategy(meet_type="dual")
            assert isinstance(strategy, AquaOptimizer)

    def test_router_uses_aqua_by_default(self):
        """Router should use Aqua by default (Aqua is primary optimizer)."""
        router = MeetOptimizationRouter()  # prefer_gurobi=False by default
        strategy = router.get_strategy(meet_type="dual")
        assert isinstance(strategy, AquaOptimizer)

    def test_dual_meet_uses_dual_profile(self):
        """Dual meets should use VISAA dual scoring profile."""
        router = MeetOptimizationRouter()  # Aqua is default
        strategy = router.get_strategy(meet_type="dual")

        assert isinstance(strategy, AquaOptimizer)
        assert strategy.profile.name == "VISAA Dual Meet"
        assert strategy.profile.individual_points == [8, 6, 5, 4, 3, 2, 1]

    def test_championship_meet_uses_championship_profile(self):
        """Championship meets should use VCAC championship scoring profile."""
        router = MeetOptimizationRouter()  # Aqua is default
        strategy = router.get_strategy(meet_type="championship")

        assert isinstance(strategy, AquaOptimizer)
        assert strategy.profile.name == "VCAC Championship"
        assert len(strategy.profile.individual_points) == 12

    def test_quality_mode_propagates(self):
        """Quality mode should be passed to Aqua optimizer."""
        router = MeetOptimizationRouter()  # Aqua is default

        strategy = router.get_strategy(meet_type="dual", quality_mode="thorough")
        assert isinstance(strategy, AquaOptimizer)
        assert strategy.quality_mode == "thorough"

    def test_force_heuristic_strategy(self):
        """Force strategy should override auto-selection."""
        router = MeetOptimizationRouter()
        strategy = router.get_strategy(force_strategy="heuristic")
        assert isinstance(strategy, HeuristicStrategy)

    def test_force_aqua_strategy(self):
        """Force Aqua should work regardless of Gurobi availability."""
        router = MeetOptimizationRouter()
        strategy = router.get_strategy(meet_type="dual", force_strategy="aqua")
        assert isinstance(strategy, AquaOptimizer)

    def test_unknown_meet_type_uses_aqua(self):
        """Unknown meet types should default to Aqua with championship profile."""
        router = MeetOptimizationRouter()  # Aqua is default
        strategy = router.get_strategy(meet_type="invitational")

        assert isinstance(strategy, AquaOptimizer)
        assert strategy.profile.name == "VCAC Championship"

    def test_get_available_strategies(self):
        """Should report which strategies are available."""
        router = MeetOptimizationRouter()
        available = router.get_available_strategies()

        assert "gurobi" in available
        assert "aqua" in available
        assert "heuristic" in available
        assert available["aqua"] is True  # Always available
        assert available["heuristic"] is True  # Always available


class TestGetOptimizerConvenience:
    """Tests for get_optimizer convenience function."""

    def test_get_optimizer_default(self):
        """Default should return Aqua for dual meet (Aqua is primary)."""
        optimizer = get_optimizer()  # No args = Aqua
        assert isinstance(optimizer, AquaOptimizer)

    def test_get_optimizer_championship(self):
        """Championship should get championship profile."""
        optimizer = get_optimizer(meet_type="championship")  # Aqua is default
        assert isinstance(optimizer, AquaOptimizer)
        assert optimizer.profile.name == "VCAC Championship"

    def test_get_optimizer_prefer_gurobi(self):
        """When prefer_gurobi=True, should try Gurobi if available."""
        # Just verify the parameter is accepted (Gurobi may not be installed)
        get_optimizer(prefer_gurobi=True)
        # Result depends on Gurobi availability, but should not raise


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
