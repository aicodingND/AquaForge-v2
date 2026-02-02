---
description: Run iterative development using the Ralph Wiggum technique
---

# Ralph Wiggum Development Workflow

The "Ralph Wiggum technique" runs AI-assisted development in a **continuous loop until success criteria are met**.

## How To Use With AI Agent

When you want me to work on something iteratively until it's complete, tell me:

> "Use Ralph to [your task]. Success when [criteria]."

**Examples:**

- "Use Ralph to fix all failing tests. Success when all tests pass."
- "Use Ralph to add authentication to the API. Success when auth tests pass."
- "Use Ralph to refactor the optimization service. Success when build succeeds and tests pass."

I will then:

1. Attempt the implementation
2. Run the success check
3. If it fails, analyze the error and try again
4. Repeat until success or you stop me

## Success Criteria Available

// turbo
Check current status with:

```bash
python ralph.py --check-complete --conditions build_succeeds api_starts tests_pass
```

| Condition | What It Checks |
|-----------|----------------|
| `build_succeeds` | App imports without errors |
| `tests_pass` | All pytest tests pass |
| `no_lint_errors` | Ruff linting passes |
| `api_starts` | FastAPI starts successfully |

## Automated Loops (No AI)

For automated CI/CD style loops:

// turbo

```bash
# Keep trying until tests pass
python ralph.py --run-tests

# Keep trying until build works
python ralph.py --run-build
```

## Example Ralph Session

**You say:** "Use Ralph to add a new /api/v1/swimmers endpoint. Success when tests pass."

**I do:**

1. ➡️ Create the endpoint in `routers/data.py`
2. ➡️ Add test in `tests/test_api.py`
3. ➡️ Run: `python ralph.py --check-complete --conditions tests_pass`
4. ❌ Test fails (missing model)
5. ➡️ Add Pydantic model
6. ➡️ Run check again
7. ✅ Tests pass - DONE!

## Manual Check Commands

// turbo

```bash
# Quick build check
python ralph.py --check-complete --conditions build_succeeds

# Full validation
python ralph.py --check-complete --conditions build_succeeds tests_pass api_starts

# Run test loop
.venv\Scripts\python.exe -m pytest tests/test_api.py -v
```

## Notes

- Logs saved to `.ralph/` directory
- Use Ctrl+C to manually stop any loop
- All conditions must pass for success
