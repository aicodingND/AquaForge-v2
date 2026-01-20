"""
Tests for Pipeline Architecture

Tests the new pipeline-based architecture for dual meet and championship workflows.
"""

import pandas as pd
import pytest

from swim_ai_reflex.backend.pipelines import (
    ChampionshipPipeline,
    DualMeetPipeline,
    MeetType,
    ValidationResult,
)
from swim_ai_reflex.backend.pipelines.championship import ChampionshipInput
from swim_ai_reflex.backend.pipelines.dual_meet import DualMeetInput
from swim_ai_reflex.backend.services.championship import PointProjectionService
from swim_ai_reflex.backend.services.dual_meet import DualMeetScoringService
from swim_ai_reflex.backend.services.shared import (
    MeetDataValidator,
    normalize_event_name,
    normalize_swimmer_name,
    normalize_time,
)


class TestNormalization:
    """Tests for normalization utilities."""

    def test_normalize_event_name_standard(self):
        """Test standard event name normalization."""
        assert normalize_event_name("100 freestyle") == "100 Free"
        assert normalize_event_name("100 Freestyle") == "100 Free"
        assert normalize_event_name("100 Free") == "100 Free"

    def test_normalize_event_name_with_prefix(self):
        """Test event names with gender prefix."""
        assert normalize_event_name("Boys 200 IM") == "200 IM"
        assert normalize_event_name("Girls 50 Free") == "50 Free"

    def test_normalize_event_name_strokes(self):
        """Test stroke name normalization."""
        assert normalize_event_name("100 butterfly") == "100 Fly"
        assert normalize_event_name("100 backstroke") == "100 Back"
        assert normalize_event_name("100 breaststroke") == "100 Breast"

    def test_normalize_time_float(self):
        """Test float time normalization."""
        assert normalize_time(52.34) == 52.34
        assert normalize_time(0.0) == 0.0

    def test_normalize_time_string_mm_ss(self):
        """Test MM:SS.ss format."""
        assert normalize_time("1:23.45") == 83.45
        assert normalize_time("2:00.00") == 120.0

    def test_normalize_time_string_ss(self):
        """Test SS.ss format."""
        assert normalize_time("52.34") == 52.34

    def test_normalize_time_special(self):
        """Test special time values."""
        assert normalize_time("NT") == float("inf")
        assert normalize_time("NS") == float("inf")
        assert normalize_time("DQ") == float("inf")
        assert normalize_time(None) is None

    def test_normalize_swimmer_name(self):
        """Test swimmer name normalization."""
        assert normalize_swimmer_name("  john smith  ") == "John Smith"
        assert normalize_swimmer_name("JANE DOE") == "Jane Doe"
        assert normalize_swimmer_name("Smith, John") == "John Smith"


class TestValidation:
    """Tests for the MeetDataValidator."""

    @pytest.fixture
    def validator(self):
        return MeetDataValidator()

    def test_validate_valid_entry(self, validator):
        """Test validation of valid entry."""
        entry = {"swimmer": "John Smith", "event": "100 Free", "time": 52.34}
        result = validator.validate_swimmer_entry(entry)
        assert result.valid is True
        assert len(result.errors) == 0

    def test_validate_missing_swimmer(self, validator):
        """Test validation catches missing swimmer."""
        entry = {"event": "100 Free", "time": 52.34}
        result = validator.validate_swimmer_entry(entry)
        assert result.valid is False
        assert any("swimmer" in e.lower() for e in result.errors)

    def test_validate_missing_event(self, validator):
        """Test validation catches missing event."""
        entry = {"swimmer": "John Smith", "time": 52.34}
        result = validator.validate_swimmer_entry(entry)
        assert result.valid is False
        assert any("event" in e.lower() for e in result.errors)

    def test_validate_negative_time(self, validator):
        """Test validation catches negative time."""
        entry = {"swimmer": "John Smith", "event": "100 Free", "time": -1.0}
        result = validator.validate_swimmer_entry(entry)
        assert result.valid is False
        assert any("negative" in e.lower() for e in result.errors)

    def test_validate_swimmer_constraints(self, validator):
        """Test swimmer event limit validation."""
        swimmer_events = {
            "John Smith": ["100 Free", "50 Free", "200 Free"],  # 3 events = violation
        }
        result = validator.validate_swimmer_constraints(
            swimmer_events, max_individual=2
        )
        assert result.valid is False
        assert any("exceeds limit" in e.lower() for e in result.errors)

    def test_validate_full_roster(self, validator):
        """Test full roster validation."""
        entries = [
            {"swimmer": "John Smith", "event": "100 Free", "time": 52.34},
            {"swimmer": "Jane Doe", "event": "50 Free", "time": 26.12},
        ]
        result = validator.validate_full_roster(entries)
        assert result.valid is True


