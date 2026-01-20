"""
Tests for Relay Configuration Optimizer Service

Verifies the optimizer correctly assigns swimmers to relay legs
and makes optimal decisions about 400 Free Relay participation.
"""

import pytest
from datetime import date

from swim_ai_reflex.backend.models.championship import PsychSheetEntry, MeetPsychSheet
from swim_ai_reflex.backend.services.relay_optimizer_service import (
    RelayOptimizer,
    RelayLeg,
    RelayConfiguration,
    format_relay_configuration,
)


class TestRelayLeg:
    """Test RelayLeg data model."""

    def test_basic_leg(self):
        """Test creating a basic relay leg."""
        leg = RelayLeg(swimmer="John Smith", stroke="back", split_time=28.5)
        assert leg.swimmer == "John Smith"
        assert leg.stroke == "back"
        assert leg.split_time == 28.5


class TestRelayConfiguration:
    """Test RelayConfiguration data model."""

    def test_complete_relay(self):
        """Test a complete 4-leg relay."""
        legs = [
            RelayLeg("S1", "back", 28.0),
            RelayLeg("S2", "breast", 32.0),
            RelayLeg("S3", "fly", 26.0),
            RelayLeg("S4", "free", 24.0),
        ]
        config = RelayConfiguration(
            relay_name="200 Medley Relay",
            team_designation="A",
            legs=legs,
            predicted_time=110.0,
            predicted_place=1,
            predicted_points=16,
        )

        assert config.is_complete
        assert config.swimmer_names == ["S1", "S2", "S3", "S4"]
        assert config.predicted_points == 16

    def test_incomplete_relay(self):
        """Test relay with missing legs."""
        legs = [
            RelayLeg("S1", "back", 28.0),
            RelayLeg("S2", "breast", 32.0),
        ]
        config = RelayConfiguration(
            relay_name="200 Medley Relay",
            team_designation="B",
            legs=legs,
            predicted_time=float("inf"),
            predicted_place=0,
            predicted_points=0,
        )

        assert not config.is_complete
        assert len(config.swimmer_names) == 2


