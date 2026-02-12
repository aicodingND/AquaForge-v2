"""
Test suite for the attrition (DQ/DNS/scratch) probability model.

Validates empirical rates derived from 77,345 entries across 162 meets.
The key finding: DQ is negligible (0.01%) but DNS/scratch is ~20%.

CRITICAL INVARIANTS:
- DNS rates between 0% and 50% for standard events
- DQ rates < 1% for all events
- Disabled mode returns 100% completion (no attrition)
- completion_factor = 1 - attrition_rate
- Stochastic should_swimmer_compete converges to expected rate
"""

import numpy as np
import pytest

from swim_ai_reflex.backend.core.attrition_model import (
    ATTRITION_RATES,
    DEFAULT_DNS_RATE,
    DEFAULT_DQ_RATE,
    DNS_RATES,
    DQ_RATES,
    AttritionRates,
    get_completion_probability,
    should_swimmer_compete,
)


class TestEmpiricalRatesData:
    """Validate the hardcoded empirical rate data."""

    def test_dns_rates_are_positive(self):
        for event, rate in DNS_RATES.items():
            assert rate > 0, f"{event} DNS rate should be > 0"

    def test_dns_rates_under_50_percent(self):
        """No standard event should have > 50% scratch rate."""
        for event, rate in DNS_RATES.items():
            assert rate < 0.50, f"{event} DNS rate {rate} > 50%"

    def test_dq_rates_under_1_percent(self):
        """DQ is negligible — all rates should be < 1%."""
        for event, rate in DQ_RATES.items():
            assert rate < 0.01, f"{event} DQ rate {rate} >= 1%"

    def test_100_fly_has_highest_dns(self):
        """100 Fly empirically has the highest DNS rate (~25.6%)."""
        fly_rate = DNS_RATES["100 Fly"]
        for event, rate in DNS_RATES.items():
            if event != "100 Fly" and event != "400 Free Relay":
                assert fly_rate >= rate - 0.01, (
                    f"100 Fly ({fly_rate}) should be near highest, "
                    f"but {event} is {rate}"
                )

    def test_diving_has_lowest_dns(self):
        """Diving has the lowest DNS rate (~6.5%)."""
        diving_rate = DNS_RATES["Diving"]
        for event, rate in DNS_RATES.items():
            if event != "Diving":
                assert diving_rate <= rate, (
                    f"Diving ({diving_rate}) should be lowest, but {event} is {rate}"
                )

    def test_default_dns_rate_matches_global(self):
        """Default rate ~20% matches the global average."""
        assert 0.15 < DEFAULT_DNS_RATE < 0.25

    def test_default_dq_rate_near_zero(self):
        assert DEFAULT_DQ_RATE < 0.001

    def test_standard_events_covered(self):
        """All 8 individual championship events plus diving and relays."""
        expected_individual = {
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
        assert expected_individual.issubset(set(DNS_RATES.keys()))


class TestAttritionRatesDataclass:
    """Test the AttritionRates container."""

    def test_default_instance_is_enabled(self):
        rates = AttritionRates()
        assert rates.enabled is True

    def test_disabled_instance(self):
        rates = AttritionRates.disabled()
        assert rates.enabled is False
        assert rates.dns_rate("100 Fly") == 0.0
        assert rates.dq_rate("100 Fly") == 0.0
        assert rates.completion_factor("100 Fly") == 1.0

    def test_dns_rate_known_event(self):
        rates = AttritionRates()
        result = rates.dns_rate("100 Fly")
        assert result == DNS_RATES["100 Fly"]

    def test_dns_rate_unknown_event_uses_default(self):
        rates = AttritionRates()
        result = rates.dns_rate("800 Free")
        assert result == DEFAULT_DNS_RATE

    def test_dq_rate_known_event(self):
        rates = AttritionRates()
        result = rates.dq_rate("200 Free")
        assert result == DQ_RATES["200 Free"]

    def test_dq_rate_unknown_event_uses_default(self):
        rates = AttritionRates()
        result = rates.dq_rate("800 Free")
        assert result == DEFAULT_DQ_RATE

    def test_attrition_rate_is_sum(self):
        """attrition_rate = dns_rate + dq_rate."""
        rates = AttritionRates()
        for event in DNS_RATES:
            expected = rates.dns_rate(event) + rates.dq_rate(event)
            assert abs(rates.attrition_rate(event) - expected) < 1e-10

    def test_completion_factor_is_complement(self):
        """completion_factor = 1 - attrition_rate."""
        rates = AttritionRates()
        for event in DNS_RATES:
            expected = 1.0 - rates.attrition_rate(event)
            assert abs(rates.completion_factor(event) - expected) < 1e-10

    def test_completion_factor_between_0_and_1(self):
        rates = AttritionRates()
        for event in DNS_RATES:
            cf = rates.completion_factor(event)
            assert 0.0 < cf <= 1.0, f"{event} completion factor {cf} out of range"

    def test_from_json_missing_file_uses_defaults(self, tmp_path):
        rates = AttritionRates.from_json(tmp_path / "nonexistent.json")
        assert rates.enabled is True
        assert rates.dns_rate("100 Fly") > 0

    def test_from_json_loads_real_file(self):
        """Load from the actual generated dq_dns_rates.json."""
        from pathlib import Path

        json_path = Path(__file__).parent.parent / "data" / "dq_dns_rates.json"
        if not json_path.exists():
            pytest.skip("dq_dns_rates.json not generated yet")
        rates = AttritionRates.from_json(json_path)
        assert rates.enabled is True
        assert len(rates.dns_rates) > 0
        assert rates.dns_rate("100 Fly") > 0.20


class TestCompletionProbability:
    """Test the get_completion_probability utility function."""

    def test_known_event(self):
        prob = get_completion_probability("100 Fly")
        expected = 1.0 - DNS_RATES["100 Fly"] - DQ_RATES.get("100 Fly", DEFAULT_DQ_RATE)
        assert abs(prob - expected) < 1e-10

    def test_diving_high_completion(self):
        """Diving should have ~93% completion (lowest attrition)."""
        prob = get_completion_probability("Diving")
        assert prob > 0.90

    def test_fly_lower_completion(self):
        """100 Fly should have ~74% completion (highest attrition)."""
        prob = get_completion_probability("100 Fly")
        assert 0.70 < prob < 0.80

    def test_custom_rates(self):
        custom = AttritionRates(dns_rates={"Test Event": 0.5}, default_dns=0.1)
        prob = get_completion_probability("Test Event", custom)
        assert abs(prob - 0.5) < 0.01  # ~50% completion


class TestShouldSwimmerCompete:
    """Test the stochastic decision function."""

    def test_always_competes_when_disabled(self):
        disabled = AttritionRates.disabled()
        for _ in range(100):
            assert should_swimmer_compete("100 Fly", np.random.random(), disabled)

    def test_never_competes_with_rng_zero(self):
        """rng=0.0 should always result in scratch (0 < any positive attrition rate)."""
        rates = AttritionRates()
        assert not should_swimmer_compete("100 Fly", 0.0, rates)

    def test_always_competes_with_rng_high(self):
        """rng close to 1.0 should always result in competing."""
        rates = AttritionRates()
        assert should_swimmer_compete("100 Fly", 0.99, rates)

    def test_stochastic_converges_to_expected_rate(self):
        """Over many trials, competition rate should match 1 - attrition."""
        rates = AttritionRates()
        np.random.seed(42)
        n_trials = 50000
        event = "100 Fly"
        competed = sum(
            should_swimmer_compete(event, np.random.random(), rates)
            for _ in range(n_trials)
        )
        actual_rate = competed / n_trials
        expected_rate = rates.completion_factor(event)
        # Allow 1% tolerance for stochastic convergence
        assert abs(actual_rate - expected_rate) < 0.01, (
            f"Expected ~{expected_rate:.3f}, got {actual_rate:.3f}"
        )

    def test_diving_competes_more_often(self):
        """Diving (6.5% DNS) should compete more often than 100 Fly (25.6% DNS)."""
        rates = AttritionRates()
        np.random.seed(123)
        n = 10000
        diving_competed = sum(
            should_swimmer_compete("Diving", np.random.random(), rates)
            for _ in range(n)
        )
        fly_competed = sum(
            should_swimmer_compete("100 Fly", np.random.random(), rates)
            for _ in range(n)
        )
        assert diving_competed > fly_competed


class TestSingletonBehavior:
    """Test the module-level singleton."""

    def test_singleton_is_enabled(self):
        assert ATTRITION_RATES.enabled is True

    def test_singleton_has_standard_events(self):
        assert len(ATTRITION_RATES.dns_rates) >= 9  # 8 individual + diving + relays
