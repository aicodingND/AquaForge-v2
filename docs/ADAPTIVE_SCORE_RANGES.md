# Adaptive Score Ranges - Dynamic Validation Based on Event Composition

## 🎯 **Problem Statement**

**Current Issue:**

- Fixed score range (80-120) assumes full dual meet
- Doesn't account for partial meets (boys only, no diving, etc.)
- Validation incorrectly flags partial meets as "inflated"

**Example:**

```
Boys Only Meet:
- 6 individual events × 2 genders = 6 events (not 12)
- Expected score: 40-60 per team (not 80-120)
- Current validation: ❌ "Score too low!"
```

## 📊 **Event Composition Matrix**

### **All Possible Meet Configurations:**

| Configuration | Events | Max Points/Team | Expected Range |
|--------------|--------|-----------------|----------------|
| **Boys Individual Only** | 6 | 36 | 30-40 |
| **Girls Individual Only** | 6 | 36 | 30-40 |
| **Boys Individual + Diving** | 7 | 42 | 35-45 |
| **Girls Individual + Diving** | 7 | 42 | 35-45 |
| **Boys Individual + Relays** | 9 | 54 | 45-60 |
| **Girls Individual + Relays** | 9 | 54 | 45-60 |
| **Boys Full (Ind + Div + Relay)** | 10 | 60 | 50-65 |
| **Girls Full (Ind + Div + Relay)** | 10 | 60 | 50-65 |
| **Coed Individual Only** | 12 | 72 | 60-75 |
| **Coed Individual + Diving** | 14 | 84 | 70-85 |
| **Coed Individual + Relays** | 18 | 108 | 90-110 |
| **Full Dual Meet (All)** | 24 | 144 | 120-140 |

### **Scoring Breakdown:**

**Individual Events:**

- 1st place: 6 pts
- 2nd place: 4 pts
- 3rd place: 3 pts
- 4th place: 2 pts
- 5th place: 1 pt
- **Max per event:** 6 pts (if sweep 1-2-3)
- **Typical per event:** 4-5 pts (competitive meet)

**Relay Events:**

- Same scoring as individual
- **Max per relay:** 6 pts
- **Typical per relay:** 4-5 pts

**Diving:**

- Same scoring as individual
- **Max:** 6 pts
- **Typical:** 4-5 pts

## 🔧 **Adaptive Scoring Formula**

### **Calculate Expected Range:**

```python
def calculate_expected_score_range(events: List[str]) -> Tuple[int, int]:
    """
    Calculate expected score range based on event composition.
    
    Args:
        events: List of event names
    
    Returns:
        (min_expected, max_expected) score range
    """
    # Count event types
    individual_count = sum(1 for e in events if not is_relay(e) and not is_diving(e))
    relay_count = sum(1 for e in events if is_relay(e))
    diving_count = sum(1 for e in events if is_diving(e))
    
    total_events = len(events)
    
    # Calculate theoretical maximum (all 1st places)
    theoretical_max = total_events * 6
    
    # Expected range:
    # - Minimum: ~70% of theoretical max (losing most events)
    # - Maximum: ~95% of theoretical max (winning most events)
    min_expected = int(theoretical_max * 0.50)  # Losing team
    max_expected = int(theoretical_max * 0.95)  # Winning team
    
    return min_expected, max_expected


def is_relay(event: str) -> bool:
    """Check if event is a relay."""
    return 'relay' in event.lower()


def is_diving(event: str) -> bool:
    """Check if event is diving."""
    return 'diving' in event.lower()


def detect_meet_type(events: List[str]) -> dict:
    """
    Detect meet configuration from event list.
    
    Returns:
        dict with meet type info
    """
    # Count by type
    boys_events = [e for e in events if 'boys' in e.lower()]
    girls_events = [e for e in events if 'girls' in e.lower()]
    individual_events = [e for e in events if not is_relay(e) and not is_diving(e)]
    relay_events = [e for e in events if is_relay(e)]
    diving_events = [e for e in events if is_diving(e)]
    
    # Determine configuration
    has_boys = len(boys_events) > 0
    has_girls = len(girls_events) > 0
    has_individual = len(individual_events) > 0
    has_relays = len(relay_events) > 0
    has_diving = len(diving_events) > 0
    
    # Classify
    if has_boys and has_girls:
        gender_type = "Coed"
    elif has_boys:
        gender_type = "Boys Only"
    elif has_girls:
        gender_type = "Girls Only"
    else:
        gender_type = "Unknown"
    
    # Event composition
    components = []
    if has_individual:
        components.append("Individual")
    if has_diving:
        components.append("Diving")
    if has_relays:
        components.append("Relays")
    
    event_type = " + ".join(components) if components else "Unknown"
    
    return {
        'gender_type': gender_type,
        'event_type': event_type,
        'full_type': f"{gender_type} - {event_type}",
        'total_events': len(events),
        'boys_events': len(boys_events),
        'girls_events': len(girls_events),
        'individual_events': len(individual_events),
        'relay_events': len(relay_events),
        'diving_events': len(diving_events),
        'has_boys': has_boys,
        'has_girls': has_girls,
        'has_individual': has_individual,
        'has_relays': has_relays,
        'has_diving': has_diving
    }
```

