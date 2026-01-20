"""
Integration Tests for AquaForge API

These tests verify the full integration between the API and backend services.
They go beyond unit tests to ensure the complete flow works correctly.

Run with: pytest tests/test_api_integration.py -v
"""

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """Create test client for API."""
    from swim_ai_reflex.backend.api.main import api_app

    return TestClient(api_app)


@pytest.fixture
def realistic_seton_data():
    """Realistic Seton team data for integration testing."""
    return [
        # Swimmer 1 - Versatile
        {"swimmer": "Michael Chen", "event": "200 Medley Relay", "time": "1:42.50"},
        {"swimmer": "Michael Chen", "event": "50 Freestyle", "time": "22.34"},
        {"swimmer": "Michael Chen", "event": "100 Freestyle", "time": "49.12"},
        {"swimmer": "Michael Chen", "event": "100 Butterfly", "time": "54.78"},
        # Swimmer 2 - Distance
        {"swimmer": "James Wilson", "event": "200 Freestyle", "time": "1:48.90"},
        {"swimmer": "James Wilson", "event": "500 Freestyle", "time": "4:52.30"},
        {"swimmer": "James Wilson", "event": "200 IM", "time": "2:05.45"},
        # Swimmer 3 - Sprint
        {"swimmer": "David Lee", "event": "50 Freestyle", "time": "21.89"},
        {"swimmer": "David Lee", "event": "100 Freestyle", "time": "47.56"},
        {"swimmer": "David Lee", "event": "200 Freestyle Relay", "time": "1:32.00"},
        # Swimmer 4 - Stroke
        {"swimmer": "Ryan Park", "event": "100 Backstroke", "time": "56.23"},
        {"swimmer": "Ryan Park", "event": "100 Breaststroke", "time": "1:02.45"},
        {"swimmer": "Ryan Park", "event": "200 IM", "time": "2:08.90"},
        # Swimmer 5 - Breaststroke specialist
        {"swimmer": "Kevin Tran", "event": "100 Breaststroke", "time": "1:00.12"},
        {"swimmer": "Kevin Tran", "event": "200 IM", "time": "2:10.34"},
        # Swimmer 6 - Fly specialist
        {"swimmer": "Alex Kim", "event": "100 Butterfly", "time": "53.45"},
        {"swimmer": "Alex Kim", "event": "200 IM", "time": "2:07.89"},
    ]


@pytest.fixture
def realistic_opponent_data():
    """Realistic opponent team data for integration testing."""
    return [
        # Opponent swimmers with competitive times
        {"swimmer": "Tom Anderson", "event": "50 Freestyle", "time": "22.10"},
        {"swimmer": "Tom Anderson", "event": "100 Freestyle", "time": "48.45"},
        {"swimmer": "Tom Anderson", "event": "100 Butterfly", "time": "55.12"},
        {"swimmer": "Jake Martinez", "event": "200 Freestyle", "time": "1:50.23"},
        {"swimmer": "Jake Martinez", "event": "500 Freestyle", "time": "4:55.67"},
        {"swimmer": "Chris Brown", "event": "100 Backstroke", "time": "57.89"},
        {"swimmer": "Chris Brown", "event": "200 IM", "time": "2:09.45"},
        {"swimmer": "Nick Taylor", "event": "100 Breaststroke", "time": "1:03.78"},
        {"swimmer": "Nick Taylor", "event": "200 IM", "time": "2:12.34"},
        {"swimmer": "Matt Garcia", "event": "50 Freestyle", "time": "23.45"},
        {"swimmer": "Matt Garcia", "event": "100 Freestyle", "time": "50.12"},
    ]


