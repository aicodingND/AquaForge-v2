# Coverage Examples

## Running Coverage - Step by Step

### Example 1: Basic Coverage Run

```bash
# Step 1: Navigate to project root
cd /Users/mpage1/Desktop/AquaForge/AquaForge_v1.0.0-next_2026-01-10

# Step 2: Activate virtual environment
source .venv/bin/activate

# Step 3: Run tests with coverage
pytest --cov

# Expected output:
# ============================= test session starts ==============================
# ...
# ---------- coverage: platform darwin, python 3.13 -----------
# Name                                          Stmts   Miss  Cover
# -----------------------------------------------------------------
# swim_ai_reflex/backend/core/scoring.py          245     12    95%
# swim_ai_reflex/backend/core/optimizer.py        189      8    96%
# ...
# -----------------------------------------------------------------
# TOTAL                                          2847    156    95%
# ========================= XX passed in X.XXs ==========================
```

### Example 2: HTML Report Generation

```bash
# Generate HTML report
pytest --cov --cov-report=html

# Expected output:
# ...
# Coverage HTML written to dir htmlcov

# Open in browser (macOS)
open htmlcov/index.html

# What you'll see:
# - Interactive file tree
# - Green/red highlighting of covered/uncovered lines
# - Per-file statistics
# - Drill-down to individual files
```

### Example 3: Fast Unit Test Coverage

```bash
# Skip slow and E2E tests for quick feedback
pytest --cov -m "not slow and not e2e" --cov-report=term-missing

# Expected output:
# ============================= test session starts ==============================
# collected 150 items / 45 deselected / 105 selected
# ...
# ---------- coverage: platform darwin, python 3.13 -----------
# Name                                  Stmts   Miss  Cover   Missing
# -------------------------------------------------------------------
# swim_ai_reflex/core/scoring.py          245     12    95%   45-47, 123
# swim_ai_reflex/core/optimizer.py        189      8    96%   234-236
# -------------------------------------------------------------------
# TOTAL                                  2847    156    95%
```

## Example Scenarios

### Scenario 1: Check Coverage for Specific Module

**Goal**: See coverage for the scoring module only

```bash
# Run coverage for specific module
pytest --cov=swim_ai_reflex.backend.core.scoring --cov-report=term-missing

# Output shows only scoring.py coverage:
# Name                                  Stmts   Miss  Cover   Missing
# -------------------------------------------------------------------
# swim_ai_reflex/core/scoring.py          245     12    95%   45-47, 123
```

### Scenario 2: Identify Uncovered Code

**Goal**: Find which files need more tests

```bash
# Show only files with missing coverage
pytest --cov --cov-report=term:skip-covered

# Output skips 100% covered files:
# Name                                  Stmts   Miss  Cover
# ---------------------------------------------------------
# swim_ai_reflex/core/scoring.py          245     12    95%
# swim_ai_reflex/services/data.py         156     45    71%
# ---------------------------------------------------------
# TOTAL                                  2847    156    95%
```

### Scenario 3: Coverage for Pull Request

**Goal**: Generate coverage report for CI/CD pipeline

```bash
# Generate XML report for upload to Codecov/Coveralls
pytest --cov --cov-report=xml --cov-report=term

# Creates coverage.xml file
ls -la coverage.xml
# -rw-r--r-- 1 user staff 45678 Feb  1 19:30 coverage.xml

# Upload to Codecov (in CI/CD)
bash <(curl -s https://codecov.io/bash)
```

### Scenario 4: Coverage Threshold Enforcement

**Goal**: Fail build if coverage drops below 80%

```bash
# Set fail threshold
pytest --cov --cov-fail-under=80

# If coverage is below 80%:
# FAIL Required test coverage of 80% not reached. Total coverage: 75.23%
# Exit code: 1

# If coverage is 80% or above:
# Exit code: 0
```

### Scenario 5: Coverage for New Feature Branch

**Goal**: Check coverage impact of new code

```bash
# On feature branch
git checkout feature/new-optimizer

# Run coverage and save report
pytest --cov --cov-report=json -o jsonfile=coverage-feature.json

# Switch to main and compare
git checkout main
pytest --cov --cov-report=json -o jsonfile=coverage-main.json

# Install diff-cover
pip install diff-cover

# See coverage diff
diff-cover coverage-feature.json --compare-branch=origin/main
```

## Real-World Examples

### Example: Adding Tests for Uncovered Code

**Before**: Coverage report shows missing lines

```bash
pytest --cov=swim_ai_reflex.backend.core.scoring --cov-report=term-missing

# Output:
# Name                           Stmts   Miss  Cover   Missing
# ------------------------------------------------------------
# swim_ai_reflex/core/scoring.py   245     12    95%   45-47, 123
```

**Action**: Add test for lines 45-47

```python
# tests/test_scoring.py

def test_edge_case_empty_entries():
    """Test scoring with empty entries list."""
    result = calculate_score(entries=[])
    assert result == 0  # Now covers lines 45-47
```

**After**: Re-run coverage

