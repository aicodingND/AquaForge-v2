"""
Tests for Dual Meet Scoring with Entry Schema Normalization

Verifies that the dual meet scoring correctly handles various input formats
using the centralized entry schema normalization.
"""

import pandas as pd
import pytest

from swim_ai_reflex.backend.services.dual_meet.scoring import (
    DualMeetScoringService,
)


class TestDualMeetScoringService:
    """Test the dual meet scoring service with various input formats."""

    @pytest.fixture
    def service(self):
        """Create a scoring service instance."""
        return DualMeetScoringService()

    def test_score_event_basic(self, service):
        """Test basic event scoring."""
        our_entries = [
            {"swimmer": "John Smith", "time": 50.0},
            {"swimmer": "Tom Brown", "time": 52.0},
        ]
        opponent_entries = [
            {"swimmer": "Mike Jones", "time": 51.0},
            {"swimmer": "Dave Wilson", "time": 53.0},
        ]

        result = service.score_event(
            our_entries=our_entries,
            opponent_entries=opponent_entries,
            event_name="100 Free",
        )

        # Our team: 1st (8) + 3rd (5) = 13
        # Opponent: 2nd (6) + 4th (4) = 10
        assert result.our_points == 13
        assert result.opponent_points == 10
        assert result.total_points == 23  # 4 swimmers scored

    def test_score_event_with_exhibition(self, service):
        """Test that exhibition swimmers don't score."""
        our_entries = [
            {"swimmer": "John Smith", "time": 50.0},
            {"swimmer": "Young Kid", "time": 51.0, "grade": 7},  # Exhibition
        ]
        opponent_entries = [
            {"swimmer": "Mike Jones", "time": 52.0},
        ]

        result = service.score_event(
            our_entries=our_entries,
            opponent_entries=opponent_entries,
            event_name="100 Free",
        )

        # Young Kid places 2nd but doesn't score (grade 7 < 9)
        # Mike Jones gets 2nd place points instead of 3rd
        assert result.our_points == 8  # Only John scores (1st place)
        assert result.opponent_points == 6  # Mike gets bumped up to 2nd

    def test_score_meet_basic(self, service):
        """Test scoring a complete meet."""
        our_roster = pd.DataFrame(
            [
                {"swimmer": "John Smith", "event": "100 Free", "time": 50.0},
                {"swimmer": "Tom Brown", "event": "100 Free", "time": 52.0},
                {"swimmer": "Sam Lee", "event": "50 Free", "time": 23.0},
                {"swimmer": "Bob Garcia", "event": "50 Free", "time": 24.0},
            ]
        )

        opponent_roster = pd.DataFrame(
            [
                {"swimmer": "Mike Jones", "event": "100 Free", "time": 51.0},
                {"swimmer": "Dave Wilson", "event": "100 Free", "time": 53.0},
                {"swimmer": "Pat Miller", "event": "50 Free", "time": 22.5},
                {"swimmer": "Jim Davis", "event": "50 Free", "time": 25.0},
            ]
        )

        result = service.score_meet(
            our_roster=our_roster,
            opponent_roster=opponent_roster,
        )

        # Both events scored with 4 swimmers each
        assert result.our_score > 0
        assert result.opponent_score > 0
        assert len(result.event_results) == 2  # 100 Free and 50 Free