## 📊 **Adaptive Validation**

### **Score Validation with Adaptive Ranges:**

```python
def validate_score_adaptive(score: float, events: List[str]) -> dict:
    """
    Validate score against adaptive expected range.
    
    Args:
        score: Team's total score
        events: List of events in meet
    
    Returns:
        dict with validation results
    """
    # Calculate expected range
    min_expected, max_expected = calculate_expected_score_range(events)
    
    # Detect meet type
    meet_info = detect_meet_type(events)
    
    # Validate
    is_valid = min_expected <= score <= max_expected
    
    # Determine status
    if score > max_expected * 1.2:
        status = "INVALID - Score too high (possible duplicate data)"
        severity = "error"
    elif score > max_expected:
        status = "WARNING - Score higher than expected"
        severity = "warning"
    elif score < min_expected * 0.7:
        status = "WARNING - Score lower than expected"
        severity = "warning"
    else:
        status = "VALID - Score within expected range"
        severity = "success"
    
    return {
        'is_valid': is_valid,
        'status': status,
        'severity': severity,
        'score': score,
        'min_expected': min_expected,
        'max_expected': max_expected,
        'meet_type': meet_info['full_type'],
        'total_events': meet_info['total_events'],
        'theoretical_max': meet_info['total_events'] * 6,
        'efficiency': (score / (meet_info['total_events'] * 6)) * 100 if meet_info['total_events'] > 0 else 0
    }
```

## 🎯 **Expected Score Ranges by Configuration**

### **Boys/Girls Only Meets:**

**Boys Individual Only (6 events):**

```
Theoretical Max: 36 points
Expected Range: 18-34 points
Typical Winner: 22-28 points
Typical Loser: 12-18 points
```

**Girls Individual Only (6 events):**

```
Theoretical Max: 36 points
Expected Range: 18-34 points
Typical Winner: 22-28 points
Typical Loser: 12-18 points
```

### **With Diving:**

**Boys Individual + Diving (7 events):**

```
Theoretical Max: 42 points
Expected Range: 21-40 points
Typical Winner: 26-33 points
Typical Loser: 14-21 points
```

**Girls Individual + Diving (7 events):**

```
Theoretical Max: 42 points
Expected Range: 21-40 points
Typical Winner: 26-33 points
Typical Loser: 14-21 points
```

### **With Relays:**

**Boys Individual + Relays (9 events):**

```
Theoretical Max: 54 points
Expected Range: 27-51 points
Typical Winner: 33-42 points
Typical Loser: 18-27 points
```

**Girls Individual + Relays (9 events):**

```
Theoretical Max: 54 points
Expected Range: 27-51 points
Typical Winner: 33-42 points
Typical Loser: 18-27 points
```

### **Full Single-Gender Meets:**

**Boys Full (Individual + Diving + Relays, 10 events):**

```
Theoretical Max: 60 points
Expected Range: 30-57 points
Typical Winner: 37-47 points
Typical Loser: 20-30 points
```

**Girls Full (Individual + Diving + Relays, 10 events):**

```
Theoretical Max: 60 points
Expected Range: 30-57 points
Typical Winner: 37-47 points
Typical Loser: 20-30 points
```

### **Coed Meets:**

**Coed Individual Only (12 events):**

```
Theoretical Max: 72 points
Expected Range: 36-68 points
Typical Winner: 44-56 points
Typical Loser: 24-36 points
```

**Coed Individual + Diving (14 events):**

```
Theoretical Max: 84 points
Expected Range: 42-80 points
Typical Winner: 52-66 points
Typical Loser: 28-42 points
```

**Coed Individual + Relays (18 events):**

```
Theoretical Max: 108 points
Expected Range: 54-103 points
Typical Winner: 66-84 points
Typical Loser: 36-54 points
```

**Full Dual Meet (All events, 24 events):**

```
Theoretical Max: 144 points
Expected Range: 72-137 points
Typical Winner: 88-112 points
Typical Loser: 48-72 points
```

