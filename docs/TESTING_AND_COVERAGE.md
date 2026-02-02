# Testing and Coverage Guide

## Overview

This guide explains how to run tests and generate coverage reports for the AquaForge project.

## Quick Start

```bash
# Run all tests with coverage
pytest --cov

# Run tests with HTML coverage report
pytest --cov --cov-report=html

# Open coverage report in browser
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
```

## Test Organization

### Test Markers

Tests are organized using pytest markers:

- `@pytest.mark.e2e` - End-to-end browser tests (requires running servers)
- `@pytest.mark.slow` - Slow running tests
- `@pytest.mark.integration` - Integration tests
- `@pytest.mark.timeout` - Tests with timeout requirements

### Test Types

```
tests/
├── test_*.py           - Unit tests (fast, no external dependencies)
├── test_e2e_*.py       - E2E tests (require frontend/backend servers)
├── test_integration.py - Integration tests
└── conftest.py         - Shared fixtures and configuration
```

## Running Tests

### Basic Usage

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/test_scoring.py

# Run specific test function
pytest tests/test_scoring.py::test_dual_meet_scoring

# Run tests matching pattern
pytest -k "scoring"
```

### Using Markers

```bash
# Skip E2E tests
pytest -m "not e2e"

# Skip slow tests
pytest -m "not slow"

# Run only integration tests
pytest -m integration

# Skip both E2E and slow tests
pytest -m "not e2e and not slow"
```

### Auto-Skip E2E Tests

E2E tests are automatically skipped if the frontend server is not running on localhost:3000. To run E2E tests:

1. Start the frontend: `cd frontend && npm run dev`
2. Start the backend: `python run_server.py --mode api`
3. Run tests: `pytest -m e2e`

## Coverage Reporting

### Configuration

Coverage is configured in `.coveragerc`:

- **Source**: `swim_ai_reflex` package
- **Omitted**: tests, migrations, database, __pycache__, virtual environments
- **Excluded lines**: pragmas, abstract methods, type checking imports

### Generate Coverage Reports

```bash
# Terminal report (default)
pytest --cov

# Terminal report with missing lines
pytest --cov --cov-report=term-missing

# HTML report (interactive, detailed)
pytest --cov --cov-report=html
open htmlcov/index.html

# XML report (for CI/CD)
pytest --cov --cov-report=xml

# Multiple report formats
pytest --cov --cov-report=html --cov-report=xml --cov-report=term
```

### Coverage Options

```bash
# Show only files with missing coverage (skip 100% covered)
pytest --cov --cov-report=term:skip-covered

# Fail if coverage is below threshold
pytest --cov --cov-fail-under=80

# Show branch coverage (if/else branches)
pytest --cov --cov-branch

# Coverage for specific module only
pytest --cov=swim_ai_reflex.backend.core.scoring
```

### Example Output

```
---------- coverage: platform darwin, python 3.11.7 -----------
Name                                          Stmts   Miss  Cover   Missing
---------------------------------------------------------------------------
swim_ai_reflex/backend/core/scoring.py          245     12    95%   45-47, 123
swim_ai_reflex/backend/core/optimizer.py        189      8    96%   234-236
swim_ai_reflex/backend/services/data.py         156     23    85%   78-89, 145
---------------------------------------------------------------------------
TOTAL                                          2847    156    95%
```

## CI/CD Integration

### GitHub Actions Example

```yaml
- name: Run tests with coverage
  run: |
    pytest --cov --cov-report=xml --cov-report=term

- name: Upload coverage to Codecov
  uses: codecov/codecov-action@v3
  with:
    files: ./coverage.xml
```

## Best Practices

### Writing Testable Code

1. **Keep functions small and focused**
   - Easier to test
   - Better coverage tracking

2. **Use dependency injection**
   ```python
   # Good - testable
   def calculate_score(entries: list, scorer: ScoringStrategy):
       return scorer.score(entries)

   # Bad - hard to test
   def calculate_score(entries: list):
       scorer = GurobiBinaryScorer()  # hardcoded dependency
       return scorer.score(entries)
   ```

3. **Separate I/O from logic**
   - Test logic without file operations
   - Mock I/O in tests

### Coverage Tips

1. **Don't chase 100% coverage**
   - Focus on critical paths
   - 80-90% is often sufficient

2. **Exclude boilerplate**
   ```python
   def __repr__(self):  # pragma: no cover
       return f"Swimmer({self.name})"
   ```

3. **Test edge cases**
   - Empty inputs
   - Boundary values
   - Error conditions

4. **Use parametrize for similar tests**
   ```python
   @pytest.mark.parametrize("time,expected", [
       ("52.34", 52.34),
       ("1:05.67", 65.67),
       ("10:23.45", 623.45),
   ])
   def test_time_parsing(time, expected):
       assert parse_time(time) == expected
   ```

## Troubleshooting

### Tests Skipped Unexpectedly

```bash
# Check which tests are being skipped
pytest --collect-only -m "e2e"

# Force run E2E tests (may fail without server)
pytest tests/test_e2e_*.py --no-skip
```

### Coverage Not Showing All Files

Ensure `.coveragerc` source path is correct:
```ini
[run]
source = swim_ai_reflex  # matches your package structure
```

### Coverage Data Not Combining

```bash
# Clear old coverage data
coverage erase

# Run tests
pytest --cov

# Manually combine if needed
coverage combine
coverage report
```

## Advanced Usage

### Parallel Test Execution

```bash
# Install pytest-xdist
pip install pytest-xdist

# Run tests in parallel (faster)
pytest -n auto --cov

# Note: may need to combine coverage after
coverage combine
```

### Continuous Coverage Monitoring

```bash
# Watch for file changes and re-run tests
pip install pytest-watch

# Auto-run tests on file changes
ptw --cov
```

### Coverage Diff (Compare Branches)

```bash
# Generate coverage on main branch
git checkout main
pytest --cov --cov-report=json -o jsonfile=coverage-main.json

# Generate coverage on feature branch
git checkout feature-branch
pytest --cov --cov-report=json -o jsonfile=coverage-feature.json

# Compare (requires diff-cover)
pip install diff-cover
diff-cover coverage-feature.json --compare-branch=main
```

## Resources

- [pytest documentation](https://docs.pytest.org/)
- [pytest-cov documentation](https://pytest-cov.readthedocs.io/)
- [Coverage.py documentation](https://coverage.readthedocs.io/)
- [AquaForge testing guide](./TESTING.md)

## Quick Reference

```bash
# Common commands
pytest                              # Run all tests
pytest -v                          # Verbose output
pytest -k "scoring"                # Run tests matching pattern
pytest -m "not slow"               # Skip slow tests
pytest --cov                       # Run with coverage
pytest --cov --cov-report=html     # HTML coverage report
pytest --lf                        # Run last failed tests
pytest --sw                        # Stop on first failure
pytest -x                          # Exit on first failure
pytest --pdb                       # Drop into debugger on failure
```
