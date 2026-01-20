"""
Tests for Constraint Validator Service

Tests back-to-back constraints including relay legs, diver handling,
and VCAC 400 Free Relay penalty.
"""

import pytest
from swim_ai_reflex.backend.services.constraint_validator import (
    validate_lineup,
    is_back_to_back,
    normalize_event_name,
    generate_back_to_back_constraints_for_gurobi,
    EVENT_ORDER,
)


class TestNormalizeEventName:
    """Test event name normalization."""

    def test_medley_relay_variations(self):
        assert normalize_event_name("200 Medley Relay") == "200 Medley Relay"
        assert normalize_event_name("200 medley relay") == "200 Medley Relay"
        assert normalize_event_name("Medley Relay") == "200 Medley Relay"
        assert normalize_event_name("Boys 200 Medley Relay") == "200 Medley Relay"

    def test_free_relay_variations(self):
        assert normalize_event_name("200 Free Relay") == "200 Free Relay"
        assert normalize_event_name("400 Free Relay") == "400 Free Relay"
        assert normalize_event_name("Girls 200 Free Relay") == "200 Free Relay"

    def test_individual_events(self):
        assert normalize_event_name("50 Free") == "50 Free"
        assert normalize_event_name("100 Freestyle") == "100 Free"
        assert normalize_event_name("200 Free") == "200 Free"
        assert normalize_event_name("500 Free") == "500 Free"

    def test_stroke_events(self):
        assert normalize_event_name("100 Fly") == "100 Fly"
        assert normalize_event_name("100 Butterfly") == "100 Fly"
        assert normalize_event_name("100 Back") == "100 Back"
        assert normalize_event_name("100 Backstroke") == "100 Back"
        assert normalize_event_name("100 Breast") == "100 Breast"
        assert normalize_event_name("100 Breaststroke") == "100 Breast"

    def test_im_and_diving(self):
        assert normalize_event_name("200 IM") == "200 IM"
        assert normalize_event_name("200 Individual Medley") == "200 IM"
        assert normalize_event_name("Diving") == "Diving"
        assert normalize_event_name("1 Meter Diving") == "Diving"


class TestBackToBackDetection:
    """Test back-to-back constraint detection."""

    def test_medley_relay_blocks_200_free(self):
        """200 Medley Relay swimmer cannot swim 200 Free."""
        assert is_back_to_back("200 Medley Relay", "200 Free") is True

    def test_200_free_relay_blocks_100_back(self):
        """200 Free Relay swimmer cannot swim 100 Back."""
        assert is_back_to_back("200 Free Relay", "100 Back") is True

    def test_500_free_blocks_200_free_relay(self):
        """500 Free swimmer cannot swim 200 Free Relay leg."""
        assert is_back_to_back("500 Free", "200 Free Relay") is True

    def test_200_im_blocks_50_free(self):
        """200 IM swimmer cannot swim 50 Free."""
        assert is_back_to_back("200 IM", "50 Free") is True

    def test_100_breast_blocks_400_free_relay(self):
        """100 Breast swimmer cannot swim 400 Free Relay leg."""
        assert is_back_to_back("100 Breast", "400 Free Relay") is True

    def test_400_free_relay_blocks_nothing(self):
        """400 Free Relay is last event, blocks nothing."""
        assert is_back_to_back("400 Free Relay", "200 Free") is False

    def test_non_consecutive_events(self):
        """Non-consecutive events are not back-to-back."""
        assert is_back_to_back("200 Medley Relay", "50 Free") is False
        assert is_back_to_back("200 Free", "100 Fly") is False
        assert is_back_to_back("100 Back", "400 Free Relay") is False


class TestValidateLineupBackToBack:
    """Test back-to-back validation in full lineup."""

    def test_valid_lineup_no_back_to_back(self):
        """Lineup with no back-to-back violations is valid."""
        assignments = {
            "Smith, John": ["50 Free", "100 Back"],
            "Jones, Mike": ["200 Free", "100 Fly"],
        }
        result = validate_lineup(assignments)
        assert result.is_valid is True
        assert len(result.violations) == 0

    def test_invalid_200im_50free_same_swimmer(self):
        """200 IM and 50 Free back-to-back is invalid."""
        assignments = {
            "Smith, John": ["200 IM", "50 Free"],
        }
        result = validate_lineup(assignments)
        assert result.is_valid is False
        assert len(result.violations) == 1
        assert result.violations[0].violation_type == "back_to_back"
        assert "200 IM" in result.violations[0].events_involved
        assert "50 Free" in result.violations[0].events_involved

    def test_invalid_medley_relay_200_free(self):
        """Swimmer on Medley Relay cannot swim 200 Free."""
        assignments = {
            "Smith, John": ["200 Free"],
        }
        relay_assignments = {
            "200 Medley Relay": [
                "Smith, John",
                "Jones, Mike",
                "Brown, Pete",
                "Wilson, Tom",
            ]
        }
        result = validate_lineup(assignments, relay_assignments=relay_assignments)
        assert result.is_valid is False
        assert any(v.violation_type == "back_to_back" for v in result.violations)

    def test_invalid_500_free_to_200_free_relay(self):
        """500 Free swimmer cannot be on 200 Free Relay."""
        assignments = {
            "Smith, John": ["500 Free"],
        }
        relay_assignments = {
            "200 Free Relay": [
                "Smith, John",
                "Jones, Mike",
                "Brown, Pete",
                "Wilson, Tom",
            ]
        }
        result = validate_lineup(assignments, relay_assignments=relay_assignments)
        assert result.is_valid is False

    def test_back_to_back_override_becomes_warning(self):
        """With override, back-to-back becomes warning not error."""
        assignments = {
            "Smith, John": ["200 IM", "50 Free"],
        }
        result = validate_lineup(assignments, allow_override=True)
        assert result.is_valid is True  # Valid because warnings only
        assert len(result.warnings) == 1
        assert result.warnings[0].violation_type == "back_to_back"