class TestDualMeetInputNormalization:
    """Test that various input formats are correctly normalized."""

    @pytest.fixture
    def service(self):
        return DualMeetScoringService()

    def test_time_format_mm_ss(self, service):
        """Test MM:SS.ss time format."""
        our_entries = [
            {"swimmer": "John Smith", "time": "1:02.34"},  # String format
        ]
        opponent_entries = [
            {"swimmer": "Mike Jones", "time": 60.0},  # Float format
        ]

        result = service.score_event(
            our_entries=our_entries,
            opponent_entries=opponent_entries,
            event_name="100 Free",
        )

        # Mike Jones is faster, should be 1st
        assert result.opponent_points == 8  # 1st place
        assert result.our_points == 6  # 2nd place

    def test_nt_time_sorts_last(self, service):
        """Test that NT (no time) swimmers sort to the end."""
        our_entries = [
            {"swimmer": "John Smith", "time": 50.0},
            {"swimmer": "No Time Kid", "time": "NT"},
        ]
        opponent_entries = [
            {"swimmer": "Mike Jones", "time": 51.0},
        ]

        result = service.score_event(
            our_entries=our_entries,
            opponent_entries=opponent_entries,
            event_name="100 Free",
        )

        # John 1st, Mike 2nd, No Time 3rd
        assert result.entries[0].swimmer == "John Smith"
        assert result.entries[2].swimmer == "No Time Kid"
        assert result.entries[2].place == 3

    def test_relay_scoring(self, service):
        """Test relay event scoring uses relay points table."""
        our_entries = [
            {"swimmer": "Relay A", "time": 180.0},
        ]
        opponent_entries = [
            {"swimmer": "Relay B", "time": 185.0},
        ]

        result = service.score_event(
            our_entries=our_entries,
            opponent_entries=opponent_entries,
            event_name="400 Free Relay",
        )

        # Relay uses [10, 5, 3] points
        assert result.our_points == 10  # 1st place relay
        assert result.opponent_points == 5  # 2nd place relay


class TestDualMeetEventNormalization:
    """Test that event names are normalized correctly."""

    @pytest.fixture
    def service(self):
        return DualMeetScoringService()

    def test_event_name_variations(self, service):
        """Test various event name formats are normalized."""
        our_roster = pd.DataFrame(
            [
                {"swimmer": "John Smith", "event": "100 freestyle", "time": 50.0},
                {"swimmer": "Tom Brown", "event": "100 FR", "time": 52.0},
                {"swimmer": "Sam Lee", "event": "100 free", "time": 54.0},
            ]
        )

        opponent_roster = pd.DataFrame(
            [
                {"swimmer": "Mike Jones", "event": "100 Free", "time": 51.0},
            ]
        )

        result = service.score_meet(
            our_roster=our_roster,
            opponent_roster=opponent_roster,
        )

        # All should be normalized to the same event
        # Should be just 1 event after normalization
        assert len(result.event_results) == 1


class TestDualMeetTeamIsIssues:
    """Test edge cases identified from real-world issues."""

    @pytest.fixture
    def service(self):
        return DualMeetScoringService()

    def test_all_points_distributed(self, service):
        """Verify all 29 points are distributed in a 7-swimmer event."""
        our_entries = [{"swimmer": f"Our{i}", "time": 50.0 + i} for i in range(4)]
        opponent_entries = [{"swimmer": f"Opp{i}", "time": 51.0 + i} for i in range(3)]

        result = service.score_event(
            our_entries=our_entries,
            opponent_entries=opponent_entries,
            event_name="100 Free",
        )

        # Points: 8 + 6 + 5 + 4 + 3 + 2 + 1 = 29
        assert result.total_points == 29

    def test_score_lineup_method(self, service):
        """Test scoring from combined lineup DataFrame."""
        combined = pd.DataFrame(
            [
                {
                    "swimmer": "John Smith",
                    "event": "100 Free",
                    "time": 50.0,
                    "team": "Seton",
                },
                {
                    "swimmer": "Mike Jones",
                    "event": "100 Free",
                    "time": 51.0,
                    "team": "Opponent",
                },
                {
                    "swimmer": "Tom Brown",
                    "event": "100 Free",
                    "time": 52.0,
                    "team": "Seton",
                },
            ]
        )

        result = service.score_lineup(combined, our_team="Seton")

        assert result.our_team == "Seton"
        assert result.opponent_team == "Opponent"
        # Seton: 1st (8) + 3rd (5) = 13
        # Opponent: 2nd (6) = 6
        assert result.our_score == 13
        assert result.opponent_score == 6


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
