# PRISM Deep Dive: Championship Scoring Analysis

## Date: 2026-01-18
## Focus: Input/Output Values and Score Calculations

---

## 🔮 PHASE 1: PERCEIVE - Data Flow Mapping

### Complete Data Flow Pipeline

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        INPUT SOURCES                                     │
├─────────────────────────────────────────────────────────────────────────┤
│  1. PSYCH SHEET (CSV/JSON)                                              │
│     ├── swimmer: string ("John Smith")                                  │
│     ├── team: string ("SST", "OUT", etc.)                              │
│     ├── event: string ("Boys 100 Free")                                │
│     ├── time: float/string (52.34 or "52.34")                          │
│     ├── gender: string ("Boys"/"Girls")                                │
│     └── grade: string ("11", optional)                                 │
│                                                                         │
│  2. MEET PROFILE (rules.py)                                            │
│     ├── individual_points: [16,13,12,11,10,9,7,5,4,3,2,1] (VCAC)      │
│     ├── relay_points: [32,26,24,22,20,18,14,10,8,6,4,2] (2x indiv)   │
│     ├── max_scorers_per_team_individual: 4                            │
│     └── max_individual_events_per_swimmer: 2                          │
│                                                                         │
│  3. FRONTEND REQUEST                                                    │
│     ├── scoring_type: "vcac_championship" | "visaa_state"             │
│     ├── optimizer_backend: "gurobi" | "heuristic"                      │
│     └── enforce_fatigue: boolean                                       │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                     PROCESSING STAGES                                    │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  STAGE 1: VALIDATION (data_contracts.py)                               │
│  ─────────────────────────────────────────                              │
│  ► Input: Raw dicts from request                                       │
│  ► Output: ValidatedEntry objects                                      │
│  ► Normalizes: times → float seconds, events → canonical names         │
│                                                                         │
│  STAGE 2: ENTRY BUILDING (championship_formatter.py)                   │
│  ─────────────────────────────────────────────────────                  │
│  ► Input: Validated entries                                            │
│  ► Output: List[ChampionshipEntry] dataclass objects                   │
│  ► Purpose: Typed objects for strategy consumption                     │
│                                                                         │
│  STAGE 3A: OPTIMIZATION (ChampionshipGurobiStrategy)                   │
│  ────────────────────────────────────────────────────                   │
│  ► Input: List[ChampionshipEntry], target_team="SST"                   │
│  ► Output: ChampionshipOptimizationResult                              │
│  ► Logic:                                                              │
│      1. Filter to individual events only                               │
│      2. Build point matrix based on placement vs ALL competitors       │
│      3. Apply constraints (max 2 indiv/swimmer, no back-to-back)      │
│      4. Solve with Gurobi to maximize target team's points            │
│                                                                         │
│  STAGE 3B: PROJECTION (PointProjectionService)                         │
│  ──────────────────────────────────────────────                         │
│  ► Input: List[Dict] entries, target_team, meet_profile               │
│  ► Output: StandingsProjection                                         │
│  ► Logic:                                                              │
│      1. Group entries by event                                         │
│      2. Sort each event by seed time                                   │
│      3. Assign points based on placement (respecting max scorers)     │
│      4. Sum team totals across all events                             │
│      5. Identify swing events for target team                         │
│                                                                         │
│  STAGE 4: FORMATTING (championship_formatter.py)                       │
│  ─────────────────────────────────────────────────                      │
│  ► Input: ChampionshipOptimizationResult + StandingsProjection         │
│  ► Output: OptimizationResponse (JSON)                                 │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         OUTPUT VALUES                                    │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  seton_score: float                                                     │
│  ├── Source: ChampionshipOptimizationResult.total_points               │
│  └── Meaning: Optimized total projected points for target team         │
│                                                                         │
│  championship_standings: List[{rank, team, points}]                    │
│  ├── Source: StandingsProjection.standings                             │
│  └── Meaning: ALL teams' projected scores, sorted by rank             │
│                                                                         │
│  event_breakdowns: Dict[event → EventProjection]                       │
│  ├── Source: StandingsProjection.event_projections                     │
│  └── Meaning: Per-event point breakdown by team                       │
│                                                                         │
│  swing_events: List[SwingEvent]                                        │
│  ├── Source: StandingsProjection.swing_events                          │
│  └── Meaning: Events where target team can gain significant points    │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 🔬 PHASE 2: MULTI-PERSPECTIVE CRITIQUE

