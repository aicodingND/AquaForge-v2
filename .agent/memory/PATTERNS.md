# Successful Patterns 🎯

Capture patterns that work well for reuse.

---

## Format

```markdown
## [Date] Pattern: {name}

**Context:** {when this applies}
**What Worked:** {description}
**Reuse When:** {conditions}
**Example:**
```python
# code snippet
```
```

---

## Logged Patterns

<!-- Append new entries below this line -->

## 2026-02-01 Pattern: Router with Fallback Strategy

**Context:** Selecting between multiple optimization strategies
**What Worked:** Primary strategy (Aqua) with automatic fallback to Gurobi
**Reuse When:** Any scenario requiring primary/fallback selection
**Example:**
```python
def get_strategy(self, meet_type: str) -> BaseStrategy:
    # Primary: Aqua (zero cost)
    if not self.prefer_gurobi:
        return AquaOptimizer(profile=self._get_profile(meet_type))

    # Fallback: Gurobi (if available and preferred)
    if self.has_gurobi():
        return GurobiStrategy()

    return AquaOptimizer(...)  # Ultimate fallback
```

## 2026-02-01 Pattern: Parallel Optimizer Validation

**Context:** Validating new optimizer against established one
**What Worked:** Run both in parallel, compare results before switching
**Reuse When:** Replacing critical algorithms
**Example:**
```python
# Run both
aqua_result = aqua_optimizer.optimize(roster)
gurobi_result = gurobi_optimizer.optimize(roster)

# Compare
assert abs(aqua_result.score - gurobi_result.score) < threshold
```

## 2026-02-02 Pattern: Verify Domain Rules Against Authoritative Sources

**Context:** Domain-specific rules (scoring, eligibility) documented in multiple places
**What Worked:** Before trusting internal docs, verify against authoritative external sources (NFHS rules, NCAA Rule 7, USA Swimming, governing body websites). Cross-check code against docs — found 3 doc files with swapped scoring tables that the code had correct.
**Reuse When:** Any domain rule that affects scoring, eligibility, or constraints
**Checklist:**
1. Read the code implementation first (it may be correct)
2. Search for authoritative sources (governing body rules, official PDFs)
3. Cross-reference all internal docs against the authoritative source
4. Fix any discrepancies, noting the correction date and source
5. Add regression tests to protect the verified behavior

## 2026-02-02 Pattern: Multi-Layer Code Audit for Rule Enforcement

**Context:** A business rule (diving counts as individual event) needed verification
**What Worked:** Traced the rule through ALL code layers: rules definition, scoring engine, optimizer strategies (3 different ones), validation, and tests. Found it was correctly enforced everywhere.
**Reuse When:** Verifying a critical business rule is consistently enforced
**Layers to check:**
1. Rules definition (rules.py)
2. Scoring engine (scoring.py)
3. Each optimizer strategy (championship, gurobi, aqua)
4. Validation layer (validation.py, scoring_validator.py)
5. Tests (existing coverage)

## 2026-02-02 Pattern: Live Meet Tracker Architecture

**Context:** Real-time championship meet tracking during competition
**What Worked:** Service + API separation with in-memory state
**Reuse When:** Building real-time tracking/monitoring systems
**Example:**
```python
# Service layer (business logic)
class LiveMeetTracker:
    def record_result(...) -> RecordedResult
    def get_current_standings() -> LiveStandings
    def get_clinch_scenarios() -> List[ClinchScenario]

# API layer (HTTP endpoints)
@router.post("/result")
def record_result(request) -> Dict:
    tracker = _get_tracker(request.meet_name)
    result = tracker.record_result(...)
    return serialize(result)
```

Key decisions:
- In-memory tracker instances (fast, simple for single-server)
- Psych sheet provides initial projections
- Combines actual + projected for live standings
- Clinch scenarios guide coaching decisions
