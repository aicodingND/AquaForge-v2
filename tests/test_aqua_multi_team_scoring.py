"""
Tests for AquaOptimizer multi-team championship scoring.

Verifies that per-team scorer caps are correctly enforced when multiple
opponent teams compete, rather than pooling all opponents into one team.

Bug reference: MISTAKES.md 2026-02-16 — "AquaOptimizer's score_event() has
the same bug (single team counter for all opponents) — still needs fixing"
"""

import pytest

from swim_ai_reflex.backend.core.strategies.aqua_optimizer import (
    FatigueModel,
    ScoringEngine,
    ScoringProfile,
)


@pytest.fixture
def championship_engine():
    """ScoringEngine with VISAA championship profile (max 4 scorers per team)."""
    profile = ScoringProfile.visaa_championship()
    fatigue = FatigueModel(enabled=False)
    return ScoringEngine(profile, fatigue)


@pytest.fixture
def simple_profile():
    """Minimal profile for testing: 4-place scoring, max 2 per team."""
    profile = ScoringProfile(
        name="test_multi_team",
        individual_points=[10, 7, 5, 3],
        relay_points=[20, 14, 10, 6],
        max_scorers_per_team=2,
        max_entries_per_event=4,
    )
    fatigue = FatigueModel(enabled=False)
    return ScoringEngine(profile, fatigue)


class TestMultiTeamScorerCaps:
    """Verify per-team scorer caps in score_event()."""

    def test_single_opponent_team_caps_at_max(self, simple_profile):
        """When all opponents are one team, cap applies to that team."""
        seton_entries = [
            {"swimmer": "S1", "time": 25.0, "grade": 12},
        ]
        # 3 opponents from same team — only 2 should score (max_scorers=2)
        opponent_entries = [
            {"swimmer": "O1", "time": 22.0, "grade": 12, "team": "ALPHA"},
            {"swimmer": "O2", "time": 23.0, "grade": 12, "team": "ALPHA"},
            {"swimmer": "O3", "time": 24.0, "grade": 12, "team": "ALPHA"},
        ]
        s_pts, o_pts, details = simple_profile.score_event(
            seton_entries, opponent_entries
        )
        # O1 gets 1st (10 pts), O2 gets 2nd (7 pts), O3 is capped out
        # S1 gets 3rd place (5 pts) — O3's cap frees up a scoring slot
        assert s_pts == 5.0, f"Expected S1 to get 3rd place (5 pts), got {s_pts}"
        assert o_pts == 17.0, f"Expected 10+7=17 opponent pts, got {o_pts}"

    def test_multi_team_each_capped_independently(self, simple_profile):
        """Different teams each get their own cap."""
        seton_entries = [
            {"swimmer": "S1", "time": 30.0, "grade": 12},
        ]
        # 2 from ALPHA + 2 from BETA = 4 opponents, all within their team caps
        opponent_entries = [
            {"swimmer": "A1", "time": 22.0, "grade": 12, "team": "ALPHA"},
            {"swimmer": "A2", "time": 23.0, "grade": 12, "team": "ALPHA"},
            {"swimmer": "B1", "time": 24.0, "grade": 12, "team": "BETA"},
            {"swimmer": "B2", "time": 25.0, "grade": 12, "team": "BETA"},
        ]
        s_pts, o_pts, details = simple_profile.score_event(
            seton_entries, opponent_entries
        )
        # A1=1st(10), A2=2nd(7), B1=3rd(5), B2=4th(3) — all within caps
        # S1 doesn't score (only 4 scoring places, all taken)
        assert s_pts == 0.0
        assert o_pts == 25.0

    def test_multi_team_caps_open_slots_for_seton(self, simple_profile):
        """When opponent teams overflow their caps, Seton gets higher placements."""
        seton_entries = [
            {"swimmer": "S1", "time": 26.0, "grade": 12},
        ]
        # 3 from ALPHA (cap=2, so 3rd is capped) + 1 from BETA
        opponent_entries = [
            {"swimmer": "A1", "time": 22.0, "grade": 12, "team": "ALPHA"},
            {"swimmer": "A2", "time": 23.0, "grade": 12, "team": "ALPHA"},
            {"swimmer": "A3", "time": 24.0, "grade": 12, "team": "ALPHA"},  # CAPPED
            {"swimmer": "B1", "time": 25.0, "grade": 12, "team": "BETA"},
        ]
        s_pts, o_pts, details = simple_profile.score_event(
            seton_entries, opponent_entries
        )
        # A1=1st(10), A2=2nd(7), A3=CAPPED, B1=3rd(5), S1=4th(3)
        assert s_pts == 3.0, f"S1 should get 4th (3 pts), got {s_pts}"
        assert o_pts == 22.0, f"Expected 10+7+5=22 opponent pts, got {o_pts}"

    def test_seton_also_capped(self, simple_profile):
        """Seton team also respects the max_scorers_per_team cap."""
        seton_entries = [
            {"swimmer": "S1", "time": 22.0, "grade": 12},
            {"swimmer": "S2", "time": 23.0, "grade": 12},
            {"swimmer": "S3", "time": 24.0, "grade": 12},  # Should be capped
        ]
        opponent_entries = [
            {"swimmer": "O1", "time": 25.0, "grade": 12, "team": "ALPHA"},
        ]
        s_pts, o_pts, details = simple_profile.score_event(
            seton_entries, opponent_entries
        )
        # S1=1st(10), S2=2nd(7), S3=CAPPED, O1=3rd(5)
        assert s_pts == 17.0, f"Expected 10+7=17 seton pts (S3 capped), got {s_pts}"
        assert o_pts == 5.0

    def test_no_team_field_defaults_to_opponent(self, simple_profile):
        """Opponents without a 'team' field get 'opponent' as default."""
        seton_entries = [
            {"swimmer": "S1", "time": 26.0, "grade": 12},
        ]
        # 3 opponents with no team field — all pooled as "opponent", cap=2
        opponent_entries = [
            {"swimmer": "O1", "time": 22.0, "grade": 12},
            {"swimmer": "O2", "time": 23.0, "grade": 12},
            {"swimmer": "O3", "time": 24.0, "grade": 12},
        ]
        s_pts, o_pts, details = simple_profile.score_event(
            seton_entries, opponent_entries
        )
        # O1=1st(10), O2=2nd(7), O3=CAPPED (pooled as "opponent"), S1=3rd(5)
        assert s_pts == 5.0, f"S1 should get 3rd (5 pts), got {s_pts}"


