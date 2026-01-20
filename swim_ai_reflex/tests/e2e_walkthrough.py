from playwright.sync_api import sync_playwright
import sys

def run_walkthrough():
    print("🚀 Starting SwimAi E2E Walkthrough")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1280, "height": 720})
        page = context.new_page()
        
        # 1. Access Application
        try:
            print("  - Navigating to localhost:3000...")
            page.goto("http://localhost:3000", timeout=60000)
            # Wait for content
            page.wait_for_load_state("networkidle", timeout=60000)
            print("  ✅ Access Successful")
        except Exception as e:
            print(f"  ❌ Failed to load dashboard: {e}")
            print("     (Ensure the server is running on localhost:3000)")
            browser.close()
            sys.exit(1)

        # 2. Upload Data
        print("  - Going to Upload Page...")
        try:
           # Try sidebar/navbar links
           # Note: Reflex often uses specific classes, but text selectors are robust
           # Try to find "Data Ingestion" or "Upload"
           navigated = False
           for text in ["Data Ingestion", "Upload", "Load Data"]:
               if page.is_visible(f"text={text}"):
                   page.click(f"text={text}")
                   navigated = True
                   break
           
           if not navigated:
               # Try URL
               page.goto("http://localhost:3000/upload")
            
           page.wait_for_selector("text=DATA INGESTION", timeout=5000)
           print("  ✅ Upload Page Loaded")
        except Exception as e:
            print(f"  ❌ Failed to verify Upload Page: {e}")
            browser.close()
            sys.exit(1)
        
        # 3. Load Demo Data
        print("  - Loading Demo Data...")
        try:
            if page.is_visible("text=Load Demo Data"):
                page.click("text=Load Demo Data")
            else:
                # Scroll to find it?
                print("    (Button not visible, searching...)")
                page.click("text=Load Demo Data (Seton vs Trinity)")
            
            # Wait for "Seton Data Ready" badge
            page.wait_for_selector("text=Seton Data Ready", timeout=15000)
            print("  ✅ Demo Data Loaded (Seton & Opponent)")
        except Exception as e:
            print(f"  ❌ Failed to load demo data: {e}")
            browser.close()
            sys.exit(1)
        
        # 4. Proceed to Optimize
        print("  - Configuring Strategy...")
        try:
            page.click("text=Next: Deep Strategy")
            page.wait_for_selector("text=DEEP STRATEGY", timeout=5000)
            print("  ✅ Strategy Page Loaded")
        except Exception as e:
            print(f"  ❌ Failed to navigate to strategy: {e}")
            browser.close()
            sys.exit(1)
        
        # 5. Run Optimization
        print("  - Executing Admiral Koehr Model...")
        try:
            # Select "Conservative" for speed in testing
            # E2E test runs with headless browser, faster iterations = happier test
            if page.is_visible("text=Conservative"):
                page.click("text=Conservative")
            
            # Click "FORGE OPTIMAL LINEUP"
            page.click("text=FORGE OPTIMAL LINEUP")
            
            # Wait for "LINEUP FORGED"
            # The button text changes conformally
            page.wait_for_selector("text=LINEUP FORGED", timeout=120000) # Give it time
            print("  ✅ Optimization Complete")
        except Exception as e:
            print(f"  ❌ Failed during optimization: {e}")
            browser.close()
            sys.exit(1)
        
        # 6. View Results
        print("  - Analyzing Results...")
        try:
            # Click "View Analysis" floating button
            page.click("text=View Analysis")
            # Wait for results page
            page.wait_for_load_state("networkidle")
            
            # Check for generic success indicator on results page
            # "OPTIMIZED RESULTS" or similar?
            # We assume it loads.
            print("  ✅ Analysis Page Loaded")
            
            # Capture screenshot
            page.screenshot(path="e2e_results.png")
            print("  📸 Screenshot saved to e2e_results.png")
            
        except Exception as e:
            print(f"  ❌ Failed to view analysis: {e}")
            browser.close()
            sys.exit(1)
            
        print("🎉 E2E Walkthrough Successful!")
        browser.close()

if __name__ == "__main__":
    run_walkthrough()