class TestDualMeetScoring:
    """Tests for dual meet scoring service."""

    @pytest.fixture
    def scoring_service(self):
        return DualMeetScoringService()

    @pytest.fixture
    def sample_our_entries(self):
        return [
            {"swimmer": "Smith", "event": "100 Free", "time": 52.0, "grade": 11},
            {"swimmer": "Jones", "event": "100 Free", "time": 54.0, "grade": 10},
        ]

    @pytest.fixture
    def sample_opponent_entries(self):
        return [
            {"swimmer": "Brown", "event": "100 Free", "time": 53.0, "grade": 12},
            {"swimmer": "Wilson", "event": "100 Free", "time": 55.0, "grade": 11},
        ]

    def test_score_event(
        self, scoring_service, sample_our_entries, sample_opponent_entries
    ):
        """Test single event scoring."""
        result = scoring_service.score_event(
            our_entries=sample_our_entries,
            opponent_entries=sample_opponent_entries,
            event_name="100 Free",
        )

        assert result.event == "100 Free"
        assert len(result.entries) == 4
        assert result.entries[0].swimmer == "Smith"  # Fastest
        assert result.our_points > 0
        assert result.opponent_points > 0

    def test_exhibition_swimmer_no_points(self, scoring_service):
        """Test that exhibition swimmers don't score."""
        our = [
            {"swimmer": "JV Kid", "event": "100 Free", "time": 52.0, "grade": 7}
        ]  # Exhibition
        opp = [{"swimmer": "Varsity", "event": "100 Free", "time": 60.0, "grade": 12}]

        result = scoring_service.score_event(our, opp, "100 Free")

        # Grade 7 swimmer should be exhibition
        jv_entry = next(e for e in result.entries if e.swimmer == "JV Kid")
        assert jv_entry.is_exhibition is True
        assert jv_entry.points == 0


class TestDualMeetPipeline:
    """Tests for dual meet pipeline."""

    @pytest.fixture
    def pipeline(self):
        return DualMeetPipeline()

    @pytest.fixture
    def sample_input(self):
        our_data = [
            {"swimmer": "Smith", "event": "100 Free", "time": 52.34, "grade": 11},
            {"swimmer": "Jones", "event": "50 Free", "time": 24.56, "grade": 10},
        ]
        opp_data = [
            {"swimmer": "Brown", "event": "100 Free", "time": 53.21, "grade": 12},
            {"swimmer": "Wilson", "event": "50 Free", "time": 25.12, "grade": 11},
        ]
        return DualMeetInput(
            our_roster=pd.DataFrame(our_data),
            opponent_roster=pd.DataFrame(opp_data),
            our_team="Seton",
            opponent_team="Trinity",
        )

    def test_pipeline_instantiation(self, pipeline):
        """Test pipeline instantiation."""
        assert pipeline.meet_type == MeetType.DUAL_MEET

    def test_pipeline_validation_valid(self, pipeline, sample_input):
        """Test pipeline validation with valid data."""
        result = pipeline.validate_input(sample_input)
        assert result.valid is True

    def test_pipeline_validation_empty_roster(self, pipeline):
        """Test pipeline validation with empty roster."""
        data = DualMeetInput(
            our_roster=pd.DataFrame(),
            opponent_roster=pd.DataFrame(
                [{"swimmer": "X", "event": "100 Free", "time": 52}]
            ),
        )
        result = pipeline.validate_input(data)
        assert result.valid is False


