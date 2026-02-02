"""
Tests for Point Projection Service

Verifies the projection engine correctly calculates expected team standings
based on psych sheet data and meet-specific scoring rules.
"""

import json
from datetime import date
from pathlib import Path

import pytest

from swim_ai_reflex.backend.core.rules import VCACChampRules, get_meet_profile
from swim_ai_reflex.backend.models.championship import MeetPsychSheet, PsychSheetEntry
from swim_ai_reflex.backend.services.point_projection_service import (
    PointProjectionEngine,
)


class TestPsychSheetEntry:
    """Test PsychSheetEntry data model."""

    def test_basic_entry(self):
        """Test creating a basic entry."""
        entry = PsychSheetEntry(
            swimmer_name="John Smith",
            team="Seton",
            event="Boys 50 Free",
            seed_time=23.45,
        )
        assert entry.swimmer_name == "John Smith"
        assert entry.team == "Seton"
        assert entry.seed_time == 23.45
        assert not entry.is_diving

    def test_diving_detection(self):
        """Test auto-detection of diving events."""
        entry = PsychSheetEntry(
            swimmer_name="Jane Doe",
            team="Trinity",
            event="Girls Diving",
            seed_time=0,
            dive_score=245.5,
        )
        assert entry.is_diving

    def test_time_formatting(self):
        """Test time string formatting."""
        # Under 1 minute
        entry1 = PsychSheetEntry(
            swimmer_name="Fast", team="A", event="50 Free", seed_time=23.45
        )
        assert entry1.formatted_time == "23.45"

        # Over 1 minute
        entry2 = PsychSheetEntry(
            swimmer_name="Mid", team="A", event="100 Free", seed_time=55.67
        )
        assert entry2.formatted_time == "55.67"

        # Multiple minutes
        entry3 = PsychSheetEntry(
            swimmer_name="Long", team="A", event="200 Free", seed_time=125.34
        )
        assert entry3.formatted_time == "2:05.34"

        # No time
        entry4 = PsychSheetEntry(
            swimmer_name="NT", team="A", event="50 Free", seed_time=float("inf")
        )
        assert entry4.formatted_time == "NT"


class TestMeetPsychSheet:
    """Test MeetPsychSheet data model."""

    def test_from_dict(self):
        """Test loading from dictionary."""
        data = {
            "meet_name": "Test Meet",
            "meet_date": "2026-02-07",
            "teams": ["Seton", "Trinity"],
            "entries": [
                {
                    "swimmer_name": "John",
                    "team": "Seton",
                    "event": "50 Free",
                    "seed_time": 23.0,
                },
                {
                    "swimmer_name": "Jane",
                    "team": "Trinity",
                    "event": "50 Free",
                    "seed_time": 24.0,
                },
            ],
        }
        psych = MeetPsychSheet.from_dict(data)

        assert psych.meet_name == "Test Meet"
        assert len(psych.entries) == 2
        assert psych.entries[0].seed_rank == 1  # Faster time
        assert psych.entries[1].seed_rank == 2

    def test_get_event_entries(self):
        """Test filtering by event."""
        entries = [
            PsychSheetEntry("A", "Seton", "50 Free", 23.0),
            PsychSheetEntry("B", "Seton", "100 Free", 55.0),
            PsychSheetEntry("C", "Trinity", "50 Free", 24.0),
        ]
        psych = MeetPsychSheet(
            meet_name="Test",
            meet_date=date.today(),
            teams=["Seton", "Trinity"],
            entries=entries,
        )

        free50 = psych.get_event_entries("50 Free")
        assert len(free50) == 2
        assert free50[0].swimmer_name == "A"  # Faster seed

    def test_get_team_entries(self):
        """Test filtering by team."""
        entries = [
            PsychSheetEntry("A", "Seton", "50 Free", 23.0),
            PsychSheetEntry("B", "Seton", "100 Free", 55.0),
            PsychSheetEntry("C", "Trinity", "50 Free", 24.0),
        ]
        psych = MeetPsychSheet(
            meet_name="Test",
            meet_date=date.today(),
            teams=["Seton", "Trinity"],
            entries=entries,
        )

        seton = psych.get_team_entries("Seton")
        assert len(seton) == 2


