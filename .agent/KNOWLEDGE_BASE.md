# 🧠 AquaForge Knowledge Base

## Persistent Context for AI Development Sessions

**Last Updated**: 2026-02-02
**Purpose**: Single source of truth for domain knowledge, rules, and context that Antigravity should reference during coding sessions.

---

## 📌 How to Use This File

1. **AI Sessions**: Antigravity should read this file at the start of significant coding sessions
2. **Updates**: Add new domain knowledge as we learn it (rules, constraints, decisions)
3. **Structure**: Keep sections organized by topic for easy reference
4. **Changelog**: Document significant updates at the bottom

---

## 🏊 Domain: Competitive Swimming

### VISAA (Virginia Independent Schools Athletic Association)

| Fact                | Value                                  | Source            |
| ------------------- | -------------------------------------- | ----------------- |
| Seton Division      | Division II                            | setonswimming.org |
| State Championships | February 12-14, 2026                   | visaa.org         |
| Venue               | SwimRVA, Richmond, VA                  | setonswimming.org |
| Governing Rules     | NFHS (National Federation High School) | visaa.org         |

### Seton School Swim Team

| Fact               | Value                              | Notes                           |
| ------------------ | ---------------------------------- | ------------------------------- |
| Head Coach         | Jim Koehr                          | Since 2002, coaching since 2000 |
| Diving Coach       | Ashley Keapproth                   | VISAA Diving Coach of Year 2024 |
| Grades             | 7-12                               | Middle + High School            |
| Participation      | ~40% of 350 students               |                                 |
| Boys State Titles  | 2006, 2009, 2010, 2011             | Division II                     |
| Girls State Titles | 2008, 2009, 2010, 2011, 2021, 2023 | Division II                     |
| 2025 Results       | Runner-up (both teams)             | Division II                     |

### Grade-Based Scoring Rules

```
DUAL MEETS:
  Grades 6-7: EXHIBITION ONLY
    - Can compete in events
    - Can displace opponents from scoring positions
    - DO NOT score points
    - Strategic use: "Event swarmers"

  Grades 8-12: VARSITY / SCORING ELIGIBLE
    - Can compete and score
    - Full points awarded
    - min_scoring_grade = 8 in code

CHAMPIONSHIP MEETS (VCAC, VISAA State):
  - NO exhibition swims allowed
  - Only Varsity swimmers (grade 8+) participate
  - ALL entered swimmers score
  - 7th graders → JV Invitational (separate meet)
  - Source: Seton Parents' Handbook 2024-25
```

### Dual Meet Scoring (Coach Koehr Official)

```text
Source: setonswimming.org/so-how-is-a-high-school-meet-scored-anyway/

INDIVIDUAL (top 7 score):
Place:  1st  2nd  3rd  4th  5th  6th  7th
Points:  8    6    5    4    3    2    1
Total per event: 29 points

RELAY (top 3 score):
Place:  1st  2nd  3rd
Points: 10    5    3
Total per event: 18 points

DIVING: Scored same as individual (top 7)
Points: 8+6+5+4+3+2+1 = 29 points

TOTAL DUAL MEET POINTS: 315
┌─────────────────────────────────────────────────────────────┐
│ Category      │ Events  │ Points/Event │ Total Points      │
├───────────────┼─────────┼──────────────┼───────────────────┤
│ Individual    │ 8       │ 29           │ 232               │
│ Relay         │ 3       │ 18           │ 54                │
│ Diving        │ 1       │ 29           │ 29                │
├───────────────┼─────────┼──────────────┼───────────────────┤
│ TOTAL         │ 12      │ -            │ 315 points        │
└─────────────────────────────────────────────────────────────┘

EVENTS (in order):
  1. 200 Medley Relay (relay)
  2. 200 Free (individual)
  3. 200 IM (individual)
  4. 50 Free (individual)
  5. Diving (individual)
  6. 100 Fly (individual)
  7. 100 Free (individual)
  8. 500 Free (individual)
  9. 200 Free Relay (relay)
  10. 100 Back (individual)
  11. 100 Breast (individual)
  12. 400 Free Relay (relay)

TEAM CONSTRAINTS:
- 4 scoring entries per individual event (varsity)
- 2 scoring entries per relay event (A and B)
- Additional swimmers = "exhibition" (x before seed time)

SWIMMER CONSTRAINTS (NFHS Rule 3-2-1):
- Max 2 individual events (diving counts as 1 individual)
- Max 4 events total (verified: NOT 3 — some docs had this wrong)
- Valid combos: 2 indiv + 2 relay, OR 1 indiv + 3 relay
- Source: NFHS Rule 3-2-1, setonswimming.org, VISAA State Championship Meet Info

RELAY RULES:
- Coach can swap relay swimmers during meet if someone earns faster time
- Lineup can change nearly up to race time
```

