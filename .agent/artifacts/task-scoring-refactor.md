# Task: Scoring System Refactor & Optimization Routing

**Status:** ✅ Phase 1-2 Complete
**Created:** 2026-02-01
**Updated:** 2026-02-01 22:58
**Priority:** High (VCAC Championship Feb 7, 2026)

---

## Objective

Refactor the AquaForge scoring and optimization system to:

1. ✅ Properly separate dual meet vs championship scoring
2. ✅ Add regression guards (tests) to prevent future breakage
3. 🟡 Route optimization correctly by meet type and event type
4. ✅ Ensure relay scoring is correct for all meet/event combinations
5. 🟡 Include all optimization algorithms (Gurobi, Aqua, Heuristic, Stackelberg)

---

## Completed Work

### Phase 1: Fix Forfeit Logic ✅ COMPLETE

- [x] Identified root cause: `pd.concat` creating NaN for `scoring_eligible`
- [x] Fixed `dual_meet_scoring.py` to recalculate from grade
- [x] Exhibition swimmers (grade < 8) now correctly get 0 points
- [x] Forfeit points go to team with eligible swimmers

### Phase 2: Relay Scoring Verification ✅ COMPLETE

- [x] Added 6 relay-specific tests
- [x] Verified dual meet relays use [10, 5, 3]
- [x] Verified VCAC championship relays use 2x individual points
- [x] Verified VISAA State relays use correct 16-place table

### Phase 3: Regression Test Suite ✅ COMPLETE

- [x] Created `tests/test_scoring_constraints.py`
- [x] 20 tests covering all scoring rules
- [x] All tests passing

### Phase 4: Documentation ✅ COMPLETE

- [x] Updated `KNOWLEDGE_BASE.md` with bug fix details
- [x] Created this task artifact for tracking

---

## Remaining Work

### Phase 5: Optimization Router (Next)

- [ ] Create `MeetOptimizationRouter` class
- [ ] Route by meet type: `dual` → Gurobi/Aqua, `championship` → ChampionshipStrategy
- [ ] Include Aqua optimizer as zero-cost Gurobi alternative
- [ ] Add tests for routing logic

---

## Test Status

```text
tests/test_scoring_constraints.py - 20/20 PASSING ✅

├── TestDualMeetScoringConstraints (6 tests)
├── TestForfeitPointsConstraints (2 tests)
├── TestChampionshipScoringConstraints (4 tests)
├── TestRelayScoringConstraints (6 tests)
└── TestScoringModeRouting (2 tests)

Full Suite: 277 passed, 16 skipped ✅
E2E Test: 232 total points, Seton 124 ✅
```

---

## Files Modified

| File                          | Change                             | Status |
| ----------------------------- | ---------------------------------- | ------ |
| `dual_meet_scoring.py`        | Fixed scoring_eligible calculation | ✅      |
| `KNOWLEDGE_BASE.md`           | Added bug fix documentation        | ✅      |
| `test_scoring_constraints.py` | Created 20 regression tests        | ✅      |
| `test_e2e_final.py`           | Updated score range expectation    | ✅      |

---

## Optimization Algorithms Available

| Algorithm        | File                       | Use Case              | Status      |
| ---------------- | -------------------------- | --------------------- | ----------- |
| **Gurobi**       | `gurobi_strategy.py`       | Dual meets (exact)    | ✅ Working   |
| **Aqua**         | `aqua_optimizer.py`        | All meets (zero-cost) | ✅ Available |
| **Heuristic**    | `heuristic_strategy.py`    | Quick fallback        | ✅ Available |
| **Championship** | `championship_strategy.py` | Multi-team            | ✅ Available |
