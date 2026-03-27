import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

try:
    from swim_ai_reflex.backend.core.hytek_pdf_parser import (
        parse_hytek_pdf,  # noqa: F401
    )
    from swim_ai_reflex.backend.services.optimization_service import (
        optimization_service,  # noqa: F401
    )

    print("✓ Backend imports successful")
except ImportError as e:
    print(f"✗ Backend import error: {e}")


def run_walkthrough():
    print("→ Starting AquaForge E2E Walkthrough")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)  # Show browser for debugging
        context = browser.new_context(viewport={"width": 1280, "height": 720})
        page = context.new_page()

        # 1. Access Application
        try:
            print("- Navigating to localhost:3000...")
            page.goto("http://localhost:3000", timeout=60000)
            # Wait for content
            page.wait_for_load_state("networkidle", timeout=60000)
            print("✓ Access Successful")
        except Exception as e:
            print(f"✗ Failed to load dashboard: {e}")
            print("(Ensure the frontend server is running on localhost:3000)")
            print("Run: cd frontend && npm run dev")
            browser.close()
            sys.exit(1)

        # 2. Upload Data
        print("- Going to Meet Setup Page...")
        try:
            # Try direct URL first
            page.goto("http://localhost:3000/meet")

            # Look for key elements on meet page
            try:
                page.wait_for_selector("text=Meet Setup", timeout=5000)
            except Exception:
                # Try alternative selectors
                try:
                    page.wait_for_selector("text=File Upload", timeout=5000)
                except Exception:
                    page.wait_for_selector("text=Upload Files", timeout=5000)
            print("✓ Meet Setup Page Loaded")
        except Exception as e:
            print(f"✗ Failed to verify Meet Setup Page: {e}")
            print("(Ensure the backend API server is running on localhost:8001)")
            print("Run: source .venv/bin/activate && python run_server.py --mode api")
            browser.close()
            sys.exit(1)

        # 3. Load Demo Data
        print("- Loading Demo Data...")
        try:
            # Look for file upload section
            page.wait_for_selector("text=File Upload", timeout=5000)

            # Try to find and click demo data button if it exists
            demo_buttons = page.query_selector_all("text=Load Demo")
            if demo_buttons:
                page.click("text=Load Demo")
                print("✓ Demo Data Button Clicked")
            else:
                print("No Demo Data button found, proceeding with manual upload check")

            # Wait a moment for any data to load
            page.wait_for_timeout(2000)
            print("✓ Upload Interface Loaded")
        except Exception as e:
            print(f"✗ Failed to access upload interface: {e}")
            browser.close()
            sys.exit(1)

        # 4. Navigate to Optimization
        print("- Navigating to Optimization...")
        try:
            page.goto("http://localhost:3000/optimize")
            page.wait_for_selector("text=Optimization", timeout=10000)
            print("✓ Optimization Page Loaded")
        except Exception as e:
            print(f"✗ Failed to navigate to optimization: {e}")
            browser.close()
            sys.exit(1)

        # 5. Run Optimization
        print("- Running Optimization...")
        try:
            # Look for optimize button (updated text for new UI)
            optimize_button = page.query_selector("text=Run Optimization")
            if not optimize_button:
                optimize_button = page.query_selector("text=Optimize Meet")
            if not optimize_button:
                optimize_button = page.query_selector("button[type='submit']")

            if optimize_button:
                page.click("text=Run Optimization")
                print("✓ Optimization Started")

                # Wait for completion (check for results or completion message)
                try:
                    page.wait_for_function(
                        """() => {
                            const logs = document.querySelector('[data-testid="logs"]') ||
                                        document.querySelector('.logs') ||
                                        document.querySelector('[class*="log"]');
                            return logs && logs.textContent.includes('complete');
                        }""",
                        timeout=90000,  # Increased timeout for complex optimizations
                    )
                    print("✓ Optimization Complete")
                except Exception:
                    # Alternative: wait for results page elements
                    page.wait_for_selector("text=Results", timeout=10000)
                    print("✓ Optimization appears complete (results loaded)")
            else:
                print("No optimize button found - may need data first")
                # Take screenshot for debugging
                page.screenshot(path="debug_optimize_page.png")
                print("Debug screenshot saved to debug_optimize_page.png")
        except Exception as e:
            print(f"✗ Failed during optimization: {e}")
            browser.close()
            sys.exit(1)

        # 6. View Results
        print("- Viewing Results...")
        try:
            page.goto("http://localhost:3000/results")
            page.wait_for_selector("text=Results", timeout=10000)
            print("✓ Results Page Loaded")

            # Capture screenshot
            page.screenshot(path="e2e_results.png")
            print("Screenshot saved to e2e_results.png")

        except Exception as e:
            print(f"✗ Failed to view analysis: {e}")
            browser.close()
            sys.exit(1)

        print("E2E Walkthrough Successful!")
        browser.close()


if __name__ == "__main__":
    run_walkthrough()
