"""
Test suite for championship adjustment factors.

Validates the empirical speed-up factors derived from 25,830 entries
across 52 championship meets. These factors adjust seed times to
account for swimmers typically going faster at championships.

CRITICAL INVARIANTS:
- All factors < 1.0 (swimmers go faster, not slower)
- Default factor ~0.99 (1% speed-up across all events)
- Disabled mode returns identity (factor = 1.0, no adjustment)
- Invalid times (0, negative, 599+) pass through unchanged
"""

import pandas as pd
import pytest

from swim_ai_reflex.backend.core.championship_factors import (
    CHAMPIONSHIP_FACTORS,
    DEFAULT_FACTOR,
    EVENT_CONFIDENCE,
    EVENT_FACTORS,
    ChampionshipFactors,
    adjust_time,
    adjust_times_df,
    get_event_confidence,
    get_low_confidence_events,
)


class TestEventFactorsData:
    """Validate the hardcoded empirical factor data."""

    def test_all_factors_less_than_one(self):
        """Swimmers go faster at championships — all factors must be < 1.0."""
        for event, factor in EVENT_FACTORS.items():
            assert factor < 1.0, f"{event} factor {factor} >= 1.0"

    def test_all_factors_greater_than_threshold(self):
        """No event has more than 2% speed-up (sanity check)."""
        for event, factor in EVENT_FACTORS.items():
            assert factor > 0.98, f"{event} factor {factor} too low (> 2% speed-up)"

    def test_default_factor_reasonable(self):
        """Default factor should be ~0.99 (1% speed-up)."""
        assert 0.98 < DEFAULT_FACTOR < 1.0

    def test_standard_events_covered(self):
        """All 8 standard championship events have factors."""
        expected = {
            "50 Free",
            "100 Free",
            "200 Free",
            "500 Free",
            "100 Back",
            "100 Breast",
            "100 Fly",
            "200 IM",
        }
        assert set(EVENT_FACTORS.keys()) == expected

    def test_confidence_tiers_valid(self):
        """All confidence tiers are high, medium, or low."""
        for event, tier in EVENT_CONFIDENCE.items():
            assert tier in ("high", "medium", "low"), (
                f"{event} has invalid tier: {tier}"
            )

    def test_confidence_covers_same_events_as_factors(self):
        """Confidence tiers should exist for every event with a factor."""
        assert set(EVENT_CONFIDENCE.keys()) == set(EVENT_FACTORS.keys())

    def test_50_free_is_low_confidence(self):
        """50 Free has 82%+ flip rate — must be flagged low."""
        assert EVENT_CONFIDENCE["50 Free"] == "low"


class TestChampionshipFactorsDataclass:
    """Test the ChampionshipFactors container."""

    def test_default_instance_is_enabled(self):
        factors = ChampionshipFactors()
        assert factors.enabled is True

    def test_disabled_instance(self):
        factors = ChampionshipFactors.disabled()
        assert factors.enabled is False
        assert factors.get_factor("100 Free") == 1.0

    def test_get_factor_known_event(self):
        factors = ChampionshipFactors()
        result = factors.get_factor("200 Free")
        assert result == EVENT_FACTORS["200 Free"]

    def test_get_factor_unknown_event_uses_default(self):
        factors = ChampionshipFactors()
        result = factors.get_factor("1650 Free")
        assert result == DEFAULT_FACTOR

    def test_get_confidence_known_event(self):
        factors = ChampionshipFactors()
        assert factors.get_confidence("200 IM") == "high"

    def test_get_confidence_unknown_event_defaults_medium(self):
        factors = ChampionshipFactors()
        assert factors.get_confidence("1650 Free") == "medium"

    def test_from_json_missing_file_uses_defaults(self, tmp_path):
        factors = ChampionshipFactors.from_json(tmp_path / "nonexistent.json")
        assert factors.enabled is True
        assert factors.get_factor("100 Free") == EVENT_FACTORS["100 Free"]

    def test_from_json_loads_real_file(self):
        """Load from the actual generated championship_factors.json."""
        from pathlib import Path

        json_path = Path(__file__).parent.parent / "data" / "championship_factors.json"
        if not json_path.exists():
            pytest.skip("championship_factors.json not generated yet")
        factors = ChampionshipFactors.from_json(json_path)
        assert factors.enabled is True
        assert len(factors.event_factors) > 0


