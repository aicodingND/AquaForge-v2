# Ralph Guidelines - Best Practices

## Starting a Ralph Session

### 1. Define Clear Success Criteria

```
❌ Bad:  "Make the API better"
✅ Good: "Add /api/v1/swimmers endpoint. Success: test_swimmers passes"
```

### 2. Specify Scope

```
❌ Bad:  "Fix the app"
✅ Good: "Fix import errors in swim_ai_reflex/backend/api/"
```

### 3. Set Iteration Limit

```
❌ Bad:  "Keep trying forever"
✅ Good: "Max 10 iterations, then checkpoint"
```

## During Ralph Execution

### DO ✅

- Run tests after each change
- Make small, incremental changes
- Log what you're attempting
- Check for regressions
- Commit working checkpoints

### DON'T ❌

- Make multiple unrelated changes at once
- Skip the success check
- Ignore test failures
- Keep trying the same failing approach
- Expand scope mid-task

## Task Templates

### Template: Add API Endpoint

```
Task: Add [METHOD] /api/v1/[path] endpoint
Files: routers/[module].py, tests/test_api.py
Success: pytest tests/test_api.py::Test[Module]::test_[name] passes
Max Iterations: 10
```

### Template: Fix Bug

```
Task: Fix [error message/behavior]
Files: [file where error occurs]
Success: [test that reproduces bug] passes
Max Iterations: 5
```

### Template: Refactor Module

```
Task: Refactor [module] to [improvement]
Files: [module]/*.py, tests/test_[module].py
Success: All existing tests pass + no lint errors
Max Iterations: 20
Checkpoint: Every 5 iterations
```

### Template: Add Feature

```
Task: Implement [feature description]
Files: [relevant files]
Success: [feature test] passes
Max Iterations: 15
```

## Iteration Patterns

### Pattern: Test First (TDD)

```
1. Write failing test
2. Run test (confirm it fails)
3. Implement minimum code to pass
4. Run test (confirm it passes)
5. Refactor if needed
6. Run test (confirm still passes)
```

### Pattern: Fix Forward

```
1. Identify error
2. Make targeted fix
3. Run full test suite
4. If new errors, fix those too
5. Repeat until clean
```

### Pattern: Bisect

```
1. Find last known good state
2. Identify what changed
3. Revert half the changes
4. Test - if passes, problem in reverted half
5. Binary search until found
```

## Communication

### Progress Updates

Every 3-5 iterations, report:

- What was attempted
- Current status
- Remaining blockers
- Next approach

### Completion Report

When done:

- Summary of changes
- Files modified
- Tests added/modified
- Any follow-up needed

### Escalation

When stuck:

- What was tried
- Why it didn't work
- Suggested alternatives
- Request for guidance

## Quality Checks

Before each iteration completes:

```bash
# Build check
python -c "from swim_ai_reflex.backend.api.main import api_app"

# Test check
python -m pytest tests/test_api.py -v --tb=short

# Lint check (optional)
ruff check . --fix
```

## Recovery Procedures

### If Tests Start Failing

1. Don't panic
2. Check which test failed
3. Check if it's related to your change
4. If unrelated, might be flaky - rerun
5. If related, revert and try different approach

### If Build Breaks

1. Check the error message
2. Usually import/syntax error
3. Fix the specific error
4. Rerun build check
5. Don't proceed until build passes

### If Stuck in Loop

1. Stop after 3 identical errors
2. Document what was tried
3. Consider alternative approaches
4. Ask for human input if needed
