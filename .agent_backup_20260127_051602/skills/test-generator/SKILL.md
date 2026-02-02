---
name: Test Generator
description: Generate comprehensive tests from code using TDD principles
triggers:
  - generate tests
  - write tests for
  - add test coverage
  - TDD
---

# Test Generator Skill 🧪

Use this skill to generate comprehensive tests following TDD principles.

---

## TDD Workflow

The optimal flow with AI assistance:

```
1. Describe feature/function needed
2. Generate failing tests FIRST
3. Confirm tests fail
4. Implement code to pass tests
5. Confirm tests pass
6. Refactor with confidence
```

---

## Test Generation Procedure

### Step 1: Understand the Target

Before generating tests:
- What is the function/class supposed to do?
- What are the inputs and outputs?
- What are the edge cases?
- What constraints apply?

### Step 2: Identify Test Categories

For each function, consider:

| Category    | Description              | Example                                       |
| ----------- | ------------------------ | --------------------------------------------- |
| Happy Path  | Normal expected inputs   | `test_score_calculation_basic`                |
| Edge Cases  | Boundary conditions      | `test_empty_roster`, `test_single_swimmer`    |
| Error Cases | Invalid inputs           | `test_invalid_team_raises`, `test_null_input` |
| Integration | Multiple components      | `test_optimizer_with_scorer`                  |
| Performance | Speed/memory (if needed) | `test_optimization_under_1_second`            |

### Step 3: Generate Tests

Use this template for pytest:

```python
"""Tests for [module/function name]."""
import pytest
from [module] import [function_or_class]


class TestFunctionName:
    """Tests for function_name()."""

    # Happy path tests
    def test_basic_usage(self):
        """Test normal expected usage."""
        result = function_name(valid_input)
        assert result == expected_output

    def test_another_valid_case(self):
        """Test another valid scenario."""
        pass

    # Edge cases
    def test_empty_input(self):
        """Test behavior with empty input."""
        result = function_name([])
        assert result == []  # or expected behavior

    def test_boundary_value(self):
        """Test boundary conditions."""
        pass

    # Error cases
    def test_invalid_input_raises(self):
        """Test that invalid input raises appropriate error."""
        with pytest.raises(ValueError):
            function_name(invalid_input)

    def test_null_input_raises(self):
        """Test that None raises appropriate error."""
        with pytest.raises(TypeError):
            function_name(None)


# Fixtures
@pytest.fixture
def sample_data():
    """Provide sample test data."""
    return {...}
```

---

## AquaForge-Specific Test Patterns

### Scoring Tests

```python
class TestScoring:
    """Tests for scoring calculations."""

    def test_dual_meet_individual_scoring(self):
        """Verify dual meet individual scoring: 8-6-5-4-3-2-1."""
        scorer = DualMeetScorer()
        assert scorer.get_points(place=1, event_type="individual") == 8
        assert scorer.get_points(place=7, event_type="individual") == 1
        assert scorer.get_points(place=8, event_type="individual") == 0

    def test_vcac_relay_scoring(self):
        """Verify VCAC relay scoring: 16-13-12-11-10-9-7-5-4-3-2-1."""
        scorer = VCACScorer()
        assert scorer.get_points(place=1, event_type="relay") == 16
        assert scorer.get_points(place=12, event_type="relay") == 1
```

### Optimization Tests

```python
class TestOptimization:
    """Tests for optimization constraints."""

    def test_max_two_individual_events(self):
        """Verify no swimmer exceeds 2 individual events."""
        result = optimize(roster)
        for swimmer in result.assignments:
            individual_count = sum(
                1 for e in swimmer.events
                if e.event_type == "individual"
            )
            assert individual_count <= 2

    def test_relay_3_counts_at_vcac(self):
        """Verify 400 FR counts as individual slot at VCAC."""
        result = optimize(roster, meet_type="vcac")
        for swimmer in result.assignments:
            if "400 Free Relay" in swimmer.events:
                other_individual = sum(
                    1 for e in swimmer.events
                    if e.event_type == "individual"
                )
                assert other_individual <= 1  # Relay 3 takes one slot
```

### API Tests

```python
class TestAPI:
    """Tests for API endpoints."""

    def test_optimize_endpoint_success(self, client, sample_roster):
        """Test successful optimization request."""
        response = client.post(
            "/api/v1/optimize",
            json={"roster": sample_roster, "mode": "dual"}
        )
        assert response.status_code == 200
        assert "our_score" in response.json()

    def test_optimize_endpoint_validation(self, client):
        """Test validation of invalid request."""
        response = client.post(
            "/api/v1/optimize",
            json={"roster": []}  # Empty roster
        )
        assert response.status_code == 422
```

---

## Coverage Targets

For AquaForge, target these coverage levels:

| Component                | Target | Priority |
| ------------------------ | ------ | -------- |
| Scoring calculations     | 100%   | Critical |
| Optimization constraints | 100%   | Critical |
| API endpoints            | 90%    | High     |
| Data validation          | 90%    | High     |
| Frontend components      | 70%    | Medium   |
| Utility functions        | 80%    | Medium   |

---

## Running Generated Tests

```bash
# Run specific test file
python -m pytest tests/test_new_feature.py -v

# Run with coverage
python -m pytest tests/ --cov=swim_ai_reflex --cov-report=html

# Run marked tests only
python -m pytest -m "scoring" -v
```

---

## Integration with Workflow

This skill integrates with `/ralph` workflow:

```markdown
### Step 1: Generate Tests
// skill: test-generator
Generate tests for [feature]

### Step 2: Verify Failure
// turbo
pytest tests/test_new_feature.py -v  # Should FAIL

### Step 3: Implement
[Implementation here]

### Step 4: Verify Pass
// turbo
pytest tests/test_new_feature.py -v  # Should PASS
```

---

_Skill: test-generator | Version: 1.0 | Pattern: TDD_
