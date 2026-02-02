"""
Tests for Strategic Exhibition Deployment.

Verifies:
- Exhibition swimmer identification (grade ≤7)
- Displacement opportunity calculation
- Points denied calculation
- Assignment respects event limits
"""

import pandas as pd
import pytest

from swim_ai_reflex.backend.core.exhibition_strategy import (
    ExhibitionDeploymentAnalyzer,
    analyze_exhibition_strategy,
)


class TestExhibitionSwimmerIdentification:
    """Tests for identifying exhibition swimmers."""

    def test_grade_7_is_exhibition(self):
        """Grade 7 swimmers should be exhibition."""
        roster = pd.DataFrame(
            [
                {
                    "swimmer": "7th_Grader",
                    "grade": 7,
                    "event": "100 Free",
                    "time": 55.0,
                },
                {
                    "swimmer": "9th_Grader",
                    "grade": 9,
                    "event": "100 Free",
                    "time": 56.0,
                },
            ]
        )

        analyzer = ExhibitionDeploymentAnalyzer()
        exhibition = analyzer.get_exhibition_swimmers(roster)

        assert len(exhibition) == 1
        assert exhibition.iloc[0]["swimmer"] == "7th_Grader"

    def test_grade_6_is_exhibition(self):
        """Grade 6 swimmers should be exhibition."""
        roster = pd.DataFrame(
            [
                {
                    "swimmer": "6th_Grader",
                    "grade": 6,
                    "event": "100 Free",
                    "time": 58.0,
                },
            ]
        )

        analyzer = ExhibitionDeploymentAnalyzer()
        exhibition = analyzer.get_exhibition_swimmers(roster)

        assert len(exhibition) == 1

    def test_grade_8_is_not_exhibition(self):
        """Grade 8+ swimmers are varsity, not exhibition."""
        roster = pd.DataFrame(
            [
                {
                    "swimmer": "8th_Grader",
                    "grade": 8,
                    "event": "100 Free",
                    "time": 54.0,
                },
                {
                    "swimmer": "12th_Grader",
                    "grade": 12,
                    "event": "100 Free",
                    "time": 53.0,
                },
            ]
        )

        analyzer = ExhibitionDeploymentAnalyzer()
        exhibition = analyzer.get_exhibition_swimmers(roster)

        assert len(exhibition) == 0


class TestDisplacementOpportunities:
    """Tests for finding displacement opportunities."""

    def test_fast_exhibition_displaces_opponent(self):
        """Fast exhibition swimmer should identify displacement opportunity."""
        seton = pd.DataFrame(
            [
                {"swimmer": "Fast_7th", "grade": 7, "event": "100 Free", "time": 55.0},
            ]
        )
        opponent = pd.DataFrame(
            [
                {"swimmer": "Opp_1", "grade": 10, "event": "100 Free", "time": 56.0},
                {"swimmer": "Opp_2", "grade": 10, "event": "100 Free", "time": 57.0},
            ]
        )

        result = analyze_exhibition_strategy(seton, opponent)

        assert len(result.opportunities) >= 1
        opp = result.opportunities[0]
        assert opp.swimmer == "Fast_7th"
        assert opp.opponent_displaced == "Opp_1"
        assert opp.points_denied > 0

    def test_slow_exhibition_no_opportunity(self):
        """Slow exhibition swimmer should have no displacement opportunities."""
        seton = pd.DataFrame(
            [
                {"swimmer": "Slow_7th", "grade": 7, "event": "100 Free", "time": 70.0},
            ]
        )
        opponent = pd.DataFrame(
            [
                {"swimmer": "Opp_1", "grade": 10, "event": "100 Free", "time": 55.0},
            ]
        )

        result = analyze_exhibition_strategy(seton, opponent)

        assert len(result.opportunities) == 0

    def test_points_denied_calculation(self):
        """Points denied should equal difference in place points."""
        seton = pd.DataFrame(
            [
                # Fast 7th grader beats opponent's 2nd place swimmer
                {"swimmer": "Fast_7th", "grade": 7, "event": "100 Free", "time": 54.0},
            ]
        )
        opponent = pd.DataFrame(
            [
                {
                    "swimmer": "Opp_1",
                    "grade": 10,
                    "event": "100 Free",
                    "time": 52.0,
                },  # 1st
                {
                    "swimmer": "Opp_2",
                    "grade": 10,
                    "event": "100 Free",
                    "time": 55.0,
                },  # Was 2nd, now 3rd
            ]
        )

        result = analyze_exhibition_strategy(seton, opponent)

        # Opp_2 moves from 2nd (6 pts) to 3rd (5 pts) = 1 pt denied
        assert len(result.opportunities) >= 1
        # Find the opportunity for Opp_2
        opp = [o for o in result.opportunities if o.opponent_displaced == "Opp_2"]
        assert len(opp) == 1
        assert opp[0].points_denied == 1  # 6 - 5 = 1


class TestExhibitionAssignment:
    """Tests for assigning exhibition swimmers to events."""

    def test_respects_max_events_per_swimmer(self):
        """Should not assign swimmer to more than max events."""
        seton = pd.DataFrame(
            [
                {"swimmer": "Fast_7th", "grade": 7, "event": "100 Free", "time": 55.0},
                {"swimmer": "Fast_7th", "grade": 7, "event": "50 Free", "time": 25.0},
                {"swimmer": "Fast_7th", "grade": 7, "event": "100 Back", "time": 60.0},
            ]
        )
        opponent = pd.DataFrame(
            [
                {"swimmer": "Opp_1", "grade": 10, "event": "100 Free", "time": 56.0},
                {"swimmer": "Opp_2", "grade": 10, "event": "50 Free", "time": 26.0},
                {"swimmer": "Opp_3", "grade": 10, "event": "100 Back", "time": 61.0},
            ]
        )

        analyzer = ExhibitionDeploymentAnalyzer()
        result = analyzer.analyze_deployment(seton, opponent, max_events_per_swimmer=2)

        # Fast_7th should only be assigned to 2 events max
        if "Fast_7th" in result.recommended_assignments:
            assert len(result.recommended_assignments["Fast_7th"]) <= 2


class TestNoExhibitionSwimmers:
    """Tests when no exhibition swimmers are available."""

    def test_empty_result_when_no_exhibition(self):
        """Should return empty result when no exhibition swimmers."""
        seton = pd.DataFrame(
            [
                {"swimmer": "Varsity", "grade": 10, "event": "100 Free", "time": 55.0},
            ]
        )
        opponent = pd.DataFrame(
            [
                {"swimmer": "Opp_1", "grade": 10, "event": "100 Free", "time": 56.0},
            ]
        )

        result = analyze_exhibition_strategy(seton, opponent)

        assert len(result.opportunities) == 0
        assert result.total_points_denied == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
