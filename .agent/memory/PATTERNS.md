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

## High-Value Repeats (proven improvements — always apply)

| Pattern | When to Apply | Payoff |
|---------|---------------|--------|
| **Callback ref pattern** | Any custom hook accepting `on*` callbacks | Eliminates infinite re-render loops |
| **Verify domain rules vs authoritative sources** | Any scoring/eligibility/constraint change | Caught 3 swapped scoring tables + wrong grade rules |
| **Multi-layer code audit** | Verifying a business rule is enforced | Confirmed diving rule across 5 code layers — zero gaps |
| **Primary + fallback strategy** | Any service with alternative backends | Saved $10K/yr Gurobi license, zero downtime |
| **Read the file before editing** | Every code change | Caught `// ...` broken JSX instantly |

**On every frontend task:** Apply callback ref pattern to any new custom hook with callbacks.
**On every domain-rule task:** Verify against external source (NFHS, NCAA, VISAA) before documenting.

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

## 2026-02-02 Pattern: Heuristic Format Detection Facade
**Context:** Parsing multiple uploaded file formats (CSV, generic text, HTML) with a single entry point.
**Solution:** `PsychSheetParser.parse()` acts as a facade. checks file extension or content signatures (e.g., regex match for "HyTek") to select strategy.
**Reuse:** When building import services for ambiguous inputs.

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

## 2026-02-02 Pattern: Callback Ref for Stable React Hook Dependencies

**Context:** Inline callbacks passed to custom hooks cause infinite re-render loops when included in `useEffect`/`useCallback` dependency arrays.
**What Worked:** Store callbacks in `useRef` and update synchronously during render. Effects read `ref.current` instead of the callback directly — the ref identity never changes, so effects stay stable.
**Reuse When:** Any custom hook accepts callback options (`onLoad`, `onSave`, `onError`, `onChange`) that callers define inline.
**Example:**
```tsx
function useMyHook({ onLoad, onSave }: Options) {
  // Stable refs — updated every render, but identity never changes
  const onLoadRef = useRef(onLoad);
  const onSaveRef = useRef(onSave);
  onLoadRef.current = onLoad;
  onSaveRef.current = onSave;

  useEffect(() => {
    // ✅ Only fires when `key` changes, not on every render
    const data = localStorage.getItem(key);
    if (data) onLoadRef.current?.(JSON.parse(data));
  }, [key]);

  const save = useCallback((data) => {
    localStorage.setItem(key, JSON.stringify(data));
    onSaveRef.current?.(data);
  }, [key]); // ✅ Stable — no callback in deps
}
```
**Why it works:** `useRef` returns a mutable object with a stable identity across renders. Assigning `.current` during render is safe (synchronous, no side effects). React never "sees" the ref change, so dependency arrays remain stable.
**Anti-pattern it replaces:**
```tsx
// ❌ onLoad is new every render → effect fires every render
useEffect(() => { onLoad?.(data); }, [key, onLoad]);
```
