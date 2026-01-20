# AquaForge Championship Adaptation Strategy

## 2026 VISAA State Swimming & Diving Championships

**Document Created**: January 15, 2026  
**Status**: Strategic Planning & Analysis  
**Author**: AI-Assisted Analysis

---

## 📅 Event Overview: Seton's Next Event

### 2026 VISAA State Swimming & Diving Championships

| Detail             | Information                                                              |
| ------------------ | ------------------------------------------------------------------------ |
| **Dates**          | February 12-14, 2026 (Thursday-Saturday)                                 |
| **Swimming Venue** | SwimRVA / Collegiate Aquatic Center, 505 Ridgedale Parkway, Richmond, VA |
| **Diving Venue**   | St. Catherine's School, 6001 Grove Avenue, Richmond, VA 23226            |
| **Hosts**          | Bishop Ireton High School & Collegiate School                            |
| **Governing Body** | Virginia Independent Schools Athletic Association (VISAA)                |
| **Rulebook**       | National Federation High School (NFHS) Swimming & Diving Rules           |

### Schedule Breakdown

| Day          | Date   | Events                                                                                              |
| ------------ | ------ | --------------------------------------------------------------------------------------------------- |
| **Thursday** | Feb 12 | Boys Diving Prelims/Semis (4:15 PM at St. Catherine's), Team Warm-ups, Coaches Meetings             |
| **Friday**   | Feb 13 | Swimming Prelims Events 1-12 (9:15 AM), Girls Diving Prelims/Semis (4:15 PM), Swim Finals (5:50 PM) |
| **Saturday** | Feb 14 | Swimming Prelims Events 13-24 (9:15 AM), Diving Finals (afternoon), Swim Finals (5:15 PM)           |

---

## 🏆 Teams & Competition Context

### Seton School Swim Team Profile

| Attribute             | Details                                                |
| --------------------- | ------------------------------------------------------ |
| **School**            | Seton School, Manassas, Virginia                       |
| **Head Coach**        | Jim Koehr (since 2002, coaching since 2000)            |
| **Division**          | VISAA Division II                                      |
| **Participation**     | ~40% of 350 student body (grades 7-12)                 |
| **Head Diving Coach** | Ashley Keapproth (VISAA Diving Coach of the Year 2024) |

### Historical Success

**Boys' State Championships (Division II):**

- 2006, 2009, 2010, 2011

**Girls' State Championships (Division II):**

- 2008, 2009, 2010, 2011, 2021, 2023

**2025 Results:**

- Boys: Division II Runner-up
- Girls: Division II Runner-up

**Conference Titles:** 60 conference/championship titles (1995-2026)

### Coach Jim Koehr Recognition

- VISAA Swimming Coach of the Year: 2018, 2019
- VISAA Silver Anniversary Legacy Award (one of 25 most influential individuals)
- VISAA Executive Committee Secretary: 2005-2019
- Has hosted/co-hosted VISAA State Championship 7 times

---

## 📊 VISAA Championship Scoring Rules

### Championship Format Scoring

**Championship Finals Points (16 places):**

```
1st:  40 pts    5th:  28 pts    9th:  18 pts     13th: 8 pts
2nd:  34 pts    6th:  26 pts    10th: 14 pts     14th: 6 pts
3rd:  32 pts    7th:  24 pts    11th: 12 pts     15th: 4 pts
4th:  30 pts    8th:  22 pts    12th: 10 pts     16th: 2 pts
```

**Consolation Finals Points (16 places):**

```
1st:  20 pts    5th:  14 pts    9th:  9 pts      13th: 4 pts
2nd:  17 pts    6th:  13 pts    10th: 7 pts      14th: 3 pts
3rd:  16 pts    7th:  12 pts    11th: 6 pts      15th: 2 pts
4th:  15 pts    8th:  11 pts    12th: 5 pts      16th: 1 pt
```

### Key Scoring Rules

| Rule                      | Description                                                             |
| ------------------------- | ----------------------------------------------------------------------- |
| **Prelims/Finals System** | Swimmers qualify through prelims for championship or consolation finals |
| **Bonus Events**          | Swimmers in "bonus events" are NOT eligible to score                    |
| **Multi-Team Format**     | All Division II teams compete simultaneously                            |
| **Relay Scoring**         | Relays score double points                                              |
| **NFHS Rules**            | National Federation High School rulebook governs                        |

---

## 🔄 Constraint Differences: Dual Meet vs. Championship

| Constraint                 | Current AquaForge (Dual Meet) | Championship Meet                | Adaptation Required |
| -------------------------- | ----------------------------- | -------------------------------- | ------------------- |
| **Opponents**              | Single opponent               | 15-30+ teams                     | ⚠️ **MAJOR**        |
| **Scoring System**         | 6-4-3-2-1-0 (top 6)           | 40-34-32-30... (16 places)       | ⚠️ **MAJOR**        |
| **Format**                 | Timed finals                  | Prelims → Finals                 | ⚠️ **MAJOR**        |
| **Entry Limits**           | 3 per event per team          | Varies (typically 2-3 per event) | ✅ Minor            |
| **Individual Event Limit** | 2 events + relays             | 2 events + relays                | ✅ Same             |
| **Strategy Focus**         | Beat one opponent             | Maximize team points             | ⚠️ **MAJOR**        |
| **Information Available**  | Full opponent roster          | Psych sheet with seed times      | ⚠️ **MODERATE**     |
| **Exhibition Rules**       | Grades 7-8 non-scoring        | May vary by championship         | ✅ Minor            |

---

## 🧠 AquaForge Adaptation: Analysis & Recommendations

### Current System Capabilities

AquaForge currently uses:

1. **Nash Equilibrium Solver** - Game theory optimization for 1v1 matchups
2. **Heuristic Fallback** - For complex/large datasets
3. **Event Swarming Strategy** - Strategic sacrifice of weak events
4. **Fatigue Modeling** - Multi-event swimmer fatigue impacts
5. **Exhibition Swimmer Logic** - 7th-8th grade non-scoring displacement

### ✅ PLUSSES: What Works Well for Championships

#### 1. **Core Optimization Engine**

- The heuristic/mathematical optimization framework is solid
- Fatigue modeling remains critical for multi-day championships
- Nash Equilibrium concepts can extend to multi-party scenarios

#### 2. **Event Swarming Concepts**

- Strategic event selection remains valuable
- "Best events" identification translates directly
- Relay swimmer allocation logic applies

#### 3. **Data Infrastructure**

- Excel/CSV parsing for psych sheets
- Swimmer time database
- Event categorization already exists

#### 4. **Exhibition Logic**

- 7th-8th grade handling may still apply in VISAA
- Displacement strategy concepts useful for consolation scoring

---

### ⚠️ MINUSES: Significant Challenges

#### 1. **Multi-Team Optimization Complexity**

- **Current:** 1v1 optimization (tractable)
- **Required:** 15-30+ team simultaneous optimization
- **Issue:** Exponential complexity increase
- **Solution Difficulty:** 🔴 HIGH

#### 2. **Prelims/Finals Format**

- **Current:** Timed finals only
- **Required:** Two-stage qualification system
- **Issue:** Need to model prelim qualifying times and finals performance
- **Solution Difficulty:** 🟠 MEDIUM

#### 3. **Scoring System Overhaul**

- **Current:** Dual meet scoring (6-4-3-2-1-0)
- **Required:** Championship scoring (40-34-32... with prelims/finals)
- **Issue:** Complete scoring module rewrite
- **Solution Difficulty:** 🟡 MEDIUM-LOW

#### 4. **Opponent Information Uncertainty**

- **Current:** Full opponent roster available
- **Championship:** Psych sheet times only; actual attendance uncertain
- **Issue:** Must handle probabilistic entries
- **Solution Difficulty:** 🟠 MEDIUM

#### 5. **Strategic Paradigm Shift**

- **Current:** Beat opponent team
- **Championship:** Maximize team points regardless of individual wins
- **Issue:** Different optimization objective function
- **Solution Difficulty:** 🟠 MEDIUM

---

## 💡 Suggested Adaptation Strategies

### Strategy A: "Psych Sheet Analyzer" Mode (Simpler)

**Concept:** Transform AquaForge from optimizer to analyzer/recommender

**Features:**

1. **Import psych sheet** (from SwimCloud or HyTek export)
2. **Analyze Seton positions** - Where do our swimmers seed?
3. **Identify scoring opportunities** - Events where Seton is in striking distance
4. **Time drop predictions** - Which swimmers are likely to improve?
5. **Relay configuration optimization** - Best relay order/splits
6. **Point projection** - Expected team score range

**Pros:**

- ✅ Faster to implement (weeks vs. months)
- ✅ Highly valuable for coach decision-making
- ✅ Leverages existing data infrastructure

**Cons:**

- ❌ Less "optimization," more "analysis"
- ❌ Doesn't fully utilize Nash Equilibrium solver

**Complexity:** 🟡 MEDIUM

---

### Strategy B: "Championship Optimizer" Mode (Complex)

**Concept:** Build full multi-team optimization engine

**Features:**

1. **Multi-team scoring simulation** - Model all competitors
2. **Prelims/Finals prediction** - Two-stage optimization
3. **Monte Carlo simulation** - Handle entry uncertainty
4. **Event selection optimization** - Which events to enter each swimmer
5. **Relay formation optimization** - Best relay configurations
6. **What-if scenarios** - Impact of scratches/changes

**Technical Approach:**

```python
# Simplified Championship Optimizer Architecture
class ChampionshipOptimizer:
    def __init__(self):
        self.scoring = ChampionshipScoring()  # New scoring module
        self.simulator = MonteCarloSimulator()
        self.multi_team_engine = MultiTeamNashSolver()

    def optimize_entries(self, our_roster, psych_sheet, constraints):
        """
        Optimize which events each swimmer should enter
        to maximize expected team points.
        """
        scenarios = self.simulator.generate_scenarios(psych_sheet)
        for scenario in scenarios:
            points = self.calculate_expected_points(our_roster, scenario)
        return optimal_entries

    def optimize_relays(self, available_swimmers, relay_events):
        """
        Find optimal relay configurations considering:
        - Individual event fatigue
        - Split times vs. individual times
        - Leg order optimization
        """
        return optimal_relay_assignments
```

**Pros:**

- ✅ Full optimization capability
- ✅ Unique competitive advantage
- ✅ Extends platform value significantly

**Cons:**

- ❌ Significant development effort (months)
- ❌ Computational complexity challenges
- ❌ Data acquisition challenges (competitor information)

**Complexity:** 🔴 HIGH

---

### Strategy C: "Hybrid Focus" Mode (Recommended)

**Concept:** Combine targeted optimization with comprehensive analysis

**Phase 1 (Pre-Championship): Analysis Mode**

- Import psych sheet
- Seed time analysis
- Point projection modeling
- Event entry recommendations

**Phase 2 (Entry Optimization):**

- Optimize which 2 individual events each swimmer should enter
- Consider: seed position, time drop potential, fatigue, relay needs

**Phase 3 (Relay Optimization):**

- Full relay formation optimization (existing strength)
- Consider: who's swimming individuals, split vs. relay specialties

**Phase 4 (Finals Strategy):**

- Re-optimize after prelims
- Adjust for actual qualifying positions
- Late scratch/strategy recommendations

**Implementation Priority:**

| Component                   | Priority | Effort       | Value    |
| --------------------------- | -------- | ------------ | -------- |
| Psych sheet import          | 🔴 P0    | Low          | High     |
| Championship scoring module | 🔴 P0    | Medium       | Critical |
| Seed position analysis      | 🔴 P0    | Low          | High     |
| Point projection            | 🟠 P1    | Medium       | High     |
| Entry optimization          | 🟠 P1    | Medium       | High     |
| Relay optimizer             | 🟠 P1    | Low (exists) | High     |
| Monte Carlo simulation      | 🟡 P2    | High         | Medium   |
| Multi-team Nash solver      | 🟢 P3    | Very High    | Medium   |

**Pros:**

- ✅ Delivers value incrementally
- ✅ Coach can use features as they're built
- ✅ Manages complexity progressively

**Cons:**

- ❌ Not "complete" initially
- ❌ Requires iterative development

**Complexity:** 🟠 MEDIUM (phased)

---

## 🔧 Technical Implementation Recommendations

### New Backend Modules Needed

```
swim_ai_reflex/backend/
├── services/
│   ├── optimization_service.py        # Existing
│   └── championship_service.py        # NEW
├── core/
│   ├── scoring.py                     # Existing (needs extension)
│   ├── championship_scoring.py        # NEW
│   ├── psych_sheet_parser.py          # NEW
│   └── point_projector.py             # NEW
└── models/
    ├── championship_models.py         # NEW
    └── psych_sheet_models.py          # NEW
```

### New Frontend Views Needed

```
frontend/src/app/
├── championship/
│   ├── page.tsx                       # Championship mode landing
│   ├── psych-sheet/page.tsx           # Psych sheet upload/analysis
│   ├── entries/page.tsx               # Entry optimization
│   ├── relays/page.tsx                # Relay optimization
│   └── projections/page.tsx           # Point projections
```

### Data Model Extensions

```python
# Championship-specific models
class ChampionshipMeet(BaseModel):
    meet_name: str
    meet_date: datetime
    venue: str
    divisions: List[str]
    scoring_system: ScoringSystem
    events: List[ChampionshipEvent]

class PsychSheetEntry(BaseModel):
    swimmer_name: str
    team: str
    event: str
    seed_time: float
    seed_rank: int
    personal_best: Optional[float]
    season_best: Optional[float]

class ChampionshipScoring(BaseModel):
    championship_finals: Dict[int, int]  # place -> points
    consolation_finals: Dict[int, int]
    bonus_heats_score: bool = False
```

---

## 📋 Implementation Roadmap

### Sprint 1: Foundation (1-2 weeks)

- [ ] Define `ChampionshipScoring` module with VISAA point tables
- [ ] Create psych sheet CSV/Excel parser
- [ ] Build basic seed position analysis view
- [ ] Add "Championship Mode" toggle to UI

### Sprint 2: Analysis Features (2-3 weeks)

- [ ] Point projection engine (given seed times, estimate team score)
- [ ] Event-by-event breakdown view
- [ ] "Time needed to score" calculator
- [ ] Comparison with historical results

### Sprint 3: Entry Optimization (2-3 weeks)

- [ ] Event selection optimizer per swimmer
- [ ] Constraint satisfaction (2 individual + relay limit)
- [ ] Fatigue impact on multi-event swimmers
- [ ] UI for coach to override/adjust

### Sprint 4: Relay & Finals (2 weeks)

- [ ] Extend existing relay optimizer for championship
- [ ] Post-prelims re-optimization
- [ ] Finals heat/lane analysis
- [ ] Real-time scoring tracking

### Future Sprints

- Monte Carlo simulation for uncertainty
- Historical trend analysis
- Competitor analysis (team-level)
- Mobile access for poolside use

---

## 🏁 Summary

### Key Takeaways

1. **The 2026 VISAA Championships are February 12-14** at SwimRVA in Richmond
2. **Seton is coming off Division II Runner-up finishes** for both boys and girls in 2025
3. **AquaForge's core optimizer needs significant adaptation** for multi-team championship format
4. **Recommended approach: Hybrid/Phased implementation** starting with analysis tools
5. **Quick wins available:** Psych sheet analysis, point projections, relay optimization

### Next Steps

1. **Confirm with Coach Koehr** - Which features would be most valuable?
2. **Obtain sample psych sheet** - From previous VISAA championships or SwimCloud
3. **Begin Sprint 1** - Championship scoring module and psych sheet parser
4. **Set timeline** - Aim for basic functionality before February 12

### Resources

- **Seton Swimming Website:** [setonswimming.org](https://setonswimming.org)
- **VISAA:** [visaa.org](https://visaa.org)
- **SwimCloud** (for psych sheets and results)
- **SwimRVA** (venue information)

---

_This document is a living analysis. Update as requirements evolve and new information becomes available._

**Sources:**

- setonswimming.org (Coach information, team history, 2026 event details)
- visaa.org (Championship structure, divisions, scoring rules)
- swimmingworldmagazine.com (Coach recognition)
- scribd.com (VISAA scoring documentation)
