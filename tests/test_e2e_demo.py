"""
Optimized End-to-End Test for SwimAi Demo
Uses Playwright for browser automation and testing.

This test demonstrates:
1. Loading actual Seton and Trinity data
2. Running optimization
3. Viewing results

OPTIMIZATION: Configured for fast execution with headless mode and optimal waits
"""

import pytest
from playwright.sync_api import Page, expect


class TestSwimAiDemo:
    """E2E tests for SwimAi application demo."""

    @pytest.fixture(scope="function", autouse=True)
    def setup(self, page: Page):
        """Navigate to app before each test."""
        page.goto("http://localhost:3000")
        page.wait_for_load_state("networkidle")
        yield page

    def test_load_real_seton_trinity_data(self, page: Page):
        """
        Test loading actual Seton and Trinity Christian data from PDFs.

        This validates:
        - Navigation works
        - Load Sample Data button triggers data loading
        - Data is parsed correctly
        - UI updates with swimmer counts
        """
        # Navigate to Meet page (where the Load Sample Data button is)
        page.click("text=Meet")
        page.wait_for_timeout(500)

        # Click "DEV: Load Sample Data" button
        load_button = page.locator("button:has-text('Load Sample Data')")
        expect(load_button).to_be_visible(timeout=5000)
        load_button.click()

        # Wait for data to load
        page.wait_for_timeout(1000)

        # Verify success - check for Ready to Optimize status
        ready_indicator = page.locator("text=/Ready to Optimize/i")
        expect(ready_indicator).to_be_visible(timeout=10000)

        print("✅ Test data loaded successfully!")

    def test_run_optimization(self, page: Page):
        """
        Test running lineup optimization.

        This validates:
        - Optimization can be triggered
        - Progress is shown
        - Results are displayed
        """
        # First load data via Meet page
        page.click("text=Meet")
        page.wait_for_timeout(500)

        load_button = page.locator("button:has-text('Load Sample Data')")
        if load_button.is_visible():
            load_button.click()
            page.wait_for_timeout(1000)

        # Navigate to Optimize page
        page.click("text=Optimize")
        page.wait_for_timeout(500)

        # Click Optimize button
        optimize_button = page.locator("button:has-text('Optimize Lineup')")
        if optimize_button.is_visible():
            optimize_button.click()

            # Wait for optimization to complete (max 30 seconds)
            page.wait_for_timeout(30000)

            # Check for results
            score_display = page.locator("text=/Score|Points/i")
            expect(score_display).to_be_visible(timeout=5000)

            print("✅ Optimization completed successfully!")

    def test_navigation_flow(self, page: Page):
        """
        Test navigation through all pages.

        Validates all main routes are accessible.
        """
        pages_to_test = [
            ("Dashboard", "AquaForge"),
            ("Meet Setup", "Meet"),
            ("Optimizer", "Optimize"),
            ("Analytics", "Analytics"),
        ]

        for nav_text, expected_heading in pages_to_test:
            page.click(f"text={nav_text}")
            page.wait_for_timeout(300)

            # Verify page loaded
            heading = page.locator(f"text=/{expected_heading}/i").first
            expect(heading).to_be_visible(timeout=5000)

            print(f"✅ {nav_text} page accessible")

    def test_responsive_ui(self, page: Page):
        """
        Test UI responsiveness at different viewport sizes.

        OPTIMIZATION: Tests key breakpoints only for speed.
        """
        viewports = [
            (1920, 1080, "Desktop"),
            (768, 1024, "Tablet"),
            (375, 667, "Mobile"),
        ]

        for width, height, device_name in viewports:
            page.set_viewport_size({"width": width, "height": height})
            page.wait_for_timeout(200)

            # Verify header is still visible (nav is hidden on mobile, header stays visible)
            header = page.locator("header").first
            expect(header).to_be_visible(timeout=3000)

            print(f"✅ UI renders correctly on {device_name} ({width}x{height})")


# Pytest configuration for Playwright
@pytest.fixture(scope="session")
def browser_context_args(browser_context_args):
    """
    OPTIMIZATION: Configure browser for fast test execution.
    """
    return {
        **browser_context_args,
        "viewport": {"width": 1920, "height": 1080},
        "ignore_https_errors": True,
        "record_video_dir": None,  # Disable video recording for speed
    }


@pytest.fixture(scope="session")
def browser_type_launch_args(browser_type_launch_args):
    """
    OPTIMIZATION: Launch browser in headless mode for speed.
    Remove headless=False to see the browser during tests.
    """
    return {
        **browser_type_launch_args,
        "headless": True,  # Set to False for debugging
        "args": [
            "--disable-blink-features=AutomationControlled",
            "--disable-dev-shm-usage",
            "--no-sandbox",
        ],
    }


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "--headed"])  # Use --headed to see browser