class TestChampionshipPipeline:
    """Tests for championship pipeline."""

    @pytest.fixture
    def pipeline(self):
        return ChampionshipPipeline()

    @pytest.fixture
    def sample_entries(self):
        return [
            {
                "swimmer": "Smith",
                "team": "Seton",
                "event": "100 Free",
                "seed_time": 52.34,
            },
            {
                "swimmer": "Jones",
                "team": "Seton",
                "event": "50 Free",
                "seed_time": 24.56,
            },
            {
                "swimmer": "Brown",
                "team": "Trinity",
                "event": "100 Free",
                "seed_time": 53.21,
            },
            {
                "swimmer": "Wilson",
                "team": "Oakcrest",
                "event": "100 Free",
                "seed_time": 54.00,
            },
        ]

    def test_pipeline_instantiation(self, pipeline):
        """Test pipeline instantiation."""
        assert pipeline.meet_type == MeetType.CONFERENCE_CHAMPIONSHIP

    def test_pipeline_validation_valid(self, pipeline, sample_entries):
        """Test validation with valid entries."""
        data = ChampionshipInput(entries=sample_entries, target_team="Seton")
        result = pipeline.validate_input(data)
        assert result.valid is True

    def test_pipeline_validation_empty(self, pipeline):
        """Test validation with empty entries."""
        data = ChampionshipInput(entries=[], target_team="Seton")
        result = pipeline.validate_input(data)
        assert result.valid is False

    def test_projection(self, pipeline, sample_entries):
        """Test standings projection."""
        projection = pipeline.project_only(sample_entries, "Seton")

        assert projection.meet_name == "Championship"
        assert len(projection.standings) >= 1
        assert projection.target_team_total > 0


class TestPointProjectionService:
    """Tests for point projection service."""

    @pytest.fixture
    def service(self):
        return PointProjectionService("vcac_championship")

    @pytest.fixture
    def sample_entries(self):
        return [
            {
                "swimmer": "Fast",
                "team": "Seton",
                "event": "100 Free",
                "seed_time": 50.0,
            },
            {
                "swimmer": "Medium",
                "team": "Seton",
                "event": "100 Free",
                "seed_time": 52.0,
            },
            {
                "swimmer": "Slow",
                "team": "Trinity",
                "event": "100 Free",
                "seed_time": 54.0,
            },
            {
                "swimmer": "Slowest",
                "team": "Oakcrest",
                "event": "100 Free",
                "seed_time": 56.0,
            },
        ]

    def test_project_standings(self, service, sample_entries):
        """Test projection produces standings."""
        result = service.project_standings(sample_entries, "Seton")

        assert result.target_team == "Seton"
        assert len(result.standings) >= 1
        assert result.target_team_total > 0

    def test_swing_events_identified(self, service, sample_entries):
        """Test swing events are identified."""
        result = service.project_standings(sample_entries, "Seton")

        # Swing events should be identified for swimmers with improvement potential
        # This depends on the data configuration
        assert isinstance(result.swing_events, list)

    def test_event_projection(self, service, sample_entries):
        """Test single event projection."""
        result = service.project_event("100 Free", sample_entries)

        assert result.event == "100 Free"
        assert len(result.entries) == 4
        assert result.entries[0].swimmer == "Fast"  # Fastest swimmer
        assert result.entries[0].predicted_place == 1


class TestValidationResult:
    """Tests for ValidationResult class."""

    def test_add_error(self):
        """Test adding errors."""
        result = ValidationResult(valid=True)
        result.add_error("Test error")

        assert result.valid is False
        assert "Test error" in result.errors

    def test_add_warning(self):
        """Test adding warnings."""
        result = ValidationResult(valid=True)
        result.add_warning("Test warning")

        assert result.valid is True  # Warnings don't affect validity
        assert "Test warning" in result.warnings

    def test_merge(self):
        """Test merging results."""
        result1 = ValidationResult(valid=True, errors=[], warnings=["w1"])
        result2 = ValidationResult(valid=False, errors=["e1"], warnings=["w2"])

        merged = result1.merge(result2)

        assert merged.valid is False
        assert "e1" in merged.errors
        assert "w1" in merged.warnings
        assert "w2" in merged.warnings


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
