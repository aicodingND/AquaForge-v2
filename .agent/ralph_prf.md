# Ralph Wiggum Technique - Product Requirements Framework (PRF)

## Overview

**Ralph** is an iterative AI development methodology that runs tasks in a continuous loop until success criteria are met. Named after the persistent (if sometimes misguided) Simpsons character, it embodies the principle: *"Keep trying until it works."*

## Core Philosophy

```
"I'm helping!" - Ralph Wiggum

Translation: Continuous, autonomous iteration with clear success criteria.
```

## Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Task Completion Rate | 95%+ | Tasks completed within max iterations |
| False Positive Rate | <5% | Tasks marked complete that aren't |
| Average Iterations | <10 | Iterations needed for typical tasks |
| Build Stability | 100% | No regressions introduced |

## Use Cases

### ✅ Ideal For Ralph

- Large refactors with clear end states
- Test-driven development (write test → implement until green)
- Batch operations (process all files matching X)
- Bug fixing with reproducible test cases
- API endpoint development
- Migration tasks with validation

### ❌ Not Ideal For Ralph

- Ambiguous requirements ("make it better")
- Subjective quality decisions ("make it pretty")
- Security-critical implementations (needs human review)
- Novel architecture decisions
- Tasks without testable success criteria

## Task Types

### Type 1: Test-Driven

```
Task: "Add /api/v1/swimmers endpoint"
Success: pytest tests/test_api.py::test_swimmers_endpoint passes
```

### Type 2: Build-Driven

```
Task: "Fix all import errors"
Success: python -m py_compile **/*.py returns 0
```

### Type 3: Lint-Driven

```
Task: "Fix all linting issues"
Success: ruff check . returns 0
```

### Type 4: Integration-Driven

```
Task: "Make E2E test pass"
Success: pytest tests/test_e2e.py passes
```

## Iteration Limits

| Task Complexity | Max Iterations | Escalation |
|-----------------|----------------|------------|
| Simple (1 file) | 5 | Ask for help |
| Medium (2-5 files) | 15 | Checkpoint & review |
| Large (5+ files) | 30 | Break into subtasks |
| Critical | 3 | Human review required |

## Guardrails

1. **Never delete production data**
2. **Never commit directly to main/master**
3. **Always run tests before declaring success**
4. **Stop if same error occurs 3+ times**
5. **Checkpoint progress every 5 iterations**

## Integration Points

### With This AI Agent

```
User: "Use Ralph to [task]. Success when [criteria]."
Agent: Implements → Checks → Loops until success
```

### With CI/CD

```yaml
# In GitHub Actions
- run: python ralph.py --check-complete --conditions tests_pass build_succeeds
```

### With Git Hooks

```bash
# pre-commit hook
python ralph.py --check-complete --conditions no_lint_errors
```