### Championship Meet Scoring (VISAA States)

```text
CHAMPIONSHIP FINALS (places 1-16):
40-34-32-30-28-26-24-22-18-14-12-10-8-6-4-2

CONSOLATION FINALS (places 1-16):
20-17-16-15-14-13-12-11-9-7-6-5-4-3-2-1

Note: "Bonus events" swimmers do NOT score

CHAMPIONSHIP MEET RULES (from Coach Koehr, Seton Handbook 2024-25):
- NO exhibition swims allowed — ALL entered swimmers score
- Only Varsity swimmers participate (Coach publishes eligible list)
- 7th graders do NOT enter championships (swim at JV Invitational)
- Seeded by time, not by team
- ⚠️ Miss an event = DISQUALIFIED for rest of meet!
- Top 12 or 16 places score (varies by meet)
- Diving scored same as swimming events
- Source: setonswimming.org Parents' Handbook 2024-25
```

### VCAC Championship Scoring (Feb 7, 2026)

```text
Standard 12-place championship scoring (NCAA Rule 7 / NFHS):
Relay = exactly 2x Individual at every placement.

INDIVIDUAL/DIVING (places 1-12):
16-13-12-11-10-9-7-5-4-3-2-1

RELAY (places 1-12, 2x individual):
32-26-24-22-20-18-14-10-8-6-4-2

NO EXHIBITION at championships. All entered swimmers score.
Only Varsity (grade 8+) eligible. 7th graders → JV Invitational.

Source: NCAA Rule 7, NFHS, setonswimming.org, Seton Handbook 2024-25
Corrected: 2026-02-02 — previous version had individual/relay tables swapped
```

### RELAY SCORING: COMPARISON BY MEET TYPE

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│ MEET TYPE          │ INDIVIDUAL        │ RELAY             │ RATIO         │
├────────────────────┼───────────────────┼───────────────────┼───────────────┤
│ DUAL MEET          │ [8,6,5,4,3,2,1]   │ [10,5,3]          │ SEPARATE      │
│                    │ Top 7 score       │ Top 3 score       │ NOT 2x!       │
├────────────────────┼───────────────────┼───────────────────┼───────────────┤
│ VCAC CHAMPIONSHIP  │ [16,13,12,11...]  │ [32,26,24,22...]  │ RELAY = 2x    │
│ (Feb 7, 2026)      │ Top 12 score      │ Top 12 score      │ STANDARD      │
├────────────────────┼───────────────────┼───────────────────┼───────────────┤
│ VISAA STATE        │ [20,17,16,15...]  │ [40,34,32,30...]  │ RELAY = 2x    │
│ Championship       │ Top 16 score      │ Top 16 score      │ STANDARD      │
└─────────────────────────────────────────────────────────────────────────────┘

⚠️ BOTH championship formats use relay = 2x individual (NCAA/NFHS standard).
⚠️ DUAL MEETS: Relays have their own table [10,5,3], NOT a multiplier!
⚠️ DIVING uses INDIVIDUAL point scale (not relay) in ALL meet types.

