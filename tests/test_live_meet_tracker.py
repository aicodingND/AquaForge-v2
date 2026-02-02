"""
Tests for Live Meet Tracker.

Tests real-time tracking of championship meet results,
standings calculations, and clinch scenario analysis.
"""

import pytest

from swim_ai_reflex.backend.services.live_meet_tracker import (
    ClinchScenario,
    LiveMeetTracker,
    LiveStandings,
    RecordedResult,
    create_live_tracker,
)

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def tracker():
    """Create a fresh tracker for testing."""
    return create_live_tracker(meet_profile="vcac_championship")


@pytest.fixture
def sample_entries():
    """Sample psych sheet entries for testing."""
    return [
        {
            "swimmer": "John Smith",
            "team": "SST",
            "event": "Boys 50 Free",
            "seed_time": 22.45,
        },
        {
            "swimmer": "Mike Jones",
            "team": "SST",
            "event": "Boys 50 Free",
            "seed_time": 23.10,
        },
        {
            "swimmer": "Bob Wilson",
            "team": "Trinity",
            "event": "Boys 50 Free",
            "seed_time": 22.67,
        },
        {
            "swimmer": "Tom Davis",
            "team": "Trinity",
            "event": "Boys 50 Free",
            "seed_time": 23.50,
        },
        {
            "swimmer": "Jim Brown",
            "team": "Paul VI",
            "event": "Boys 50 Free",
            "seed_time": 22.89,
        },
        {
            "swimmer": "Dan White",
            "team": "Paul VI",
            "event": "Boys 50 Free",
            "seed_time": 23.25,
        },
        # 100 Free entries
        {
            "swimmer": "John Smith",
            "team": "SST",
            "event": "Boys 100 Free",
            "seed_time": 49.50,
        },
        {
            "swimmer": "Bob Wilson",
            "team": "Trinity",
            "event": "Boys 100 Free",
            "seed_time": 50.10,
        },
        {
            "swimmer": "Jim Brown",
            "team": "Paul VI",
            "event": "Boys 100 Free",
            "seed_time": 51.00,
        },
    ]


# ============================================================================
# Test: Basic Recording
# ============================================================================


class TestRecordResult:
    """Tests for recording individual results."""

    def test_record_single_result(self, tracker):
        """Record a single result and verify it's stored."""
        result = tracker.record_result(
            event="Boys 50 Free", place=1, swimmer="John Smith", team="SST", time=22.15
        )

        assert isinstance(result, RecordedResult)
        assert result.event == "Boys 50 Free"
        assert result.place == 1
        assert result.swimmer == "John Smith"
        assert result.team == "SST"
        assert result.points > 0  # First place should have points

    def test_first_place_gets_max_points(self, tracker):
        """Verify first place gets maximum points."""
        result = tracker.record_result(
            event="Boys 50 Free", place=1, swimmer="John Smith", team="SST", time=22.15
        )

        # VCAC championship individual 1st = 16 points
        assert result.points == 16

    def test_relay_first_place_points(self, tracker):
        """Verify relay first place gets relay points."""
        result = tracker.record_result(
            event="Boys 200 Medley Relay",
            place=1,
            swimmer="SST Relay A",
            team="SST",
            time=95.50,
        )

        # VCAC championship relay 1st = 32 points (or 64 if 2x)
        assert result.points >= 32

    def test_multiple_results_same_event(self, tracker):
        """Record multiple results for the same event."""
        tracker.record_result("Boys 50 Free", 1, "John Smith", "SST", 22.15)
        tracker.record_result("Boys 50 Free", 2, "Bob Wilson", "Trinity", 22.45)
        tracker.record_result("Boys 50 Free", 3, "Jim Brown", "Paul VI", 22.67)

        assert len(tracker.results["Boys 50 Free"]) == 3
        assert tracker.teams == {"SST", "Trinity", "Paul VI"}

    def test_record_event_results_batch(self, tracker):
        """Record all results for an event at once."""
        results = [
            {"place": 1, "swimmer": "John Smith", "team": "SST", "time": 22.15},
            {"place": 2, "swimmer": "Bob Wilson", "team": "Trinity", "time": 22.45},
            {"place": 3, "swimmer": "Jim Brown", "team": "Paul VI", "time": 22.67},
        ]

        recorded = tracker.record_event_results("Boys 50 Free", results)

        assert len(recorded) == 3
        assert "Boys 50 Free" in tracker.completed_events


# ============================================================================
# Test: Standings Calculations
# ============================================================================


class TestGetCurrentStandings:
    """Tests for current standings calculation."""

    def test_empty_standings(self, tracker):
        """Empty tracker returns zero standings."""
        standings = tracker.get_current_standings()

        assert isinstance(standings, LiveStandings)
        assert standings.events_completed == 0

    def test_standings_after_one_event(self, tracker):
        """Standings update correctly after one event."""
        # SST wins 1st and 3rd, Trinity gets 2nd
        tracker.record_result("Boys 50 Free", 1, "John Smith", "SST", 22.15)
        tracker.record_result("Boys 50 Free", 2, "Bob Wilson", "Trinity", 22.45)
        tracker.record_result("Boys 50 Free", 3, "Mike Jones", "SST", 22.67)

        standings = tracker.get_current_standings()

        # SST should have more actual points than Trinity
        assert standings.team_totals["SST"] > standings.team_totals["Trinity"]

    def test_standings_track_multiple_events(self, tracker):
        """Standings accumulate across multiple events."""
        # Event 1
        tracker.record_result("Boys 50 Free", 1, "John Smith", "SST", 22.15)
        tracker.record_result("Boys 50 Free", 2, "Bob Wilson", "Trinity", 22.45)

        standings1 = tracker.get_current_standings()
        sst1 = standings1.team_totals.get("SST", 0)

        # Event 2
        tracker.record_result("Boys 100 Free", 1, "John Smith", "SST", 49.50)

        standings2 = tracker.get_current_standings()
        sst2 = standings2.team_totals.get("SST", 0)

        # Total should increase
        assert sst2 > sst1


