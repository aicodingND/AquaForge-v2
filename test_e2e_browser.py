"""
E2E Browser Test Script using Playwright
Simulates a user flow:
1. Navigate to Dashboard
2. Navigate to Upload Page
3. Upload Roster Files
4. Proceed to Optimize
5. Run Optimization
6. Verify Results appear
"""

import os
from playwright.sync_api import sync_playwright

UPLOAD_DIR = r"c:\Users\Michael\Desktop\AquaForgeFinal\uploads"
SETON_FILE = os.path.join(UPLOAD_DIR, "Seton Boys v3.1.xlsx")
OPPONENT_FILE = os.path.join(UPLOAD_DIR, "Immanuel Boys V3.xlsx")


def run_browser_simulation():
    print("=" * 60)
    print("BROWSER SIMULATION STARTING")
    print("=" * 60)

    with sync_playwright() as p:
        # Launch browser (headless=False to see it if needed, using True for speed/stability in script)
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1280, "height": 800})
        page = context.new_page()

        try:
            # 1. Dashboard
            print("1. Navigating to Dashboard...")
            page.goto("http://localhost:3000/")
            page.wait_for_load_state("networkidle")

            # Check title
            title = page.title()
            print(f"   Page Title: {title}")

            # 2. Go to Upload
            print("2. Clicking 'New Optimization'...")
            # Look for the card or button that links to upload
            # Assuming 'New Optimization' text is clickable or inside a clickable box
            page.get_by_text("New Optimization").click()
            page.wait_for_url("**/upload")
            print("   Reached Upload Page")

            # 3. Upload Files
            print("3. Uploading Files...")

            # Locate file input - standard reflex upload component often hides the input
            # We might need to find inputs with type='file'
            # Note: Reflex often uses an ID 'upload1' for the upload component
            page.locator("input[type='file']")

            # Reflex uses a hidden file input. We need to trigger the file chooser event if we click,
            # OR directly attach to the input if it exists in DOM.
            # Strategy: Click the upload area to trigger file chooser, but intercept it.
            with page.expect_file_chooser() as fc_info:
                page.locator("#upload1").click()
            file_chooser = fc_info.value
            file_chooser.set_files([SETON_FILE, OPPONENT_FILE])
            print("   Files selected via File Chooser")

            # Click "Process Groups" button
            print("   Clicking 'Process Groups'...")
            page.get_by_role("button", name="Process Groups & Analyze Files").click()

            # Wait for processing - look for toast or status change
            # "Ingestion Complete" text is a good indicator based on state.py
            print("   Waiting for processing...")
            try:
                page.wait_for_selector("text=Ingestion Complete", timeout=15000)
                print("   ✅ Ingestion Complete detected")
            except Exception:
                print("   ⚠️ Timed out waiting for 'Ingestion Complete' toast/text")

            # 4. Verify Roster Stats (Optional but good)
            # Look for Seton swimmer count
            # page.get_by_text("Seton Swimming").is_visible()

            # 5. Proceed
            print("5. Proceeding to Strategy...")
            # Button text: "Confirm & Proceed to Strategy"
            page.get_by_role("button", name="Confirm & Proceed to Strategy").click()
            page.wait_for_url("**/optimize")
            print("   Reached Optimize Page")

            # 6. Run Optimization
            print("6. Running Optimization...")
            # Button text: "FORGE OPTIMAL LINEUP"
            page.get_by_role("button", name="FORGE OPTIMAL LINEUP").click()

            # Wait for completion - look for "LINEUP FORGED" or "Optimization Complete"
            print("   Waiting for optimization (this may take a moment)...")
            try:
                page.wait_for_selector(
                    "text=LINEUP FORGED", timeout=100000
                )  # Give it time for Gurobi
                print("   ✅ LINEUP FORGED!")
            except Exception:
                print("   ❌ Optimization timed out or failed to show success message")
                # Debug: take screenshot
                page.screenshot(path="opt_failure.png")

            # 7. Check Results Button
            if page.get_by_role("button", name="View Analysis Results").is_visible():
                print("   'View Analysis Results' button is visible.")
            else:
                print("   ⚠️ Results button not found immediately.")

        except Exception as e:
            print(f"❌ BROWSER ERROR: {e}")
            page.screenshot(path="error_state.png")
            import traceback

            traceback.print_exc()
        finally:
            browser.close()
            print("=" * 60)
            print("SIMULATION END")
            print("=" * 60)


if __name__ == "__main__":
    run_browser_simulation()