## 🔍 **Validation Examples**

### **Example 1: Boys Only Meet**

```python
events = [
    "Boys 200 Free",
    "Boys 200 IM",
    "Boys 50 Free",
    "Boys 100 Fly",
    "Boys 100 Free",
    "Boys 500 Free",
    "Boys 100 Back",
    "Boys 100 Breast"
]

# Detect meet type
meet_info = detect_meet_type(events)
# Result: "Boys Only - Individual"

# Calculate range
min_exp, max_exp = calculate_expected_score_range(events)
# Result: (24, 46) - 8 events × 6 pts = 48 max

# Validate score
result = validate_score_adaptive(score=35, events=events)
# Result: VALID - Score within expected range (24-46)
```

### **Example 2: Full Dual Meet**

```python
events = [
    "Girls 200 Medley Relay", "Boys 200 Medley Relay",
    "Girls 200 Free", "Boys 200 Free",
    # ... (all 24 events)
]

# Calculate range
min_exp, max_exp = calculate_expected_score_range(events)
# Result: (72, 137) - 24 events × 6 pts = 144 max

# Validate score of 158
result = validate_score_adaptive(score=158, events=events)
# Result: INVALID - Score too high (possible duplicate data)
# 158 > 137 × 1.2 = 164.4 (still within error margin)
# 158 > 137 (max expected) → WARNING
```

### **Example 3: Girls Individual + Diving**

```python
events = [
    "Girls 200 Free",
    "Girls 200 IM",
    "Girls 50 Free",
    "Girls Diving",
    "Girls 100 Fly",
    "Girls 100 Free",
    "Girls 500 Free",
    "Girls 100 Back",
    "Girls 100 Breast"
]

# Calculate range
min_exp, max_exp = calculate_expected_score_range(events)
# Result: (27, 51) - 9 events × 6 pts = 54 max

# Validate score
result = validate_score_adaptive(score=42, events=events)
# Result: VALID - Score within expected range (27-51)
```

## 📋 **Implementation Checklist**

### **Files to Modify:**

1. **✅ `backend/services/score_validation_service.py`**
   - Add `calculate_expected_score_range()`
   - Add `detect_meet_type()`
   - Add `validate_score_adaptive()`
   - Update main validation to use adaptive ranges

2. **✅ `states/optimization_state.py`**
   - Use adaptive validation instead of fixed ranges
   - Display meet type in UI
   - Show expected range in results

3. **✅ `components/analysis.py`**
   - Display meet configuration
   - Show adaptive score range
   - Highlight if score is outside expected range

4. **✅ `FINAL_VERIFICATION_CHECKLIST.md`**
   - Update score ranges to be adaptive
   - Add meet type detection step
   - Include configuration-specific ranges

## 🎯 **User Experience**

### **Before (Fixed Ranges):**

```
Boys Only Meet:
Score: 35 points
Validation: ❌ "Score too low! Expected 80-120"
User: Confused - this is normal for boys only!
```

### **After (Adaptive Ranges):**

```
Boys Only Meet (8 individual events):
Score: 35 points
Expected Range: 24-46 points
Validation: ✅ "Score within expected range"
Meet Type: Boys Only - Individual
Efficiency: 73% of theoretical maximum
User: Confident - score is realistic!
```

## 📊 **Summary Table**

| Meet Configuration | Events | Theoretical Max | Expected Min | Expected Max | Typical Winner | Typical Loser |
|-------------------|--------|-----------------|--------------|--------------|----------------|---------------|
| Boys Ind Only | 6-8 | 36-48 | 18-24 | 34-46 | 22-30 | 12-20 |
| Girls Ind Only | 6-8 | 36-48 | 18-24 | 34-46 | 22-30 | 12-20 |
| Boys Ind + Div | 7-9 | 42-54 | 21-27 | 40-51 | 26-34 | 14-22 |
| Girls Ind + Div | 7-9 | 42-54 | 21-27 | 40-51 | 26-34 | 14-22 |
| Boys Full | 10-12 | 60-72 | 30-36 | 57-68 | 37-45 | 20-30 |
| Girls Full | 10-12 | 60-72 | 30-36 | 57-68 | 37-45 | 20-30 |
| Coed Ind Only | 12-16 | 72-96 | 36-48 | 68-91 | 44-60 | 24-40 |
| Coed Full | 20-24 | 120-144 | 60-72 | 114-137 | 74-90 | 40-60 |

---

**KEY INSIGHT:** Score validation MUST be adaptive based on event composition. A score of 35 is INVALID for a full dual meet but PERFECT for a boys-only individual meet!
