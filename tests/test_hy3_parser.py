"""
Tests for HY3 file parser adapter.

Tests the adapter layer that converts hytek-parser output into
AquaForge's standard DataFrame format.
"""

from unittest.mock import MagicMock, patch

import pytest

from swim_ai_reflex.backend.core.hy3_parser import (
    _age_to_grade,
    _best_time,
    _format_event_name,
    parse_hy3_file,
)

# ── Unit Tests: Helper Functions ──────────────────────────────────────────


class TestFormatEventName:
    """Test event name formatting from HyTek fields."""

    def test_individual_freestyle(self):
        assert _format_event_name(200, "FREESTYLE", False, "FEMALE") == "Girls 200 Free"

    def test_individual_backstroke(self):
        assert _format_event_name(100, "BACKSTROKE", False, "MALE") == "Boys 100 Back"

    def test_individual_breaststroke(self):
        assert (
            _format_event_name(100, "BREASTSTROKE", False, "FEMALE")
            == "Girls 100 Breast"
        )

    def test_individual_butterfly(self):
        assert _format_event_name(100, "BUTTERFLY", False, "MALE") == "Boys 100 Fly"

    def test_individual_im(self):
        assert _format_event_name(200, "MEDLEY", False, "FEMALE") == "Girls 200 IM"

    def test_relay_medley(self):
        assert (
            _format_event_name(200, "MEDLEY", True, "MALE") == "Boys 200 Medley Relay"
        )

    def test_relay_free(self):
        assert (
            _format_event_name(200, "FREESTYLE", True, "FEMALE")
            == "Girls 200 Free Relay"
        )

    def test_400_free_relay(self):
        assert (
            _format_event_name(400, "FREESTYLE", True, "MALE") == "Boys 400 Free Relay"
        )

    def test_no_gender(self):
        assert _format_event_name(50, "FREESTYLE", False, "UNKNOWN") == "50 Free"

    def test_500_free(self):
        assert _format_event_name(500, "FREESTYLE", False, "FEMALE") == "Girls 500 Free"


class TestAgeToGrade:
    """Test age → grade estimation."""

    def test_age_14_is_grade_9(self):
        assert _age_to_grade(14) == 9

    def test_age_15_is_grade_10(self):
        assert _age_to_grade(15) == 10

    def test_age_16_is_grade_11(self):
        assert _age_to_grade(16) == 11

    def test_age_17_is_grade_12(self):
        assert _age_to_grade(17) == 12

    def test_age_18_is_grade_12(self):
        assert _age_to_grade(18) == 12

    def test_age_13_is_grade_8(self):
        assert _age_to_grade(13) == 8

    def test_age_under_12_is_none(self):
        assert _age_to_grade(11) is None

    def test_none_is_none(self):
        assert _age_to_grade(None) is None


class TestBestTime:
    """Test time extraction priority."""

    def test_finals_preferred(self):
        entry = MagicMock()
        entry.finals_time = 25.5
        entry.prelim_time = 26.0
        entry.seed_time = 27.0
        assert _best_time(entry) == 25.5

    def test_prelim_when_no_finals(self):
        entry = MagicMock()
        entry.finals_time = None
        entry.prelim_time = 26.0
        entry.seed_time = 27.0
        assert _best_time(entry) == 26.0

    def test_seed_when_no_results(self):
        entry = MagicMock()
        entry.finals_time = None
        entry.prelim_time = None
        entry.seed_time = 27.0
        assert _best_time(entry) == 27.0

    def test_none_when_all_none(self):
        entry = MagicMock()
        entry.finals_time = None
        entry.prelim_time = None
        entry.seed_time = None
        assert _best_time(entry) is None

    def test_skips_non_numeric_codes(self):
        """Non-numeric time codes (NT, NS, DQ) should be skipped."""
        entry = MagicMock()
        # Simulate a ReplacedTimeTimeCode enum value
        entry.finals_time = None
        entry.prelim_time = "NT"  # Not a float
        entry.seed_time = 28.5
        assert _best_time(entry) == 28.5


# ── Integration Test: Full Parser ─────────────────────────────────────────