class TestScoringEligibleOpponentTimes:
    """Test the per-team filtering helper for score_event_fast."""

    def test_filters_by_team_cap(self):
        """Only max_scorers entries per team pass through."""
        entries = [
            {"time": 22.0, "team": "ALPHA"},
            {"time": 23.0, "team": "ALPHA"},
            {"time": 24.0, "team": "ALPHA"},
            {"time": 25.0, "team": "BETA"},
            {"time": 26.0, "team": "BETA"},
        ]
        result = ScoringEngine.get_scoring_eligible_opponent_times(
            entries, max_scorers_per_team=2
        )
        # ALPHA: 22, 23 (24 capped). BETA: 25, 26.
        assert result == [22.0, 23.0, 25.0, 26.0]

    def test_preserves_sort_order(self):
        """Output times are sorted regardless of input order."""
        entries = [
            {"time": 30.0, "team": "BETA"},
            {"time": 20.0, "team": "ALPHA"},
            {"time": 25.0, "team": "ALPHA"},
        ]
        result = ScoringEngine.get_scoring_eligible_opponent_times(
            entries, max_scorers_per_team=2
        )
        assert result == [20.0, 25.0, 30.0]

    def test_no_team_field_pools_as_opponent(self):
        """Entries without team field get pooled under 'opponent'."""
        entries = [
            {"time": 22.0},
            {"time": 23.0},
            {"time": 24.0},
        ]
        result = ScoringEngine.get_scoring_eligible_opponent_times(
            entries, max_scorers_per_team=2
        )
        # All pooled as "opponent" — only first 2 pass
        assert result == [22.0, 23.0]

    def test_skips_zero_and_negative_times(self):
        """Invalid times are excluded."""
        entries = [
            {"time": 0, "team": "ALPHA"},
            {"time": -1.0, "team": "ALPHA"},
            {"time": 22.0, "team": "ALPHA"},
        ]
        result = ScoringEngine.get_scoring_eligible_opponent_times(
            entries, max_scorers_per_team=4
        )
        assert result == [22.0]


class TestChampionshipMultiTeamScoring:
    """Integration test with VISAA championship profile."""

    def test_visaa_four_teams_sixteen_scorers(self, championship_engine):
        """VISAA: 4 teams × 4 scorers each = 16 scoring slots (all 16 places filled)."""
        seton_entries = [
            {"swimmer": "S1", "time": 50.0, "grade": 12},
        ]
        # 4 teams × 4 swimmers each = 16 opponents
        opponent_entries = []
        for team_idx, team in enumerate(["TEAM_A", "TEAM_B", "TEAM_C", "TEAM_D"]):
            for i in range(4):
                opponent_entries.append(
                    {
                        "swimmer": f"{team}_{i}",
                        "time": 45.0 + team_idx * 0.5 + i * 0.1,
                        "grade": 12,
                        "team": team,
                    }
                )

        s_pts, o_pts, details = championship_engine.score_event(
            seton_entries, opponent_entries
        )
        # All 16 opponent scoring slots are filled; S1 at time 50.0 is 17th — no points
        assert s_pts == 0.0, f"S1 should score 0 (17th place), got {s_pts}"

    def test_visaa_overflowed_teams_open_slots(self, championship_engine):
        """When teams have >4 entries, caps open scoring slots for later swimmers."""
        seton_entries = [
            {"swimmer": "S1", "time": 50.0, "grade": 12},
        ]
        # 1 team with 8 swimmers, but cap is 4 — only 4 score
        opponent_entries = [
            {
                "swimmer": f"BIG_TEAM_{i}",
                "time": 45.0 + i * 0.5,
                "grade": 12,
                "team": "BIG",
            }
            for i in range(8)
        ]
        s_pts, o_pts, details = championship_engine.score_event(
            seton_entries, opponent_entries
        )
        # BIG: 4 score (capped at 4), 4 don't. S1 gets 5th place.
        # VISAA 5th place individual = 14 points
        assert s_pts == 14.0, f"S1 should get 5th place (14 pts), got {s_pts}"
