---
description: Complete E2E debug, optimize and refactor workflow - runs until the entire app is fixed
---

# E2E Fix Workflow 🔧

A comprehensive workflow that uses **all available tools and MCP servers** to systematically debug, optimize, and refactor AquaForge until it's completely fixed and production-ready.

---

## How To Invoke

Tell Antigravity:

- `/e2e-fix` - Run the full workflow
- "Fix everything in AquaForge"
- "Run the complete E2E debug workflow"

---

## 🔄 THE LOOP

This workflow runs in a **continuous improvement loop** until all checks pass:

```
┌─────────────────────────────────────────────────────────────────┐
│                         START                                    │
└──────────────────────────┬──────────────────────────────────────┘
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│  PHASE 1: SCAN - Identify all issues                            │
│  • Type errors (pyright)                                        │
│  • Lint errors (ruff)                                           │
│  • Test failures (pytest)                                       │
│  • TODO/FIXME items                                             │
│  • Import issues                                                 │
└──────────────────────────┬──────────────────────────────────────┘
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│  PHASE 2: FIX - Use AI + sequential-thinking to fix issues     │
│  • Auto-fix lint issues                                          │
│  • Fix type errors with Pylance guidance                        │
│  • Debug and fix failing tests                                   │
│  • Apply refactoring patterns                                    │
└──────────────────────────┬──────────────────────────────────────┘
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│  PHASE 3: VERIFY - Re-run all checks                            │
│  If any fail → Return to PHASE 2                                │
│  If all pass → Continue to PHASE 4                              │
└──────────────────────────┬──────────────────────────────────────┘
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│  PHASE 4: E2E TEST - Browser automation                         │
│  • Start dev server                                              │
│  • Run browser tests                                             │
│  • Test optimization workflow                                    │
│  • Capture results                                               │
└──────────────────────────┬──────────────────────────────────────┘
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│  PHASE 5: DEPLOY PREP - Ready for production                    │
│  • Docker build                                                  │
│  • Cloud Run deploy (optional)                                   │
│  • Update documentation                                          │
└──────────────────────────┬──────────────────────────────────────┘
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                         ✅ COMPLETE                              │
└─────────────────────────────────────────────────────────────────┘
```

---

## PHASE 1: SCAN 🔍

// turbo-all

### Step 1.1: Activate Virtual Environment

```bash
source .venv/bin/activate
```

### Step 1.2: Run Type Checking (Pyright/Pylance)

```bash
pyright --stats 2>&1 | head -100
```

**Record:** Number of errors, warnings, and files checked.

### Step 1.3: Run Linting (Ruff)

```bash
ruff check . --statistics 2>&1 | head -50
```

**Record:** Number of fixable vs non-fixable issues.

### Step 1.4: Run Tests (Pytest)

```bash
python -m pytest tests/ -v --tb=short -q 2>&1 | tail -50
```

**Record:** Number of passed/failed/skipped tests.

### Step 1.5: Scan for Technical Debt

```bash
grep -rn "TODO\|FIXME\|XXX\|HACK" --include="*.py" swim_ai_reflex/ 2>/dev/null | head -30
```

**Record:** Critical TODOs that need addressing.

### Step 1.6: Check for Import Issues

```bash
python -c "from swim_ai_reflex.backend.api.main import app; print('✅ Main app imports successfully')"
```

### Step 1.7: Create Issue Summary

After running all scans, Antigravity should:
1. Create a prioritized list of issues
2. Categorize by severity (Critical, High, Medium, Low)
3. Estimate fix effort for each
4. Use `sequential-thinking` MCP to plan the fix order

---

## PHASE 2: FIX 🔧

### Step 2.1: Auto-Fix Lint Issues

// turbo

```bash
ruff check . --fix --unsafe-fixes
```

// turbo

```bash
ruff format .
```

### Step 2.2: Fix Type Errors

For each type error from pyright:
1. View the file with the error
2. Use `sequential-thinking` MCP to analyze the issue
3. Apply the fix
4. Re-check with `pyright <file>`

**Example Analysis Prompt for sequential-thinking:**
> "Analyze this pyright error: [error message]. The file is [filename]. Determine the root cause and the correct fix."

### Step 2.3: Fix Failing Tests

For each failing test:
1. Run the specific test with verbose output:
   ```bash
   python -m pytest tests/test_[name].py::[test_name] -v --tb=long
   ```
2. Analyze the failure using `sequential-thinking`
3. Fix the underlying code or test
4. Re-run to verify

### Step 2.4: Address Critical TODOs

For any TODO marked as Critical:
1. View the context around the TODO
2. Implement the missing functionality
3. Remove the TODO comment
4. Add appropriate tests

### Step 2.5: Refactoring Opportunities

Look for and apply these patterns:
- Extract duplicate code into shared functions
- Simplify complex conditionals
- Add type hints to untyped functions
- Improve error handling
- Optimize database queries

---

## PHASE 3: VERIFY ✅

// turbo-all

### Step 3.1: Re-run Type Check

```bash
pyright 2>&1 | tail -20
```

**Success Criteria:** 0 errors

### Step 3.2: Re-run Linting

```bash
ruff check . 2>&1 | tail -20
```

**Success Criteria:** 0 errors

### Step 3.3: Re-run All Tests

```bash
python -m pytest tests/ -v --tb=short 2>&1 | tail -30
```

**Success Criteria:** All tests pass (0 failures)

### Step 3.4: Verify Imports

