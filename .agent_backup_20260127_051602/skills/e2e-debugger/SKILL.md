---
name: E2E Debugger
description: Debug end-to-end test failures, Playwright issues, and browser-based testing problems
triggers:
  - E2E test failures
  - Playwright errors
  - browser test issues
  - UI not rendering
  - element not found
---

# E2E Debugger Skill 🧪

Use this skill when debugging end-to-end tests, Playwright failures, or browser-based issues.

---

## Quick Diagnosis Checklist

### 1. Server Status
```bash
# Check if backend is running
curl http://localhost:8001/api/v1/health

# Check if frontend is running
curl http://localhost:3000
```

### 2. Common Error Categories

| Error                | Likely Cause                  | Quick Fix                 |
| -------------------- | ----------------------------- | ------------------------- |
| `TimeoutError`       | Server not started            | Start servers first       |
| `Element not found`  | Wrong selector / not rendered | Update selector, add wait |
| `Navigation timeout` | Page not loading              | Check server logs         |
| `Connection refused` | Server down                   | Restart servers           |
| `CORS error`         | API request blocked           | Check Caddyfile proxy     |

---

## Debugging Procedure

### Step 1: Verify Environment

```bash
# Terminal 1: Backend
cd /Users/mpage1/Desktop/AquaForge/AquaForge_v1.0.0-next_2026-01-10
source .venv/bin/activate
python run_server.py --mode api

# Terminal 2: Frontend
cd frontend
npm run dev
```

### Step 2: Check Test Prerequisites

Before running E2E tests:
- [ ] Backend running on port 8001
- [ ] Frontend running on port 3000
- [ ] Playwright installed: `npm install -g playwright`
- [ ] Browsers installed: `playwright install`

### Step 3: Run Test Isolated

```bash
# Run specific test file
python -m pytest tests/test_e2e_browser.py -v

# Run with debug output
python -m pytest tests/test_e2e_browser.py -v -s --tb=long

# Run with headed browser (visible)
PLAYWRIGHT_HEADLESS=0 python -m pytest tests/test_e2e_browser.py -v
```

### Step 4: Use Browser Subagent for Visual Debugging

For visual issues, delegate to browser subagent:
```
// subagent: browser
Task: Navigate to localhost:3000, take screenshot, verify [specific element] renders
Return: Screenshot confirmation and any errors in console
```

---

## Common Issues & Solutions

### Issue: "No element found" / Selector fails

**Diagnosis:**
1. Element not yet rendered (timing issue)
2. Selector changed (UI update)
3. Element behind modal/overlay

**Solutions:**
```python
# Add explicit wait
await page.wait_for_selector('[data-testid="submit-button"]', timeout=10000)

# Use more robust selector
page.locator('button:has-text("Submit")')

# Wait for network idle
await page.wait_for_load_state('networkidle')
```

### Issue: "Navigation timeout"

**Diagnosis:**
1. Server not responding
2. Page has errors preventing load
3. Redirect loop

**Solutions:**
```python
# Increase timeout
page.set_default_timeout(30000)

# Wait for specific response
await page.wait_for_response(lambda r: '/api/v1/optimize' in r.url)
```

### Issue: "API request failed"

**Diagnosis:**
1. CORS misconfiguration
2. Backend error
3. Wrong API URL

**Solutions:**
```python
# Check API directly
response = requests.get('http://localhost:8001/api/v1/health')
print(response.status_code, response.json())

# Verify frontend API URL in .env
# NEXT_PUBLIC_API_URL=http://localhost:8001
```

### Issue: Test passes locally, fails in CI

**Diagnosis:**
1. Timing differences
2. Missing dependencies
3. Environment variables

**Solutions:**
- Add more waits and retries
- Use environment-agnostic selectors
- Ensure all env vars are set in CI

---

## AquaForge-Specific E2E Patterns

### Testing Optimization Flow

```python
async def test_optimization_e2e(page):
    # 1. Navigate to app
    await page.goto('http://localhost:3000')

    # 2. Load sample data
    await page.click('[data-testid="load-sample"]')

    # 3. Wait for data to load
    await page.wait_for_selector('[data-testid="roster-loaded"]')

    # 4. Click optimize
    await page.click('[data-testid="optimize-button"]')

    # 5. Wait for results
    await page.wait_for_selector('[data-testid="results-table"]', timeout=30000)

    # 6. Verify results
    score = await page.text_content('[data-testid="team-score"]')
    assert int(score) > 0
```

### Testing File Upload

```python
async def test_file_upload(page):
    # Set file input
    await page.set_input_files(
        'input[type="file"]',
        'data/test_psych_sheet.csv'
    )

    # Wait for processing
    await page.wait_for_selector('[data-testid="file-processed"]')
```

---

## Debug Tools

### Take Screenshot on Failure
```python
@pytest.fixture
def page_with_screenshot(page):
    yield page
    if pytest.current_test.failed:
        page.screenshot(path=f'test_outputs/{test_name}_failure.png')
```

### Record Video
```python
# In conftest.py
browser_context_args = {
    "record_video_dir": "test_outputs/videos/"
}
```

### Console Log Capture
```python
page.on('console', lambda msg: print(f'CONSOLE: {msg.text}'))
page.on('pageerror', lambda err: print(f'PAGE ERROR: {err}'))
```

---

## 🚀 Upgrade: AI-Powered Browser Automation

**For brittle selectors that keep breaking, consider upgrading to Stagehand:**

Traditional Playwright selectors are fast but break when UI changes. Stagehand adds an AI layer for resilient automation.

### Quick Comparison

| Approach         | Speed    | Resilience   | Best For              |
| ---------------- | -------- | ------------ | --------------------- |
| CSS Selectors    | ⚡ Fast   | ❌ Brittle    | Stable UIs            |
| data-testid      | ⚡ Fast   | ✅ Good       | Internal apps         |
| **Stagehand AI** | 🐢 Slower | ✅✅ Excellent | Dynamic UIs, scraping |

### Migration Example

**Before (Playwright):**
```python
await page.click("#submit-btn")
await page.fill("input[name='search']", "VCAC")
```

**After (Stagehand):**
```python
await page.act("Click the submit button")
await page.act("Type VCAC in the search box")
```

### When to Use Stagehand

- ✅ SwimCloud scraping (UI changes frequently)
- ✅ Complex multi-step flows
- ✅ Data extraction with schemas
- ❌ Simple internal UI tests (overkill)

**See full documentation:** Load `browser-automation` skill

```
# To load Stagehand skill:
"Load the browser-automation skill"
```

---

## Integration with Workflows

This skill integrates with:
- `/e2e-fix` workflow - Full E2E debug/fix cycle
- `/ralph` workflow - Iterative test fixing
- `browser-automation` skill - AI-powered alternative

---

_Skill: e2e-debugger | Version: 1.1 | See also: browser-automation_
