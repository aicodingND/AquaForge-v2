"""
Verification Tests for Championship Scoring Data Flow

These tests verify the PRISM analysis findings about championship scoring:
1. Points table accuracy
2. Max scorers enforcement
3. Score discrepancy between optimizer and projection
4. Team normalization consistency
"""

import pytest

from swim_ai_reflex.backend.core.rules import get_meet_profile


def get_projection_service(meet_profile: str = "vcac_championship"):
    """Lazy import to avoid circular import issues."""
    from swim_ai_reflex.backend.services.championship.projection import (
        PointProjectionService,
    )

    return PointProjectionService(meet_profile=meet_profile)


class TestPointsTableAccuracy:
    """Verify scoring tables are correctly configured."""

    def test_vcac_individual_points(self):
        """VCAC individual points: 16-13-12-11-10-9-7-5-4-3-2-1 (12-place scoring)"""
        rules = get_meet_profile("vcac_championship")
        expected = [16, 13, 12, 11, 10, 9, 7, 5, 4, 3, 2, 1]
        assert rules.individual_points == expected, (
            f"VCAC individual points mismatch: {rules.individual_points}"
        )

    def test_vcac_relay_points(self):
        """VCAC relay points: 32-26-24-22-20-18-14-10-8-6-4-2 (2x individual)"""
        rules = get_meet_profile("vcac_championship")
        expected = [32, 26, 24, 22, 20, 18, 14, 10, 8, 6, 4, 2]
        assert rules.relay_points == expected, (
            f"VCAC relay points mismatch: {rules.relay_points}"
        )

    def test_vcac_max_scorers(self):
        """VCAC max 4 scorers per team per individual event."""
        rules = get_meet_profile("vcac_championship")
        assert rules.max_scorers_per_team_individual == 4

    def test_visaa_state_individual_points(self):
        """VISAA State: 20-17-16-15-14-13-12-11-9-7-6-5-4-3-2-1 (16-place scoring)"""
        rules = get_meet_profile("visaa_state")
        expected = [20, 17, 16, 15, 14, 13, 12, 11, 9, 7, 6, 5, 4, 3, 2, 1]
        assert rules.individual_points == expected


class TestMaxScorersEnforcement:
    """Verify that only top N scorers per team count."""

    def test_projection_enforces_max_scorers(self):
        """Only top 4 SST swimmers should score in an event."""
        service = get_projection_service("vcac_championship")

        # Create 6 SST swimmers in same event
        entries = [
            {
                "swimmer": f"Swimmer{i}",
                "team": "SST",
                "event": "Boys 100 Free",
                "time": 50.0 + i,
            }
            for i in range(6)
        ]

        result = service.project_event("Boys 100 Free", entries)

        # Count how many SST swimmers are scoring
        # Note: Team names are normalized, so 'SST' becomes 'Seton'
        scoring_count = sum(
            1 for e in result.entries if e.is_scoring and e.team == "Seton"
        )

        assert scoring_count == 4, (
            f"Expected 4 scorers, got {scoring_count}. Max scorers rule not enforced."
        )

    def test_projection_points_for_max_scorers(self):
        """Verify correct points allocated to top 4."""
        service = get_projection_service("vcac_championship")

        # Create 6 SST swimmers
        entries = [
            {
                "swimmer": f"Swimmer{i}",
                "team": "SST",
                "event": "Boys 100 Free",
                "time": 50.0 + i,
            }
            for i in range(6)
        ]

        result = service.project_event("Boys 100 Free", entries)

        # Expected points: 1st=16, 2nd=13, 3rd=12, 4th=11, 5th=0, 6th=0 (VCAC individual)
        expected_points = [16, 13, 12, 11, 0, 0]
        actual_points = [e.points for e in result.entries]

        assert actual_points == expected_points, (
            f"Points mismatch: expected {expected_points}, got {actual_points}"
        )

    def test_multi_team_max_scorers(self):
        """Each team limited to 4 scorers independently."""
        service = get_projection_service("vcac_championship")

        # Mix of SST and OUT swimmers (use realistic names that survive normalization)
        entries = [
            {
                "swimmer": "John Smith",
                "team": "SST",
                "event": "Boys 100 Free",
                "time": 50.0,
            },  # 1st
            {
                "swimmer": "Mike Jones",
                "team": "OUT",
                "event": "Boys 100 Free",
                "time": 50.5,
            },  # 2nd
            {
                "swimmer": "Tom Brown",
                "team": "SST",
                "event": "Boys 100 Free",
                "time": 51.0,
            },  # 3rd
            {
                "swimmer": "Dave Wilson",
                "team": "OUT",
                "event": "Boys 100 Free",
                "time": 51.5,
            },  # 4th
            {
                "swimmer": "Sam Lee",
                "team": "SST",
                "event": "Boys 100 Free",
                "time": 52.0,
            },  # 5th
            {
                "swimmer": "Bob Garcia",
                "team": "SST",
                "event": "Boys 100 Free",
                "time": 52.5,
            },  # 6th
            {
                "swimmer": "Chris Davis",
                "team": "SST",
                "event": "Boys 100 Free",
                "time": 53.0,
            },  # 7th - 5th SST
            {
                "swimmer": "Pat Miller",
                "team": "OUT",
                "event": "Boys 100 Free",
                "time": 53.5,
            },  # 8th
        ]

        result = service.project_event("Boys 100 Free", entries)

        # SST should have 4 scorers (normalized to 'Seton')
        sst_scoring = sum(
            1 for e in result.entries if e.is_scoring and e.team == "Seton"
        )
        assert sst_scoring == 4, f"Seton should have 4 scorers, got {sst_scoring}"

        # Chris Davis (7th place) should NOT score - 5th SST swimmer
        chris_entry = next(
            (e for e in result.entries if "Chris Davis" in e.swimmer), None
        )
        assert chris_entry is not None, "Chris Davis not found in entries"
        assert chris_entry.is_scoring is False, (
            "Chris Davis should not be scoring (5th SST swimmer)"
        )


