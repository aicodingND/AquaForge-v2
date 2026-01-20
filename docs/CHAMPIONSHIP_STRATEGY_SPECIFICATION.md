# AquaForge Championship Strategy System

## Comprehensive Technical Specification

**Document:** Architecture & Design Specification  
**Target Event:** VCAC Championship (Feb 7, 2026)  
**Created:** January 16, 2026  
**Version:** 2.0

---

## 📋 Executive Summary

This document specifies a comprehensive **Championship Strategy & Rostering System** for AquaForge, extending beyond dual-meet capabilities to handle multi-team championship events with sophisticated optimization, scenario planning, and real-time race-day adjustments.

### Design Philosophy

> **"Championship meets are not dual meets at scale—they require fundamentally different strategic thinking."**

In a dual meet, you beat ONE opponent. In a championship, you:

1. Maximize your finish position against ALL teams
2. Focus resources where they matter most
3. Make trade-offs that wouldn't exist in a 1v1 scenario

---

## 🏗️ System Architecture

### Module Hierarchy

```
ChampionshipStrategySystem/
├── Core Engine (Orchestration)
│   ├── ChampionshipStrategyEngine      # Main orchestrator
│   └── MeetConfigurationManager        # Rules, constraints, profiles
│
├── Optimization Layer (Gurobi-Powered)
│   ├── RosterOptimizer                # Entry selection (MILP)
│   ├── RelayOptimizer                 # Relay configuration (Hungarian + MILP)
│   └── GlobalOptimizer                # Joint individual + relay (complex ILP)
│
├── Analysis Layer
│   ├── PointProjectionEngine          # ✅ EXISTS - Core projections
│   ├── OpponentAnalyzer               # Multi-team threat assessment
│   └── SwingEventIdentifier           # ✅ EXISTS - Leverage points
│
├── Simulation Layer
│   ├── ScenarioSimulator              # What-if analysis
│   ├── MonteCarloProjector            # Probabilistic outcomes
│   └── SensitivityAnalyzer            # High-impact variables
│
└── Race Day Layer
    ├── LiveScoreTracker               # Real-time standings
    ├── DynamicStrategyAdjuster        # Mid-meet pivots
    └── PostMeetAnalyzer               # Actual vs. projected review
```

---

## 📊 Method-by-Method Analysis

### TIER 1: ESSENTIAL (High Value, Must Implement)

---

#### 1.1 RosterOptimizer (Gurobi-Powered MILP)

**What It Does:**  
Optimally assigns swimmers to individual events while respecting all meet constraints.

**Why It's Essential:**  
The current `EntrySelectionOptimizer` uses scipy's MILP which works but is limited. Gurobi provides:

- 10-100x faster solve times for complex problems
- Better handling of edge cases
- Support for soft constraints and multi-objective optimization
- Industry-standard reliability

**Current State:** ✅ Exists (scipy MILP) → ⬆️ Upgrade to Gurobi

**Mathematical Formulation:**

```
DECISION VARIABLES:
  x[i,j] ∈ {0,1}  = 1 if swimmer i assigned to event j

OBJECTIVE:
  MAXIMIZE Σᵢⱼ (expected_points[i,j] × x[i,j])

CONSTRAINTS:
  1. Σⱼ x[i,j] ≤ 2                           ∀i (max 2 individual events)
  2. Σⱼ x[i,j] ≤ 1      if diver[i]=True     ∀i (divers get 1 slot)
  3. Σᵢ (x[i,j] × rank[i,j] ≤ 4) ≤ 4        ∀j (max 4 scorers per event)
  4. x[i,j] = 0         if no_time[i,j]      ∀i,j (can't swim without seed)
```

**Example:**

```python
# Gurobi implementation
from gurobipy import Model, GRB

def optimize_entries(swimmers, events, point_matrix, divers):
    model = Model("entry_selection")

    # Decision variables
    x = model.addVars(len(swimmers), len(events), vtype=GRB.BINARY, name="x")

    # Objective: maximize points
    model.setObjective(
        sum(point_matrix[i,j] * x[i,j]
            for i in range(len(swimmers))
            for j in range(len(events))),
        GRB.MAXIMIZE
    )

    # Constraint: max 2 events (1 if diver)
    for i, swimmer in enumerate(swimmers):
        max_events = 1 if swimmer in divers else 2
        model.addConstr(sum(x[i,j] for j in range(len(events))) <= max_events)

    model.optimize()
    return extract_solution(model, x, swimmers, events)
```

**Pros:**

- ✅ Mathematically optimal solution
- ✅ Handles complex constraints elegantly
- ✅ Gurobi is free for academic use
- ✅ Fast (subsecond for typical meet sizes)

