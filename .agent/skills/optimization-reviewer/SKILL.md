---
name: Optimization Reviewer
description: Reviews optimizer output quality and validates lineup recommendations
triggers:
  - optimizer output review
  - lineup validation
  - suspicious optimization results
  - point totals seem wrong
---

# Optimization Reviewer Skill 📊

Use this skill to review and validate optimizer output quality.

---

## Quick Validation Checks

### 1. Constraint Compliance

| Constraint              | Check                            |
| ----------------------- | -------------------------------- |
| Max 2 individual events | No swimmer exceeds limit         |
| Relay 3 penalty (VCAC)  | 400 FR counts as individual slot |
| Diving counts           | Adds to individual limit         |
| Max 4 events total      | Individual + relay ≤ 4           |
| Grade restrictions      | 7-8th graders marked exhibition  |

### 2. Point Plausibility

| Meet Type         | Expected Total Range   |
| ----------------- | ---------------------- |
| Dual meet         | 150-315 pts (one team) |
| VCAC Championship | 200-500 pts (one team) |
| VISAA States      | 300-800 pts (one team) |

---

## Review Procedure

### Step 1: Load Optimization Result

```python
# Expected result structure
{
    "status": "success",
    "meet_mode": "championship" | "dual",
    "our_lineup": [...],
    "opponent_lineup": [...] | null,
    "our_projected_score": int,
    "opponent_projected_score": int | null,
    "events": [
        {
            "event_name": str,
            "our_entries": [...],
            "projected_score": int
        }
    ]
}
```

### Step 2: Validate Per-Swimmer Constraints

```python
def validate_swimmer_constraints(lineup):
    for swimmer in swimmers:
        individual_events = count_individual_events(swimmer)
        relay_events = count_relay_events(swimmer)
        is_diver = swimmer.has_diving
        
        # Check individual limit
        effective_individual = individual_events + (1 if is_diver else 0)
        relay_penalty = max(0, relay_events - 2)  # Only relay 3 costs
        total_effective = effective_individual + relay_penalty
        
        assert total_effective <= 2, f"{swimmer.name} exceeds individual limit"
        assert individual_events + relay_events <= 4, f"{swimmer.name} exceeds total limit"
```

### Step 3: Validate Point Calculations

For each event:
1. Verify placement predictions are reasonable
2. Check scoring table is correct for meet type
3. Confirm exhibition swimmers have 0 points

### Step 4: Strategic Review

#### Red Flags
- ⚠️ Top swimmer doing 0 events (unless relay-only strategy)
- ⚠️ Weak swimmer in high-scoring event slot
- ⚠️ A-relay missing expected top swimmers
- ⚠️ Exhibition swimmer displacing varsity scorer

#### Good Signs
- ✅ Top swimmers in their best 1-2 events
- ✅ Good depth coverage across events
- ✅ Relay optimization preserves best splits
- ✅ Fatigue-aware event distribution

---

## Common Optimization Issues

### Issue: Suboptimal Relay Selection

**Symptoms:** B-relay faster than A-relay, or key swimmer missing from relay

**Diagnosis:**
```python
# Check relay split times
def audit_relay(relay_result):
    a_relay_splits = [s.best_split for s in relay_result.a_relay]
    b_relay_splits = [s.best_split for s in relay_result.b_relay]
    
    a_total = sum(a_relay_splits)
    b_total = sum(b_relay_splits)
    
    if b_total < a_total:
        print(f"WARNING: B relay ({b_total}) faster than A relay ({a_total})")
```

**Fix:** Review Hungarian algorithm assignment, check for missing split data

### Issue: Expected High-Scorer Not Assigned

**Symptoms:** Known top swimmer has 0 or 1 events

**Diagnosis:**
1. Check if swimmer has valid times in system
2. Verify constraint compliance allows more events
3. Check if relay preservation is limiting individual events

**Fix:** Review input data, ensure all times are loaded

### Issue: Total Points Seem Low

**Symptoms:** Point total significantly below expectations

**Diagnosis:**
1. Compare against historical results
2. Check for missing events in calculation
3. Verify opponent strength (dual meets)

**Fix:** Audit event coverage, verify complete roster loading

---

## Quality Metrics

### Optimization Quality Score

```python
def calculate_quality_score(result):
    score = 100
    
    # Penalty for constraint violations
    if has_constraint_violations(result):
        score -= 30
    
    # Penalty for unused top swimmers
    if top_swimmers_underutilized(result):
        score -= 20
    
    # Penalty for suboptimal relays
    if relay_not_optimized(result):
        score -= 15
    
    # Bonus for fatigue-aware distribution
    if fatigue_well_managed(result):
        score += 10
    
    return min(100, max(0, score))
```

### Grade Thresholds

| Score  | Grade | Action               |
| ------ | ----- | -------------------- |
| 90-100 | A     | Deploy confidently   |
| 75-89  | B     | Review edge cases    |
| 60-74  | C     | Manual review needed |
| <60    | F     | Debug before using   |

---

## Integration with PRISM

When reviewing complex optimizations, invoke PRISM perspectives:

1. **🔬 Logic**: Is the optimization mathematically sound?
2. **🛡️ Robustness**: What edge cases could break this?
3. **⚡ Performance**: Is the solver finding global optimum?
4. **🧪 Testability**: Can we verify this is correct?

---

_Skill: optimization-reviewer | Version: 1.0_
