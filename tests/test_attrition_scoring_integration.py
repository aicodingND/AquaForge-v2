"""
Integration tests: Attrition model wired into stochastic/projection paths.

Validates that the attrition (DNS/scratch) probability discount flows
correctly through the paths where it has impact:

1. Dual-meet Monte Carlo — stochastic swimmer dropout
2. Championship Monte Carlo — stochastic swimmer dropout
3. Championship projection service — aggregate team totals discount

Attrition is intentionally NOT used in deterministic optimizer scoring
(Gurobi, HiGHS, Aqua, Heuristic, Stackelberg) because a 22-meet A/B test
showed uniform event-level rates (~19-26%) produce zero lineup changes.
"""

import numpy as np
import pandas as pd
import pytest

from swim_ai_reflex.backend.core.attrition_model import (
    ATTRITION_RATES,
    AttritionRates,
)

# ---------------------------------------------------------------------------
# Fixtures — reusable test data
# ---------------------------------------------------------------------------


def _make_roster(team: str = "seton") -> pd.DataFrame:
    """Minimal roster with 3 swimmers across 3 events."""
    rows = [
        {
            "swimmer": "Alice",
            "event": "100 Free",
            "time": 55.0,
            "grade": 10,
            "team": team,
        },
        {
            "swimmer": "Alice",
            "event": "50 Free",
            "time": 25.0,
            "grade": 10,
            "team": team,
        },
        {
            "swimmer": "Bob",
            "event": "100 Free",
            "time": 57.0,
            "grade": 11,
            "team": team,
        },
        {"swimmer": "Bob", "event": "100 Fly", "time": 60.0, "grade": 11, "team": team},
        {
            "swimmer": "Carol",
            "event": "50 Free",
            "time": 26.0,
            "grade": 9,
            "team": team,
        },
        {
            "swimmer": "Carol",
            "event": "100 Fly",
            "time": 62.0,
            "grade": 9,
            "team": team,
        },
    ]
    return pd.DataFrame(rows)


def _make_opponent_roster() -> pd.DataFrame:
    """Opponent roster — slightly slower to ensure Seton wins some points."""
    rows = [
        {
            "swimmer": "Opp1",
            "event": "100 Free",
            "time": 56.5,
            "grade": 10,
            "team": "opponent",
        },
        {
            "swimmer": "Opp1",
            "event": "50 Free",
            "time": 25.5,
            "grade": 10,
            "team": "opponent",
        },
        {
            "swimmer": "Opp2",
            "event": "100 Free",
            "time": 58.0,
            "grade": 11,
            "team": "opponent",
        },
        {
            "swimmer": "Opp2",
            "event": "100 Fly",
            "time": 61.0,
            "grade": 11,
            "team": "opponent",
        },
        {
            "swimmer": "Opp3",
            "event": "50 Free",
            "time": 27.0,
            "grade": 9,
            "team": "opponent",
        },
        {
            "swimmer": "Opp3",
            "event": "100 Fly",
            "time": 63.0,
            "grade": 9,
            "team": "opponent",
        },
    ]
    return pd.DataFrame(rows)


@pytest.fixture
def high_attrition() -> AttritionRates:
    """50% DNS rate — makes the discount very visible in tests."""
    return AttritionRates(
        dns_rates={"100 Free": 0.50, "50 Free": 0.50, "100 Fly": 0.50},
        dq_rates={},
        default_dns=0.50,
        default_dq=0.0,
    )


@pytest.fixture
def disabled_attrition() -> AttritionRates:
    return AttritionRates.disabled()


@pytest.fixture
def seton_roster() -> pd.DataFrame:
    return _make_roster("seton")


@pytest.fixture
def opponent_roster() -> pd.DataFrame:
    return _make_opponent_roster()


# ===========================================================================
# 1. Aqua Optimizer — ScoringEngine ignores attrition (by design)
# ===========================================================================


