"""
Tests for Entry Schema Normalization

Tests all edge cases for column name variations, team codes, gender,
time formats, and validation.
"""

import pytest

from swim_ai_reflex.backend.services.shared.entry_schema import (
    StandardEntry,
    find_column_value,
    normalize_entry_dict,
    normalize_gender,
    normalize_grade,
    normalize_team_code,
    validate_entry,
)


class TestColumnNameVariations:
    """Test that various column name formats are correctly mapped."""

    def test_vcac_json_format(self):
        """VCAC JSON uses swimmer_name, team_code, seed_time."""
        entry = {
            "swimmer_name": "John Smith",
            "team_code": "SST",
            "event": "50 Free",
            "seed_time": 23.45,
            "gender": "M",
        }
        result = normalize_entry_dict(entry)
        assert result["swimmer"] == "John Smith"
        assert result["team"] == "SST"
        assert result["time"] == 23.45

    def test_csv_format(self):
        """CSV uses swimmer, team, time."""
        entry = {
            "swimmer": "Jane Doe",
            "team": "Trinity Christian",
            "event": "100 Free",
            "time": "1:02.34",
        }
        result = normalize_entry_dict(entry)
        assert result["swimmer"] == "Jane Doe"
        assert result["team"] == "TCS"
        assert result["time"] == 62.34

    def test_swimcloud_format(self):
        """SwimCloud uses athlete_name, school, best_time."""
        entry = {
            "athlete_name": "Bob Wilson",
            "school": "Oakcrest",
            "event_name": "200 IM",
            "best_time": 150.5,
        }
        result = normalize_entry_dict(entry)
        assert result["swimmer"] == "Bob Wilson"
        assert result["team"] == "OAK"
        assert result["time"] == 150.5

    def test_mixed_capitalization(self):
        """Column names with mixed case should still work."""
        entry = {
            "SWIMMER": "Mary Johnson",
            "Team_Code": "ics",
            "Event": "100 Back",
            "Time": 58.9,
        }
        result = normalize_entry_dict(entry)
        assert result["swimmer"] == "Mary Johnson"
        assert result["team"] == "ICS"


class TestTeamCodeNormalization:
    """Test team code standardization."""

    def test_three_letter_codes(self):
        """Standard codes should pass through unchanged."""
        assert normalize_team_code("SST") == "SST"
        assert normalize_team_code("TCS") == "TCS"
        assert normalize_team_code("ICS") == "ICS"

    def test_lowercase_codes(self):
        """Lowercase codes should be uppercased."""
        assert normalize_team_code("sst") == "SST"
        assert normalize_team_code("tcs") == "TCS"

    def test_full_team_names(self):
        """Full team names should map to codes."""
        assert normalize_team_code("Seton") == "SST"
        assert normalize_team_code("Seton Swimming") == "SST"
        assert normalize_team_code("Trinity Christian School") == "TCS"
        assert normalize_team_code("Immanuel Christian High School") == "ICS"
        assert normalize_team_code("Bishop O'Connell") == "DJO"

    def test_partial_matches(self):
        """Partial team names should still match."""
        assert normalize_team_code("seton school") == "SST"
        assert normalize_team_code("trinity") == "TCS"
        assert normalize_team_code("immanuel") == "ICS"

    def test_unknown_team(self):
        """Unknown teams should return truncated uppercase."""
        result = normalize_team_code("Unknown Team Name")
        assert result == "UNKN"


class TestGenderNormalization:
    """Test gender value standardization."""

    def test_standard_codes(self):
        """Standard M/F codes."""
        assert normalize_gender("M") == "M"
        assert normalize_gender("F") == "F"

    def test_lowercase(self):
        """Lowercase m/f."""
        assert normalize_gender("m") == "M"
        assert normalize_gender("f") == "F"

    def test_full_words(self):
        """Full gender words."""
        assert normalize_gender("Male") == "M"
        assert normalize_gender("female") == "F"

    def test_boys_girls(self):
        """Boys/Girls format."""
        assert normalize_gender("Boys") == "M"
        assert normalize_gender("girls") == "F"

    def test_empty(self):
        """Empty string returns empty."""
        assert normalize_gender("") == ""


class TestGradeNormalization:
    """Test grade value standardization."""

    def test_integer_grades(self):
        """Integer grades."""
        assert normalize_grade(9) == 9
        assert normalize_grade(12) == 12

    def test_string_grades(self):
        """String grades with suffixes."""
        assert normalize_grade("9th") == 9
        assert normalize_grade("12") == 12

    def test_grade_names(self):
        """Named grades."""
        assert normalize_grade("freshman") == 9
        assert normalize_grade("Senior") == 12
        assert normalize_grade("Jr") == 11

    def test_out_of_range(self):
        """Out of range grades return None."""
        assert normalize_grade(5) is None
        assert normalize_grade(13) is None

    def test_none(self):
        """None input returns None."""
        assert normalize_grade(None) is None