SOURCE: NCAA Rule 7, NFHS, setonswimming.org, Coach Koehr
TESTS: test_scoring_constraints.py (regression protection)
Corrected: 2026-02-02 — VCAC was previously listed as "inverted" (wrong)
```


```text
THE RULES:
1. Max 2 INDIVIDUAL events per swimmer
2. DIVING COUNTS AS 1 INDIVIDUAL EVENT
3. There are only 3 RELAYS (200 Medley, 200 Free, 400 Free)
4. First 2 relays are FREE (don't count toward individual limit)
5. Relay 3 COUNTS AS 1 individual event

FORMULA:
  individual_slots_used = swim_individual_count + (1 if diving else 0)
  relay_penalty = max(0, relay_count - 2)  # only relay 3 costs a slot
  total_effective_individual = individual_slots_used + relay_penalty

  VALID if: total_effective_individual <= 2

EXAMPLES:
┌────────┬───────┬────────┬─────────────┬───────────────────────────────┐
│ Swim   │ Dive  │ Relays │ Eff. Indiv  │ Valid?                        │
├────────┼───────┼────────┼─────────────┼───────────────────────────────┤
│ 2      │ No    │ 2      │ 2           │ ✅ Yes (max normal swimmer)   │
│ 1      │ Yes   │ 2      │ 2           │ ✅ Yes (1 swim + dive = 2)    │
│ 2      │ Yes   │ 0      │ 3           │ ❌ NO (dive puts over limit)  │
│ 1      │ No    │ 3      │ 2           │ ✅ Yes (1 swim + relay3 = 2)  │
│ 2      │ No    │ 3      │ 3           │ ❌ NO (2 swim + relay3 = 3)   │
│ 0      │ Yes   │ 3      │ 2           │ ✅ Yes (dive + relay3 = 2)    │
│ 1      │ Yes   │ 3      │ 3           │ ❌ NO (1 swim + dive + R3 = 3)│
│ 0      │ No    │ 3      │ 1           │ ✅ Yes (relay3 only = 1)      │
└────────┴───────┴────────┴─────────────┴───────────────────────────────┘

VALIDATION PSEUDOCODE:
  def is_valid_entry(swim_individual: int, is_diver: bool, relay_count: int) -> bool:
      if swim_individual > 2: return False
      if relay_count > 3: return False

      individual_used = swim_individual + (1 if is_diver else 0)
      relay_penalty = max(0, relay_count - 2)
      effective_individual = individual_used + relay_penalty

      return effective_individual <= 2
```

### VCAC Team Constraints

```text
- Top 4 scorers per team per event (not 3!)
- A and B relays BOTH score
- Unlimited entries per event, but only top 4 score
- Non-scoring entries marked "Exhibition"

TEAMS: Seton, Trinity Christian, Oakcrest, Fredericksburg Christian,
       Immanuel Christian, St. John Paul the Great
```

### Strategic Optimization Rules (FOR ALGORITHM)

```text
IMPORTANT: Max 2 individual events is a CEILING, not a target.
The optimizer MUST consider using swimmers for 0, 1, or 2 events.

DECISION FACTORS:
1. POINT VALUE: Does this swimmer score more points in Event A than
   another swimmer who would take their spot?

2. OPPORTUNITY COST: If Swimmer X does Event A, they can't do Event B.
   Is Event A worth more than Event B for this swimmer?

3. RELAY PRIORITY: If swimmer is critical for relay (especially A relay),
   consider using 0-1 individual events to preserve them for relay.

4. DEPTH vs CONCENTRATION:
   - Deep team → spread entries across more swimmers
   - Weak team → concentrate best swimmers in best events

5. FATIGUE TRADEOFF: Swimmer doing 2 indiv + 2 relays (4 events) will
   have ~4-6% fatigue penalty. May be better to use 1 indiv + 2 relays.

STRATEGIC SCENARIOS:

Scenario A: "Relay Anchor"
  - Star swimmer is critical for 200 Free Relay and 400 Free Relay
  - Consider: 0 individual events, 2 relays (preserves for relay speed)
  - Or: 1 individual (their best), 2 relays

Scenario B: "Event Specialist"
  - Swimmer is top-3 in one event, outside top-8 in all others
  - Consider: 1 individual event only (their specialty)
  - Don't waste them in an event where they won't score

Scenario C: "Dual Threat"
  - Swimmer is top-3 in two different events
  - Use: 2 individual events (maximize their point contribution)

Scenario D: "Depth Player"
  - Swimmer is 5th-8th in multiple events
  - Consider: 1 event where they're strongest
  - Or: 2 events if team is weak and needs coverage

ALGORITHM HINT:
  For each swimmer, calculate:
    expected_points(events=[]) → what points lost if swimmer does 0 events
    expected_points(events=[A]) → points from their best event
    expected_points(events=[A,B]) → points from top 2 events (with fatigue)

  Choose configuration that maximizes TEAM points, not individual points.
```

---

## 🔧 System Architecture

### Tech Stack

| Component       | Technology                        | Notes               |
| --------------- | --------------------------------- | ------------------- |
| Frontend        | Next.js 16 (React 19, TypeScript) | Tailwind v4         |
| Backend         | FastAPI (Python 3.11+)            | Uvicorn             |
| Optimizer       | Nash Equilibrium + Heuristic      | Custom solver       |
| Data Processing | Pandas, NumPy                     |                     |
| Deployment      | Docker, Railway                   | Caddy reverse proxy |

### Key Ports

| Service        | Port  | Notes                       |
| -------------- | ----- | --------------------------- |
| Frontend (dev) | 3000  | Next.js dev server          |
| Backend API    | 8001  | FastAPI/Uvicorn             |
| Production     | $PORT | Railway assigns dynamically |

### Critical File Locations

```
/frontend/src/           - Next.js application
/swim_ai_reflex/backend/ - FastAPI backend
  /api/routers/          - API endpoints
  /services/             - Business logic
  /core/                 - Optimization, scoring
/.agent/                 - AI context and workflows
/docs/                   - Documentation
```

---

## 🧮 Optimization Engine

### Methods

| Method      | Description                | Use Case             |
| ----------- | -------------------------- | -------------------- |
| `gurobi`    | Integer programming solver | Precise optimization |
| `heuristic` | Greedy algorithm           | Fast, large datasets |
| `nash`      | Nash Equilibrium solver    | 1v1 game theory      |

### Key Constraints

1. **Max 2 individual events per swimmer** (diving counts as 1 individual)
2. **Max 4 total events per swimmer** (NFHS Rule 3-2-1)
3. **Max scorers per team per event**: 3 (dual), 4 (championship)
4. **Exhibition swimmers (grades 6-7) score 0 points** (dual meets only)
5. **Championship meets: no exhibition, all entered swimmers score**
6. **Fatigue modeling for multi-event swimmers**
7. **Relay swimmers have different fatigue profile**

### Scoring Types

- `visaa_top7` - Current default (top 7 places score)
- `dual_meet` - Standard 6-4-3-2-1-0
- `championship` - **TO BE IMPLEMENTED** (40-34-32...)

---

## 📋 Business Rules & Decisions

### Confirmed Decisions

| Decision                      | Date       | Rationale                     |
| ----------------------------- | ---------- | ----------------------------- |
| 6th-7th grade = exhibition    | 2025       | VISAA rules (grade 8+ scores) |
| Nash Equilibrium for 1v1      | 2025       | Game theory optimal           |
| Next.js migration from Reflex | 2026-01-10 | Better maintainability        |
| Fatigue = 1-3% per event      | 2025       | Coach validated estimate      |

### Open Questions

- [ ] Championship mode: Monte Carlo vs deterministic?
- [ ] Multi-team optimization: tractable approach?
- [ ] Psych sheet data source: SwimCloud API or manual?

---

## 🐛 Known Issues & Gotchas

1. **PDF Multi-Meet Parsing**: Files with multiple meets cause score inflation. Use `meet_alignment_service.align_meet_data` before optimization.

2. **Cache Invalidation**: PDF caching uses MD5 hash. Clear cache when testing new parsing logic.

3. **Frontend Assets**: Do NOT add generic `/assets/*` handler to Caddyfile - breaks Reflex static assets.

4. **Port Conflict**: Backend uses 8001, not 8000, to avoid conflicts.

5. **Playwright**: Web scraper has lazy imports to avoid crashes if playwright not installed.

6. **Team Name Scoring Bug (Previously "X - 0" scores)**: The `full_meet_scoring()` function only recognizes teams named `'seton'` or `'opponent'`. If opponent rosters have their real team names (e.g., "St. Mary's"), they score 0. **FIX:** In `optimization_service.py`, forcibly set `nash_opponent_lineup["team"] = "opponent"` and `best_lineup["team"] = "seton"` before scoring. Do NOT use `.fillna()` - it only sets null values!

7. **Championship target_team Bug (Jan 2026)**: The `ChampionshipGurobiStrategy` filters entries by team CODE (e.g., "SST"), but the router was passing the full name ("Seton"). **FIX:** In `optimization.py` line 182, use `target_team="SST"`, not `target_team="Seton"`. The strategy filters by `e.team.upper() == target_team.upper()` which requires the CODE.

8. **Championship "X - 0" Display Bug**: The frontend was showing championship scores as "254 - 0" (dual meet format) when it should show "Projected Score: 254". **FIX:** In `optimize/page.tsx` lines 220-235, check `meetMode === 'championship'` and render appropriate UI. Championship mode has no opponent, so "vs 0" was confusing.

---

## 📅 Important Dates

| Date            | Event                     | Action Needed           |
| --------------- | ------------------------- | ----------------------- |
| Feb 12-14, 2026 | VISAA State Championships | Championship mode ready |
| Spring 2026     | Season ends               |                         |

---

## 🏗️ Architecture Decisions

### Meet Type Pipeline Pattern (ADR-001)

**Decision:** Dual meet and championship workflows use separate pipeline classes with a shared data layer.

**Context:**
- Dual meets and championship meets have fundamentally different structures
- Mixing them in `optimization_service.py` caused the 270-0 scoring bug
- They have different inputs (2 rosters vs psych sheet), outputs, and algorithms

**Key Insight:**
| Aspect       | Dual Meet                      | Championship Meet   |
| ------------ | ------------------------------ | ------------------- |
| Input        | 2 team rosters                 | Unified psych sheet |
| Teams        | 2 (head-to-head)               | 6-8+ (multi-team)   |
| Algorithm    | Nash Equilibrium / Game Theory | Entry Selection ILP |
| API          | Single endpoint                | Multi-step wizard   |
| Optimization | Beat ONE opponent              | Maximize vs field   |

**Implementation:**
- `pipelines/dual_meet.py` - DualMeetPipeline class
- `pipelines/championship.py` - ChampionshipPipeline class
- `services/shared/` - Validation, normalization, caching

**Reference:** [MEET_TYPE_ARCHITECTURE.md](../docs/MEET_TYPE_ARCHITECTURE.md)

### Key Gotchas

1. **Interface Incompatibility**: `predict_best_lineups(our_roster, opponent)` vs `optimize_entries(psych_sheet, target_team)` - don't try to merge them!

2. **VCAC Relay 3 Penalty**: 400 Free Relay counts as individual event slot. Dedicated analysis in `Relay400TradeoffAnalyzer`.

3. **Championship is Multi-Step**: Project → Optimize Entries → Optimize Relays → Export. Don't try to do it in one API call.

---

## 📝 Changelog

| Date       | Update                                                      | Author |
| ---------- | ----------------------------------------------------------- | ------ |
| 2026-02-02 | **Fixed VCAC scoring tables** - relay=2x individual (was swapped) | AI     |
| 2026-02-02 | **Grade rules fixed** - exhibition = grades 6-7 (not 7-8)  | AI     |
| 2026-02-02 | **Championship rules verified** - no exhibition, all score  | AI     |
| 2026-02-02 | **Diving as individual event** - verified across all layers | AI     |
| 2026-02-02 | **NFHS Rule 3-2-1** - max 4 events, max 2 individual       | AI     |
| 2026-01-18 | **Fixed championship target_team bug** - "SST" not "Seton"  | AI     |
| 2026-01-18 | PRISM analysis: Debugged E2E championship optimization      | AI     |
| 2026-01-17 | **Pipeline Architecture Implemented** - Phase 1 complete    | AI     |
| 2026-01-17 | Created DualMeetPipeline + ChampionshipPipeline             | AI     |
| 2026-01-17 | Created shared services (validation, normalization)         | AI     |
| 2026-01-17 | New API routers: /api/v2/dual-meet, /api/v2/championship    | AI     |
| 2026-01-17 | 29 new pipeline tests (189 total passing)                   | AI     |
| 2026-01-17 | PRISM analysis: Meet type architecture redesign             | AI     |
| 2026-01-17 | Created MEET_TYPE_ARCHITECTURE.md with pipeline pattern     | AI     |
| 2026-01-17 | Created PRISM workflow for meta-cognitive problem-solving   | AI     |
| 2026-01-17 | Created data_contracts.py for centralized validation        | AI     |
| 2026-01-17 | Integrated data contracts into optimization router          | AI     |
| 2026-01-17 | Added 35 dataflow validation tests (161 total passing)      | AI     |
| 2026-01-16 | Refactored back-to-back constraint to use proper validation | AI     |
| 2026-01-16 | Coach-facing strategy reports (MD + HTML)                   | AI     |
| 2026-01-16 | VCAC point projection complete (Seton #1 at 1202 pts)       | AI     |
| 2026-01-16 | Integration tests fixed: 125 passed, 1 failed               | AI     |
| 2026-01-16 | Diving score projection added to PointProjectionEngine      | AI     |
| 2026-01-16 | Unified VCAC psych sheet created (997 entries, 7 teams)     | AI     |
| 2026-01-16 | Fixed legacy test files (pandas boolean filtering)          | AI     |
| 2026-01-16 | Test suite at 94% pass rate (125/133)                       | AI     |
| 2026-01-16 | SwimCloud scraping complete for all VCAC teams              | AI     |
| 2026-01-15 | Created knowledge base, added VISAA championship info       | AI     |
| 2026-01-10 | Next.js migration completed                                 |        |
| 2025-12-30 | Meet alignment service integrated                           | AI     |

---

## 🧠 Meta-Cognitive Development Principles

### Always-On Self-Reflection

For any non-trivial task, implicitly apply these principles:

**1. State Understanding First**
- Before solving, articulate what the problem actually is
- Identify hidden assumptions
- Clarify success criteria

**2. Multi-Perspective Critique**
Before finalizing any solution, quickly review from these angles:
| Perspective   | Key Question                       |
| ------------- | ---------------------------------- |
| 🔬 Logic       | Is this sound? What am I assuming? |
| 🛡️ Robustness  | What could go wrong? Edge cases?   |
| ⚡ Performance | Is this efficient? Will it scale?  |
| 🧪 Testability | How do I verify this works?        |

**3. Confidence Calibration**
- If confidence < 80%, say so explicitly
- Enumerate what would increase confidence
- Ask for user input on uncertain decisions

**4. Learning Extraction**
After completing significant tasks:
- What worked well?
- What should be different next time?
- Update knowledge base if relevant

**5. Show Your Work**
- Don't just provide solutions, explain reasoning
- Document non-obvious decisions
- Make trade-offs explicit

### Invoking Deep Thinking

For complex problems, explicitly invoke `/prism`:
- Architecture decisions
- Complex debugging
- Feature design
- Performance optimization

### The Golden Question

Before any implementation:
> "If I were a senior engineer reviewing this in a code review, what would I critique?"

Answer that question before submitting.

---

## 🐛 Bug Fixes & Lessons Learned

### 2026-02-01: Exhibition Swimmer Forfeit Points Bug

**Problem**: Exhibition swimmers (grade < 8) were incorrectly receiving forfeit points in dual meets.

**Root Cause**: When `fill_empty_slots()` added placeholder swimmers, it created a `scoring_eligible` column only for placeholders. After `pd.concat`, original swimmers had `NaN` for this column. The code then used `fillna(True)`, incorrectly marking grade 7 swimmers as scoring-eligible.

**Impact**:
- Test case showed Seton (all exhibition) receiving 15 points instead of 0
- Total meet points were correct (29), but distribution was wrong

**Fix**: Modified `dual_meet_scoring.py` to recalculate `scoring_eligible` from grade for any row where it's `NaN`, before applying `fillna`.

**Regression Tests Added**:
- `test_forfeit_points_go_to_eligible_team` - Verifies exhibition teams get 0 points
- `test_exhibition_swimmers_do_not_displace_scorers` - Verifies eligible swimmers get full points

**Files Modified**:
- `swim_ai_reflex/backend/core/dual_meet_scoring.py` (lines 106-130)
- `tests/test_scoring_constraints.py` (20 tests total)

**Lesson**: When using `pd.concat` with DataFrames that have different columns, always handle the resulting `NaN` values explicitly before using `fillna` with a default.

---

## 🔗 Quick Reference Links

- **Seton Swimming**: https://setonswimming.org
- **VISAA**: https://visaa.org
- **SwimCloud**: https://www.swimcloud.com
- **API Docs (local)**: http://localhost:8001/api/docs

---

_This file is the primary source of truth for AI sessions. Keep it updated!_