# ============================================================================
# Test: Remaining Points
# ============================================================================


class TestGetRemainingPoints:
    """Tests for remaining points calculation."""

    def test_all_points_available_initially(self, tracker):
        """Before any results, all points are available."""
        tracker.teams.add("SST")

        remaining = tracker.get_remaining_points()

        assert "SST" in remaining
        assert remaining["SST"]["max_possible"] > 0

    def test_points_decrease_after_events(self, tracker):
        """Remaining points decrease as events complete."""
        tracker.teams.add("SST")
        initial = tracker.get_remaining_points()
        initial_max = initial["SST"]["max_possible"]

        # Complete an event
        tracker.record_event_results(
            "Boys 50 Free",
            [
                {"place": 1, "swimmer": "Test", "team": "SST", "time": 22.0},
            ],
        )

        after = tracker.get_remaining_points()
        after_max = after["SST"]["max_possible"]

        # Should have fewer remaining points
        assert after_max < initial_max


# ============================================================================
# Test: Clinch Scenarios
# ============================================================================


class TestGetClinchScenarios:
    """Tests for clinch scenario analysis."""

    def test_clinch_scenarios_structure(self, tracker):
        """Verify clinch scenarios return proper structure."""
        tracker.teams.update({"SST", "Trinity", "Paul VI"})

        # Record some results to establish standings
        tracker.record_result("Boys 50 Free", 1, "John Smith", "SST", 22.15)
        tracker.record_result("Boys 50 Free", 2, "Bob Wilson", "Trinity", 22.45)
        tracker.record_result("Boys 50 Free", 3, "Jim Brown", "Paul VI", 22.67)

        scenarios = tracker.get_clinch_scenarios("SST")

        assert isinstance(scenarios, list)
        for scenario in scenarios:
            assert isinstance(scenario, ClinchScenario)
            assert hasattr(scenario, "target_position")
            assert hasattr(scenario, "can_clinch")


# ============================================================================
# Test: Swing Events
# ============================================================================


class TestGetSwingRemaining:
    """Tests for swing event identification."""

    def test_swing_events_structure(self, tracker, sample_entries):
        """Verify swing events return proper structure."""
        tracker.set_psych_sheet(sample_entries, target_team="SST")

        swing = tracker.get_swing_remaining("SST")

        assert isinstance(swing, list)
        if swing:
            assert "event" in swing[0]
            assert "potential_gain" in swing[0]

    def test_swing_sorted_by_potential(self, tracker, sample_entries):
        """Swing events should be sorted by potential gain."""
        tracker.set_psych_sheet(sample_entries, target_team="SST")

        swing = tracker.get_swing_remaining("SST")

        if len(swing) >= 2:
            for i in range(len(swing) - 1):
                assert swing[i]["potential_gain"] >= swing[i + 1]["potential_gain"]


# ============================================================================
# Test: Event Status
# ============================================================================


class TestEventStatus:
    """Tests for event status tracking."""

    def test_all_upcoming_initially(self, tracker):
        """All events start as upcoming."""
        status = tracker.get_event_status()

        for event in tracker.EVENT_ORDER:
            assert status[event] == "upcoming"

    def test_event_becomes_in_progress(self, tracker):
        """Event becomes in_progress after first result."""
        tracker.record_result("Boys 50 Free", 1, "John Smith", "SST", 22.15)

        status = tracker.get_event_status()

        assert status["Boys 50 Free"] == "in_progress"

    def test_event_becomes_completed(self, tracker):
        """Event becomes completed when all scoring places recorded."""
        # Record many results to mark complete
        for i in range(12):
            tracker.record_result(
                "Boys 50 Free",
                i + 1,
                f"Swimmer {i}",
                "SST" if i % 2 == 0 else "Trinity",
                22.0 + i * 0.5,
            )

        status = tracker.get_event_status()

        assert status["Boys 50 Free"] == "completed"


# ============================================================================
# Test: Coach Summary
# ============================================================================


class TestGenerateCoachSummary:
    """Tests for coach summary generation."""

    def test_summary_is_string(self, tracker):
        """Summary should be a string."""
        tracker.teams.add("SST")

        summary = tracker.generate_coach_summary("SST")

        assert isinstance(summary, str)
        assert len(summary) > 0

    def test_summary_includes_standings(self, tracker):
        """Summary should include current standings."""
        tracker.teams.update({"SST", "Trinity"})
        tracker.record_result("Boys 50 Free", 1, "John Smith", "SST", 22.15)

        summary = tracker.generate_coach_summary("SST")

        assert "SST" in summary
        assert "Standings" in summary or "standings" in summary.lower()


# ============================================================================
# Test: Factory Function
# ============================================================================


def test_create_live_tracker():
    """Factory function creates valid tracker."""
    tracker = create_live_tracker()

    assert isinstance(tracker, LiveMeetTracker)
    assert tracker.meet_profile == "vcac_championship"


def test_create_live_tracker_custom_profile():
    """Factory with custom profile."""
    tracker = create_live_tracker(meet_profile="visaa_state")

    assert tracker.meet_profile == "visaa_state"