class TestEventGenderPreservation:
    """Test that gender is correctly extracted and preserved in events."""

    def test_gender_from_event_prefix(self):
        """Gender should be extracted from event prefix."""
        entry = {
            "swimmer": "John",
            "team": "SST",
            "event": "Boys 100 Free",
            "time": 50.0,
        }
        result = normalize_entry_dict(entry)
        assert result["gender"] == "M"
        assert "Boys" in result["event"]

    def test_gender_from_data_field(self):
        """Gender from data field should be added to event."""
        entry = {
            "swimmer": "Jane",
            "team": "SST",
            "event": "100 Free",
            "time": 50.0,
            "gender": "F",
        }
        result = normalize_entry_dict(entry)
        assert result["gender"] == "F"
        assert "Girls" in result["event"]

    def test_m_f_prefix_conversion(self):
        """M/F prefixes should become Boys/Girls."""
        entry = {"swimmer": "John", "team": "SST", "event": "M 50 Free", "time": 23.0}
        result = normalize_entry_dict(entry)
        assert result["event"] == "Boys 50 Free"


class TestTimeNormalization:
    """Test time format handling."""

    def test_float_time(self):
        """Float times pass through."""
        entry = {"swimmer": "John", "team": "SST", "event": "50 Free", "time": 23.45}
        result = normalize_entry_dict(entry)
        assert result["time"] == 23.45

    def test_string_float_time(self):
        """String float times are converted."""
        entry = {"swimmer": "John", "team": "SST", "event": "50 Free", "time": "23.45"}
        result = normalize_entry_dict(entry)
        assert result["time"] == 23.45

    def test_mm_ss_format(self):
        """MM:SS.ss format is converted to seconds."""
        entry = {
            "swimmer": "John",
            "team": "SST",
            "event": "200 Free",
            "time": "1:52.34",
        }
        result = normalize_entry_dict(entry)
        assert abs(result["time"] - 112.34) < 0.01

    def test_nt_time(self):
        """NT (no time) becomes infinity."""
        entry = {"swimmer": "John", "team": "SST", "event": "50 Free", "time": "NT"}
        result = normalize_entry_dict(entry)
        assert result["time"] == float("inf")

    def test_dq_time(self):
        """DQ becomes infinity."""
        entry = {"swimmer": "John", "team": "SST", "event": "50 Free", "time": "DQ"}
        result = normalize_entry_dict(entry)
        assert result["time"] == float("inf")


class TestValidation:
    """Test entry validation."""

    def test_valid_entry(self):
        """Complete valid entry passes validation."""
        entry = {"swimmer": "John", "team": "SST", "event": "50 Free", "time": 23.5}
        normalized = normalize_entry_dict(entry)
        result = validate_entry(normalized)
        assert result.is_valid
        assert len(result.errors) == 0

    def test_missing_swimmer(self):
        """Missing swimmer fails validation."""
        entry = {"swimmer": "", "team": "SST", "event": "50 Free", "time": 23.5}
        normalized = normalize_entry_dict(entry)
        result = validate_entry(normalized)
        assert not result.is_valid
        assert any("swimmer" in e.lower() for e in result.errors)

    def test_missing_team(self):
        """Missing team fails validation."""
        entry = {"swimmer": "John", "team": "", "event": "50 Free", "time": 23.5}
        normalized = normalize_entry_dict(entry)
        result = validate_entry(normalized)
        assert not result.is_valid
        assert any("team" in e.lower() for e in result.errors)

    def test_missing_time_warning(self):
        """Missing time generates warning but still valid."""
        entry = {"swimmer": "John", "team": "SST", "event": "50 Free", "time": None}
        normalized = normalize_entry_dict(entry)
        result = validate_entry(normalized)
        # Still valid (can participate, just no seed time)
        assert result.is_valid
        assert any("time" in w.lower() for w in result.warnings)

    def test_fast_time_warning(self):
        """Unusually fast time generates warning."""
        entry = {"swimmer": "John", "team": "SST", "event": "50 Free", "time": 5.0}
        normalized = normalize_entry_dict(entry)
        result = validate_entry(normalized)
        assert result.is_valid
        assert any("fast" in w.lower() for w in result.warnings)


class TestStandardEntry:
    """Test StandardEntry dataclass."""

    def test_from_dict(self):
        """Create StandardEntry from dictionary."""
        data = {
            "swimmer_name": "John Smith",
            "team_code": "SST",
            "event": "50 Free",
            "seed_time": 23.45,
            "gender": "M",
        }
        entry = StandardEntry.from_dict(data)
        assert entry.swimmer == "John Smith"
        assert entry.team == "SST"
        assert entry.time == 23.45

    def test_to_dict(self):
        """Convert StandardEntry to dictionary."""
        entry = StandardEntry(
            swimmer="John Smith",
            team="SST",
            event="Boys 50 Free",
            time=23.45,
            gender="M",
        )
        result = entry.to_dict()
        assert result["swimmer"] == "John Smith"
        assert result["team"] == "SST"
        assert result["time"] == 23.45


class TestFindColumnValue:
    """Test flexible column value lookup."""

    def test_exact_match(self):
        """Exact column name match."""
        data = {"swimmer": "John"}
        assert find_column_value(data, "swimmer") == "John"

    def test_alias_match(self):
        """Alias column name match."""
        data = {"swimmer_name": "John"}
        assert find_column_value(data, "swimmer") == "John"

    def test_case_insensitive(self):
        """Case-insensitive column match."""
        data = {"SWIMMER": "John"}
        assert find_column_value(data, "swimmer") == "John"

    def test_underscore_space_match(self):
        """Underscore/space variations match."""
        data = {"swimmer name": "John"}
        assert find_column_value(data, "swimmer") == "John"

    def test_default_value(self):
        """Default value when not found."""
        data = {"other": "value"}
        assert find_column_value(data, "swimmer", "Unknown") == "Unknown"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
