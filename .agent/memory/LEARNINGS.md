# Session Learnings 📚

Key learnings from each session that should persist.

---

## 2026-02-01 Session

### Key Learnings

1. **Aqua is now primary optimizer** - $10K/year Gurobi license saved
2. **Exhibition swimmers (grade ≤7) never score** - can only displace opponents
3. **Relay scoring differs by meet type:**
   - Dual: Standard points [10, 5, 3]
   - Championship: 2x individual points
   - VCAC: Inverted (individual > relay)

### Agent Updates Made

- Updated `optimization_router.py` with `prefer_gurobi` flag
- Created `ExhibitionDeploymentAnalyzer` for strategic exhibition placement
- Documented relay scoring in `KNOWLEDGE_BASE.md`

### Next Session Context

- P2: Port Nash equilibrium to Gurobi (if needed as fallback)
- Championship modules for Feb 7 VCAC meet
- Validate Aqua vs Gurobi in parallel before full transition

---

## 2026-02-02 Session

### Championship Event Counting: How Diving, Individual Events, and Relays Affect Swimmer Limits

#### The Rule (All Meet Types)

Every swimmer is limited to **max 2 individual events**. What counts as "individual" is nuanced:

```
EFFECTIVE INDIVIDUAL COUNT =
    swim_individual_count       (0-2 swimming events)
  + (1 if is_diver else 0)     (diving = 1 individual slot)
  + relay_3_penalty             (VCAC only: 400 FR = 1 individual slot)

VALID if: effective_individual <= 2
```

#### Diving Counts as 1 Individual Event

- Diving uses the **individual point scale** (not relay) in all meet types
- Diving counts as **1 individual event slot** toward the max-2 limit
- A diver who also swims 2 individual events = 3 effective individual = **INVALID**
- A diver who swims 1 individual event = 2 effective individual = **VALID**

#### VCAC Championship Specifics (Feb 7, 2026)

| Combination | Eff. Indiv | Total Events | Valid? |
|---|---|---|---|
| 2 swim, no dive, 2 relays | 2 | 4 | YES |
| 1 swim, dive, 2 relays | 2 | 4 | YES |
| 2 swim, dive, 0 relays | 3 | 3 | NO |
| 1 swim, no dive, 3 relays (400FR) | 2 | 4 | YES |
| 2 swim, no dive, 3 relays (400FR) | 3 | 5 | NO |
| 0 swim, dive, 3 relays (400FR) | 2 | 4 | YES |
| 1 swim, dive, 3 relays (400FR) | 3 | 5 | NO |

#### Where This Is Enforced (Code Layers)

| Layer | File | How Diving Is Handled |
|---|---|---|
| Rules validation | `core/rules.py:293-313` | `VCACChampRules.is_valid_entry()` adds `1 if is_diver` |
| Championship optimizer | `strategies/championship_strategy.py:169-176` | Deducts 1 from limit per diver |
| Dual meet Gurobi | `strategies/gurobi_strategy.py:110` | Diving implicitly in `individual_events` (no "Relay") |
| Dual meet Aqua | `strategies/aqua_optimizer.py:316,334` | Same implicit counting |
| Scoring engine | `core/scoring.py:98-99` | `is_relay=False` → uses `individual_points` |

#### Relay Impact on Swimmer Counts

| Meet Type | Relay 1 & 2 | Relay 3 (400 FR) | Max Total |
|---|---|---|---|
| Dual Meet | Free (no slot cost) | Free (no slot cost) | 4 events |
| VCAC Championship | Free (no slot cost) | **Costs 1 individual slot** | 4 events |
| VISAA State | Free (no slot cost) | TBD (verify before States) | 4 events |

#### Scoring Impact: Diving Point Scale

| Meet Type | Diving 1st Place | Relay 1st Place | Ratio |
|---|---|---|---|
| Dual Meet | 8 pts | 10 pts | Relay > Individual |
| VCAC Championship | 16 pts | 32 pts | Relay = 2x Individual |
| VISAA State | 20 pts | 40 pts | Relay = 2x Individual |

#### Regression Tests Added

9 new tests in `tests/test_scoring_constraints.py::TestDivingCountsAsIndividualEvent`:
- `test_vcac_diving_counts_as_individual_flag`
- `test_vcac_diver_plus_1_swim_is_valid`
- `test_vcac_diver_plus_2_swims_is_invalid`
- `test_vcac_diver_plus_1_swim_plus_2_relays_is_valid`
- `test_vcac_diver_only_is_valid`
- `test_vcac_diver_plus_1_swim_plus_relay3_is_invalid`
- `test_vcac_non_diver_plus_2_swims_is_valid`
- `test_diving_uses_individual_points_not_relay`
- `test_diving_scored_as_individual_in_full_meet`

#### Verified: Max 4 Total Events Per Swimmer (NFHS Rule 3-2-1)

**Question raised:** User suspected championship meets may limit swimmers to 3 total events
(2 individual + 1 relay, or 3 relays) rather than 4.

**Answer: 4 events is correct.** Verified via multiple sources:

- **NFHS Rule 3-2-1:** "A competitor shall be permitted to enter a maximum of four events,
  no more than two of which may be individual events."
  - Source: [NFHS Swimming Rules Interpretations 2025-26](https://nfhs.org/resources/sports/swimming-and-diving-rules-interpretations-2025-26)
  - Source: [High School Swimming 101](https://www.gomotionapp.com/rechsersd/__doc__/High%20School%20Swimming.pdf)

- **VISAA follows NFHS rules.** The VISAA State Championship meet info confirms 4-event max.
  - Source: [VISAA 2025 State Championship Meet Info](https://setonswimming.org/wp-content/uploads/2024/11/VISAA-Swim-Dive-State-Championship-2025-Meet-Information.pdf)

- **Seton Swimming confirms:** "No swimmer can swim more than 2 individual events or more than 4 events total."
  - Source: [setonswimming.org](https://setonswimming.org/so-how-is-a-high-school-meet-scored-anyway/)

**Where "3 events" comes from:** Modified/Junior High programs often have a 3-event max
(1 relay + 2 individual, or 2 relays + 1 individual). This may have been confused with
varsity championship rules.

**The "4" that may have caused confusion:** "Top 4 scorers per team per event" is a
DIFFERENT constraint — that's max scoring entries per team per individual event at VCAC
championship. This is NOT the same as max events per swimmer.

Valid event combinations (all meet types):
```
2 individual + 2 relays = 4 events ✅
2 individual + 1 relay  = 3 events ✅
1 individual + 3 relays = 4 events ✅
0 individual + 3 relays = 3 events ✅
```

**Docs fixed:** `IDEAL_DATA_FORMAT.md` and `CSV_TEMPLATE_GUIDE.md` incorrectly said
"Max 3 total events" — corrected to "Max 4 total events (NFHS Rule 3-2-1)".

**Code verified:** All rules classes correctly use `max_total_events_per_swimmer = 4`.

#### Verified: Championship Meets = Varsity Only, All Swimmers Score

**Question raised:** Are all swimmers scoring at championship meets, or do exhibition
rules still apply?

**Answer: All entered swimmers score at championships. No exhibition.**

- **VCAC Championship & VISAA State:** No exhibition swims allowed. Only Varsity
  swimmers participate. Coach Koehr publishes an eligible swimmer list for championship season.
- **7th graders:** Do NOT enter championship meets. They swim at the separate JV Invitational.
- **8th-12th graders:** All entered swimmers are scoring-eligible. Grade-based exhibition
  logic from dual meets does NOT apply at championships.
- **Top 4 per team per event:** Still enforced — if a team has 5+ entries, only top 4 score.

Sources:
- [Seton Parents' Handbook 2024-25](https://setonswimming.org/wp-content/uploads/2024/11/Seton-Swim-Dive-Team-Handbook-24-25-v16.pdf)
- [setonswimming.org](https://setonswimming.org/so-how-is-a-high-school-meet-scored-anyway/)

**Code change:** Added `no_exhibition: bool = True` to `VCACChampRules` in `rules.py`.

**Implication for optimizer:** When running championship optimization, the grade-based
`min_scoring_grade` filter is a safety net only. In practice, every swimmer in championship
data should be varsity (grade 8+), and all of them score.

#### CRITICAL FIX: VCAC Scoring Tables Were Swapped in Documentation

**Discovery:** During consolidation, found that `VCAC_CHAMPIONSHIP_FEB7_2026.md` had individual
and relay scoring tables swapped. The doc claimed Individual=[32,26,24...] and Relay=[16,13,12...]
with a warning "INDIVIDUAL events are worth MORE than relays!" This was propagated to the JSON
data file, PRISM analysis, and KNOWLEDGE_BASE relay comparison table.

**Resolution:** The CODE was correct all along. Relay = 2x Individual is the universal standard
for championship swimming scoring:
- **NCAA Rule 7** explicitly defines 12-place scoring with relay = 2x individual
- **USA Swimming** rules state "Individual point values shall be doubled for relays"
- **NFHS** follows the same standard
- **setonswimming.org** confirms this for VCAC/VISAA meets

**Files fixed (4):**
- `docs/VCAC_CHAMPIONSHIP_FEB7_2026.md` - Scoring tables corrected
- `data/meets/2026-02-07_vcac_championship.json` - individual/relay arrays swapped to correct
- `docs/PRISM_CHAMPIONSHIP_SCORING_ANALYSIS.md` - All scoring references corrected
- `.agent/KNOWLEDGE_BASE.md` - Relay comparison table and VCAC section corrected

**Lesson:** Always verify domain rules against authoritative external sources (NCAA, NFHS,
governing body) before documenting. Internal docs can propagate errors if not cross-checked.

#### Grade Exhibition Rules Fixed

**Discovery:** `SCORING_RULES.yaml` had `exhibition_grades: [7, 8]` which incorrectly includes
8th graders as exhibition. The code uses `min_scoring_grade = 8` (grade >= 8 scores).

**Fix:** Changed to `exhibition_grades: [6, 7]` and `scoring_grades: [8, 9, 10, 11, 12]`.

#### Known Gaps (Non-Critical)

- `enforce_max_events_per_swimmer()` in `scoring.py:202` is a no-op placeholder
- `VISAAStateRules` and `SetonDualRules` lack `is_valid_entry()` methods
- `is_individual_event()` on `VISAADualRules` excludes diving (by design, never called)
- VISAA State relay-3 penalty not yet confirmed (verify before Feb 12-14 States)

---

## 2026-02-02 Session (Championship Focus)

### Key Implementations

1. **P0: Live Meet Tracker** - Real-time championship tracking
   - `record_result()` returns points immediately
   - `get_clinch_scenarios()` shows paths to each position
   - 9 API endpoints for meet-day use

2. **P1: Scenario Analyzer** - What-if line-up analysis
   - `compare_scenarios()` for A/B testing lineups
   - `find_best_swap()` for optimal event changes
   - `quick_what_if()` for natural language queries

### VCAC Scoring Verified
- Individual 1st = 16 points
- Relay 1st = 32 points
- Full table: [16, 13, 12, 11, 10, 9, 7, 5, 4, 3, 2, 1]

### Next Session Context
- Complete P1 tests
- Wire live tracker API to main app
- Test with real VCAC psych sheet data
