"""
Tests for Entry Selection Optimizer Service

Verifies the optimizer correctly assigns swimmers to events to maximize team points
using MILP (Mixed Integer Linear Programming).
"""

import pytest
from datetime import date

from swim_ai_reflex.backend.models.championship import PsychSheetEntry, MeetPsychSheet
from swim_ai_reflex.backend.services.entry_optimizer_service import (
    EntrySelectionOptimizer,
    SwimmerAssignment,
    OptimizationResult,
    compare_assignments,
)
from swim_ai_reflex.backend.core.rules import get_meet_profile


class TestSwimmerAssignment:
    """Test SwimmerAssignment data model."""

    def test_basic_assignment(self):
        """Test creating a basic assignment."""
        assignment = SwimmerAssignment(
            swimmer_name="John Smith",
            team="Seton",
            individual_events=["Boys 50 Free", "Boys 100 Free"],
        )
        assert assignment.swimmer_name == "John Smith"
        assert len(assignment.individual_events) == 2
        assert assignment.total_events == 2
        assert assignment.is_valid

    def test_diver_effective_individual_count(self):
        """Test that diving counts as 1 individual event."""
        # Diver with 1 swim event = 2 effective (valid)
        assignment = SwimmerAssignment(
            swimmer_name="Jane Diver",
            team="Seton",
            individual_events=["Boys 100 Free"],
            is_diver=True,
        )
        assert assignment.effective_individual_count == 2
        assert assignment.is_valid

    def test_diver_with_too_many_events(self):
        """Test that diver + 2 swim events is invalid."""
        assignment = SwimmerAssignment(
            swimmer_name="Jane Diver",
            team="Seton",
            individual_events=["Boys 50 Free", "Boys 100 Free"],
            is_diver=True,
        )
        assert assignment.effective_individual_count == 3
        assert not assignment.is_valid

    def test_relay_penalty(self):
        """Test that 3rd relay counts as individual."""
        assignment = SwimmerAssignment(
            swimmer_name="Relay Heavy",
            team="Seton",
            individual_events=["Boys 50 Free"],
            relay_events=["200 Medley Relay", "200 Free Relay", "400 Free Relay"],
        )
        # 1 individual + 1 relay penalty (3rd relay) = 2
        assert assignment.effective_individual_count == 2
        assert assignment.is_valid

    def test_max_relay_penalty(self):
        """Test relay + individual combination at limit."""
        assignment = SwimmerAssignment(
            swimmer_name="Max Load",
            team="Seton",
            individual_events=["Boys 50 Free", "Boys 100 Free"],
            relay_events=["200 Medley Relay", "200 Free Relay", "400 Free Relay"],
        )
        # 2 individual + 1 relay penalty = 3 (INVALID)
        assert assignment.effective_individual_count == 3
        assert not assignment.is_valid


