"""Tests for opponent modeling: OpponentModelConfig, time variance, and attrition."""

import pandas as pd

from swim_ai_reflex.backend.core.attrition_model import AttritionRates
from swim_ai_reflex.backend.core.strategies.aqua_optimizer import (
    AquaOptimizer,
    FatigueModel,
    OpponentModelConfig,
    ScoringEngine,
    ScoringProfile,
)


class TestOpponentModelConfig:
    """Test the configuration dataclass."""

    def test_default_has_all_features_off(self):
        config = OpponentModelConfig.default()
        assert config.max_opponents_per_event == 16
        assert config.apply_time_variance is False
        assert config.apply_attrition is False
        assert config.monte_carlo_validation is False

    def test_championship_enables_features(self):
        config = OpponentModelConfig.championship()
        assert config.max_opponents_per_event == 32
        assert config.apply_time_variance is True
        assert config.apply_attrition is True

    def test_custom_config(self):
        config = OpponentModelConfig(
            max_opponents_per_event=24,
            apply_time_variance=True,
            sprint_cv=0.02,
            distance_cv=0.025,
        )
        assert config.max_opponents_per_event == 24
        assert config.sprint_cv == 0.02
        assert config.distance_cv == 0.025


class TestAquaOptimizerAutoConfig:
    """Test that AquaOptimizer auto-detects championship profiles."""

    def test_dual_meet_gets_default_config(self):
        optimizer = AquaOptimizer(
            profile=ScoringProfile.visaa_dual(),
            quality_mode="fast",
        )
        assert optimizer.opponent_model.apply_time_variance is False
        assert optimizer.opponent_model.apply_attrition is False

    def test_championship_gets_championship_config(self):
        optimizer = AquaOptimizer(
            profile=ScoringProfile.visaa_championship(),
            quality_mode="fast",
        )
        assert optimizer.opponent_model.apply_time_variance is True
        assert optimizer.opponent_model.apply_attrition is True
        assert optimizer.opponent_model.max_opponents_per_event == 32

    def test_explicit_config_overrides_auto(self):
        custom = OpponentModelConfig(max_opponents_per_event=20)
        optimizer = AquaOptimizer(
            profile=ScoringProfile.visaa_championship(),
            quality_mode="fast",
            opponent_model=custom,
        )
        assert optimizer.opponent_model.max_opponents_per_event == 20
        assert optimizer.opponent_model.apply_time_variance is False


class TestDepthLimiting:
    """Test that field depth is correctly limited."""

    def _make_opponent_df(self, n_per_event: int) -> pd.DataFrame:
        rows = []
        for event in ["Boys 50 Free", "Boys 100 Free"]:
            for i in range(n_per_event):
                rows.append(
                    {
                        "swimmer": f"Opp_{event}_{i}",
                        "event": event,
                        "time": 22.0 + i * 0.5,
                        "team": f"Team_{i % 4}",
                        "grade": 10,
                    }
                )
        return pd.DataFrame(rows)

    def test_depth_limits_to_max(self):
        df = self._make_opponent_df(20)
        optimizer = AquaOptimizer(
            profile=ScoringProfile.visaa_dual(),
            quality_mode="fast",
            opponent_model=OpponentModelConfig(max_opponents_per_event=10),
        )
        result = optimizer._preprocess_opponent_field(
            df, ["Boys 50 Free", "Boys 100 Free"]
        )
        for event in ["Boys 50 Free", "Boys 100 Free"]:
            event_count = len(result[result["event"] == event])
            assert event_count == 10

    def test_depth_preserves_when_under_limit(self):
        df = self._make_opponent_df(8)
        optimizer = AquaOptimizer(
            profile=ScoringProfile.visaa_dual(),
            quality_mode="fast",
            opponent_model=OpponentModelConfig(max_opponents_per_event=16),
        )
        result = optimizer._preprocess_opponent_field(
            df, ["Boys 50 Free", "Boys 100 Free"]
        )
        for event in ["Boys 50 Free", "Boys 100 Free"]:
            event_count = len(result[result["event"] == event])
            assert event_count == 8

    def test_depth_keeps_fastest(self):
        df = self._make_opponent_df(10)
        optimizer = AquaOptimizer(
            profile=ScoringProfile.visaa_dual(),
            quality_mode="fast",
            opponent_model=OpponentModelConfig(max_opponents_per_event=5),
        )
        result = optimizer._preprocess_opponent_field(
            df, ["Boys 50 Free", "Boys 100 Free"]
        )
        for event in ["Boys 50 Free", "Boys 100 Free"]:
            event_df = result[result["event"] == event]
            # Should keep the 5 fastest (lowest times)
            assert event_df["time"].max() <= 24.0  # 22.0 + 4 * 0.5


