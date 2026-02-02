"""
Pytest configuration for AquaForge test suite.

This configures:
- Playwright browser fixtures (page, browser, context)
- Common test fixtures
- pytest-playwright settings
- Auto-skip for browser tests when server not running
"""

import socket

import pandas as pd
import pytest

# ==================== Server Detection ====================


def is_server_running(host: str = "localhost", port: int = 3000) -> bool:
    """Check if a server is running on the specified host:port."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(1)
    try:
        sock.connect((host, port))
        sock.close()
        return True
    except (TimeoutError, OSError):
        return False


# ==================== Playwright Configuration ====================


@pytest.fixture(scope="session")
def base_url():
    """Base URL for Playwright tests."""
    return "http://localhost:3000"


@pytest.fixture(scope="session")
def browser_context_args(browser_context_args):
    """Configure browser context for all tests."""
    return {
        **browser_context_args,
        "viewport": {"width": 1920, "height": 1080},
        "ignore_https_errors": True,
    }


@pytest.fixture(scope="session")
def browser_type_launch_args(browser_type_launch_args):
    """Configure browser launch options."""
    return {
        **browser_type_launch_args,
        "headless": True,  # Set to False for debugging
        "slow_mo": 0,  # Milliseconds between actions (useful for debugging)
    }


@pytest.fixture
def skip_if_no_server():
    """Skip test if frontend dev server is not running."""
    if not is_server_running("localhost", 3000):
        pytest.skip("Frontend dev server not running on localhost:3000")


# ==================== API Test Configuration ====================


@pytest.fixture
def api_base_url() -> str:
    """Base URL for API tests."""
    return "http://localhost:8000"


@pytest.fixture
def api_v1_url(api_base_url: str) -> str:
    """API v1 URL."""
    return f"{api_base_url}/api/v1"


# ==================== Test Data Fixtures ====================


@pytest.fixture
def sample_seton_entries() -> list:
    """Sample Seton team entries for testing."""
    return [
        {"swimmer": "John Doe", "event": "100 Free", "time": "52.34", "grade": "10"},
        {"swimmer": "Jane Smith", "event": "100 Free", "time": "54.12", "grade": "11"},
        {"swimmer": "John Doe", "event": "200 Free", "time": "1:55.00", "grade": "10"},
        {"swimmer": "Jane Smith", "event": "50 Free", "time": "26.45", "grade": "11"},
    ]


@pytest.fixture
def sample_opponent_entries() -> list:
    """Sample opponent team entries for testing."""
    return [
        {"swimmer": "Bob Wilson", "event": "100 Free", "time": "53.00", "grade": "10"},
        {"swimmer": "Alice Brown", "event": "100 Free", "time": "55.50", "grade": "9"},
        {
            "swimmer": "Bob Wilson",
            "event": "200 Free",
            "time": "1:58.00",
            "grade": "10",
        },
        {"swimmer": "Alice Brown", "event": "50 Free", "time": "27.00", "grade": "9"},
    ]


# ==================== Pytest Hooks ====================


def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line(
        "markers", "e2e: mark test as end-to-end browser test (requires running server)"
    )
    config.addinivalue_line("markers", "slow: mark test as slow running")
    config.addinivalue_line("markers", "integration: mark test as integration test")
    config.addinivalue_line("markers", "timeout: mark test with timeout")


def pytest_collection_modifyitems(config, items):
    """Auto-skip E2E browser tests if no server is running."""
    skip_no_server = pytest.mark.skip(
        reason="Frontend server not running on localhost:3000 (start with 'npm run dev')"
    )

    for item in items:
        # Check if this is an E2E browser test (uses Playwright page fixture)
        if "test_e2e" in item.nodeid and not is_server_running("localhost", 3000):
            item.add_marker(skip_no_server)


# Suppress pandas downcasting warnings
pd.set_option("future.no_silent_downcasting", True)
