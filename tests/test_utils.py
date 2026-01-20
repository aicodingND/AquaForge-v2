"""
Testing utilities for the refactored SwimAI application.
Provides fixtures, mocks, and helpers for testing.

NOTE: This module is DEPRECATED. It depends on the old Reflex states module
which was removed during the Next.js migration. The test helpers were for
the legacy UI and are no longer needed.
"""

from typing import Any, Dict, List

import pandas as pd
import pytest

# Skip entire module - depends on deprecated states
pytestmark = pytest.mark.skip(
    reason="Deprecated: uses legacy swim_ai_reflex.states module"
)

try:
    from swim_ai_reflex.states import (
        OptimizationState,
        RosterState,
        UIState,
        UploadState,
    )

    from swim_ai_reflex.backend.config import AppConfig
except ImportError:
    # Provide stubs to prevent import errors when module is collected
    UIState = RosterState = OptimizationState = UploadState = AppConfig = None


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def sample_seton_data() -> List[Dict[str, Any]]:
    """Sample Seton roster data for testing."""
    return [
        {
            "swimmer": "John Smith",
            "grade": 11,
            "gender": "M",
            "event": "Boys 50 Free",
            "time": 23.5,
            "team": "Seton",
            "is_relay": False,
            "is_diving": False,
        },
        {
            "swimmer": "Sarah Davis",
            "grade": 12,
            "gender": "F",
            "event": "Girls 100 Back",
            "time": 62.5,
            "team": "Seton",
            "is_relay": False,
            "is_diving": False,
        },
    ]


@pytest.fixture
def sample_opponent_data() -> List[Dict[str, Any]]:
    """Sample opponent roster data for testing."""
    return [
        {
            "swimmer": "Tom Wilson",
            "grade": 11,
            "gender": "M",
            "event": "Boys 50 Free",
            "time": 24.0,
            "team": "Opponent",
            "is_relay": False,
            "is_diving": False,
        }
    ]


@pytest.fixture
def sample_dataframe() -> pd.DataFrame:
    """Sample DataFrame for testing."""
    return pd.DataFrame(
        [
            {"swimmer": "John", "event": "50 Free", "time": 23.5, "team": "Seton"},
            {"swimmer": "Jane", "event": "100 Back", "time": 62.0, "team": "Seton"},
        ]
    )


@pytest.fixture
def test_config() -> AppConfig:
    """Test configuration with safe defaults."""
    config = AppConfig()
    config.security.upload_directory = "test_uploads"
    config.security.max_file_size_mb = 5
    config.optimization.cache_ttl_minutes = 1  # Short TTL for testing
    return config


# ============================================================================
# State Fixtures
# ============================================================================


@pytest.fixture
def ui_state() -> UIState:
    """Fresh UIState instance for testing."""
    return UIState()


@pytest.fixture
def roster_state(sample_seton_data, sample_opponent_data) -> RosterState:
    """RosterState with sample data loaded."""
    state = RosterState()
    state.set_seton_roster("test_seton.pdf", sample_seton_data)
    state.set_opponent_roster("test_opponent.pdf", sample_opponent_data)
    return state


@pytest.fixture
def optimization_state() -> OptimizationState:
    """Fresh OptimizationState instance for testing."""
    return OptimizationState()


@pytest.fixture
def upload_state() -> UploadState:
    """Fresh UploadState instance for testing."""
    return UploadState()


# ============================================================================
# Mock Helpers
# ============================================================================


class MockOptimizationService:
    """Mock optimization service for testing without running actual optimization."""

    @staticmethod
    async def predict_best_lineups(*args, **kwargs) -> Dict[str, Any]:
        """Mock optimization that returns fake results."""
        return {
            "seton_score": 150.0,
            "opponent_score": 120.0,
            "best_lineup": [{"swimmer": "John", "event": "50 Free", "points": 5}],
            "details": [],
            "from_cache": False,
            "iterations": 500,
        }