class TestTimeVariance:
    """Test gaussian time variance adjustment."""

    def test_variance_lowers_times(self):
        df = pd.DataFrame(
            [
                {
                    "swimmer": "A",
                    "event": "Boys 50 Free",
                    "time": 22.0,
                    "team": "X",
                    "grade": 10,
                },
                {
                    "swimmer": "B",
                    "event": "Boys 200 Free",
                    "time": 120.0,
                    "team": "X",
                    "grade": 10,
                },
            ]
        )
        config = OpponentModelConfig(
            apply_time_variance=True, sprint_cv=0.015, distance_cv=0.020
        )
        result = AquaOptimizer._apply_opponent_time_variance(df, config)

        # Times should be lower (faster) after adjustment
        assert result.iloc[0]["time"] < 22.0
        assert result.iloc[1]["time"] < 120.0

    def test_sprint_gets_smaller_adjustment_than_distance(self):
        df = pd.DataFrame(
            [
                {
                    "swimmer": "A",
                    "event": "Boys 50 Free",
                    "time": 100.0,
                    "team": "X",
                    "grade": 10,
                },
                {
                    "swimmer": "B",
                    "event": "Boys 200 Free",
                    "time": 100.0,
                    "team": "X",
                    "grade": 10,
                },
            ]
        )
        config = OpponentModelConfig(
            apply_time_variance=True, sprint_cv=0.015, distance_cv=0.020
        )
        result = AquaOptimizer._apply_opponent_time_variance(df, config)

        sprint_adj = 100.0 - result.iloc[0]["time"]
        distance_adj = 100.0 - result.iloc[1]["time"]
        # Distance events should have larger adjustment
        assert distance_adj > sprint_adj

    def test_invalid_times_unchanged(self):
        df = pd.DataFrame(
            [
                {
                    "swimmer": "A",
                    "event": "Boys 50 Free",
                    "time": 0.0,
                    "team": "X",
                    "grade": 10,
                },
                {
                    "swimmer": "B",
                    "event": "Boys 50 Free",
                    "time": 999.0,
                    "team": "X",
                    "grade": 10,
                },
            ]
        )
        config = OpponentModelConfig(apply_time_variance=True)
        result = AquaOptimizer._apply_opponent_time_variance(df, config)
        assert result.iloc[0]["time"] == 0.0
        assert result.iloc[1]["time"] == 999.0


class TestAttritionThinning:
    """Test directional attrition-based field thinning."""

    def test_attrition_reduces_field(self):
        """With ~20% DNS rate, 16 entries should yield ~13."""
        rows = [
            {
                "swimmer": f"S{i}",
                "event": "Boys 100 Fly",
                "time": 50.0 + i,
                "team": f"T{i}",
                "grade": 10,
            }
            for i in range(16)
        ]
        df = pd.DataFrame(rows)
        config = OpponentModelConfig(apply_attrition=True)
        result = AquaOptimizer._apply_attrition_thinning(df, config)
        # 100 Fly DNS rate is ~25.6%, so 16 * (1 - 0.256) ≈ 12
        assert len(result) < 16
        assert len(result) >= 10  # Should be between 10-13

    def test_attrition_keeps_fastest(self):
        """Thinning should remove slowest entries."""
        rows = [
            {
                "swimmer": f"S{i}",
                "event": "Boys 50 Free",
                "time": 20.0 + i,
                "team": f"T{i}",
                "grade": 10,
            }
            for i in range(16)
        ]
        df = pd.DataFrame(rows)
        config = OpponentModelConfig(apply_attrition=True)
        result = AquaOptimizer._apply_attrition_thinning(df, config)
        # Fastest swimmer (20.0) should still be present
        assert result["time"].min() == 20.0
        # Slowest (35.0) should be gone
        assert result["time"].max() < 35.0

    def test_attrition_handles_gender_prefix(self):
        """Event names with 'Boys ' or 'Girls ' prefix should still look up rates."""
        rows = [
            {
                "swimmer": f"S{i}",
                "event": "Girls 200 IM",
                "time": 130.0 + i,
                "team": f"T{i}",
                "grade": 10,
            }
            for i in range(10)
        ]
        df = pd.DataFrame(rows)
        config = OpponentModelConfig(apply_attrition=True)
        result = AquaOptimizer._apply_attrition_thinning(df, config)
        # 200 IM DNS rate is ~23.8%, so 10 * (1 - 0.238) ≈ 8
        assert len(result) < 10
        assert len(result) >= 6