**Cons:**

- ❌ Requires Gurobi license (free for academic, $$ for commercial)
- ❌ Learning curve for model formulation
- ❌ Overkill for very small meets

**Recommendation:** ⭐⭐⭐⭐⭐ **MUST HAVE** - Upgrade from scipy to Gurobi

---

#### 1.2 RelayOptimizer (Gurobi + Hungarian Hybrid)

**What It Does:**  
Optimizes A and B relay compositions for all 3 relays, considering VCAC's unique rule where Relay 3 (400 Free) costs an individual event slot.

**Why It's Essential:**  
Relays are complex at VCAC:

- 200 Medley: Fixed stroke order (Back→Breast→Fly→Free)
- 200 Free: Flexible order
- 400 Free: **Counts as individual event** (massive trade-off)

**Algorithm Design:**

```
STAGE 1: POOL IDENTIFICATION
  - Who is available for relays?
  - Consider individual event commitments
  - Identify "relay-only" swimmers (weak in individual)

STAGE 2: MEDLEY RELAY (Hungarian Algorithm)
  - Assignment problem: swimmers → strokes
  - Minimize total relay time
  - Use scipy or Gurobi's assignment solver

STAGE 3: FREE RELAYS (Greedy + MILP)
  - 200 Free: Simple greedy (4 fastest)
  - 400 Free: MILP with trade-off analysis (see below)

STAGE 4: 400 FREE TRADE-OFF ANALYSIS
  - For each potential 400 Free swimmer:
    - Calculate individual points they'd score
    - Calculate marginal relay points they'd add
    - If relay_gain > individual_loss → include
    - Otherwise → skip 400 relay or use different swimmer
```

**400 Free Trade-Off Example:**

| Swimmer | 100 Free Split | Individual Points Lost | Relay Points Gained | Net    |
| ------- | -------------- | ---------------------- | ------------------- | ------ |
| Mike S. | 48.2           | 22 (100 Free 4th)      | +3 (faster relay)   | -19 ❌ |
| Tom J.  | 52.1           | 0 (non-scorer)         | +2                  | +2 ✅  |
| Dan K.  | 49.5           | 6 (100 Free 7th)       | +4                  | -2 ❌  |

**Decision:** Use Tom J on 400 relay, scratch Mike S to swim 100 Free.

**Pros:**

- ✅ Handles VCAC's unique relay-3 rule correctly
- ✅ Explicit trade-off analysis visible to coach
- ✅ Considers both individual AND relay points

**Cons:**

- ❌ Requires accurate split times (often estimated from individual times)
- ❌ Doesn't model relay exchange efficiency

**Recommendation:** ⭐⭐⭐⭐⭐ **MUST HAVE**

---

#### 1.3 ScenarioSimulator

**What It Does:**  
Runs "what-if" analysis to answer strategic questions before making decisions.

**Why It's Essential:**  
Coaches need to answer questions like:

- "What if we move John from 50 Free to 100 Fly?"
- "What if their best sprinter scratches?"
- "How many points do we lose if Sarah gets sick?"

**Key Methods:**

```python
class ScenarioSimulator:

    def simulate_entry_change(self, swimmer, old_events, new_events) -> Projection:
        """Move swimmer from one event lineup to another."""
        # Create modified psych sheet
        # Rerun projection
        # Return delta analysis

    def simulate_time_drop(self, swimmer, event, new_time) -> Projection:
        """What if swimmer improves their time?"""

    def simulate_scratch(self, swimmer, events="all") -> Projection:
        """What if swimmer scratches (injury, illness)?"""

    def simulate_opponent_change(self, opponent_team, swimmer, change_type) -> Projection:
        """Model opponent roster changes."""

    def compare_scenarios(self, scenario_a, scenario_b) -> Comparison:
        """Side-by-side comparison of two strategies."""
```

**Example Output:**

```
SCENARIO: Move Daniel Sokban from 50 Free → 100 Free

CURRENT:
  50 Free: Daniel Sokban (2nd place, 26 pts)
  100 Free: Michael Zahorchak (3rd place, 24 pts)
  TOTAL: 50 pts

PROPOSED:
  50 Free: Michael Zahorchak (4th place, 22 pts)  ← moved up
  100 Free: Daniel Sokban (1st place, 32 pts)    ← moved here
  TOTAL: 54 pts

RECOMMENDATION: ✅ MAKE THE CHANGE (+4 pts net)
```

**Pros:**

- ✅ Critical for decision-making
- ✅ Low implementation complexity
- ✅ Highly valuable to coaches

**Cons:**