class TestOptimizationIntegration:
    """Full integration tests for the optimization endpoint."""

    @pytest.mark.timeout(60)
    @pytest.mark.slow
    def test_full_optimization_flow(
        self, client, realistic_seton_data, realistic_opponent_data
    ):
        """Test complete optimization from data to results."""
        # Step 1: Preview the optimization
        preview_response = client.post(
            "/api/v1/optimize/preview",
            json={
                "seton_data": realistic_seton_data,
                "opponent_data": realistic_opponent_data,
                "optimizer_backend": "heuristic",
            },
        )
        assert preview_response.status_code == 200
        preview = preview_response.json()
        assert preview["valid"]
        assert preview["seton"]["swimmer_count"] == 6
        assert preview["opponent"]["swimmer_count"] == 5

        # Step 2: Run the actual optimization
        optimize_response = client.post(
            "/api/v1/optimize",
            json={
                "seton_data": realistic_seton_data,
                "opponent_data": realistic_opponent_data,
                "optimizer_backend": "heuristic",
                "max_individual_events": 4,
                "enforce_fatigue": True,
            },
        )
        assert optimize_response.status_code == 200
        result = optimize_response.json()

        # Verify structure
        assert result["success"]
        assert "seton_score" in result
        assert "opponent_score" in result
        assert "results" in result
        assert "optimization_time_ms" in result

        # Scores should be reasonable
        assert result["seton_score"] >= 0
        assert result["opponent_score"] >= 0

    @pytest.mark.timeout(60)
    @pytest.mark.slow
    def test_optimization_with_export(
        self, client, realistic_seton_data, realistic_opponent_data
    ):
        """Test optimization followed by export."""
        # Run optimization
        opt_response = client.post(
            "/api/v1/optimize",
            json={
                "seton_data": realistic_seton_data,
                "opponent_data": realistic_opponent_data,
            },
        )
        assert opt_response.status_code == 200
        opt_result = opt_response.json()

        # Export as CSV - this returns a direct file response, not JSON
        export_response = client.post(
            "/api/v1/export",
            json={
                "format": "csv",
                "optimization_results": {"details": opt_result.get("results", [])},
                "seton_score": opt_result["seton_score"],
                "opponent_score": opt_result["opponent_score"],
            },
        )
        assert export_response.status_code == 200
        # CSV export returns direct file content, not JSON
        content_type = export_response.headers.get("content-type", "")
        assert "text/csv" in content_type or "application/json" in content_type
        # Verify we got some content
        assert len(export_response.content) > 0

    @pytest.mark.timeout(60)
    @pytest.mark.slow
    def test_optimization_analytics_flow(
        self, client, realistic_seton_data, realistic_opponent_data
    ):
        """Test optimization with analytics."""
        # Analyze depth before optimization
        depth_response = client.post(
            "/api/v1/analytics/depth", json=realistic_seton_data
        )
        assert depth_response.status_code == 200
        depth = depth_response.json()
        assert depth["total_swimmers"] == 6

        # Compare teams
        compare_response = client.post(
            "/api/v1/analytics/compare",
            json={
                "seton_data": realistic_seton_data,
                "opponent_data": realistic_opponent_data,
            },
        )
        assert compare_response.status_code == 200


class TestDataIntegration:
    """Integration tests for data handling."""

    def test_submit_and_validate_team(self, client):
        """Test submitting team data and validating it."""
        team_data = {
            "team_name": "Test Team",
            "team_type": "seton",
            "entries": [
                {"swimmer": "Test Swimmer", "event": "50 Freestyle", "time": "25.00"},
                {"swimmer": "Test Swimmer", "event": "100 Freestyle", "time": "55.00"},
            ],
        }

        response = client.post("/api/v1/data/team", json=team_data)
        assert response.status_code == 200
        result = response.json()

        assert result["success"]
        assert result["team_name"] == "Test Team"
        assert result["swimmer_count"] == 1
        assert result["entry_count"] == 2
        assert "50 Freestyle" in result["events"]


class TestAPIClient:
    """Tests for the API client module."""

    def test_client_import(self):
        """Verify the API client can be imported."""
        from swim_ai_reflex.backend.api.client import AquaForgeClient

        assert AquaForgeClient is not None

    def test_client_instantiation(self):
        """Verify the client can be instantiated."""
        from swim_ai_reflex.backend.api.client import AquaForgeClient

        client = AquaForgeClient("http://localhost:8001")
        assert client.base_url == "http://localhost:8001"


class TestErrorHandling:
    """Test error handling in the API."""

    def test_empty_data_returns_error(self, client):
        """Empty data should return appropriate error."""
        response = client.post(
            "/api/v1/optimize",
            json={
                "seton_data": [],
                "opponent_data": [],
            },
        )
        assert response.status_code == 400

    def test_invalid_team_type(self, client):
        """Invalid team type should return error."""
        response = client.post(
            "/api/v1/data/team",
            json={"team_name": "Test", "team_type": "invalid", "entries": []},
        )
        assert response.status_code == 422  # Validation error

    def test_invalid_export_format(self, client):
        """Invalid export format should return error."""
        response = client.post(
            "/api/v1/export",
            json={
                "format": "invalid_format",
                "optimization_results": {},
            },
        )
        assert response.status_code == 422  # Validation error


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