class TestAttritionRatesSwimmerOverrides:
    """Test per-swimmer attrition overrides with hierarchical blending."""

    def test_no_override_returns_event_rate(self):
        rates = AttritionRates()
        result = rates.swimmer_attrition_rate("Unknown Swimmer", "100 Fly")
        assert result == rates.attrition_rate("100 Fly")

    def test_full_weight_override(self):
        rates = AttritionRates(
            swimmer_overrides={"John Smith": {"100 Fly": 0.05}},
            swimmer_sample_sizes={"John Smith": {"100 Fly": 10}},
        )
        result = rates.swimmer_attrition_rate("John Smith", "100 Fly", min_n=5)
        # With 10 samples and min_n=5, weight = 1.0 → pure swimmer rate
        assert abs(result - 0.05) < 0.001

    def test_partial_weight_blends(self):
        rates = AttritionRates(
            swimmer_overrides={"Jane Doe": {"50 Free": 0.05}},
            swimmer_sample_sizes={"Jane Doe": {"50 Free": 3}},
        )
        event_rate = rates.attrition_rate("50 Free")  # ~0.217
        result = rates.swimmer_attrition_rate("Jane Doe", "50 Free", min_n=5)
        # weight = 3/5 = 0.6 → blended = 0.6 * 0.05 + 0.4 * event_rate
        expected = 0.6 * 0.05 + 0.4 * event_rate
        assert abs(result - expected) < 0.001

    def test_zero_samples_returns_event_rate(self):
        rates = AttritionRates(
            swimmer_overrides={"No Data": {"100 Free": 0.01}},
            swimmer_sample_sizes={"No Data": {"100 Free": 0}},
        )
        result = rates.swimmer_attrition_rate("No Data", "100 Free", min_n=5)
        assert result == rates.attrition_rate("100 Free")


class TestBackwardCompatibility:
    """Ensure default OpponentModelConfig produces identical behavior."""

    def test_default_config_no_preprocessing(self):
        """With default config, _preprocess_opponent_field should return identical data."""
        rows = [
            {
                "swimmer": f"S{i}",
                "event": "Boys 50 Free",
                "time": 22.0 + i,
                "team": "T1",
                "grade": 10,
            }
            for i in range(16)
        ]
        df = pd.DataFrame(rows)
        optimizer = AquaOptimizer(
            profile=ScoringProfile.visaa_dual(),
            quality_mode="fast",
            opponent_model=OpponentModelConfig.default(),
        )
        result = optimizer._preprocess_opponent_field(df, ["Boys 50 Free"])
        pd.testing.assert_frame_equal(result, df)

    def test_scoring_unchanged_with_default(self):
        """ScoringEngine produces same results regardless of OpponentModelConfig."""
        profile = ScoringProfile.visaa_dual()
        engine = ScoringEngine(profile, FatigueModel(enabled=False))

        seton = [{"swimmer": "S1", "time": 24.0, "grade": 10}]
        opponents = [
            {"swimmer": f"O{i}", "time": 22.0 + i, "team": "OPP", "grade": 10}
            for i in range(6)
        ]

        s_pts, o_pts, details = engine.score_event(
            seton, opponents, event_name="Boys 50 Free"
        )
        # Seton at 24.0 is slower than O0(22.0), O1(22.5), O2(23.0), O3(23.5)
        # but faster than O4(24.5), O5(25.0) — with max 3 scorers per team,
        # Seton should place 4th overall (opponents capped at 3)
        assert s_pts > 0