- ❌ Doesn't account for psychological factors
- ❌ Assumes deterministic outcomes (see Monte Carlo below)

**Recommendation:** ⭐⭐⭐⭐⭐ **MUST HAVE**

---

### TIER 2: VALUABLE (High ROI, Should Implement)

---

#### 2.1 OpponentAnalyzer

**What It Does:**  
Analyzes all competing teams to identify threats, weaknesses, and opportunities.

**Why It's Valuable:**  
Championship strategy isn't just about maximizing YOUR points—it's about maximizing your RELATIVE position. You need to know:

- Who are you really competing against for your target position?
- Where can you steal points from the teams ahead?
- Where must you defend against teams behind?

**Key Methods:**

```python
class OpponentAnalyzer:

    def rank_threats(self, target_team) -> List[ThreatAssessment]:
        """Rank all teams by their threat level to target."""
        # Consider:
        # - Point differential
        # - Head-to-head event matchups
        # - Depth in key events

    def find_vulnerable_events(self, opponent_team) -> List[Event]:
        """Find events where opponent is weak."""
        # Low depth, no top-3 finishers, etc.

    def defensive_analysis(self, target_team, chasing_teams) -> Strategy:
        """Protect your position from teams behind."""

    def offensive_analysis(self, target_team, leading_teams) -> Strategy:
        """Close the gap on teams ahead."""

    def head_to_head(self, team1, team2) -> Comparison:
        """✅ EXISTS - Detailed 1v1 comparison."""
```

**Example: VCAC 2026 Threat Analysis for Seton**

```
TARGET: Seton (SST) - Projected 2nd (482 pts)

DEFENSIVE PRIORITIES (teams behind):
  #3 Trinity (TCS) - 436 pts, gap: 46 pts
      → Battle events: Boys 50 Free, Girls 100 Free
      → Risk level: MEDIUM (would need 5+ upsets)

  #4 Paul VI (PVI) - 362 pts, gap: 120 pts
      → Risk level: LOW (safe margin)

OFFENSIVE TARGETS (teams ahead):
  #1 Bishop O'Connell (DJO) - 1021 pts, gap: 539 pts
      → Gap too large to close
      → Focus: Secure 2nd, don't overextend
```

**Pros:**

- ✅ Enables strategic focus
- ✅ Prevents wasted effort on unreachable goals
- ✅ Identifies where to concentrate resources

**Cons:**

- ❌ Requires accurate opponent data
- ❌ Opponents may also be strategizing

**Recommendation:** ⭐⭐⭐⭐ **SHOULD HAVE**

---

#### 2.2 MonteCarloProjector (Probabilistic Simulation)

**What It Does:**  
Runs thousands of simulated meets with random variance to produce probability distributions of outcomes instead of single-point estimates.

**Why It's Valuable:**  
Current projection assumes seed times = final times. Reality:

- Swimmers have good days and bad days
- Time variance is typically 1-3% of swim time
- Upsets happen

Monte Carlo answers: "What's the probability Seton finishes 2nd or better?"

**Algorithm:**

```python
class MonteCarloProjector:

    def __init__(self, variance_model="historical"):
        self.variance_model = variance_model

    def simulate_meet(self, psych_sheet, n_simulations=10000):
        results = []

        for _ in range(n_simulations):
            # Add random variance to each seed time
            simulated_times = self._apply_variance(psych_sheet)

            # Re-rank based on simulated times
            simulated_psych = self._create_simulated_psych(simulated_times)

            # Project points
            projection = self.engine.project_full_meet(simulated_psych)
            results.append(projection.standings)

        return self._aggregate_results(results)

    def _apply_variance(self, psych_sheet):
        """Apply realistic time variance."""
        # Variance model: Normal distribution
        # Mean: seed_time
        # StdDev: seed_time * 0.015 (1.5% typical variance)

        for entry in psych_sheet.entries:
            variance = entry.seed_time * 0.015
            entry.simulated_time = np.random.normal(entry.seed_time, variance)
```

**Example Output:**

```
MONTE CARLO PROJECTION: VCAC 2026 (10,000 simulations)

Seton Finish Position Probabilities:
  1st place:  0.2%   (unlikely - DJO dominant)
  2nd place: 67.3%   (most likely)
  3rd place: 28.1%   (Trinity threat)
  4th place:  4.2%   (upset scenario)
  5th+:       0.2%   (very unlikely)

Expected Points: 482 ± 34 (95% CI: 416-548)
```

**Pros:**

- ✅ Realistic uncertainty quantification
- ✅ Identifies true risk levels
- ✅ Academically rigorous approach

**Cons:**

