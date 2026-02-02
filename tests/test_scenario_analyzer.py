"""
Tests for Scenario Analyzer.

Tests what-if analysis for line-up decisions.
"""

from datetime import date

import pytest

from swim_ai_reflex.backend.models.championship import (
    MeetPsychSheet,
    PsychSheetEntry,
)
from swim_ai_reflex.backend.services.scenario_analyzer import (
    ScenarioAnalyzer,
    ScenarioComparison,
    SwapOption,
    create_scenario_analyzer,
)

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def sample_psych_sheet():
    """Create a sample psych sheet for testing."""
    entries = [
        PsychSheetEntry(
            swimmer_name="John Smith", team="SST", event="Boys 50 Free", seed_time=22.45
        ),
        PsychSheetEntry(
            swimmer_name="John Smith",
            team="SST",
            event="Boys 100 Free",
            seed_time=49.50,
        ),
        PsychSheetEntry(
            swimmer_name="Mike Jones", team="SST", event="Boys 50 Free", seed_time=23.10
        ),
        PsychSheetEntry(
            swimmer_name="Mike Jones", team="SST", event="Boys 100 Fly", seed_time=55.00
        ),
        PsychSheetEntry(
            swimmer_name="Bob Wilson",
            team="Trinity",
            event="Boys 50 Free",
            seed_time=22.67,
        ),
        PsychSheetEntry(
            swimmer_name="Bob Wilson",
            team="Trinity",
            event="Boys 100 Free",
            seed_time=50.10,
        ),
        PsychSheetEntry(
            swimmer_name="Tom Davis",
            team="Trinity",
            event="Boys 50 Free",
            seed_time=23.50,
        ),
        PsychSheetEntry(
            swimmer_name="Jim Brown",
            team="Paul VI",
            event="Boys 50 Free",
            seed_time=22.89,
        ),
        PsychSheetEntry(
            swimmer_name="Jim Brown",
            team="Paul VI",
            event="Boys 100 Free",
            seed_time=51.00,
        ),
    ]

    return MeetPsychSheet(
        meet_name="Test Championship",
        meet_date=date.today(),
        teams=["SST", "Trinity", "Paul VI"],
        entries=entries,
    )


@pytest.fixture
def analyzer(sample_psych_sheet):
    """Create analyzer with sample data."""
    return create_scenario_analyzer(sample_psych_sheet, target_team="SST")


# ============================================================================
# Test: Scenario Comparison
# ============================================================================


class TestCompareScenarios:
    """Tests for comparing line-up scenarios."""

    def test_compare_identical_lineups(self, analyzer):
        """Identical lineups should have zero net change."""
        lineup = {
            "John Smith": ["Boys 50 Free", "Boys 100 Free"],
            "Mike Jones": ["Boys 100 Fly"],
        }

        comparison = analyzer.compare_scenarios(lineup, lineup)

        assert isinstance(comparison, ScenarioComparison)
        assert comparison.net_change == 0

    def test_compare_returns_recommendation(self, analyzer):
        """Comparison should include a recommendation."""
        base = {"John Smith": ["Boys 50 Free"]}
        alt = {"John Smith": ["Boys 100 Free"]}

        comparison = analyzer.compare_scenarios(base, alt)

        assert comparison.recommendation is not None
        assert len(comparison.recommendation) > 0

    def test_compare_tracks_changes(self, analyzer):
        """Comparison should track what changed."""
        base = {"John Smith": ["Boys 50 Free"]}
        alt = {"John Smith": ["Boys 100 Free"]}

        comparison = analyzer.compare_scenarios(base, alt)

        assert len(comparison.changes_made) >= 1


# ============================================================================
# Test: Find Best Swap
# ============================================================================


class TestFindBestSwap:
    """Tests for finding optimal event swaps."""

    def test_find_swaps_returns_list(self, analyzer):
        """Should return list of swap options."""
        swaps = analyzer.find_best_swap(
            swimmer="John Smith", from_event="Boys 100 Free"
        )

        assert isinstance(swaps, list)

    def test_swap_options_have_net_change(self, analyzer):
        """Each swap should have net change calculated."""
        swaps = analyzer.find_best_swap(
            swimmer="John Smith", from_event="Boys 100 Free"
        )

        for swap in swaps:
            assert isinstance(swap, SwapOption)
            assert hasattr(swap, "net_change")
            assert hasattr(swap, "feasible")

    def test_swaps_sorted_by_gain(self, analyzer):
        """Swaps should be sorted by net gain."""
        swaps = analyzer.find_best_swap(
            swimmer="John Smith", from_event="Boys 100 Free"
        )

        # Filter to feasible only and check sorting
        feasible = [s for s in swaps if s.feasible]
        if len(feasible) >= 2:
            for i in range(len(feasible) - 1):
                assert feasible[i].net_change >= feasible[i + 1].net_change


# ============================================================================
# Test: Quick What-If
# ============================================================================


class TestQuickWhatIf:
    """Tests for natural language what-if queries."""

    def test_quick_what_if_returns_string(self, analyzer):
        """Should return a string response."""
        result = analyzer.quick_what_if(
            "move John Smith from Boys 100 Free to Boys 50 Free"
        )

        assert isinstance(result, str)
        assert len(result) > 0

    def test_quick_what_if_handles_unknown_format(self, analyzer):
        """Should handle unknown query format gracefully."""
        result = analyzer.quick_what_if("do something random")

        assert "Unknown" in result or "Try" in result


# ============================================================================
# Test: Factory Function
# ============================================================================


def test_create_scenario_analyzer(sample_psych_sheet):
    """Factory should create valid analyzer."""
    analyzer = create_scenario_analyzer(sample_psych_sheet)

    assert isinstance(analyzer, ScenarioAnalyzer)
    assert analyzer.target_team == "SST"
