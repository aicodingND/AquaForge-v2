# E2E Dataflow Overhaul - Fix Plan

**Date:** January 16, 2026  
**Status:** In Progress  
**Priority:** Critical

---

## 🚨 Issues Identified

### 1. **Scoring Input/Output Mismatch (270-0 Bug)**

**Root Cause:**

- `optimization_service.py` line 646 returned `best_scored` (Seton only) as details
- But line 637 calculated `final_totals` from `combined_lineup` (both teams)
- Router expected details to have both teams' scores for matching swimmers to points

**Impact:**

- Scores showing as "270 - 0" or other inflated values
- Opponent scores not displaying correctly
- Event-level scoring breakdown broken

**Fix Applied:**

- ✅ Changed line 646 to use `final_scored_df` instead of `best_scored`
- This ensures details contain BOTH teams with proper dual meet scoring

---

### 2. **Championship Mode Incomplete Integration**

**Root Cause:**

- Championship mode partially implemented in router (lines 134-206)
- Missing time population (line 189 TODO)
- Response formatting incomplete
- No proper separation between dual meet and championship workflows

**Impact:**

- Championship mode doesn't work properly
- Scores not calculated correctly for championship format
- Missing event assignments and recommendations

**Fixes Needed:**

1. Complete championship response formatting
2. Add proper time lookup from entries
3. Implement separate championship scoring display
4. Add championship-specific validation

---

### 3. **Event Name Normalization Issues**

**Root Cause:**

- Fuzzy matching attempts in router (lines 312-367) indicate event name mismatches
- Different parts of system use different event naming conventions
- `normalize_event_name` imported but unused in optimization_service.py

**Impact:**

- Event details not matching between lineup and scoring
- Fuzzy matching failures causing 0 points for some events
- Inconsistent event names across system

**Fixes Needed:**

1. Apply consistent event normalization throughout
2. Use `normalize_event_name` in optimization_service.py
3. Ensure event names match between all components

---

### 4. **Dual Meet Walkthrough Issues**

**Root Cause:**

- Complex fuzzy matching logic in router suggests data structure mismatches
- Details DataFrame structure doesn't align with lineup DataFrame
- Team name normalization inconsistent

**Impact:**

- Walkthrough fails to display proper event-by-event breakdown
- Swimmer-to-score matching failures
- Missing opponent information

**Fixes Needed:**

1. Simplify event matching logic
2. Ensure consistent DataFrame structures
3. Add better error handling and logging

---

## 🔧 Implementation Plan

### Phase 1: Core Scoring Fix ✅

- [x] Fix details field in optimization_service.py (use final_scored_df)
- [ ] Test dual meet scoring end-to-end
- [ ] Verify scores are correct (not inflated)

### Phase 2: Event Normalization

- [ ] Apply normalize_event_name consistently
- [ ] Update optimization_service.py to normalize events
- [ ] Update router to use normalized events
- [ ] Remove fuzzy matching fallbacks

### Phase 3: Championship Mode Complete Integration

- [ ] Create separate championship response formatter
- [ ] Add time lookup from entries
- [ ] Implement championship scoring display
- [ ] Add championship-specific constraints
- [ ] Test championship mode end-to-end

### Phase 4: Dual Meet Walkthrough Fix

- [ ] Simplify router event matching logic
- [ ] Ensure DataFrame structures align
- [ ] Add comprehensive logging
- [ ] Test dual meet walkthrough

### Phase 5: Testing & Validation

- [ ] Create E2E test for dual meet mode
- [ ] Create E2E test for championship mode
- [ ] Verify all scores are accurate
- [ ] Test with real data

---

## 📝 Code Changes Made

### File: `optimization_service.py`

**Line 639-652:** Changed details field

```python
# OLD (BROKEN):
"details": best_scored.to_dict("records")
if best_scored is not None
else [],

# NEW (FIXED):
"details": final_scored_df.to_dict("records")
if final_scored_df is not None and not final_scored_df.empty
else [],
```

**Impact:** Fixes the 270-0 scoring bug by ensuring details contain both teams

---

## 🧪 Testing Checklist

- [ ] Dual meet optimization returns correct scores
- [ ] Opponent scores display correctly
- [ ] Event-by-event breakdown shows both teams
- [ ] Championship mode works independently
- [ ] No fuzzy matching warnings in logs
- [ ] All event names normalized consistently

---

## 📊 Success Criteria

1. **Dual Meet Mode:**

   - Scores display correctly (e.g., "145 - 132" not "270 - 0")
   - Both teams show in event breakdown
   - All swimmers matched to their points
   - No fuzzy matching needed

2. **Championship Mode:**

   - Separate workflow from dual meet
   - Proper championship scoring (1st=20, 2nd=17, etc.)
   - Event assignments complete with times
   - Recommendations generated

3. **Overall:**
   - No errors in logs
   - Fast response times
   - Consistent event naming
   - Clean code without workarounds

---

_Last Updated: 2026-01-16 18:05 EST_
