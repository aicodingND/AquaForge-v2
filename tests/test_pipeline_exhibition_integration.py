"""
Integration test for Championship Pipeline Exhibition Stage.

Verifies that the ExhibitionDeploymentAnalyzer is correctly integrated
into the pipeline and returns expected results.
"""

from unittest.mock import MagicMock, patch

import pytest

from swim_ai_reflex.backend.pipelines.championship import (
    ChampionshipInput,
    create_championship_pipeline,
)


@pytest.fixture
def mock_analyzer():
    """Mock the exhibition analyzer."""
    # Patch the class in its module of origin, since it's imported locally
    with patch(
        "swim_ai_reflex.backend.core.exhibition_strategy.ExhibitionDeploymentAnalyzer"
    ) as MockAnalyzer:
        mock_instance = MockAnalyzer.return_value

        # Mock result structure
        mock_result = MagicMock()
        mock_result.recommended_assignments = {"John Smith": ["Boys 50 Free"]}
        mock_result.total_points_denied = 12.0
        mock_result.summary = "Test deployment"

        mock_opportunity = MagicMock()
        mock_opportunity.swimmer = "John Smith"
        mock_opportunity.event = "Boys 50 Free"
        mock_opportunity.opponent_displaced = "Bob"
        mock_opportunity.points_denied = 2.0
        mock_opportunity.explanation = "Displaced Bob"
        mock_result.opportunities = [mock_opportunity]

        mock_instance.analyze_deployment.return_value = mock_result
        yield MockAnalyzer


def test_pipeline_exhibition_stage_runs(mock_analyzer):
    """Verify exhibition stage runs when requested."""
    pipeline = create_championship_pipeline()

    # Input data
    entries = [
        {
            "swimmer": "John Smith",
            "team": "SST",
            "event": "Boys 50 Free",
            "seed_time": 25.0,
            "grade": 7,
        },
        {"swimmer": "Bob", "team": "Other", "event": "Boys 50 Free", "seed_time": 26.0},
    ]

    data = ChampionshipInput(entries=entries, target_team="SST")

    # Mock projection service to avoid unrelated errors
    pipeline.projection_service = MagicMock()

    # Create a mock projection result with real numbers that can be formatted
    mock_projection = MagicMock()
    mock_projection.target_team_rank = 1
    mock_projection.target_team_total = 100.0
    mock_projection.standings = [("SST", 100.0), ("Other", 80.0)]
    mock_projection.swing_events = []
    # Add to_dict method
    mock_projection.to_dict.return_value = {
        "standings": [("SST", 100.0), ("Other", 80.0)],
        "target_team_total": 100.0,
        "target_team_rank": 1,
        "swing_events": [],
    }

    pipeline.projection_service.project_standings.return_value = mock_projection

    # Run pipeline with exhibition stage
    result = pipeline.run(data, stage="exhibition")

    # Check if analyzer was called
    assert mock_analyzer.called
    assert mock_analyzer.return_value.analyze_deployment.called

    # Check result structure
    assert result.exhibition_strategy is not None
    assert result.exhibition_strategy["status"] == "success"
    assert result.exhibition_strategy["total_points_denied"] == 12.0


def test_pipeline_skips_exhibition_by_default(mock_analyzer):
    """Verify exhibition stage is skipped if not requested."""
    pipeline = create_championship_pipeline()

    # Input data
    entries = [{"swimmer": "John", "team": "SST", "event": "50 Free"}]
    data = ChampionshipInput(entries=entries)

    # Mock services
    pipeline.projection_service = MagicMock()
    mock_projection = MagicMock()
    mock_projection.target_team_rank = 1
    mock_projection.target_team_total = 100.0
    mock_projection.standings = [("SST", 100.0)]
    mock_projection.swing_events = []
    mock_projection.to_dict.return_value = {
        "standings": [],
        "target_team_total": 100.0,
        "target_team_rank": 1,
        "swing_events": [],
    }

    pipeline.projection_service.project_standings.return_value = mock_projection

    # Run pipeline without exhibition stage (default is full, but we'll specify projection)
    result = pipeline.run(data, stage="projection")

    # Analyzer should NOT be called
    assert not mock_analyzer.called
    assert result.exhibition_strategy is None