class TestTeamTotalsCalculation:
    """Verify team totals are calculated correctly."""

    def test_single_event_team_total(self):
        """Team total should sum all scoring swimmers' points."""
        service = get_projection_service("vcac_championship")

        entries = [
            {
                "swimmer": "SST1",
                "team": "SST",
                "event": "Boys 100 Free",
                "time": 50.0,
            },  # 16 pts (1st place individual)
            {
                "swimmer": "SST2",
                "team": "SST",
                "event": "Boys 100 Free",
                "time": 51.0,
            },  # 13 pts (2nd place individual)
            {
                "swimmer": "OUT1",
                "team": "OUT",
                "event": "Boys 100 Free",
                "time": 52.0,
            },  # 12 pts (3rd place individual)
        ]

        result = service.project_event("Boys 100 Free", entries)

        # SST normalized to 'Seton' - should have 16 + 13 = 29 (1st + 2nd)
        sst_points = result.team_points.get("Seton", 0)
        assert sst_points == 29.0, (
            f"Seton points should be 29 (16+13), got {sst_points}"
        )

    def test_full_meet_projection(self):
        """Full meet projection sums across all events."""
        service = get_projection_service("vcac_championship")

        entries = [
            # Event 1: Boys 100 Free
            {
                "swimmer": "SST1",
                "team": "SST",
                "event": "Boys 100 Free",
                "time": 50.0,
            },  # 16 pts (1st place)
            {
                "swimmer": "OUT1",
                "team": "OUT",
                "event": "Boys 100 Free",
                "time": 51.0,
            },  # 13 pts (2nd place)
            # Event 2: Boys 200 Free
            {
                "swimmer": "SST1",
                "team": "SST",
                "event": "Boys 200 Free",
                "time": 110.0,
            },  # 16 pts (1st place)
            {
                "swimmer": "OUT1",
                "team": "OUT",
                "event": "Boys 200 Free",
                "time": 111.0,
            },  # 13 pts (2nd place)
        ]

        result = service.project_standings(entries, "SST", "Test Meet")

        # SST should have 16 + 16 = 32 (1st in both events)
        assert result.target_team_total == 32.0, (
            f"SST total should be 32, got {result.target_team_total}"
        )


class TestOptimizerVsProjectionConsistency:
    """Verify scoring logic is consistent between optimizer and projection."""

    def test_rank_based_points_match(self):
        """Both systems should give same points for same ranking."""
        from swim_ai_reflex.backend.core.strategies.championship_strategy import (
            ChampionshipGurobiStrategy,
        )

        service = get_projection_service("vcac_championship")
        strategy = ChampionshipGurobiStrategy(meet_profile="vcac_championship")

        # Both should use same points table
        assert service.rules.individual_points == strategy.points_table, (
            "Projection and optimizer should use same points table"
        )

    def test_max_scorers_same_limit(self):
        """Both systems should use same max scorers limit."""
        from swim_ai_reflex.backend.core.strategies.championship_strategy import (
            ChampionshipGurobiStrategy,
        )

        service = get_projection_service("vcac_championship")
        strategy = ChampionshipGurobiStrategy(meet_profile="vcac_championship")

        assert service.rules.max_scorers_per_team_individual == strategy.max_scorers, (
            f"Max scorers mismatch: projection={service.rules.max_scorers_per_team_individual}, "
            f"optimizer={strategy.max_scorers}"
        )


class TestSwingEventsCalculation:
    """Verify swing events are correctly identified."""

    def test_swing_event_point_gain(self):
        """Swing event should show correct point gain for moving up one place."""
        service = get_projection_service("vcac_championship")

        entries = [
            {
                "swimmer": "OUT1",
                "team": "OUT",
                "event": "Boys 100 Free",
                "time": 50.0,
            },  # 1st: 32
            {
                "swimmer": "SST1",
                "team": "SST",
                "event": "Boys 100 Free",
                "time": 50.5,
            },  # 2nd: 26
        ]

        result = service.project_standings(entries, "SST", "Test")

        # SST1 is 2nd. If they move to 1st, gain = 32 - 26 = 6 points
        swing = next((s for s in result.swing_events if s.swimmer == "SST1"), None)

        if swing:
            assert swing.point_gain == 6.0, (
                f"Point gain should be 6 (32-26), got {swing.point_gain}"
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