class TestValidateLineupMaxEvents:
    """Test max events per swimmer validation."""

    def test_valid_two_individual_events(self):
        """Two individual events is valid."""
        assignments = {
            "Smith, John": ["50 Free", "100 Back"],
        }
        result = validate_lineup(assignments)
        assert result.is_valid is True

    def test_invalid_three_individual_events(self):
        """Three individual events is invalid."""
        assignments = {
            "Smith, John": ["50 Free", "100 Back", "100 Free"],
        }
        result = validate_lineup(assignments)
        assert result.is_valid is False
        assert any(v.violation_type == "max_events" for v in result.violations)

    def test_diver_with_one_swim_event_valid(self):
        """Diver with one swim event is valid (diving + 1 = 2)."""
        assignments = {
            "Smith, John": ["100 Back"],
        }
        divers = {"Smith, John"}
        result = validate_lineup(assignments, divers=divers)
        assert result.is_valid is True

    def test_diver_with_two_swim_events_invalid(self):
        """Diver with two swim events is invalid (diving + 2 = 3)."""
        assignments = {
            "Smith, John": ["100 Back", "100 Free"],
        }
        divers = {"Smith, John"}
        result = validate_lineup(assignments, divers=divers)
        assert result.is_valid is False


class TestVCAC400FreeRelayPenalty:
    """Test VCAC 400 Free Relay counts as individual event."""

    def test_400_free_relay_penalty_vcac(self):
        """At VCAC, 400 Free Relay counts as 1 individual event."""
        assignments = {
            "Smith, John": ["50 Free", "100 Back"],  # 2 individual
        }
        relay_assignments = {
            "400 Free Relay": [
                "Smith, John",
                "Jones, Mike",
                "Brown, Pete",
                "Wilson, Tom",
            ]
        }
        # Smith has 2 individual + 1 (400FR penalty) = 3, which exceeds limit
        result = validate_lineup(
            assignments,
            relay_assignments=relay_assignments,
            meet_profile="vcac_championship",
        )
        assert result.is_valid is False
        assert any("relay-3 penalty" in v.message for v in result.violations)

    def test_400_free_relay_no_penalty_dual_meet(self):
        """At dual meet, 400 Free Relay does NOT count as individual."""
        assignments = {
            "Smith, John": ["50 Free", "100 Back"],
        }
        relay_assignments = {
            "400 Free Relay": [
                "Smith, John",
                "Jones, Mike",
                "Brown, Pete",
                "Wilson, Tom",
            ]
        }
        result = validate_lineup(
            assignments, relay_assignments=relay_assignments, meet_profile="seton_dual"
        )
        assert result.is_valid is True  # No penalty at dual meet


class TestGurobiConstraintGeneration:
    """Test Gurobi constraint generation."""

    def test_generates_back_to_back_constraints(self):
        """Generate constraints for all back-to-back pairs."""
        swimmers = ["Smith", "Jones"]
        events = ["200 IM", "50 Free", "100 Fly"]

        constraints = generate_back_to_back_constraints_for_gurobi(swimmers, events)

        # Should have constraints for 200 IM -> 50 Free for both swimmers
        im_to_50 = [c for c in constraints if c[1] == "200 IM" and c[2] == "50 Free"]
        assert len(im_to_50) == 2

    def test_relay_constraints_only_for_relay_swimmers(self):
        """Relay back-to-back constraints only apply to relay swimmers."""
        swimmers = ["Smith", "Jones", "Brown"]
        events = ["200 Medley Relay", "200 Free"]
        relay_swimmers = {
            "200 Medley Relay": {"Smith", "Jones"}  # Brown not on relay
        }

        constraints = generate_back_to_back_constraints_for_gurobi(
            swimmers, events, relay_swimmers
        )

        # Only Smith and Jones should be blocked from 200 Free
        blocked_swimmers = [c[0] for c in constraints if c[2] == "200 Free"]
        assert "Smith" in blocked_swimmers
        assert "Jones" in blocked_swimmers
        assert "Brown" not in blocked_swimmers


class TestEventOrder:
    """Test event order constant is correct."""

    def test_event_order_length(self):
        """Standard meet has 12 events."""
        assert len(EVENT_ORDER) == 12

    def test_event_order_starts_with_medley_relay(self):
        """Meet starts with 200 Medley Relay."""
        assert EVENT_ORDER[0] == "200 Medley Relay"

    def test_event_order_ends_with_400_free_relay(self):
        """Meet ends with 400 Free Relay."""
        assert EVENT_ORDER[-1] == "400 Free Relay"

    def test_diving_is_event_5(self):
        """Diving is 5th event (index 4)."""
        assert EVENT_ORDER[4] == "Diving"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