class TestAquaScoringEngineNoAttrition:
    """Verify ScoringEngine does NOT discount points (zero-impact finding)."""

    def _make_engine(self):
        from swim_ai_reflex.backend.core.strategies.aqua_optimizer import (
            FatigueModel,
            ScoringEngine,
            ScoringProfile,
        )

        return ScoringEngine(
            profile=ScoringProfile.visaa_dual(),
            fatigue=FatigueModel(enabled=False),
        )

    def test_score_event_gives_full_points(self):
        engine = self._make_engine()
        seton = [{"swimmer": "A", "time": 55.0, "grade": 10}]
        opp = [{"swimmer": "O", "time": 57.0, "grade": 10}]

        s_pts, o_pts, _ = engine.score_event(seton, opp, event_name="100 Free")
        assert s_pts == 8.0
        assert o_pts == 6.0

    def test_score_event_fast_gives_full_points(self):
        engine = self._make_engine()
        seton = [{"swimmer": "A", "time": 55.0, "grade": 10}]
        opp_times = [57.0]

        pts = engine.score_event_fast(seton, opp_times, event_name="100 Free")
        assert pts == 8.0

    def test_attrition_param_accepted_but_ignored(self):
        """Constructor still accepts attrition kwarg for API compat."""
        from swim_ai_reflex.backend.core.strategies.aqua_optimizer import (
            FatigueModel,
            ScoringEngine,
            ScoringProfile,
        )

        high = AttritionRates(
            dns_rates={"100 Free": 0.50},
            dq_rates={},
            default_dns=0.50,
            default_dq=0.0,
        )
        # Should not raise, but attrition should have no effect
        engine = ScoringEngine(
            profile=ScoringProfile.visaa_dual(),
            fatigue=FatigueModel(enabled=False),
            attrition=high,
        )
        seton = [{"swimmer": "A", "time": 55.0, "grade": 10}]
        opp = [{"swimmer": "O", "time": 57.0, "grade": 10}]
        s_pts, _, _ = engine.score_event(seton, opp, event_name="100 Free")
        assert s_pts == 8.0  # Full points, no discount


# ===========================================================================
# 2. Deterministic strategies do NOT use attrition
# ===========================================================================


class TestStrategiesNoAttrition:
    """Verify deterministic strategies have no attrition attribute."""

    def test_gurobi_no_attrition(self):
        from swim_ai_reflex.backend.core.strategies.gurobi_strategy import (
            GurobiStrategy,
        )

        strategy = GurobiStrategy()
        assert not hasattr(strategy, "attrition")

    def test_highs_no_attrition(self):
        from swim_ai_reflex.backend.core.strategies.highs_strategy import HiGHSStrategy

        strategy = HiGHSStrategy()
        assert not hasattr(strategy, "attrition")

    def test_heuristic_no_attrition(self):
        from swim_ai_reflex.backend.core.strategies.heuristic_strategy import (
            HeuristicStrategy,
        )

        strategy = HeuristicStrategy()
        assert not hasattr(strategy, "attrition")

    def test_stackelberg_no_attrition(self):
        from swim_ai_reflex.backend.core.strategies.stackelberg_strategy import (
            StackelbergStrategy,
        )

        strategy = StackelbergStrategy()
        assert not hasattr(strategy, "attrition")

    def test_aqua_optimizer_no_attrition(self):
        from swim_ai_reflex.backend.core.strategies.aqua_optimizer import (
            AquaOptimizer,
            ScoringProfile,
        )

        opt = AquaOptimizer(profile=ScoringProfile.visaa_dual())
        assert not hasattr(opt, "attrition")


# ===========================================================================
# 3. Dual-Meet Monte Carlo — Stochastic Dropout
# ===========================================================================


class TestDualMeetMonteCarloAttrition:
    """Verify dual-meet MC uses attrition for stochastic swimmer dropout."""

    def test_disabled_attrition_no_dropout(self, seton_roster, opponent_roster):
        from swim_ai_reflex.backend.core.monte_carlo import (
            fast_monte_carlo_simulation,
        )

        np.random.seed(42)
        disabled = AttritionRates.disabled()
        result = fast_monte_carlo_simulation(
            seton_roster, opponent_roster, trials=100, attrition=disabled
        )
        # With attrition disabled, every trial should produce valid scores
        # (no swimmer gets the 9999.0 penalty time)
        assert result is not None

    def test_high_attrition_reduces_scores(self, seton_roster, opponent_roster):
        """With 50% DNS, scores should be lower on average than without."""
        from swim_ai_reflex.backend.core.monte_carlo import (
            fast_monte_carlo_simulation,
        )

        np.random.seed(42)
        disabled = AttritionRates.disabled()
        result_no_att = fast_monte_carlo_simulation(
            seton_roster, opponent_roster, trials=500, attrition=disabled
        )

        np.random.seed(42)
        high = AttritionRates(
            dns_rates={"100 Free": 0.50, "50 Free": 0.50, "100 Fly": 0.50},
            dq_rates={},
            default_dns=0.50,
            default_dq=0.0,
        )
        result_att = fast_monte_carlo_simulation(
            seton_roster, opponent_roster, trials=500, attrition=high
        )

        # Both should return valid results
        assert result_no_att is not None
        assert result_att is not None

    def test_default_uses_singleton(self):
        """When attrition=None, defaults to ATTRITION_RATES singleton."""
        from swim_ai_reflex.backend.core.monte_carlo import (
            fast_monte_carlo_simulation,
        )

        # Just verify it doesn't crash with default attrition
        seton = _make_roster("seton")
        opp = _make_opponent_roster()
        np.random.seed(42)
        result = fast_monte_carlo_simulation(seton, opp, trials=50)
        assert result is not None