- ❌ Computationally intensive (10K+ simulations)
- ❌ Variance model needs calibration with real data
- ❌ May be overkill for high school meets

**Recommendation:** ⭐⭐⭐ **NICE TO HAVE** (implement after core features)

---

#### 2.3 GlobalOptimizer (Joint Individual + Relay)

**What It Does:**  
Solves the COMBINED optimization of individual entries AND relay selections simultaneously, not sequentially.

**Why It's Valuable:**  
Currently, we optimize individuals first, then relays. But they're coupled:

- A swimmer on 400 relay loses an individual slot
- The best relay might require sacrificing individual points
- Optimal solution requires considering both together

**Mathematical Formulation (Gurobi):**

```
DECISION VARIABLES:
  x[i,j]       = 1 if swimmer i swims individual event j
  r[i,l,k]     = 1 if swimmer i swims leg l of relay k
  y[i]         = 1 if swimmer i swims 400 Free Relay (relay 3)

OBJECTIVE:
  MAXIMIZE Σ individual_points + Σ relay_points

CONSTRAINTS:
  1. Individual limit:  Σⱼ x[i,j] + diving[i] + y[i] ≤ 2   ∀i
  2. Relay leg:         Σᵢ r[i,l,k] = 1                    ∀l,k
  3. Swimmer once/relay: Σₗ r[i,l,k] ≤ 1                   ∀i,k
  4. 400 linkage:       y[i] = Σₗ r[i,l,"400FR"]          ∀i
  5. Medley stroke:     r[i,l,k] = 0 if can't swim stroke ∀i,l,k
```

**Pros:**

- ✅ True global optimum
- ✅ Handles relay-3 rule elegantly
- ✅ Single solve, consistent solution

**Cons:**

- ❌ Complex model formulation
- ❌ Harder to explain to coaches ("why this relay?")
- ❌ May be over-engineering for smaller meets

**Recommendation:** ⭐⭐⭐ **NICE TO HAVE** (advanced feature)

---

### TIER 3: USEFUL BUT NOT ESSENTIAL

---

#### 3.1 RaceDayAdjuster (Live Adjustments)

**What It Does:**  
Tracks actual results in real-time and recalculates strategy mid-meet.

**Use Cases:**

- "We're down 50 points with 4 events left—what needs to happen?"
- "Their star swimmer DQ'd—how does this change our relay strategy?"
- "Should we scratch our B swimmer from 100 Free to rest for relay?"

**Key Methods:**

```python
class RaceDayAdjuster:

    def update_standings(self, completed_events: Dict[str, Results]):
        """Feed in actual results as events complete."""

    def what_must_happen(self, target_position: int) -> Requirements:
        """Calculate minimum requirements to achieve position."""

    def recommend_scratch(self, swimmer, remaining_events) -> Decision:
        """Should swimmer scratch remaining events?"""

    def recalculate_relay(self, remaining_events) -> NewRelayConfig:
        """Should we change relay lineup mid-meet?"""
```

**Pros:**

- ✅ Enables tactical decisions during meet
- ✅ Responds to unexpected developments

**Cons:**

- ❌ Requires real-time data entry (manual or from meet software)
- ❌ Limited time for decision-making at actual meet
- ❌ Most high school meets don't have this level of coaching infrastructure

**Recommendation:** ⭐⭐ **FUTURE PHASE** (post-VCAC 2026)

---

#### 3.2 PsychSheetGenerator

**What It Does:**  
Generates hypothetical psych sheets for meets where official data isn't available yet.

**Use Cases:**

- Season planning before psych sheet is published
- What-if analysis for potential lineup changes
- Training target identification

**Recommendation:** ⭐⭐ **LOW PRIORITY** (can use existing data merge approach)

---

### TIER 4: NOT RECOMMENDED

---

#### 4.1 ❌ Machine Learning Time Predictor

**What It Would Do:**  
Use ML (Random Forest, etc.) to predict swim times based on training data.

**Why NOT Recommended:**

- Requires extensive historical training data we don't have
- High school swimming has high variance, low signal
- Over-engineering for the use case
- Monte Carlo with simple variance model is more robust

**Alternative:** Use historical variance statistics from existing data.

---

#### 4.2 ❌ Genetic Algorithm Optimizer

**What It Would Do:**  
Evolve optimal lineups using genetic algorithm.

**Why NOT Recommended:**

- MILP (Gurobi) provides provably optimal solutions
- Genetic algorithms are stochastic (different results each run)
- Harder to explain/debug
- No advantage over ILP for this problem size

**Alternative:** Gurobi MILP is faster and optimal.

---

#### 4.3 ❌ Real-Time Video Analysis