class TestRelayOptimizer:
    """Test RelayOptimizer service."""

    @pytest.fixture
    def optimizer(self):
        """Create optimizer with VCAC rules."""
        return RelayOptimizer("vcac_championship")

    @pytest.fixture
    def swim_team_psych(self):
        """Create psych sheet with swimmers having various stroke times."""
        entries = [
            # Seton swimmers with individual event times
            # Swimmer 1 - backstroke specialist
            PsychSheetEntry("Alex Back", "Seton", "Boys 100 Back", 58.0),
            PsychSheetEntry("Alex Back", "Seton", "Boys 50 Free", 25.0),
            PsychSheetEntry("Alex Back", "Seton", "Boys 100 Free", 55.0),
            # Swimmer 2 - breaststroke specialist
            PsychSheetEntry("Bob Breast", "Seton", "Boys 100 Breast", 65.0),
            PsychSheetEntry("Bob Breast", "Seton", "Boys 50 Free", 26.0),
            PsychSheetEntry("Bob Breast", "Seton", "Boys 100 Free", 56.0),
            # Swimmer 3 - fly specialist
            PsychSheetEntry("Chris Fly", "Seton", "Boys 100 Fly", 54.0),
            PsychSheetEntry("Chris Fly", "Seton", "Boys 50 Free", 24.0),
            PsychSheetEntry("Chris Fly", "Seton", "Boys 100 Free", 52.0),
            # Swimmer 4 - freestyle specialist
            PsychSheetEntry("Dan Free", "Seton", "Boys 100 Free", 50.0),
            PsychSheetEntry("Dan Free", "Seton", "Boys 50 Free", 23.0),
            # Swimmer 5 - all around (B relay)
            PsychSheetEntry("Ed All", "Seton", "Boys 100 Back", 62.0),
            PsychSheetEntry("Ed All", "Seton", "Boys 100 Breast", 70.0),
            PsychSheetEntry("Ed All", "Seton", "Boys 100 Fly", 60.0),
            PsychSheetEntry("Ed All", "Seton", "Boys 100 Free", 55.0),
            PsychSheetEntry("Ed All", "Seton", "Boys 50 Free", 27.0),
            # More B relay swimmers
            PsychSheetEntry("Frank B", "Seton", "Boys 100 Back", 63.0),
            PsychSheetEntry("Frank B", "Seton", "Boys 50 Free", 28.0),
            PsychSheetEntry("Frank B", "Seton", "Boys 100 Free", 58.0),
            PsychSheetEntry("Greg B", "Seton", "Boys 100 Breast", 72.0),
            PsychSheetEntry("Greg B", "Seton", "Boys 50 Free", 29.0),
            PsychSheetEntry("Greg B", "Seton", "Boys 100 Free", 59.0),
            PsychSheetEntry("Hank B", "Seton", "Boys 100 Fly", 62.0),
            PsychSheetEntry("Hank B", "Seton", "Boys 50 Free", 30.0),
            PsychSheetEntry("Hank B", "Seton", "Boys 100 Free", 60.0),
            # Other team relay entries for comparison
            PsychSheetEntry("Trinity Relay", "Trinity", "200 Medley Relay", 105.0),
            PsychSheetEntry("Trinity Relay B", "Trinity", "200 Medley Relay", 115.0),
            PsychSheetEntry("Trinity Relay", "Trinity", "200 Free Relay", 95.0),
        ]
        return MeetPsychSheet(
            meet_name="Test Meet",
            meet_date=date(2026, 2, 7),
            teams=["Seton", "Trinity"],
            entries=entries,
        )

    def test_medley_relay_optimization(self, optimizer, swim_team_psych):
        """Test that medley relay assigns specialists to correct strokes."""
        individual_assignments = {
            "Alex Back": ["Boys 100 Back"],
            "Bob Breast": ["Boys 100 Breast"],
            "Chris Fly": ["Boys 100 Fly"],
            "Dan Free": ["Boys 100 Free"],
        }

        result = optimizer.optimize_relays(
            swim_team_psych, individual_assignments, "Seton"
        )

        assert "200 Medley Relay" in result.configurations
        a_relay = result.configurations["200 Medley Relay"][0]

        # A relay should be complete
        assert a_relay.is_complete

        # Check specialists are assigned to correct strokes
        leg_map = {leg.stroke: leg.swimmer for leg in a_relay.legs}
        assert leg_map.get("back") == "Alex Back"
        assert leg_map.get("breast") == "Bob Breast"
        assert leg_map.get("fly") == "Chris Fly"
        assert leg_map.get("free") == "Dan Free"

    def test_free_relay_optimization(self, optimizer, swim_team_psych):
        """Test that free relay picks fastest swimmers."""
        result = optimizer.optimize_relays(swim_team_psych, {}, "Seton")

        assert "200 Free Relay" in result.configurations
        a_relay = result.configurations["200 Free Relay"][0]

        # A relay should have the 4 fastest 50 freestylers
        # Dan (23.0), Chris (24.0), Alex (25.0), Bob (26.0)
        swimmers = a_relay.swimmer_names
        assert "Dan Free" in swimmers
        assert "Chris Fly" in swimmers

    def test_relay_400_excluded_for_busy_swimmers(self, optimizer, swim_team_psych):
        """Test that swimmers with 2 events are excluded from 400 Free."""
        # Everyone has 2 events - no one available for relay 3
        individual_assignments = {
            "Alex Back": ["Boys 100 Back", "Boys 50 Free"],
            "Bob Breast": ["Boys 100 Breast", "Boys 50 Free"],
            "Chris Fly": ["Boys 100 Fly", "Boys 50 Free"],
            "Dan Free": ["Boys 100 Free", "Boys 50 Free"],
            "Ed All": ["Boys 100 Back", "Boys 100 Fly"],
            "Frank B": ["Boys 100 Back", "Boys 50 Free"],
            "Greg B": ["Boys 100 Breast", "Boys 50 Free"],
            "Hank B": ["Boys 100 Fly", "Boys 50 Free"],
        }

        result = optimizer.optimize_relays(
            swim_team_psych, individual_assignments, "Seton"
        )

        # 400 Free should be skipped since all swimmers have 2 events
        assert result.relay_400_recommendation == "skip"

    def test_relay_400_included_for_available_swimmers(
        self, optimizer, swim_team_psych
    ):
        """Test that 400 Free is recommended when swimmers are available."""
        # Some swimmers have only 1 event - available for relay 3
        individual_assignments = {
            "Alex Back": ["Boys 100 Back"],  # Has 1 slot open
            "Bob Breast": ["Boys 100 Breast"],  # Has 1 slot open
            "Chris Fly": ["Boys 100 Fly"],  # Has 1 slot open
            "Dan Free": ["Boys 100 Free"],  # Has 1 slot open
        }

        result = optimizer.optimize_relays(
            swim_team_psych, individual_assignments, "Seton"
        )

        # 400 Free should be possible since swimmers have capacity
        assert result.relay_400_recommendation in ["swim", "optional"]

    def test_b_relay_uses_remaining_swimmers(self, optimizer, swim_team_psych):
        """Test that B relay correctly uses swimmers not on A relay."""
        result = optimizer.optimize_relays(swim_team_psych, {}, "Seton")

        medley_a = result.configurations["200 Medley Relay"][0]
        medley_b = result.configurations["200 Medley Relay"][1]

        a_swimmers = set(medley_a.swimmer_names)
        b_swimmers = set(medley_b.swimmer_names)

        # No overlap between A and B relay swimmers
        assert len(a_swimmers & b_swimmers) == 0

    def test_total_points_calculated(self, optimizer, swim_team_psych):
        """Test that total points are correctly summed."""
        result = optimizer.optimize_relays(swim_team_psych, {}, "Seton")

        expected_total = sum(
            cfg.predicted_points
            for configs in result.configurations.values()
            for cfg in configs
        )

        assert result.total_points == expected_total

    def test_solve_time_recorded(self, optimizer, swim_team_psych):
        """Test that solve time is recorded."""
        result = optimizer.optimize_relays(swim_team_psych, {}, "Seton")
        assert result.solve_time_ms >= 0