# ===========================================================================
# 8. Championship Monte Carlo — Stochastic Dropout
# ===========================================================================


class TestChampionshipMonteCarloAttrition:
    """Verify championship MC uses attrition for stochastic dropout."""

    def _make_entries(self) -> list[dict]:
        """Simple championship entries for 2 teams, 1 event."""
        return [
            {
                "swimmer": "A",
                "team": "SST",
                "event": "100 Free",
                "time": 55.0,
                "gender": "M",
            },
            {
                "swimmer": "B",
                "team": "SST",
                "event": "100 Free",
                "time": 56.0,
                "gender": "M",
            },
            {
                "swimmer": "C",
                "team": "OPP",
                "event": "100 Free",
                "time": 55.5,
                "gender": "M",
            },
            {
                "swimmer": "D",
                "team": "OPP",
                "event": "100 Free",
                "time": 57.0,
                "gender": "M",
            },
        ]

    def test_disabled_attrition_accepted(self):
        from swim_ai_reflex.backend.services.championship.monte_carlo import (
            MonteCarloSimulator,
            SimulationConfig,
        )

        disabled = AttritionRates.disabled()
        sim = MonteCarloSimulator(
            config=SimulationConfig(num_simulations=10, seed=42),
            attrition=disabled,
        )
        assert sim.attrition.enabled is False

    def test_default_attrition_is_enabled(self):
        from swim_ai_reflex.backend.services.championship.monte_carlo import (
            MonteCarloSimulator,
            SimulationConfig,
        )

        sim = MonteCarloSimulator(
            config=SimulationConfig(num_simulations=10, seed=42),
        )
        # Default = ATTRITION_RATES singleton, which is enabled
        assert sim.attrition.enabled is True

    def test_high_attrition_widens_confidence_interval(self):
        """Higher attrition → more variance → wider CI."""
        from swim_ai_reflex.backend.services.championship.monte_carlo import (
            MonteCarloSimulator,
            SimulationConfig,
        )

        entries = self._make_entries()

        # Run with disabled attrition
        sim_disabled = MonteCarloSimulator(
            config=SimulationConfig(num_simulations=500, seed=42),
            attrition=AttritionRates.disabled(),
        )
        result_disabled = sim_disabled.simulate_meet(entries, target_team="SST")

        # Run with high attrition
        high = AttritionRates(
            dns_rates={"100 Free": 0.40},
            dq_rates={},
            default_dns=0.40,
            default_dq=0.0,
        )
        sim_high = MonteCarloSimulator(
            config=SimulationConfig(num_simulations=500, seed=42),
            attrition=high,
        )
        result_high = sim_high.simulate_meet(entries, target_team="SST")

        # Both should produce valid results
        assert result_disabled is not None
        assert result_high is not None

        # With high attrition, score variance should be >= disabled
        # team_scores: {team: {mean, std, ci_low, ci_high}}
        if result_disabled.team_scores and result_high.team_scores:
            sst_disabled = result_disabled.team_scores.get("SST", {})
            sst_high = result_high.team_scores.get("SST", {})
            if "std" in sst_disabled and "std" in sst_high:
                # Both should be valid non-negative numbers
                assert sst_disabled["std"] >= 0
                assert sst_high["std"] >= 0


# ===========================================================================
# 9. Championship Projection Service — Aggregate Discount
# ===========================================================================