**What It Would Do:**  
Analyze race video to extract split times and technique metrics.

**Why NOT Recommended:**

- Requires camera infrastructure
- Complex computer vision implementation
- Minimal value at high school level
- Split times are available from official timing systems

**Alternative:** Import official splits from meet results.

---

## 🔧 Implementation Roadmap

### Phase 1: Core Upgrades (VCAC 2026 Ready)

**Timeline:** 3-5 days | **Priority:** Critical

| Task                                          | Effort | Dependencies          |
| --------------------------------------------- | ------ | --------------------- |
| Upgrade EntryOptimizer to Gurobi              | 1 day  | gurobipy install      |
| Implement RelayOptimizer with 400FR trade-off | 2 days | Point projection      |
| Build ScenarioSimulator                       | 1 day  | Optimizer, Projection |
| Create coach-facing report generator          | 1 day  | All above             |

### Phase 2: Strategic Analysis (Post-VCAC)

**Timeline:** 3-5 days | **Priority:** High

| Task                                   | Effort | Dependencies     |
| -------------------------------------- | ------ | ---------------- |
| OpponentAnalyzer with threat ranking   | 1 day  | Projection       |
| Defensive/Offensive strategy generator | 2 days | OpponentAnalyzer |
| Monte Carlo probabilistic simulation   | 2 days | Projection       |

### Phase 3: Advanced Features (Optional)

**Timeline:** Variable | **Priority:** Low

| Task                         | Effort  | Dependencies        |
| ---------------------------- | ------- | ------------------- |
| GlobalOptimizer (joint MILP) | 3 days  | Gurobi expertise    |
| RaceDayAdjuster              | 2 days  | Real-time data feed |
| Web dashboard                | 5+ days | Frontend framework  |

---

## 📦 Dependencies & Existing Infrastructure

### ✅ Already Installed & Integrated

AquaForge already has a robust Gurobi-based optimization system for dual meets:

```
swim_ai_reflex/backend/core/strategies/gurobi_strategy.py  # Main Gurobi optimizer
swim_ai_reflex/backend/core/optimizer_factory.py          # Strategy factory
swim_ai_reflex/backend/services/optimization_service.py   # Service layer
```

**Key Features Already Implemented:**

- Binary decision variables: `x[swimmer, event]`
- Constraint: Max 2 individual events per swimmer
- Constraint: Max 4 swimmers per event
- Constraint: No back-to-back events
- Event importance weighting (swing events)
- Exhibition/scoring grade handling
- Probabilistic scoring mode (optional)
- WLS (Web License Service) for cloud deployment

**License Configuration:**

```bash
# Environment variables (for Railway/cloud)
WLSACCESSID=your_access_id
WLSSECRET=your_secret
LICENSEID=your_license_id

# Local license file paths checked:
# - ./gurobi.lic
# - ./swim_ai_reflex/gurobi.lic
# - /app/gurobi.lic (Docker)
```

### What to ADD for Championship

The existing `GurobiStrategy` is designed for dual meets. For championships, we need:

---

## 📝 Summary: What to Build vs. Skip

### ✅ BUILD (High Value)

| Feature                                  | Why                                 | Effort |
| ---------------------------------------- | ----------------------------------- | ------ |
| **Gurobi Entry Optimizer**               | Faster, handles complex constraints | Low    |
| **Relay Optimizer with 400FR trade-off** | VCAC-specific rule is critical      | Medium |
| **Scenario Simulator**                   | Coaches need what-if analysis       | Low    |
| **Opponent Analyzer**                    | Multi-team strategy essential       | Medium |

### ⏳ DEFER (Build Later)

| Feature                | Why                             | When          |
| ---------------------- | ------------------------------- | ------------- |
| Monte Carlo Simulation | Nice but not essential for VCAC | Post-Feb 2026 |
| Global Optimizer       | Advanced, complex               | When needed   |
| Race Day Adjuster      | Requires live infrastructure    | Future season |

### ❌ SKIP (Not Worth It)

| Feature           | Why                                |
| ----------------- | ---------------------------------- |
| ML Time Predictor | Insufficient data, overcomplicated |
| Genetic Algorithm | MILP is superior for this problem  |
| Video Analysis    | Out of scope for AquaForge         |

---

## 🎯 Immediate Next Steps

1. **Install Gurobi** - Get academic license, install `gurobipy`
2. **Upgrade EntryOptimizer** - Replace scipy MILP with Gurobi
3. **Build RelayOptimizer** - Focus on 400FR trade-off logic
4. **Create ScenarioSimulator** - Enable what-if analysis
5. **Run VCAC Projection** - Generate coach-ready report

Would you like me to start implementing any of these components?