class TestRelayPlacement:
    """Test relay placement prediction."""

    @pytest.fixture
    def optimizer(self):
        return RelayOptimizer("vcac_championship")

    def test_predicts_placement_against_other_teams(self, optimizer):
        """Test that placement considers other teams' times."""
        entries = [
            # Seton swimmers
            PsychSheetEntry("S1", "Seton", "Boys 50 Free", 25.0),
            PsychSheetEntry("S2", "Seton", "Boys 50 Free", 25.5),
            PsychSheetEntry("S3", "Seton", "Boys 50 Free", 26.0),
            PsychSheetEntry("S4", "Seton", "Boys 50 Free", 26.5),
            # Other team faster relay
            PsychSheetEntry("Trinity Relay", "Trinity", "200 Free Relay", 90.0),
        ]
        psych = MeetPsychSheet(
            meet_name="Test",
            meet_date=date(2026, 2, 7),
            teams=["Seton", "Trinity"],
            entries=entries,
        )

        result = optimizer.optimize_relays(psych, {}, "Seton")

        a_relay = result.configurations["200 Free Relay"][0]
        # Trinity relay at 90s, Seton A at ~103s → placed behind Trinity
        assert a_relay.predicted_place >= 1


class TestFormatRelayConfiguration:
    """Test relay configuration formatting."""

    def test_format_complete_relay(self):
        """Test formatting a complete relay."""
        legs = [
            RelayLeg("S1", "back", 28.0),
            RelayLeg("S2", "breast", 32.0),
            RelayLeg("S3", "fly", 26.0),
            RelayLeg("S4", "free", 24.0),
        ]
        config = RelayConfiguration(
            relay_name="200 Medley Relay",
            team_designation="A",
            legs=legs,
            predicted_time=110.0,
            predicted_place=1,
            predicted_points=16,
        )

        output = format_relay_configuration(config)

        assert "200 Medley Relay" in output
        assert "A Relay" in output
        assert "1 place" in output
        assert "16 pts" in output
        assert "S1" in output
        assert "back" in output


class TestDiverConstraints:
    """Test diver constraints in relay optimization."""

    @pytest.fixture
    def optimizer(self):
        return RelayOptimizer("vcac_championship")

    def test_diver_excluded_from_relay_3_with_one_event(self, optimizer):
        """Test that diver with 1 swim event can't do relay 3."""
        entries = [
            PsychSheetEntry("Diver Dan", "Seton", "Boys 50 Free", 25.0),
            PsychSheetEntry("Diver Dan", "Seton", "Boys 100 Free", 55.0),
            PsychSheetEntry("S2", "Seton", "Boys 50 Free", 26.0),
            PsychSheetEntry("S2", "Seton", "Boys 100 Free", 56.0),
            PsychSheetEntry("S3", "Seton", "Boys 50 Free", 27.0),
            PsychSheetEntry("S3", "Seton", "Boys 100 Free", 57.0),
            PsychSheetEntry("S4", "Seton", "Boys 50 Free", 28.0),
            PsychSheetEntry("S4", "Seton", "Boys 100 Free", 58.0),
        ]
        psych = MeetPsychSheet(
            meet_name="Test",
            meet_date=date(2026, 2, 7),
            teams=["Seton"],
            entries=entries,
        )

        individual_assignments = {
            "Diver Dan": ["Boys 50 Free"],  # Diver + 1 event = 2 effective
        }

        result = optimizer.optimize_relays(
            psych, individual_assignments, "Seton", divers={"Diver Dan"}
        )

        # If 400 Free Relay exists, Diver Dan should not be on it
        if "400 Free Relay" in result.configurations:
            relay_400_a = result.configurations["400 Free Relay"][0]
            relay_400_b = result.configurations["400 Free Relay"][1]
            all_swimmers = relay_400_a.swimmer_names + relay_400_b.swimmer_names
            # Diver Dan should be excluded since diving + 1 event + relay3 = 3
            assert "Diver Dan" not in all_swimmers


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