```bash
python -c "
from swim_ai_reflex.backend.api.main import app
from swim_ai_reflex.backend.services.optimization_service import OptimizationService
from swim_ai_reflex.backend.services.championship_formatter import format_championship_response
print('✅ All critical imports successful')
"
```

### Step 3.5: Check Build (Ralph Integration)

```bash
python ralph.py --check-complete --conditions build_succeeds tests_pass no_lint_errors
```

**Decision Point:**
- If ANY check fails → Return to PHASE 2 with specific failures
- If ALL checks pass → Continue to PHASE 4

---

## PHASE 4: E2E BROWSER TEST 🌐

### Step 4.1: Start Dev Server

```bash
python run_server.py &
```

Wait 5 seconds for server to start.

### Step 4.2: Health Check

// turbo

```bash
curl -s http://localhost:8000/api/v1/health | python -m json.tool
```

### Step 4.3: Browser E2E Test

Use `browser_subagent` to:
1. Navigate to http://localhost:8000
2. Verify the main page loads
3. Test the optimization workflow:
   - Upload test data (if upload feature exists)
   - Run optimization
   - Verify results display correctly
4. Check for any JavaScript errors in console
5. Capture screenshot of final state

**Browser Task Template:**
> "Navigate to http://localhost:8000. Verify the page loads correctly. Look for any error messages or broken UI elements. If there's an optimization form, test submitting it. Return a summary of what you found and any issues."

### Step 4.4: API Integration Test

Use Thunder Client or curl to test key endpoints:

// turbo

```bash
# Test optimization endpoint with sample data
curl -X POST http://localhost:8000/api/v1/optimize \
  -H "Content-Type: application/json" \
  -d '{"mode": "dual_meet", "seton_data": [], "opponent_data": []}' \
  2>/dev/null | python -m json.tool | head -30
```

### Step 4.5: Stop Dev Server

```bash
pkill -f "run_server.py" || true
```

**Decision Point:**
- If browser tests reveal issues → Document and fix → Return to PHASE 2
- If all E2E tests pass → Continue to PHASE 5

---

## PHASE 5: DEPLOY PREP 🚀

### Step 5.1: Docker Build Test

```bash
docker build -t aquaforge:test . 2>&1 | tail -20
```

### Step 5.2: Docker Run Test

```bash
docker run -d --name aquaforge-test -p 8001:8000 aquaforge:test
sleep 5
curl -s http://localhost:8001/api/v1/health
docker stop aquaforge-test && docker rm aquaforge-test
```

### Step 5.3: Update Documentation

Antigravity should update:
1. `docs/COST_EFFORT_LOG.md` with time spent
2. `.agent/context/current_focus.md` with completion status
3. `VERSION_LOG.md` if significant changes were made

### Step 5.4: Cloud Run Deployment (Optional)

If user requests deployment:

```
Use the cloudrun MCP server to deploy:
1. mcp_cloudrun_list_projects - Get project list
2. mcp_cloudrun_deploy_local_folder - Deploy the app
```

### Step 5.5: Firebase Check (Optional)

If Firebase features are used:

```
Use the firebase-mcp-server to verify:
1. firebase_get_environment - Check config
2. firebase_list_apps - Verify app registration
```

---

## 📊 SUCCESS CRITERIA

The workflow is COMPLETE when:

| Check        | Requirement               |
| ------------ | ------------------------- |
| Pyright      | 0 errors                  |
| Ruff         | 0 errors                  |
| Pytest       | All tests pass            |
| Imports      | All critical imports work |
| API Health   | Returns 200 OK            |
| Browser E2E  | No errors, UI functional  |
| Docker Build | Builds successfully       |

---

## 🧠 USING SEQUENTIAL-THINKING

For complex issues, use the `sequential-thinking` MCP server:

**When to use:**
- Multi-step bugs that aren't immediately obvious
- Refactoring decisions with trade-offs
- Performance optimization analysis
- Architecture questions

**How to invoke:**
```
mcp_sequential-thinking_sequentialthinking with:
- thought: "Describe the problem and current analysis"
- thoughtNumber: 1
- totalThoughts: 5 (adjust as needed)
- nextThoughtNeeded: true
```

Continue invoking until `nextThoughtNeeded: false`

---

## 🔧 TOOL REFERENCE

| Tool                    | Purpose                 | Command                                    |
| ----------------------- | ----------------------- | ------------------------------------------ |
| **Pyright**             | Type checking           | `pyright`                                  |
| **Ruff**                | Linting + formatting    | `ruff check .` / `ruff format .`           |
| **Pytest**              | Testing                 | `python -m pytest tests/`                  |
| **Ralph**               | Build verification      | `python ralph.py --check-complete`         |
| **Docker**              | Container builds        | `docker build -t aquaforge .`              |
| **curl**                | API testing             | `curl http://localhost:8000/api/v1/health` |
| **browser_subagent**    | UI testing              | Automated browser interactions             |
| **sequential-thinking** | Complex problem solving | MCP tool                                   |
| **cloudrun**            | Deployment              | MCP tool                                   |
| **firebase**            | Firebase integration    | MCP tool                                   |

---

## 📝 NOTES

- This workflow is **iterative** - it keeps running until everything passes
- Use `// turbo` annotations to auto-run safe commands
- Complex fixes should use `sequential-thinking` for systematic analysis
- Always update documentation after significant changes
- The workflow integrates with `/ralph` for build verification

---

_Workflow Version: 1.0_
_Created: 2026-01-16_
_Author: Antigravity AI_