class TestAdjustTime:
    """Test the adjust_time() utility function."""

    def test_normal_time_gets_adjusted(self):
        """A valid seed time should be multiplied by the event factor."""
        result = adjust_time(25.0, "50 Free")
        expected = 25.0 * EVENT_FACTORS["50 Free"]
        assert abs(result - expected) < 0.001

    def test_zero_time_passthrough(self):
        """Zero times should not be adjusted."""
        assert adjust_time(0.0, "50 Free") == 0.0

    def test_negative_time_passthrough(self):
        """Negative times should not be adjusted."""
        assert adjust_time(-5.0, "100 Free") == -5.0

    def test_nt_placeholder_passthrough(self):
        """Times >= 599 (NT placeholder) should not be adjusted."""
        assert adjust_time(599.0, "100 Free") == 599.0
        assert adjust_time(9999.99, "100 Free") == 9999.99

    def test_unknown_event_uses_default_factor(self):
        """Events not in the factor table use the default 0.99x."""
        result = adjust_time(100.0, "800 Free")
        expected = 100.0 * DEFAULT_FACTOR
        assert abs(result - expected) < 0.001

    def test_disabled_factors_no_adjustment(self):
        """With disabled factors, time should be unchanged."""
        disabled = ChampionshipFactors.disabled()
        assert adjust_time(25.0, "50 Free", disabled) == 25.0

    def test_custom_factors_instance(self):
        """Custom factors should override defaults."""
        custom = ChampionshipFactors(event_factors={"50 Free": 0.95})
        result = adjust_time(25.0, "50 Free", custom)
        assert abs(result - 23.75) < 0.001

    def test_adjustment_always_makes_time_faster(self):
        """Championship adjustment should always reduce time (faster)."""
        for event in EVENT_FACTORS:
            original = 60.0
            adjusted = adjust_time(original, event)
            assert adjusted < original, f"{event}: {adjusted} >= {original}"


class TestAdjustTimesDF:
    """Test the DataFrame-level adjustment function."""

    def test_basic_dataframe_adjustment(self):
        df = pd.DataFrame(
            {
                "event": ["50 Free", "100 Free", "200 Free"],
                "time": [25.0, 55.0, 120.0],
            }
        )
        result = adjust_times_df(df)
        assert "seed_time_raw" in result.columns
        assert list(result["seed_time_raw"]) == [25.0, 55.0, 120.0]
        for i, row in result.iterrows():
            expected = row["seed_time_raw"] * EVENT_FACTORS[row["event"]]
            assert abs(row["time"] - expected) < 0.001

    def test_preserves_original_in_seed_time_raw(self):
        df = pd.DataFrame({"event": ["100 Fly"], "time": [60.0]})
        result = adjust_times_df(df)
        assert result["seed_time_raw"].iloc[0] == 60.0
        assert result["time"].iloc[0] < 60.0

    def test_disabled_factors_no_change(self):
        df = pd.DataFrame({"event": ["100 Fly"], "time": [60.0]})
        disabled = ChampionshipFactors.disabled()
        result = adjust_times_df(df, factors=disabled)
        assert result["time"].iloc[0] == 60.0
        assert "seed_time_raw" not in result.columns

    def test_missing_columns_returns_unchanged(self):
        df = pd.DataFrame({"name": ["swimmer"], "score": [100]})
        result = adjust_times_df(df)
        assert list(result.columns) == ["name", "score"]


class TestConfidenceTiers:
    """Test event confidence tier functions."""

    def test_get_event_confidence_known(self):
        assert get_event_confidence("200 Free") == "high"
        assert get_event_confidence("50 Free") == "low"
        assert get_event_confidence("100 Back") == "medium"

    def test_get_event_confidence_unknown_defaults_medium(self):
        assert get_event_confidence("800 Free") == "medium"

    def test_get_low_confidence_events_includes_50_free(self):
        low = get_low_confidence_events()
        assert "50 Free" in low

    def test_get_low_confidence_events_excludes_high(self):
        low = get_low_confidence_events()
        for event in low:
            assert EVENT_CONFIDENCE[event] == "low"


class TestSingletonBehavior:
    """Test the module-level singleton."""

    def test_singleton_is_enabled(self):
        assert CHAMPIONSHIP_FACTORS.enabled is True

    def test_singleton_has_all_events(self):
        assert len(CHAMPIONSHIP_FACTORS.event_factors) == 8
