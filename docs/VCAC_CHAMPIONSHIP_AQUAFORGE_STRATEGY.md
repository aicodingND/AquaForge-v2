# VCAC Championship - AquaForge Strategy Deep Dive

**Event:** 5th Annual VCAC Conference Championship  
**Date:** February 7, 2026  
**Analysis Date:** January 15, 2026

---

## 📊 The Challenge: Dual Meet vs Championship

### Current AquaForge (Dual Meet)

```
                    Seton vs Opponent
                         ↓
        Nash Equilibrium Optimization
                         ↓
          Optimal Lineup for 1v1 Win
```

**Works because:**

- Single opponent to optimize against
- Zero-sum game (what hurts them helps us)
- Nash equilibrium finds stable strategy

### VCAC Championship

```
        Seton vs Trinity vs Oakcrest vs FCS vs ICS vs JPII
                              ↓
                    Multi-Team Scoring
                              ↓
                   Maximize Seton Points
                   (independent of opponents)
```

**Different because:**

- 6 teams competing simultaneously
- Not zero-sum (stealing points from Trinity doesn't help against Oakcrest)
- No direct head-to-head optimization

---

## 🔑 Key Insight: VCAC Uses Timed Finals

Unlike VISAA States (prelims/finals), VCAC Championship uses **timed finals** - meaning:

- All swimmers compete in one heat
- Final placement = final scoring
- Seed times = predicted placement

**This is good news!** We can predict placements from seed times.

---

## 🧮 Optimization Problem Reformulation

### Dual Meet (Current):

> "Given Seton roster and opponent roster, find lineup that maximizes win probability"

### Championship (New):

> "Given Seton roster and psych sheet with all teams, find entry selection that maximizes expected Seton points"

---

## 📈 AquaForge Applications for VCAC Championship

### Application 1: Entry Selection Optimizer

**Problem:** Which 2 individual events should each swimmer enter?

**Inputs:**

- Seton roster with times
- Psych sheet with all teams' times
- Entry constraints (2 indiv max, diving counts, relay 3 penalty)

**Output:**

- Optimal event assignments per swimmer
- Projected points per event

**Algorithm:**

```python
for each swimmer in seton_roster:
    for each possible_entry_combo in valid_combinations(swimmer):
        # Calculate expected points
        expected_points = 0
        for event in possible_entry_combo.events:
            predicted_place = predict_place(swimmer.time, psych_sheet[event])
            expected_points += VCAC_POINTS[predicted_place]

        # Track best combo for this swimmer
        if expected_points > best[swimmer]:
            best[swimmer] = (possible_entry_combo, expected_points)

# Solve assignment problem: maximize total team points
# subject to: each event has at most 4 scoring Seton swimmers
```

### Application 2: Relay Configuration Optimizer

**Problem:** How to configure A and B relays for maximum points?

**Unique to VCAC:**

- Both A and B relays score
- 1st = 16 pts, 2nd = 13 pts (relays worth less than individual!)
- Relay 3 (400 Free) counts as individual event slot

**Strategy Considerations:**

1. **Stack A relay for 1st place** (16 pts)
2. **B relay should beat C relays** (ensure it scores)
3. **Consider NOT swimming 400 relay** if swimmers need individual slots

**Example optimization:**

```
200 Medley Relay:
  A Team: Best 4 stroke specialists → Target 1st (16 pts)
  B Team: Next 4 best → Target 3rd-4th (12-11 pts)

200 Free Relay:
  A Team: Best 4 freestylers → Target 1st (16 pts)
  B Team: Next 4 → Target 4th+ (11+ pts)

400 Free Relay:
  ⚠️ This counts as individual event!
  Decision: Do we swim it?
  - If swimmer on 400 relay has 2 indiv events → Can't do 400
  - May sacrifice 400 relay to protect individual entries
```

### Application 3: Point Projection & Scenario Analysis

**Problem:** What's our projected team score? Where can we gain points?

**Features:**

- Calculate expected points per event
- Identify "swing events" where small time drops = place gains
- Model scenarios: "What if swimmer X drops 1 second?"

**Output:**

```
PROJECTED VCAC CHAMPIONSHIP RESULTS

Event               | Seton Pts | Best Case | Swing Pts
--------------------|-----------|-----------|----------
Girls 200 Free      |    56     |    64     |   +8
Girls 200 IM        |    42     |    48     |   +6
Boys 50 Free        |    38     |    52     |   +14 ⚠️ Focus!
...

Total Projected: 512 pts
Best Case: 578 pts
Target to Win: ~550 pts (based on 2025 results)
```

### Application 4: "What-If" Simulator

**Problem:** Should swimmer X do Event A or Event B?

**Interactive mode:**

```
> What if we move John from 100 Fly to 100 Free?

Current:
  John in 100 Fly: Predicted 4th (22 pts)
  100 Free spot goes to Mike: Predicted 8th (10 pts)
  Total: 32 pts

Alternative:
  John in 100 Free: Predicted 2nd (26 pts)
  Mike in 100 Fly: Predicted 6th (18 pts)
  Total: 44 pts

Recommendation: Move John to 100 Free (+12 pts)
```

---

## 🏆 Strategic Insights for VCAC Championship

### 1. Individual Events Are KING

| Event Type | 1st Place | Ratio |
| ---------- | --------- | ----- |
| Individual | 32 pts    | 2x    |
| Relay      | 16 pts    | 1x    |

**Implication:** Prioritize individual placements over relays!

A swimmer who places 1st in individual + 4th in relay earns:

- 32 + 11 = **43 points**

A swimmer who skips individual to anchor 1st relay earns:

- 16 points (only)

**Strategic move:** Consider having star swimmers do 2 individual events and only 2 "free" relays.

### 2. The "Relay 3 Penalty" is Real

If a swimmer does all 3 relays, they can only do 1 individual:

- 1 indiv @ 32 pts + 3 relays @ ~14 avg = **74 pts max**

If they do 2 relays and 2 individual:

- 2 indiv @ 26 avg + 2 relays @ 14 avg = **80 pts potential**

**Rule:** Don't put your best individual swimmers on the 400 Free Relay unless necessary.

### 3. Depth Matters - Top 4 Score!

Unlike dual meets (top 3), VCAC allows Top 4 scorers per team per event.

**Implication:**

- 4th place Seton swimmer still earns 22 pts (if they place 4th overall)
- Even 12th place earns 2 pts
- Enter strong swimmers even if they're "only" 4th on team

### 4. B Relays Are Point Machines

Both A and B relays score. If Seton has:

- A relay: 1st (16 pts)
- B relay: 4th (11 pts)

**Total: 27 pts from one relay event!**

Compare to dual meet where only A relay scores.

### 5. Divers Have Constraints

Diving counts as 1 individual event:

- Diver can: Dive + 1 swim + 2 relays (max)
- Diver cannot: Dive + 2 swim events + all 3 relays

**Implication:** Don't overload your diver-swimmers.

---

## 🔧 Implementation Roadmap

### Phase 1: Data Infrastructure (1-2 days)

- [ ] Psych sheet parser (input: PDF/CSV → structured data)
- [ ] Multi-team roster data model
- [ ] VCACChampRules integration ✅ (done!)

### Phase 2: Point Projection Engine (2-3 days)

- [ ] Predict placement from times
- [ ] Calculate expected points per swimmer per event
- [ ] Entry constraint validation (is_valid_entry method ✅)

### Phase 3: Entry Optimizer (3-5 days)

- [ ] Generate valid entry combinations per swimmer
- [ ] Assignment problem solver (which 2 events per swimmer)
- [ ] Relay configuration optimizer

### Phase 4: Frontend UI (2-3 days)

- [ ] Meet profile selector ✅ (backend done)
- [ ] Psych sheet upload
- [ ] Point projection display
- [ ] What-if analysis tool

---

## 📋 Pre-Meet Checklist for VCAC Championship

1. **Get psych sheet** (should be available ~5 days before meet)
2. **Input all team data** into AquaForge
3. **Run entry optimizer** to determine individual event assignments
4. **Configure relays** with constraint awareness
5. **Generate point projections** and identify focus events
6. **Run scenarios** for borderline decisions

---

## 💡 Quick Win: Even Without Full Implementation

Even before building the full optimizer, AquaForge can help by:

1. **Using VCACChampRules** for scoring validation
2. **Checking entry constraints** with `is_valid_entry()`
3. **Sorting swimmers by time per event** to predict placements
4. **Calculating points manually** using the point tables

---

## Summary Table: AquaForge Capability Map

| Feature          | Dual Meet         | VCAC Championship        |
| ---------------- | ----------------- | ------------------------ |
| Nash Equilibrium | ✅ Primary        | ❌ Not applicable        |
| Entry Selection  | ✅ Simple         | 🔧 Needs optimizer       |
| Point Projection | ✅ Direct         | 🔧 Needs multi-team      |
| Relay Config     | ✅ A only         | 🔧 A+B, constraint aware |
| What-If Analysis | ✅ Works          | 🔧 Needs psych sheet     |
| Scoring Rules    | ✅ VCACChampRules | ✅ VCACChampRules        |
| Entry Validation | ✅ Basic          | ✅ is_valid_entry()      |

---

_Analysis by AquaForge AI Development Team, January 15, 2026_