### 🧪 QA Engineer Perspective

**ISSUE 1: Two Different Scoring Paths**

There are TWO places where points are calculated:

| Component                                          | Purpose      | Calculation Method                      |
| -------------------------------------------------- | ------------ | --------------------------------------- |
| `ChampionshipGurobiStrategy._build_point_matrix()` | Optimization | Points based on swimmer's rank in event |
| `PointProjectionService._project_event()`          | Standings    | Points based on swimmer's rank in event |

**Concern**: Are they consistent? Let me verify:

**ChampionshipGurobiStrategy (lines 280-334):**
```python
for i, entry in enumerate(event_entries):
    if entry.swimmer_name == swimmer and entry.team.upper() == target_team.upper():
        swimmer_rank = i + 1  # 1-indexed
        break
    elif entry.team.upper() == target_team.upper():
        team_scorers_ahead += 1

if team_scorers_ahead >= self.max_scorers:
    point_matrix[(swimmer, event)] = 0.0  # Team can't score more
else:
    if swimmer_rank <= len(self.points_table):
        point_matrix[(swimmer, event)] = self.points_table[swimmer_rank - 1]
```

**PointProjectionService (lines 249-321):**
```python
for seed_rank, entry in enumerate(sorted_entries, 1):
    team = entry["team"]
    is_scoring = team_scorer_count[team] < max_scorers
    if is_scoring:
        team_scorer_count[team] += 1

    predicted_place = seed_rank
    points = 0.0
    if is_scoring and predicted_place <= len(points_table):
        points = points_table[predicted_place - 1]
```

**Finding**: Both use the same logic:
✅ Sort by seed time
✅ Check max scorers per team (4 for VCAC)
✅ Assign points from points_table based on placement

**ISSUE 2: Optimizer vs Projection Score Mismatch**

The `seton_score` in the response comes from:
- **ChampionshipGurobiStrategy**: Returns `total_points` which is the OPTIMIZED score (Gurobi found best assignments)
- **PointProjectionService**: Returns projected score based on seed times (no optimization)

**Question**: Are we returning the right score?

Currently:
- `seton_score` = Optimized score (from Gurobi)
- `championship_standings[].points` for Seton = Projected score (based on seeds)

**These could be different!**

### 🛡️ Security/Data Integrity Perspective

**ISSUE 3: Team Name Normalization**

Three places normalize team names differently:

| Location                | Method                     |
| ----------------------- | -------------------------- |
| `normalize_team_name()` | `shared/normalization.py`  |
| `target_team.upper()`   | `championship_strategy.py` |
| `e.team.upper()`        | Filter comparisons         |

**Risk**: If normalization isn't consistent, team filtering may fail.

**ISSUE 4: Time Format Inconsistency**

Entry times can be:
- `float` (52.34)
- `string` ("52.34")
- `string` ("0:52.34")
- `string` ("NT" or None)

The `normalize_time()` function handles this, but:
- `championship_strategy.py` line 297: `e.seed_time > 0` - Works only if float
- What if seed_time is still a string after entry building?

### 🏛️ Architect Perspective

**ISSUE 5: Scoring Flow Redundancy**

We're calculating points in multiple places:
1. `ChampionshipGurobiStrategy._build_point_matrix()` - For optimization
2. `PointProjectionService._project_event()` - For standings
3. `ChampionshipOptimizationResult.event_breakdown` - Post-optimization

This violates DRY. Points calculation should be centralized.

**ISSUE 6: Optimization vs Projection Scope**

| Component                  | Scope                                                         |
| -------------------------- | ------------------------------------------------------------- |
| ChampionshipGurobiStrategy | Optimizes **individual events only** (excludes relay, diving) |
| PointProjectionService     | Projects **all events** (including relay, diving)             |

The `seton_score` from optimization is **incomplete** - it only includes individual event points!

---

## 🔄 PHASE 3: SYNTHESIZE

### Critical Finding: Score Discrepancy

**The Problem:**
```
seton_score (from Gurobi) = Points from INDIVIDUAL EVENTS ONLY
championship_standings (from Projection) = Points from ALL EVENTS
```

This means:
- `seton_score` might show 154 (individual only)
- `championship_standings` for Seton might show 254 (individuals + relays + diving)

**These numbers will NOT match!**

### Verification Needed

Let me trace an example:

**VCAC SCORING:**
- Individual: [16, 13, 12, 11, 10, 9, 7, 5, 4, 3, 2, 1] (12 places)
- Relay: [32, 26, 24, 22, 20, 18, 14, 10, 8, 6, 4, 2] (12 places, 2x individual)

**Sample Event: Boys 100 Free (Individual)**
```
Rank | Swimmer      | Team | Time  | Points (if scoring)
1    | John Smith   | SST  | 48.50 | 16 ✅
2    | Mike Jones   | OUT  | 49.00 | 13
3    | Tom Brown    | SST  | 49.50 | 12 ✅
4    | Dave Wilson  | OUT  | 50.00 | 11
5    | Sam Lee      | SST  | 50.50 | 10 ✅
6    | Bob Garcia   | SST  | 51.00 | 9 ✅ (4th scorer, max reached)
7    | Chris Davis  | SST  | 51.50 | 0 ❌ (5th scorer, doesn't count)
```

SST scores: 16 + 12 + 10 + 9 = **47 points** in this event

---

## 🔧 PHASE 4: REFINE - Recommendations

### HIGH PRIORITY

**1. Align seton_score with championship_standings**

The frontend shows:
- Big number: `seton_score`
- Standings: `championship_standings`

If these don't match, it's confusing. Options:
- A: Use projection score for seton_score (consistent)
- B: Add "optimized_score" vs "baseline_score" distinction in UI
- C: Have optimizer include relay/diving estimates

**Recommended: Option A** - Use projection score for display consistency

**2. Document Score Meanings**

Add to KNOWLEDGE_BASE.md:
```
## Championship Scores

| Field                  | Meaning                     | Includes                                   |
| ---------------------- | --------------------------- | ------------------------------------------ |
| seton_score            | Optimized target team score | Individual events only (optimizer output)  |
| championship_standings | Projected meet standings    | All events (individuals + relays + diving) |
```

### MEDIUM PRIORITY

**3. Centralize Points Calculation**

Create a single `calculate_points(rank, event_type, rules)` function used by both optimizer and projector.

**4. Add Relay Points to Optimizer**

Extend ChampionshipGurobiStrategy to include relay event projections in total.

### LOW PRIORITY

**5. Time Normalization Enforcement**

Add validation that all seed_times are float when entering optimization.

---

## 📊 PHASE 5: VERIFY - Test Cases

### Test 1: Score Component Verification

```bash
# Expected: seton_score + relay_points + diving_points ≈ championship_standings[SST]
curl -s http://localhost:8001/api/v1/optimize \
  -H "Content-Type: application/json" \
  -d '{"seton_data": [...], "scoring_type": "vcac_championship"}' \
  | jq '.seton_score, .championship_standings[] | select(.team=="SST")'
```

### Test 2: Max Scorers Enforcement

```python
# Create event with 6 SST swimmers, verify only top 4 score
def test_max_scorers():
    entries = [
        {"swimmer": f"Swimmer{i}", "team": "SST", "event": "Boys 100 Free", "time": 50+i}
        for i in range(6)
    ]
    result = projection_service.project_event("Boys 100 Free", entries)
    scoring_entries = [e for e in result.entries if e.is_scoring and e.team == "SST"]
    assert len(scoring_entries) == 4  # Max 4 scorers
```

### Test 3: Points Table Accuracy

```python
def test_vcac_points():
    rules = get_meet_profile("vcac_championship")
    assert rules.individual_points[0] == 16  # 1st place individual
    assert rules.individual_points[11] == 1   # 12th place individual
    assert rules.relay_points[0] == 32        # Relay 1st (2x individual)
```

---

## 📋 SUMMARY

| Issue                               | Severity | Status | Action              |
| ----------------------------------- | -------- | ------ | ------------------- |
| seton_score vs standings mismatch   | HIGH     | OPEN   | Document or align   |
| Two scoring code paths              | MEDIUM   | OPEN   | Centralize          |
| Individual events only in optimizer | MEDIUM   | KNOWN  | Add relays          |
| Team name normalization             | LOW      | OK     | Verify with tests   |
| Time format consistency             | LOW      | OK     | Validation in place |

**Key Insight**: The current implementation correctly calculates individual event optimization and full meet projections, but the UI may be confusing because `seton_score` (optimizer output) and the Seton entry in `championship_standings` (projection output) measure different things.

---

*Generated by PRISM Analysis - 2026-01-18*
