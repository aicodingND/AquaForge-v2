"""
Tests for Data Layer - Entities, Loaders, and Service

Ensures data ingestion is accurate and production-ready for coaches.
"""

import pytest
from datetime import date
from pathlib import Path

from swim_ai_reflex.core.data.entities import (
    AthleteEntity,
    MeetEntity,
    SwimResultEntity,
    RelayResultEntity,
    VALID_GRADES,
    VALID_DISTANCES,
)


class TestEntityValidation:
    """Test Pydantic entity validation."""

    def test_athlete_entity_valid(self):
        """Test creating a valid athlete."""
        athlete = AthleteEntity(
            athlete_id=1,
            team_id=1,
            last_name="Smith",
            first_name="John",
            sex="M",
            grade="JR",
        )
        assert athlete.full_name == "John Smith"
        assert athlete.grade == "JR"

    def test_athlete_entity_grade_6_valid(self):
        """Test that grade 6 is recognized (middle schoolers)."""
        assert "6" in VALID_GRADES, (
            "Grade 6 must be in VALID_GRADES for middle schoolers"
        )

        athlete = AthleteEntity(
            athlete_id=2,
            team_id=1,
            last_name="Young",
            first_name="Emma",
            sex="F",
            grade="6",
        )
        assert athlete.grade == "6"

    def test_athlete_entity_all_grades_valid(self):
        """Test all expected grade values are valid."""
        expected_grades = {"6", "7", "8", "9", "10", "11", "12", "FR", "SO", "JR", "SR"}
        for grade in expected_grades:
            assert grade in VALID_GRADES, f"Grade {grade} should be valid"

    def test_athlete_empty_name_raises(self):
        """Test that empty names raise validation error."""
        with pytest.raises(ValueError):
            AthleteEntity(
                athlete_id=1,
                team_id=1,
                last_name="",
                first_name="John",
                sex="M",
            )

    def test_swim_result_valid(self):
        """Test creating a valid swim result."""
        result = SwimResultEntity.from_hundredths(
            meet_id=1,
            athlete_id=1,
            result_type="I",
            time_hundredths=2500,  # 25.00 seconds
            distance=50,
            stroke=1,  # Free
        )
        assert result.time_seconds == 25.0
        assert result.formatted_time == "25.00"
        assert result.event_name == "50 Free"

    def test_swim_result_long_time_format(self):
        """Test time formatting for swims over 1 minute."""
        result = SwimResultEntity.from_hundredths(
            meet_id=1,
            athlete_id=1,
            result_type="I",
            time_hundredths=12345,  # 2:03.45
            distance=200,
            stroke=1,
        )
        assert result.formatted_time == "2:03.45"

    def test_swim_result_invalid_distance_raises(self):
        """Test that invalid distances raise validation error."""
        with pytest.raises(ValueError, match="Invalid distance"):
            SwimResultEntity.from_hundredths(
                meet_id=1,
                athlete_id=1,
                result_type="I",
                time_hundredths=2500,
                distance=9991,  # Invalid (diving placeholder)
                stroke=1,
            )

    def test_swim_result_valid_distances(self):
        """Test all expected distances are valid."""
        expected = {25, 50, 100, 200, 400, 500, 800, 1000, 1500, 1650}
        assert VALID_DISTANCES == expected

    def test_meet_entity_valid(self):
        """Test creating a valid meet."""
        meet = MeetEntity(
            meet_id=1,
            name="VCAC Championship",
            start_date=date(2026, 2, 7),
            course="Y",
        )
        assert meet.season == "2025-2026"
        assert meet.course_name == "Yards"

    def test_meet_entity_course_codes(self):
        """Test all course codes work."""
        for code in ["Y", "S", "L"]:
            meet = MeetEntity(
                meet_id=1,
                name="Test Meet",
                start_date=date(2026, 1, 1),
                course=code,
            )
            assert meet.course == code

    def test_meet_entity_invalid_end_date_raises(self):
        """Test that end_date before start_date raises error."""
        with pytest.raises(ValueError, match="end_date cannot be before start_date"):
            MeetEntity(
                meet_id=1,
                name="Bad Meet",
                start_date=date(2026, 2, 7),
                end_date=date(2026, 2, 6),
                course="Y",
            )

    def test_relay_result_entity_valid(self):
        """Test creating a valid relay."""
        relay = RelayResultEntity(
            relay_id=1,
            meet_id=1,
            team_id=1,
            letter="A",
            sex="M",
            swimmers=[101, 102, 103, 104],
            distance=200,
            stroke=5,  # Medley
        )
        assert relay.event_name == "200 IM Relay"

    def test_relay_result_filters_zeros(self):
        """Test that zero athlete IDs are filtered out."""
        relay = RelayResultEntity(
            relay_id=1,
            meet_id=1,
            team_id=1,
            letter="A",
            sex="F",
            swimmers=[101, 102, 0, 103, 104, 0, 0, 0],
            distance=200,
            stroke=1,
        )
        assert relay.swimmers == [101, 102, 103, 104]

    def test_relay_incomplete_raises(self):
        """Test that relay with <4 swimmers raises error."""
        with pytest.raises(ValueError, match="at least 4 swimmers"):
            RelayResultEntity(
                relay_id=1,
                meet_id=1,
                team_id=1,
                letter="A",
                sex="M",
                swimmers=[101, 102, 103],  # Only 3
                distance=200,
                stroke=1,
            )