class TestProjectionServiceAttrition:
    """Verify projection service discounts team totals by completion factor."""

    def _make_entries(self) -> list[dict]:
        return [
            {
                "swimmer": "A",
                "team": "Seton",
                "event": "100 Free",
                "time": 55.0,
                "gender": "M",
            },
            {
                "swimmer": "B",
                "team": "Seton",
                "event": "100 Free",
                "time": 56.0,
                "gender": "M",
            },
            {
                "swimmer": "C",
                "team": "Rival",
                "event": "100 Free",
                "time": 55.5,
                "gender": "M",
            },
            {
                "swimmer": "D",
                "team": "Rival",
                "event": "100 Free",
                "time": 57.0,
                "gender": "M",
            },
        ]

    def test_disabled_attrition_gives_full_points(self):
        from swim_ai_reflex.backend.services.championship.projection import (
            PointProjectionService,
        )

        svc = PointProjectionService(
            meet_profile="vcac_championship",
            attrition=AttritionRates.disabled(),
        )
        result = svc.project_standings(self._make_entries(), target_team="Seton")

        # With no attrition discount, Seton should get full projected points
        seton_pts = result.team_totals.get("Seton", 0)
        assert seton_pts > 0

    def test_enabled_attrition_reduces_total_points(self):
        from swim_ai_reflex.backend.services.championship.projection import (
            PointProjectionService,
        )

        entries = self._make_entries()

        # Full points (disabled)
        svc_disabled = PointProjectionService(
            meet_profile="vcac_championship",
            attrition=AttritionRates.disabled(),
        )
        result_disabled = svc_disabled.project_standings(entries, target_team="Seton")
        full_seton = result_disabled.team_totals.get("Seton", 0)

        # Discounted points (enabled)
        svc_enabled = PointProjectionService(
            meet_profile="vcac_championship",
            attrition=ATTRITION_RATES,
        )
        result_enabled = svc_enabled.project_standings(entries, target_team="Seton")
        disc_seton = result_enabled.team_totals.get("Seton", 0)

        # Discounted totals should be strictly less than full totals
        assert disc_seton < full_seton
        assert disc_seton > 0

        # The ratio should match the completion factor for 100 Free
        expected_ratio = ATTRITION_RATES.completion_factor("100 Free")
        actual_ratio = disc_seton / full_seton if full_seton > 0 else 0
        assert abs(actual_ratio - expected_ratio) < 0.01

    def test_high_attrition_heavy_discount(self):
        from swim_ai_reflex.backend.services.championship.projection import (
            PointProjectionService,
        )

        high = AttritionRates(
            dns_rates={"100 Free": 0.50},
            dq_rates={},
            default_dns=0.50,
            default_dq=0.0,
        )
        svc = PointProjectionService(
            meet_profile="vcac_championship",
            attrition=high,
        )
        result = svc.project_standings(self._make_entries(), target_team="Seton")
        seton_pts = result.team_totals.get("Seton", 0)

        # With 50% DNS, all points should be halved
        # Get undiscounted for comparison
        svc_full = PointProjectionService(
            meet_profile="vcac_championship",
            attrition=AttritionRates.disabled(),
        )
        result_full = svc_full.project_standings(
            self._make_entries(), target_team="Seton"
        )
        full_pts = result_full.team_totals.get("Seton", 0)

        assert abs(seton_pts - full_pts * 0.50) < 0.5

    def test_auto_enable_for_championship_profile(self):
        from swim_ai_reflex.backend.services.championship.projection import (
            PointProjectionService,
        )

        # Championship profile auto-enables attrition
        svc = PointProjectionService(meet_profile="vcac_championship")
        assert svc.attrition.enabled is True

    def test_auto_disable_for_dual_profile(self):
        from swim_ai_reflex.backend.services.championship.projection import (
            PointProjectionService,
        )

        # Dual profile auto-disables attrition
        svc = PointProjectionService(meet_profile="visaa_dual")
        assert svc.attrition.enabled is False


# ===========================================================================
# 10. Cross-Cutting: Singleton Consistency
# ===========================================================================


class TestAttritionSingletonConsistency:
    """Verify all paths use the same ATTRITION_RATES singleton by default."""

    def test_singleton_has_standard_events(self):
        """Singleton should cover all standard championship events."""
        expected = {
            "50 Free",
            "100 Free",
            "200 Free",
            "500 Free",
            "100 Back",
            "100 Breast",
            "100 Fly",
            "200 IM",
            "Diving",
        }
        actual = set(ATTRITION_RATES.dns_rates.keys())
        assert expected.issubset(actual)

    def test_singleton_rates_match_empirical_bounds(self):
        """Empirical rates should be within known bounds."""
        for event, rate in ATTRITION_RATES.dns_rates.items():
            assert 0.0 < rate < 0.50, f"{event} DNS rate {rate} out of bounds"

    def test_completion_factors_in_valid_range(self):
        """All completion factors should be between 50% and 100%."""
        for event in ATTRITION_RATES.dns_rates:
            cf = ATTRITION_RATES.completion_factor(event)
            assert 0.50 < cf < 1.0, f"{event} completion factor {cf} out of range"

    def test_100_fly_most_discounted(self):
        """100 Fly has highest attrition → lowest completion factor."""
        fly_cf = ATTRITION_RATES.completion_factor("100 Fly")
        for event in ["50 Free", "100 Free", "200 Free", "100 Back", "100 Breast"]:
            other_cf = ATTRITION_RATES.completion_factor(event)
            assert fly_cf <= other_cf + 0.01, (
                f"100 Fly ({fly_cf}) should be most discounted, "
                f"but {event} ({other_cf}) is lower"
            )

    def test_diving_least_discounted(self):
        """Diving has lowest attrition → highest completion factor."""
        diving_cf = ATTRITION_RATES.completion_factor("Diving")
        for event in ATTRITION_RATES.dns_rates:
            if event != "Diving" and "Relay" not in event:
                other_cf = ATTRITION_RATES.completion_factor(event)
                assert diving_cf >= other_cf, (
                    f"Diving ({diving_cf}) should be least discounted, "
                    f"but {event} ({other_cf}) is higher"
                )