class TestPointProjectionEngine:
    """Test PointProjectionEngine service."""

    @pytest.fixture
    def engine(self):
        """Create engine with VCAC rules."""
        return PointProjectionEngine("vcac_championship")

    @pytest.fixture
    def sample_psych(self):
        """Load sample psych sheet data."""
        data_path = Path(__file__).parent / "data" / "vcac_sample_psych_sheet.json"
        with open(data_path) as f:
            data = json.load(f)
        return MeetPsychSheet.from_dict(data)

    def test_vcac_scoring_rules(self, engine):
        """Verify VCAC scoring tables are correct."""
        rules = engine.rules
        assert isinstance(rules, VCACChampRules)

        # Individual: [16, 13, 12, 11, 10, 9, 7, 5, 4, 3, 2, 1]
        assert rules.individual_points[0] == 16  # 1st place
        assert rules.individual_points[1] == 13  # 2nd place

        # Relay: [32, 26, 24, 22, 20, 18, 14, 10, 8, 6, 4, 2] (2x individual)
        assert rules.relay_points[0] == 32  # 1st place

    def test_event_projection_basic(self, engine, sample_psych):
        """Test projecting a single event."""
        proj = engine.project_event_points(sample_psych, "Boys 50 Free")

        assert proj.event == "Boys 50 Free"
        assert len(proj.team_results) > 0

        # Check Trinity has entries (Alex Brown should be fastest)
        assert "trinity" in proj.team_results or "Trinity" in proj.team_results

    def test_event_projection_scoring(self, engine, sample_psych):
        """Test that points are assigned correctly."""
        proj = engine.project_event_points(sample_psych, "Boys 50 Free")

        # Find the 1st place finisher - should have 32 points
        all_swimmers = []
        for team, swimmers in proj.team_results.items():
            for s in swimmers:
                all_swimmers.append(s)

        first_place = [s for s in all_swimmers if s["predicted_place"] == 1]
        assert len(first_place) == 1
        assert first_place[0]["points"] == 16  # VCAC individual 1st place = 16

    def test_team_scorer_limit(self, engine):
        """Test that max 4 scorers per team per event is enforced."""
        # Create a psych with 5 swimmers from one team
        entries = [
            PsychSheetEntry(f"Swimmer{i}", "Seton", "50 Free", 23.0 + i)
            for i in range(5)
        ]
        psych = MeetPsychSheet(
            meet_name="Test", meet_date=date.today(), teams=["Seton"], entries=entries
        )

        proj = engine.project_event_points(psych, "50 Free")
        seton_results = proj.team_results.get("seton", [])

        # Only 4 should be scoring
        scoring = [s for s in seton_results if s["scoring"]]
        assert len(scoring) == 4

        # 5th swimmer should be exhibition
        exhibition = [s for s in seton_results if s["is_exhibition"]]
        assert len(exhibition) == 1

    def test_full_meet_projection(self, engine, sample_psych):
        """Test full meet projection with standings."""
        result = engine.project_full_meet(sample_psych, "Seton")

        assert result.meet_name == "VCAC Championship 2026"
        assert len(result.standings) > 0
        assert result.target_team_total >= 0

        # Standings should be sorted by points (descending)
        for i in range(len(result.standings) - 1):
            assert result.standings[i][1] >= result.standings[i + 1][1]

    def test_swing_event_identification(self, engine, sample_psych):
        """Test finding swing events."""
        result = engine.project_full_meet(sample_psych, "Seton")

        # Swing events should be sorted by point gain
        if len(result.swing_events) > 1:
            for i in range(len(result.swing_events) - 1):
                assert (
                    result.swing_events[i]["point_gain"]
                    >= result.swing_events[i + 1]["point_gain"]
                )

    def test_head_to_head(self, engine, sample_psych):
        """Test head-to-head comparison."""
        result = engine.project_full_meet(sample_psych, "Seton")
        h2h = engine.get_head_to_head(result, "Seton", "Trinity")

        assert "team1" in h2h
        assert "team2" in h2h
        assert "overall_differential" in h2h

    def test_team_summary(self, engine, sample_psych):
        """Test team summary generation."""
        result = engine.project_full_meet(sample_psych, "Seton")
        summary = engine.summarize_team(result, "Seton")

        assert "total_points" in summary
        assert "top_scorers" in summary
        assert "best_events" in summary


class TestVCACSpecificRules:
    """Test VCAC-specific scoring behavior."""

    def test_individual_more_than_relay(self):
        """Verify VCAC relay events score 2x more than individual (correct rule)."""
        rules = get_meet_profile("vcac_championship")

        # 1st place relay (32) > 1st place individual (16) - relays are 2x
        assert rules.relay_points[0] > rules.individual_points[0]
        assert rules.relay_points[0] == 2 * rules.individual_points[0]

    def test_max_scorers_per_team(self):
        """Verify max 4 scorers per team per event."""
        rules = get_meet_profile("vcac_championship")
        assert rules.max_scorers_per_team_individual == 4


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