class TestCSVLoader:
    """Test CSV loader with real data."""

    @pytest.fixture
    def loader(self):
        """Create loader for real data."""
        from swim_ai_reflex.core.data.loaders.csv_loader import CSVLoader

        data_path = Path("data/real_exports/csv")
        if not data_path.exists():
            pytest.skip("Real CSV data not available")
        return CSVLoader(data_path)

    def test_load_teams(self, loader):
        """Test loading teams."""
        teams = loader.load_teams()
        assert len(teams) > 0

        # Find Seton
        seton = next((t for t in teams if t.code == "SST"), None)
        assert seton is not None
        assert seton.team_id == 1
        assert "Seton" in seton.name

    def test_load_athletes(self, loader):
        """Test loading athletes."""
        athletes = loader.load_athletes()
        assert len(athletes) > 1000, "Expected >1000 athletes"

        # Check active count
        active = [a for a in athletes if not a.inactive]
        assert len(active) > 500, "Expected >500 active athletes"

    def test_load_athletes_grade_6(self, loader):
        """Test that grade 6 athletes are properly loaded."""
        athletes = loader.load_athletes()
        grade_6 = [a for a in athletes if a.grade == "6"]
        assert len(grade_6) > 0, "Should have at least 1 grade 6 athlete"

    def test_load_meets_course_normalization(self, loader):
        """Test that course codes are normalized (YO -> Y)."""
        meets = loader.load_meets()

        # All courses should be valid
        for meet in meets:
            assert meet.course in ("Y", "S", "L"), f"Invalid course: {meet.course}"

        # Should have more than 300 meets (was 235 before fix)
        assert len(meets) > 300, f"Expected >300 meets, got {len(meets)}"

    def test_load_results_exhibition_flag(self, loader):
        """Test that exhibition flag is correctly parsed."""
        results = list(loader.load_results())

        exhibition_count = sum(1 for r in results if r.is_exhibition)
        total = len(results)

        # Exhibition should be ~20-25% of results
        exhibition_pct = exhibition_count / total * 100
        assert exhibition_pct < 30, f"Exhibition too high: {exhibition_pct:.1f}%"
        assert exhibition_pct > 10, f"Exhibition too low: {exhibition_pct:.1f}%"

    def test_load_results_filters_diving(self, loader):
        """Test that diving results (stroke 6, 7) are filtered."""
        results = list(loader.load_results())

        # All strokes should be 1-5
        for r in results:
            assert 1 <= r.stroke <= 5, f"Invalid stroke: {r.stroke}"

    def test_load_results_filters_invalid_distances(self, loader):
        """Test that invalid distances are filtered."""
        results = list(loader.load_results())

        # All distances should be valid
        for r in results:
            assert r.distance in VALID_DISTANCES, f"Invalid distance: {r.distance}"

    def test_load_relays(self, loader):
        """Test loading relays."""
        relays = list(loader.load_relays())
        assert len(relays) > 10000, "Expected >10000 relay records"

        # All relays should have 4+ swimmers
        for r in relays:
            assert len(r.swimmers) >= 4

    def test_validation_errors_logged(self, loader):
        """Test that validation errors are logged, not silently ignored."""
        # Load all data to trigger any errors
        loader.load_teams()
        loader.load_athletes()
        loader.load_meets()
        list(loader.load_results())

        # Some validation errors are expected (unusual distances, etc.)
        # But they should be logged
        assert hasattr(loader, "validation_errors")


class TestSwimDataService:
    """Test high-level data service."""

    @pytest.fixture
    def service(self):
        """Create data service."""
        from swim_ai_reflex.core.data.service import SwimDataService

        data_path = Path("data/real_exports/csv")
        if not data_path.exists():
            pytest.skip("Real CSV data not available")
        return SwimDataService.from_csv(data_path)

    @pytest.mark.asyncio
    async def test_get_current_roster(self, service):
        """Test getting current roster."""
        roster = await service.get_current_roster()
        assert len(roster) > 0

    @pytest.mark.asyncio
    async def test_get_summary(self, service):
        """Test getting data summary."""
        summary = await service.get_summary()
        assert "teams" in summary
        assert "athletes_total" in summary
        assert "athletes_active" in summary
        assert summary["athletes_active"] > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