class MockFileManager:
    """Mock file manager for testing without actual file I/O."""

    def __init__(self, upload_dir: str):
        self.upload_dir = upload_dir
        self.files = []

    def list_uploaded_files(self) -> List[str]:
        """Return mock file list."""
        return self.files

    def add_file(self, filename: str):
        """Add a file to the mock list."""
        self.files.append(filename)


# ============================================================================
# Test Helpers
# ============================================================================


def assert_state_clean(state: UIState):
    """Assert that UI state is in clean/initial condition."""
    assert state.current_page == "dashboard"
    assert not state.is_loading
    assert not state.has_error
    assert state.error_message == ""


def assert_roster_loaded(state: RosterState):
    """Assert that roster state has data loaded."""
    assert state.has_roster
    assert len(state.seton_data) > 0
    assert state.seton_filename != ""


def assert_optimization_complete(state: OptimizationState):
    """Assert that optimization has completed successfully."""
    assert state.optimization_done
    assert state.best_score_seton > 0
    assert len(state.optimization_scenario) > 0


def create_mock_upload_file(filename: str, content: bytes = b"test") -> Any:
    """Create a mock UploadFile object for testing."""

    class MockUploadFile:
        def __init__(self, name: str, data: bytes):
            self.filename = name
            self._data = data

        async def read(self) -> bytes:
            return self._data

    return MockUploadFile(filename, content)


# ============================================================================
# Example Test Cases
# ============================================================================


def test_ui_state_initialization(ui_state):
    """Test that UIState initializes correctly."""
    assert_state_clean(ui_state)
    assert len(ui_state.logs) == 1
    assert ui_state.logs[0] == "System initialized."


def test_ui_state_logging(ui_state):
    """Test that logging works correctly."""
    ui_state.log("Test message 1")
    ui_state.log("Test message 2")
    assert len(ui_state.logs) == 3
    assert "Test message 1" in ui_state.logs
    assert "Test message 2" in ui_state.logs


def test_roster_state_loading(roster_state):
    """Test that roster state loads data correctly."""
    assert_roster_loaded(roster_state)
    assert roster_state.seton_swimmer_count == 2
    assert roster_state.opponent_swimmer_count == 1
    assert roster_state.total_swimmer_count == 3


def test_roster_state_has_both_rosters(roster_state):
    """Test the has_both_rosters computed property."""
    assert roster_state.has_both_rosters

    # Clear opponent
    roster_state.opponent_data = []
    assert not roster_state.has_both_rosters


def test_optimization_state_score_difference(optimization_state):
    """Test score difference calculation."""
    optimization_state.set_results(150.0, 120.0, [])
    assert optimization_state.score_difference == 30.0
    assert optimization_state.is_winning


def test_upload_state_progress(upload_state):
    """Test upload progress tracking."""
    upload_state.set_upload_progress(50, "Uploading...")
    assert upload_state.upload_progress == 50
    assert upload_state.upload_status_detail == "Uploading..."

    # Test bounds
    upload_state.set_upload_progress(150)  # Over 100
    assert upload_state.upload_progress == 100

    upload_state.set_upload_progress(-10)  # Under 0
    assert upload_state.upload_progress == 0


def test_config_loading(test_config):
    """Test configuration loading."""
    assert test_config.security.max_file_size_mb == 5
    assert test_config.security.upload_directory == "test_uploads"
    assert test_config.optimization.cache_ttl_minutes == 1


# ============================================================================
# Integration Test Helpers
# ============================================================================


async def simulate_full_workflow(state, sample_data):
    """
    Simulate a full workflow from upload to optimization.
    Useful for integration testing.
    """
    # Load data
    state.roster.set_seton_roster("test.pdf", sample_data)

    # Run optimization (would need to mock the service)
    # await state.run_optimization()

    # Verify results
    # assert_optimization_complete(state.optimization)
    pass


if __name__ == "__main__":
    # Run tests with: pytest test_utils.py
    pytest.main([__file__, "-v"])
