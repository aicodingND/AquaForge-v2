"""
API Test Suite

Tests for all FastAPI endpoints to ensure stability before migration.
Run with: pytest tests/test_api.py -v
"""

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """Create test client for API."""
    from swim_ai_reflex.backend.api.main import api_app

    return TestClient(api_app)


@pytest.fixture
def sample_seton_data():
    """Sample Seton team data for testing."""
    return [
        {"swimmer": "John Smith", "event": "50 Freestyle", "time": "23.45"},
        {"swimmer": "John Smith", "event": "100 Freestyle", "time": "51.23"},
        {"swimmer": "Mike Johnson", "event": "50 Freestyle", "time": "24.12"},
        {"swimmer": "Mike Johnson", "event": "100 Butterfly", "time": "58.90"},
        {"swimmer": "David Brown", "event": "200 IM", "time": "2:15.34"},
        {"swimmer": "David Brown", "event": "100 Breaststroke", "time": "1:08.45"},
    ]


@pytest.fixture
def sample_opponent_data():
    """Sample opponent team data for testing."""
    return [
        {"swimmer": "Tom Wilson", "event": "50 Freestyle", "time": "23.89"},
        {"swimmer": "Tom Wilson", "event": "100 Freestyle", "time": "52.10"},
        {"swimmer": "James Davis", "event": "50 Freestyle", "time": "24.50"},
        {"swimmer": "James Davis", "event": "100 Butterfly", "time": "59.20"},
        {"swimmer": "Robert Lee", "event": "200 IM", "time": "2:16.00"},
        {"swimmer": "Robert Lee", "event": "100 Breaststroke", "time": "1:09.12"},
    ]


class TestHealthEndpoints:
    """Tests for health check endpoints."""

    def test_health_check(self, client):
        """Test main health endpoint."""
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "services" in data
        assert "timestamp" in data

    def test_readiness_probe(self, client):
        """Test Kubernetes readiness probe."""
        response = client.get("/api/v1/ready")
        assert response.status_code == 200
        assert response.json()["ready"]

    def test_liveness_probe(self, client):
        """Test Kubernetes liveness probe."""
        response = client.get("/api/v1/live")
        assert response.status_code == 200
        assert response.json()["alive"]


class TestDataEndpoints:
    """Tests for data management endpoints."""

    def test_list_events(self, client):
        """Test listing standard events."""
        response = client.get("/api/v1/data/events")
        assert response.status_code == 200
        data = response.json()
        assert "events" in data
        assert len(data["events"]) == 11  # Standard meet has 11 events

    def test_get_csv_template(self, client):
        """Test getting CSV template."""
        response = client.get("/api/v1/data/templates/csv")
        assert response.status_code == 200
        data = response.json()
        assert "headers" in data
        assert "swimmer" in data["headers"]

    def test_get_json_template(self, client):
        """Test getting JSON template."""
        response = client.get("/api/v1/data/templates/json")
        assert response.status_code == 200
        data = response.json()
        assert "schema" in data

    def test_invalid_template_type(self, client):
        """Test invalid template type returns error."""
        response = client.get("/api/v1/data/templates/invalid")
        assert response.status_code == 400

    def test_submit_team_data(self, client, sample_seton_data):
        """Test submitting team data as JSON."""
        response = client.post(
            "/api/v1/data/team",
            json={
                "team_name": "Test Team",
                "team_type": "seton",
                "entries": sample_seton_data,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"]
        assert data["swimmer_count"] == 3
        assert data["entry_count"] == 6


class TestOptimizationEndpoints:
    """Tests for optimization endpoints."""

    def test_list_backends(self, client):
        """Test listing optimization backends."""
        response = client.get("/api/v1/optimize/backends")
        assert response.status_code == 200
        data = response.json()
        assert "backends" in data
        assert "heuristic" in data["backends"]
        assert data["default"] == "aqua"

    def test_optimization_preview(
        self, client, sample_seton_data, sample_opponent_data
    ):
        """Test optimization preview."""
        response = client.post(
            "/api/v1/optimize/preview",
            json={
                "seton_data": sample_seton_data,
                "opponent_data": sample_opponent_data,
                "optimizer_backend": "heuristic",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["valid"]
        assert data["seton"]["swimmer_count"] == 3
        assert data["opponent"]["swimmer_count"] == 3

    def test_optimization_missing_data(self, client):
        """Test optimization with missing data."""
        response = client.post(
            "/api/v1/optimize", json={"seton_data": [], "opponent_data": []}
        )
        assert response.status_code == 400


class TestExportEndpoints:
    """Tests for export endpoints."""

    def test_list_export_formats(self, client):
        """Test listing export formats."""
        response = client.get("/api/v1/export/formats")
        assert response.status_code == 200
        data = response.json()
        assert "formats" in data
        format_ids = [f["id"] for f in data["formats"]]
        assert "csv" in format_ids
        assert "json" in format_ids

    def test_export_json(self, client):
        """Test JSON export."""
        response = client.post(
            "/api/v1/export",
            json={
                "format": "json",
                "optimization_results": {"test": "data"},
                "seton_score": 100,
                "opponent_score": 90,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"]
        assert data["format"] == "json"
        assert ".json" in data["filename"]


class TestAnalyticsEndpoints:
    """Tests for analytics endpoints."""

    def test_scoring_rules(self, client):
        """Test getting scoring rules."""
        response = client.get("/api/v1/analytics/scoring")
        assert response.status_code == 200
        data = response.json()
        assert "individual_events" in data
        assert "relay_events" in data
        assert data["individual_events"]["1st"] == 6

    def test_team_depth_analysis(self, client, sample_seton_data):
        """Test depth analysis."""
        response = client.post("/api/v1/analytics/depth", json=sample_seton_data)
        assert response.status_code == 200
        data = response.json()
        assert "event_depth" in data
        assert "total_swimmers" in data
        assert data["total_swimmers"] == 3


# Run tests if executed directly
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
