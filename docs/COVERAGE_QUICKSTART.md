# Coverage Quick Start

## Installation Check

```bash
# Verify pytest-cov is installed
pip show pytest-cov

# If not installed
pip install -r requirements-dev.txt
```

## Basic Coverage Commands

```bash
# Run all tests with coverage
pytest --cov

# Generate HTML report
pytest --cov --cov-report=html

# Open report in browser
open htmlcov/index.html  # macOS
```

## Configuration Files

### `.coveragerc` (Coverage Settings)
- **Source**: `swim_ai_reflex` package
- **HTML Output**: `htmlcov/` directory
- **XML Output**: `coverage.xml`

### `pytest.ini` (Test Settings)
- **Test Path**: `tests/` directory
- **Markers**: e2e, slow, integration, timeout
- **Options**: Short traceback, quiet mode, strict markers

## Common Workflows

### Run Tests with Coverage
```bash
# Fast: Unit tests only (skip slow/e2e)
pytest --cov -m "not slow and not e2e"

# Full: All tests with HTML report
pytest --cov --cov-report=html

# CI: Generate XML for upload
pytest --cov --cov-report=xml
```

### View Coverage
```bash
# Terminal summary
pytest --cov --cov-report=term

# Show missing lines
pytest --cov --cov-report=term-missing

# Interactive HTML report
pytest --cov --cov-report=html && open htmlcov/index.html
```

### Coverage by Module
```bash
# Core module only
pytest --cov=swim_ai_reflex.backend.core

# Multiple modules
pytest --cov=swim_ai_reflex.backend.core --cov=swim_ai_reflex.backend.services
```

## Test Markers

```bash
# Skip E2E tests (require running servers)
pytest --cov -m "not e2e"

# Skip slow tests
pytest --cov -m "not slow"

# Run only integration tests
pytest --cov -m integration

# Fast feedback loop (skip slow & e2e)
pytest --cov -m "not slow and not e2e"
```

## Coverage Targets

| Module | Target | Status |
|--------|--------|--------|
| `core/scoring.py` | 90%+ | Critical |
| `core/optimizer.py` | 85%+ | Critical |
| `services/*.py` | 80%+ | Important |
| `api/routers/*.py` | 75%+ | Important |
| `utils/*.py` | 70%+ | Nice to have |

## Interpreting Results

```
---------- coverage: platform darwin, python 3.11.7 -----------
Name                          Stmts   Miss  Cover   Missing
-----------------------------------------------------------
swim_ai_reflex/core/scoring.py  245     12    95%   45-47, 123
-----------------------------------------------------------
TOTAL                          2847    156    95%
```

- **Stmts**: Total statements
- **Miss**: Missed statements
- **Cover**: Coverage percentage
- **Missing**: Line numbers not covered

## Tips

1. **Focus on critical paths first** (scoring, optimization)
2. **Use `skip_covered = true`** to see only uncovered files
3. **Add `# pragma: no cover`** for debug code
4. **Generate HTML reports** for detailed analysis

## Troubleshooting

### "No data to report"
```bash
# Clear old coverage data
coverage erase
pytest --cov
```

### E2E tests skipped
```bash
# Start servers first
cd frontend && npm run dev  # Terminal 1
python run_server.py --mode api  # Terminal 2
pytest --cov -m e2e  # Terminal 3
```

### Coverage not showing all files
Check `.coveragerc` source path matches your package structure.

## Next Steps

- Read [full testing guide](./TESTING_AND_COVERAGE.md)
- Set up pre-commit hooks with coverage checks
- Configure CI/CD pipeline with coverage upload
- Set coverage thresholds: `pytest --cov --cov-fail-under=80`