class TestParseHy3File:
    """Test the full parse pipeline with mocked hytek-parser."""

    def test_file_not_found(self):
        with pytest.raises(FileNotFoundError):
            parse_hy3_file("/nonexistent/file.hy3")

    @patch("hytek_parser.parse_hy3")
    def test_parses_individual_entries(self, mock_parse, tmp_path):
        """Mock hytek-parser output and verify DataFrame construction."""
        # Create a temp file so the exists() check passes
        hy3_file = tmp_path / "test.hy3"
        hy3_file.write_text("A1dummy")

        # Build mock parsed file structure
        mock_swimmer = MagicMock()
        mock_swimmer.first_name = "Jane"
        mock_swimmer.last_name = "Smith"
        mock_swimmer.team_code = "SST"
        mock_swimmer.age = 16
        mock_swimmer.gender = MagicMock()
        mock_swimmer.gender.name = "FEMALE"

        mock_entry = MagicMock()
        mock_entry.swimmers = [mock_swimmer]
        mock_entry.finals_time = 62.5
        mock_entry.prelim_time = None
        mock_entry.seed_time = 63.0

        mock_stroke = MagicMock()
        mock_stroke.name = "BACKSTROKE"
        mock_gender = MagicMock()
        mock_gender.name = "FEMALE"

        mock_event = MagicMock()
        mock_event.distance = 100
        mock_event.stroke = mock_stroke
        mock_event.gender = mock_gender
        mock_event.relay = False
        mock_event.entries = [mock_entry]

        mock_team = MagicMock()
        mock_team.short_name = "Seton"

        mock_meet = MagicMock()
        mock_meet.events = {"1": mock_event}
        mock_meet.teams = {"SST": mock_team}

        mock_parsed = MagicMock()
        mock_parsed.meet = mock_meet

        mock_parse.return_value = mock_parsed

        # Run parser
        df = parse_hy3_file(str(hy3_file))

        assert len(df) == 1
        row = df.iloc[0]
        assert row["swimmer"] == "Jane Smith"
        assert row["event"] == "Girls 100 Back"
        assert row["time"] == 62.5  # Finals time preferred
        assert row["team"] == "Seton"
        assert row["grade"] == 11  # Age 16 → grade 11
        assert row["gender"] == "F"
        assert not row["is_relay"]

    @patch("hytek_parser.parse_hy3")
    def test_deduplicates_keeping_fastest(self, mock_parse, tmp_path):
        """When same swimmer has multiple entries for same event, keep fastest."""
        hy3_file = tmp_path / "test.hy3"
        hy3_file.write_text("A1dummy")

        mock_swimmer = MagicMock()
        mock_swimmer.first_name = "Alice"
        mock_swimmer.last_name = "Jones"
        mock_swimmer.team_code = "TCS"
        mock_swimmer.age = 15
        mock_swimmer.gender = MagicMock()
        mock_swimmer.gender.name = "FEMALE"

        # Two entries for same event
        mock_entry1 = MagicMock()
        mock_entry1.swimmers = [mock_swimmer]
        mock_entry1.finals_time = 28.0
        mock_entry1.prelim_time = None
        mock_entry1.seed_time = 30.0

        mock_entry2 = MagicMock()
        mock_entry2.swimmers = [mock_swimmer]
        mock_entry2.finals_time = 27.5  # Faster
        mock_entry2.prelim_time = None
        mock_entry2.seed_time = 29.0

        mock_stroke = MagicMock()
        mock_stroke.name = "FREESTYLE"
        mock_gender = MagicMock()
        mock_gender.name = "FEMALE"

        mock_event = MagicMock()
        mock_event.distance = 50
        mock_event.stroke = mock_stroke
        mock_event.gender = mock_gender
        mock_event.relay = False
        mock_event.entries = [mock_entry1, mock_entry2]

        mock_team = MagicMock()
        mock_team.short_name = "Trinity"

        mock_meet = MagicMock()
        mock_meet.events = {"3": mock_event}
        mock_meet.teams = {"TCS": mock_team}

        mock_parsed = MagicMock()
        mock_parsed.meet = mock_meet

        mock_parse.return_value = mock_parsed

        df = parse_hy3_file(str(hy3_file))

        # Should deduplicate to 1 entry with fastest time
        assert len(df) == 1
        assert df.iloc[0]["time"] == 27.5

    @patch("hytek_parser.parse_hy3")
    def test_relay_entries(self, mock_parse, tmp_path):
        """Relay entries should have composite swimmer name."""
        hy3_file = tmp_path / "test.hy3"
        hy3_file.write_text("A1dummy")

        swimmers = []
        for name in ["Alice", "Beth", "Carol", "Diana"]:
            s = MagicMock()
            s.first_name = name
            s.last_name = "Test"
            s.team_code = "SST"
            s.age = 16
            s.gender = MagicMock()
            s.gender.name = "FEMALE"
            swimmers.append(s)

        mock_entry = MagicMock()
        mock_entry.swimmers = swimmers
        mock_entry.finals_time = 112.0
        mock_entry.prelim_time = None
        mock_entry.seed_time = 115.0

        mock_stroke = MagicMock()
        mock_stroke.name = "MEDLEY"
        mock_gender = MagicMock()
        mock_gender.name = "FEMALE"

        mock_event = MagicMock()
        mock_event.distance = 200
        mock_event.stroke = mock_stroke
        mock_event.gender = mock_gender
        mock_event.relay = True
        mock_event.entries = [mock_entry]

        mock_team = MagicMock()
        mock_team.short_name = "Seton"

        mock_meet = MagicMock()
        mock_meet.events = {"1": mock_event}
        mock_meet.teams = {"SST": mock_team}

        mock_parsed = MagicMock()
        mock_parsed.meet = mock_meet

        mock_parse.return_value = mock_parsed

        df = parse_hy3_file(str(hy3_file))

        assert len(df) == 1
        row = df.iloc[0]
        assert row["swimmer"] == "Seton Relay"
        assert row["event"] == "Girls 200 Medley Relay"
        assert row["is_relay"]
        assert row["time"] == 112.0


# ── Upload Pipeline Integration ───────────────────────────────────────────


class TestHy3UploadPipeline:
    """Test that .hy3 files are accepted by the upload infrastructure."""

    def test_hy3_in_allowed_extensions(self):
        """Verify .hy3 is in the data router's allowed list."""

        # The router code has: allowed_extensions = [".xlsx", ".xls", ".csv", ".json", ".hy3"]
        # We verify by importing and checking the module source
        import inspect

        from swim_ai_reflex.backend.api.routers import data

        source = inspect.getsource(data.upload_team_file)
        assert ".hy3" in source