```bash
pytest --cov=swim_ai_reflex.backend.core.scoring --cov-report=term-missing

# Output:
# Name                           Stmts   Miss  Cover   Missing
# ------------------------------------------------------------
# swim_ai_reflex/core/scoring.py   245      9    96%   123
```

Lines 45-47 now covered!

### Example: Marking Code as Intentionally Uncovered

**Code with debug logic**:

```python
def optimize_entries(entries: list) -> dict:
    if not entries:
        return {}

    result = run_optimization(entries)

    # Debug helper - not needed in tests
    if os.getenv("DEBUG_OPTIMIZER"):  # pragma: no cover
        print_debug_info(result)      # pragma: no cover

    return result
```

**Coverage output** (debug code excluded):

```bash
# Name                              Stmts   Miss  Cover
# -----------------------------------------------------
# swim_ai_reflex/core/optimizer.py    189      0   100%
```

## Common Coverage Patterns

### Pattern 1: Parametrized Tests for Full Coverage

```python
import pytest

@pytest.mark.parametrize("event,expected_points", [
    ("100 Free", 7),      # Covers case 1
    ("200 Free", 7),      # Covers case 2
    ("100 Fly", 7),       # Covers case 3
    ("Invalid", 0),       # Covers error case
])
def test_event_points(event, expected_points):
    assert get_event_points(event) == expected_points
```

**Coverage**: 100% of event_points function

### Pattern 2: Testing Error Paths

```python
def test_invalid_time_format():
    """Test that invalid time format raises ValueError."""
    with pytest.raises(ValueError, match="Invalid time format"):
        parse_time("invalid")

    # Now covers the raise ValueError line
```

### Pattern 3: Mocking External Dependencies

```python
from unittest.mock import patch, MagicMock

def test_optimization_with_gurobi():
    """Test optimization without requiring Gurobi license."""

    with patch('swim_ai_reflex.core.optimizer.gurobi') as mock_gurobi:
        mock_gurobi.Model.return_value = MagicMock()

        result = run_optimization(entries)

        # Covers optimization code without Gurobi dependency
        assert result is not None
```

## Coverage Workflow Integration

### Pre-commit Hook

```bash
# .git/hooks/pre-commit
#!/bin/bash

# Run fast tests with coverage check
pytest --cov --cov-fail-under=80 -m "not slow and not e2e" -q

if [ $? -ne 0 ]; then
    echo "❌ Coverage check failed. Please add tests before committing."
    exit 1
fi

echo "✅ Coverage check passed"
```

### VS Code Task

```json
// .vscode/tasks.json
{
    "version": "2.0.0",
    "tasks": [
        {
            "label": "Run Tests with Coverage",
            "type": "shell",
            "command": "pytest --cov --cov-report=html",
            "group": {
                "kind": "test",
                "isDefault": true
            },
            "presentation": {
                "reveal": "always",
                "panel": "new"
            }
        }
    ]
}
```

### Makefile

```makefile
# Makefile

.PHONY: test coverage coverage-html coverage-report

test:
	pytest

coverage:
	pytest --cov --cov-report=term

coverage-html:
	pytest --cov --cov-report=html
	open htmlcov/index.html

coverage-report:
	pytest --cov --cov-report=html --cov-report=xml --cov-report=term
```

Usage:
```bash
make coverage-html  # Generate and open HTML report
```

## Interpreting Coverage Results

### Example Output Analysis

```
Name                                  Stmts   Miss  Cover   Missing
-------------------------------------------------------------------
swim_ai_reflex/core/scoring.py          245     12    95%   45-47, 123
swim_ai_reflex/core/optimizer.py        189      8    96%   234-236
swim_ai_reflex/services/data.py         156     45    71%   78-89, 145-156
-------------------------------------------------------------------
TOTAL                                   590     65    89%
```

**Analysis**:
- **scoring.py (95%)**: Excellent coverage, minor gaps at lines 45-47, 123
- **optimizer.py (96%)**: Excellent coverage, minor gap at lines 234-236
- **data.py (71%)**: Needs attention - 45 missed statements
- **TOTAL (89%)**: Good overall, but data.py needs improvement

**Action Plan**:
1. ✅ scoring.py & optimizer.py - Add tests for specific edge cases (lines 45-47, 123, 234-236)
2. ⚠️ data.py - Priority: Add tests for lines 78-89 and 145-156 (major gaps)

## Best Practices Demonstrated

1. **Start Simple**: Basic `pytest --cov` gets you started
2. **Iterate Quickly**: Use markers to skip slow tests during development
3. **Visualize**: HTML reports for detailed analysis
4. **Integrate**: Add to CI/CD with XML reports
5. **Enforce**: Use `--cov-fail-under` to maintain standards
6. **Document**: Mark intentionally untested code with `# pragma: no cover`

## Resources

- Full guide: [TESTING_AND_COVERAGE.md](./TESTING_AND_COVERAGE.md)
- Quick reference: [COVERAGE_QUICKSTART.md](./COVERAGE_QUICKSTART.md)
- Configuration: [COVERAGE_CONFIGURATION_SUMMARY.md](./COVERAGE_CONFIGURATION_SUMMARY.md)
