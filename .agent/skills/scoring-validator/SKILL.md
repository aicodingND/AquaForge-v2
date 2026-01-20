---
name: Scoring Validator
description: Validates VISAA/VCAC scoring calculations and identifies point discrepancies
triggers:
  - scoring bugs
  - point discrepancies
  - "X - 0" score display
  - wrong point totals
---

# Scoring Validator Skill 🎯

Use this skill when validating scoring calculations or debugging point-related issues.

---

## Quick Reference: Scoring Tables

### Dual Meet (Top 7 Score)

| Place      | 1st | 2nd | 3rd | 4th | 5th | 6th | 7th |
| ---------- | --- | --- | --- | --- | --- | --- | --- |
| Individual | 8   | 6   | 5   | 4   | 3   | 2   | 1   |
| Relay      | 10  | 5   | 3   | -   | -   | -   | -   |

**Total per dual meet: 315 points** (8 indiv × 29 + 3 relays × 18 + diving 29)

### VCAC Championship (Top 12 Score)

| Place      | 1st | 2nd | 3rd | 4th | 5th | 6th | 7th | 8th | 9th | 10th | 11th | 12th |
| ---------- | --- | --- | --- | --- | --- | --- | --- | --- | --- | ---- | ---- | ---- |
| Individual | 32  | 26  | 24  | 22  | 20  | 18  | 14  | 10  | 8   | 6    | 4    | 2    |
| Relay      | 16  | 13  | 12  | 11  | 10  | 9   | 7   | 5   | 4   | 3    | 2    | 1    |

### VISAA States Championship (Top 16 Score)

**Finals:** 40-34-32-30-28-26-24-22-18-14-12-10-8-6-4-2  
**Consolation:** 20-17-16-15-14-13-12-11-9-7-6-5-4-3-2-1

---

## Validation Procedure

### Step 1: Identify Scoring Context

Determine which scoring table applies:
- Is this a dual meet or championship?
- If championship: VCAC or VISAA?
- How many places score?

### Step 2: Verify Point Calculations

For each event, check:
```python
# Example validation
def validate_event_score(place: int, event_type: str, meet_type: str) -> int:
    """Returns expected points for given placement."""
    if meet_type == "dual":
        if event_type == "relay":
            return {1: 10, 2: 5, 3: 3}.get(place, 0)
        else:
            return {1: 8, 2: 6, 3: 5, 4: 4, 5: 3, 6: 2, 7: 1}.get(place, 0)
    elif meet_type == "vcac":
        if event_type == "relay":
            table = [16, 13, 12, 11, 10, 9, 7, 5, 4, 3, 2, 1]
        else:
            table = [32, 26, 24, 22, 20, 18, 14, 10, 8, 6, 4, 2]
        return table[place - 1] if 1 <= place <= 12 else 0
```

### Step 3: Check Common Bugs

1. **"X - 0" Display Bug**
   - Cause: Team name normalization failure
   - Fix: Ensure teams are named "seton" and "opponent" for dual meets
   - Location: `optimization_service.py` before `full_meet_scoring()`

2. **Exhibition Scoring**
   - Grades 7-8 should NOT contribute points
   - Check `is_exhibition` flag

3. **Missing Event Points**
   - Verify all events are included
   - Check for relay vs individual confusion

4. **Wrong Placement Lookup**
   - Off-by-one errors in table lookups
   - VISAA uses 1-16 indexing, not 0-15

### Step 4: Cross-Reference Sources

- Official: `setonswimming.org/so-how-is-a-high-school-meet-scored-anyway/`
- VCAC announcement for championship scoring
- `.agent/KNOWLEDGE_BASE.md` for stored rules

---

## Common Fixes

### Team Name Normalization
```python
# CORRECT - use assignment, not fillna
best_lineup["team"] = "seton"
opponent_lineup["team"] = "opponent"

# WRONG - fillna only sets null values
# best_lineup["team"].fillna("seton")  # Doesn't work!
```

### Championship Display
```tsx
// Check meet mode before displaying
if (meetMode === 'championship') {
  // Show "Projected Score: X"
} else {
  // Show "Team A: X - Team B: Y"
}
```

---

## Verification Checklist

- [ ] Correct scoring table selected for meet type
- [ ] Team names normalized before scoring
- [ ] Exhibition swimmers excluded from point totals
- [ ] All events counted (8 individual + 3 relay + diving)
- [ ] Place lookups use correct indexing
- [ ] Frontend displays format appropriate for meet type

---

_Skill: scoring-validator | Version: 1.0_