class TestEntrySelectionOptimizer:
    """Test EntrySelectionOptimizer MILP solver."""

    @pytest.fixture
    def optimizer(self):
        """Create optimizer with VCAC rules."""
        return EntrySelectionOptimizer("vcac_championship")

    @pytest.fixture
    def simple_psych(self):
        """Create a simple psych sheet for testing."""
        entries = [
            # Seton swimmers
            PsychSheetEntry("John Smith", "Seton", "Boys 50 Free", 22.5),
            PsychSheetEntry("John Smith", "Seton", "Boys 100 Free", 50.0),
            PsychSheetEntry("Mike Jones", "Seton", "Boys 50 Free", 23.0),
            PsychSheetEntry("Mike Jones", "Seton", "Boys 100 Fly", 55.0),
            PsychSheetEntry("Tom Brown", "Seton", "Boys 50 Free", 24.0),
            PsychSheetEntry("Tom Brown", "Seton", "Boys 100 Back", 58.0),
            # Other team swimmers
            PsychSheetEntry("Alex Fast", "Trinity", "Boys 50 Free", 21.5),
            PsychSheetEntry("Alex Fast", "Trinity", "Boys 100 Free", 48.0),
            PsychSheetEntry("Bob Speed", "Trinity", "Boys 100 Fly", 54.0),
        ]
        return MeetPsychSheet(
            meet_name="Test Meet",
            meet_date=date(2026, 2, 7),
            teams=["Seton", "Trinity"],
            entries=entries,
        )

    def test_basic_optimization(self, optimizer, simple_psych):
        """Test that optimizer produces valid results."""
        result = optimizer.optimize(simple_psych, "Seton")

        assert result.status == "optimal"
        assert result.total_points > 0
        assert len(result.assignments) > 0

    def test_max_two_events_per_swimmer(self, optimizer, simple_psych):
        """Test that no swimmer is assigned more than 2 individual events."""
        result = optimizer.optimize(simple_psych, "Seton")

        for swimmer, assignment in result.assignments.items():
            assert len(assignment.individual_events) <= 2, (
                f"{swimmer} assigned {len(assignment.individual_events)} events"
            )

    def test_diver_constraint(self, optimizer, simple_psych):
        """Test that divers get max 1 swim event."""
        result = optimizer.optimize(simple_psych, "Seton", divers={"John Smith"})

        if "John Smith" in result.assignments:
            john = result.assignments["John Smith"]
            assert len(john.individual_events) <= 1, (
                f"Diver John Smith assigned {len(john.individual_events)} swim events"
            )
            assert john.is_diver

    def test_optimal_assignment_maximizes_points(self, optimizer):
        """Test that optimizer chooses higher-scoring events."""
        # Create scenario where swimmer should choose better placement
        entries = [
            # Swimmer1 is 1st in event A (32 pts), 3rd in event B (24 pts)
            PsychSheetEntry("Swimmer1", "Seton", "Event A", 22.0),
            PsychSheetEntry("Swimmer1", "Seton", "Event B", 24.0),
            PsychSheetEntry("Other1", "Trinity", "Event A", 23.0),
            PsychSheetEntry("Other2", "Trinity", "Event B", 23.0),
            PsychSheetEntry("Other3", "Trinity", "Event B", 23.5),
        ]
        psych = MeetPsychSheet(
            meet_name="Test",
            meet_date=date(2026, 2, 7),
            teams=["Seton", "Trinity"],
            entries=entries,
        )

        result = optimizer.optimize(psych, "Seton")

        # Swimmer1 should be assigned to both events (32 + 24 = 56 pts)
        assert "Swimmer1" in result.assignments
        s1 = result.assignments["Swimmer1"]
        assert len(s1.individual_events) == 2

    def test_empty_team_returns_empty_result(self, optimizer):
        """Test handling of team with no entries."""
        entries = [
            PsychSheetEntry("Other", "Trinity", "50 Free", 23.0),
        ]
        psych = MeetPsychSheet(
            meet_name="Test",
            meet_date=date(2026, 2, 7),
            teams=["Seton", "Trinity"],
            entries=entries,
        )

        result = optimizer.optimize(psych, "Seton")
        assert result.status == "failed"
        assert "No swimmers or events" in result.message

    def test_improvement_calculation(self, optimizer, simple_psych):
        """Test that improvement is calculated correctly."""
        result = optimizer.optimize(simple_psych, "Seton")

        # Improvement = optimal - current
        assert result.improvement == result.total_points - result.current_points

    def test_result_solve_time(self, optimizer, simple_psych):
        """Test that solve time is recorded."""
        result = optimizer.optimize(simple_psych, "Seton")
        assert result.solve_time_ms >= 0


class TestVCACConstraints:
    """Test VCAC-specific constraints are handled correctly."""

    @pytest.fixture
    def optimizer(self):
        return EntrySelectionOptimizer("vcac_championship")

    def test_vcac_entry_validation(self):
        """Test VCAC entry validation function."""
        rules = get_meet_profile("vcac_championship")

        # Valid combinations
        assert rules.is_valid_entry(2, False, 2)  # 2 swim, no dive, 2 relays
        assert rules.is_valid_entry(1, True, 2)  # 1 swim, dive, 2 relays
        assert rules.is_valid_entry(1, False, 3)  # 1 swim, 3 relays (R3 penalty)
        assert rules.is_valid_entry(0, True, 3)  # dive only, 3 relays

        # Invalid combinations
        assert not rules.is_valid_entry(2, True, 0)  # 2 swim + dive = 3
        assert not rules.is_valid_entry(2, False, 3)  # 2 swim + R3 = 3
        assert not rules.is_valid_entry(1, True, 3)  # 1 swim + dive + R3 = 3


class TestCompareAssignments:
    """Test assignment comparison utility."""

    def test_compare_identifies_changes(self):
        """Test that changes are correctly identified."""
        # Current assignments
        current = {
            "John": ["50 Free", "100 Free"],
            "Mike": ["100 Fly"],
        }

        # Optimized result
        result = OptimizationResult(
            assignments={
                "John": SwimmerAssignment(
                    swimmer_name="John",
                    team="Seton",
                    individual_events=[
                        "50 Free",
                        "100 Fly",
                    ],  # Changed 100 Free -> 100 Fly
                    expected_points=50,
                ),
                "Mike": SwimmerAssignment(
                    swimmer_name="Mike",
                    team="Seton",
                    individual_events=["100 Fly", "100 Back"],  # Added 100 Back
                    expected_points=30,
                ),
            },
            total_points=80,
            current_points=70,
            improvement=10,
            status="optimal",
        )

        # Create a dummy psych (not used in compare_assignments)
        entries = [PsychSheetEntry("John", "Seton", "50 Free", 23.0)]
        psych = MeetPsychSheet(
            meet_name="Test",
            meet_date=date(2026, 2, 7),
            teams=["Seton"],
            entries=entries,
        )

        comparison = compare_assignments(psych, current, result)

        assert comparison["total_changes"] == 2
        assert comparison["improvement"] == 10


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
