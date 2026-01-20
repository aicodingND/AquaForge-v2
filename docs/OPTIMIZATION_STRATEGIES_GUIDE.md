# AquaForge Optimization Strategies - Complete Reference Guide

**Document:** Central Strategy Reference  
**Created:** January 16, 2026  
**Version:** 1.0  
**Purpose:** Comprehensive explanation of all optimization algorithms, when to use them, and how they work

---

## 📚 Table of Contents

1. [Strategy Overview](#-strategy-overview)
2. [Nash Equilibrium Solver](#1-nash-equilibrium-solver)
3. [Gurobi MILP Optimizer](#2-gurobi-milp-optimizer)
4. [Hungarian Algorithm](#3-hungarian-algorithm)
5. [Monte Carlo Simulation](#4-monte-carlo-simulation)
6. [Stackelberg Bilevel Optimization](#5-stackelberg-bilevel-optimization)
7. [Heuristic/Greedy Algorithms](#6-heuristicgreedy-algorithms)
8. [Strategy Selection Matrix](#-strategy-selection-matrix)
9. [Combined Strategy Patterns](#-combined-strategy-patterns)

---

## 🌐 Strategy Overview

AquaForge uses a portfolio of optimization algorithms, each designed for specific scenarios. No single algorithm is best for all situations—the art is knowing when to apply each.

```
                    ┌─────────────────────────────────────────────────────────────┐
                    │                   AQUAFORGE ALGORITHM PORTFOLIO              │
                    ├─────────────────────────────────────────────────────────────┤
                    │                                                              │
                    │    ┌──────────┐   ┌──────────┐   ┌──────────┐              │
                    │    │   Nash   │   │  Gurobi  │   │  Monte   │              │
                    │    │ Equilib. │   │   MILP   │   │  Carlo   │              │
                    │    └────┬─────┘   └────┬─────┘   └────┬─────┘              │
                    │         │              │              │                     │
                    │         ▼              ▼              ▼                     │
                    │    ┌──────────────────────────────────────────┐            │
                    │    │         Unified Optimization Service      │            │
                    │    └──────────────────────────────────────────┘            │
                    │         ▲              ▲              ▲                     │
                    │         │              │              │                     │
                    │    ┌────┴─────┐   ┌────┴─────┐   ┌────┴─────┐              │
                    │    │Hungarian │   │Stackelberg│  │ Heuristic│              │
                    │    │Algorithm │   │ Bilevel  │   │ Fallback │              │
                    │    └──────────┘   └──────────┘   └──────────┘              │
                    │                                                              │
                    └─────────────────────────────────────────────────────────────┘
```

---

## 1. Nash Equilibrium Solver

### What It Is

**Nash Equilibrium** is a game-theoretic concept where no player can improve their outcome by unilaterally changing their strategy. In swim meets, this means finding lineups where:

- **Seton's lineup** is optimal given what the opponent does
- **Opponent's lineup** is optimal given what Seton does

### The Math

In a two-player zero-sum game:

```
Nash Equilibrium: (s₁*, s₂*) where
  - u₁(s₁*, s₂*) ≥ u₁(s₁, s₂*) for all s₁
  - u₂(s₁*, s₂*) ≥ u₂(s₁*, s₂) for all s₂
```

For swim meets, we approximate this through **iterative best-response**:

1. Start with Seton's best lineup against a "greedy" opponent
2. Compute opponent's best response
3. Compute Seton's best response to that
4. Repeat until neither side changes (convergence)

### How It Works in AquaForge

```python
# Location: swim_ai_reflex/backend/services/optimization_service.py

MAX_NASH_ITERATIONS = 8
current_opp_lineup = greedy_opponent_lineup

for iteration in range(MAX_NASH_ITERATIONS):
    # Step 1: Seton optimizes against current opponent
    seton_lineup = optimize_seton(against=current_opp_lineup)

    # Step 2: Opponent optimizes against Seton's new lineup
    new_opp_lineup = optimize_opponent(against=seton_lineup)

    # Step 3: Check for convergence
    if lineups_equivalent(new_opp_lineup, current_opp_lineup):
        print("Nash Equilibrium reached!")
        break

    current_opp_lineup = new_opp_lineup
```

### Example

**Scenario:** Seton vs Trinity dual meet, Boys 50 Free

| Iteration | Seton Decision                | Trinity Response                 | Outcome              |
| --------- | ----------------------------- | -------------------------------- | -------------------- |
| 0         | Sokban (23.59), Smith (24.10) | Default lineup                   | Seton wins 1st, 3rd  |
| 1         | Same                          | Move Phillips (22.23) to 50 Free | Trinity wins 1st     |
| 2         | Add Zahorchak (23.80)         | Same                             | Seton: 2nd, 3rd, 4th |
| 3         | Same                          | Same                             | **EQUILIBRIUM**      |

### When to Use

| Scenario                      | Use Nash? | Why                                              |
| ----------------------------- | --------- | ------------------------------------------------ |
| **Dual meets (1v1)**          | ✅ Yes     | Opponent actively counters your strategy         |
| **Championship (multi-team)** | ❌ No      | Opponents aren't reacting specifically to you    |
| **Opponent data available**   | ✅ Yes     | Need opponent roster to model responses          |
| **Opponent unknown**          | ❌ No      | Can't model responses without data               |
| **Time-sensitive**            | ⚠️ Maybe   | 8 iterations can be slow; use heuristic fallback |

### Pros & Cons

| Pros                                 | Cons                                   |
| ------------------------------------ | -------------------------------------- |
| ✅ Game-theoretically sound           | ❌ Only works for 1v1                   |
| ✅ Accounts for opponent intelligence | ❌ Requires opponent roster data        |
| ✅ Produces "unexploitable" lineups   | ❌ May not converge (rare)              |
| ✅ Iterative improvement visible      | ❌ Slower than single-shot optimization |

### File Location

```
swim_ai_reflex/backend/services/optimization_service.py
  └─ Lines 277-430 (Nash iteration loop)
```

---

## 2. Gurobi MILP Optimizer

### What It Is

**Gurobi** is an industry-leading solver for **Mixed Integer Linear Programming (MILP)**. It finds mathematically provable optimal solutions to constrained optimization problems.

**MILP** means:

- **Variables** can be integers or continuous
- **Objective** is linear (maximize/minimize a sum)
- **Constraints** are linear inequalities

### The Math

```
MAXIMIZE:   Σᵢⱼ (expected_points[i,j] × x[i,j])

SUBJECT TO:
  1. Σⱼ x[i,j] ≤ 2                    ∀i   (max 2 events/swimmer)
  2. x[i,j] ∈ {0, 1}                  ∀i,j (binary decision)
  3. Σᵢ x[i,j] ≤ 4                    ∀j   (max 4 entries/event)
  4. back_to_back[i,j,k] ⟹ x[i,j] + x[i,k] ≤ 1   (fatigue prevention)

WHERE:
  x[i,j] = 1 if swimmer i is assigned to event j
```

### How It Works in AquaForge

```python
# Location: swim_ai_reflex/backend/core/strategies/gurobi_strategy.py

import gurobipy as gp
from gurobipy import GRB

def optimize(self, seton_roster, opponent_roster, ...):
    model = gp.Model("swim_lineup")

    # Decision variables
    x = model.addVars(swimmers, events, vtype=GRB.BINARY, name="assign")

    # Objective: maximize expected points
    model.setObjective(
        gp.quicksum(point_matrix[i,j] * x[i,j]
                    for i in swimmers for j in events),
        GRB.MAXIMIZE
    )

    # Constraint: max 2 events per swimmer
    for i in swimmers:
        model.addConstr(
            gp.quicksum(x[i,j] for j in events) <= 2,
            name=f"max_events_{i}"
        )

    # Solve
    model.optimize()

    # Extract solution
    assignments = {i: [j for j in events if x[i,j].X > 0.5]
                   for i in swimmers}
```

### Example

**Problem:** Optimize Seton's lineup for VCAC Championship

**Input:**

- 25 swimmers, 8 individual events
- Each swimmer has times for events they've swum
- Constraint: max 2 events per swimmer, max 4 scorers per event

**Gurobi Output:**

```
Optimal solution found in 0.3 seconds
Objective value: 287 points

Assignments:
  Daniel Sokban → [50 Free, 100 Free]     (32 + 26 = 58 pts)
  Michael Zahorchak → [100 Fly, 200 IM]   (24 + 22 = 46 pts)
  Maggie Schroer → [50 Free, 100 Back]    (32 + 26 = 58 pts)
  ...
```

### When to Use

| Scenario                    | Use Gurobi? | Why                                                |
| --------------------------- | ----------- | -------------------------------------------------- |
| **Need provably optimal**   | ✅ Yes       | Gurobi guarantees global optimum                   |
| **Championship multi-team** | ✅ Yes       | No opponent modeling needed                        |
| **Complex constraints**     | ✅ Yes       | Handles 100+ constraints easily                    |
| **Real-time/interactive**   | ⚠️ Depends   | Fast for small problems, may need limits for large |
| **No Gurobi license**       | ❌ No        | Requires academic or commercial license            |
| **Quick estimate needed**   | ❌ Maybe not | Heuristic is faster if optimality not critical     |

### Pros & Cons

| Pros                                   | Cons                                    |
| -------------------------------------- | --------------------------------------- |
| ✅ Provably optimal solution            | ❌ Requires Gurobi license               |
| ✅ Fast (subsecond for swim problems)   | ❌ Setup complexity (env vars, licenses) |
| ✅ Handles complex constraints natively | ❌ Learning curve for model formulation  |
| ✅ Industry-standard reliability        | ❌ Overkill for very simple problems     |
| ✅ Solution quality guarantee           |                                         |

### File Locations

```
swim_ai_reflex/backend/core/strategies/gurobi_strategy.py      # Dual meet optimizer
swim_ai_reflex/backend/core/strategies/championship_strategy.py # Multi-team optimizer
swim_ai_reflex/backend/core/optimizer_factory.py               # Strategy selection
```

---

## 3. Hungarian Algorithm

### What It Is

The **Hungarian Algorithm** (also called Kuhn-Munkres algorithm) solves the **assignment problem** in polynomial time O(n³). It finds the optimal one-to-one matching between two sets.

> **Note:** Despite the name, this was developed by Hungarian mathematicians Harold Kuhn (1955) and James Munkres (1957). It is NOT an "Armenian algorithm."

### The Math

**Problem:** Given n workers and n tasks with cost matrix C[i,j], find assignment that minimizes total cost.

```
MINIMIZE:   Σ C[i, σ(i)]    where σ is a permutation (assignment)

CONSTRAINTS:
  - Each worker assigned to exactly 1 task
  - Each task assigned to exactly 1 worker
```

### How It Works in AquaForge

For **medley relays**, we need to assign 4 swimmers to 4 strokes (Back, Breast, Fly, Free) to minimize total relay time:

```python
# Location: swim_ai_reflex/backend/services/relay_optimizer_service.py

from scipy.optimize import linear_sum_assignment
import numpy as np

def _optimize_medley_relay(self, swimmer_times, available, ...):
    strokes = ['100 Back', '100 Breast', '100 Fly', '100 Free']

    # Build cost matrix: cost[swimmer][stroke] = split time
    n = len(available)
    cost_matrix = np.full((n, 4), np.inf)  # n swimmers, 4 strokes

    for i, swimmer in enumerate(available):
        for j, stroke in enumerate(strokes):
            if stroke in swimmer_times[swimmer]:
                cost_matrix[i, j] = swimmer_times[swimmer][stroke]

    # Run Hungarian algorithm
    row_ind, col_ind = linear_sum_assignment(cost_matrix)

    # Build relay from optimal assignment
    relay_legs = []
    for i, j in zip(row_ind, col_ind):
        relay_legs.append(RelayLeg(
            swimmer=available[i],
            stroke=strokes[j],
            split_time=cost_matrix[i, j]
        ))

    return relay_legs
```

### Example

**Problem:** Assign swimmers to medley relay legs

**Available swimmers & times:**

| Swimmer | 100 Back | 100 Breast | 100 Fly | 100 Free |
| ------- | -------- | ---------- | ------- | -------- |
| Alice   | 58.2     | 1:05.3     | 1:02.1  | 54.8     |
| Bob     | 55.1     | 1:08.9     | 59.3    | 52.1     |
| Carol   | 61.3     | 1:02.8     | 57.6    | 55.2     |
| Dave    | 63.5     | 1:01.1     | 1:05.8  | 51.9     |

**Hungarian Output:**

```
Optimal assignment (minimizes total time):
  - Backstroke: Bob (55.1)
  - Breaststroke: Dave (1:01.1)
  - Butterfly: Carol (57.6)
  - Freestyle: Alice (54.8)

Total relay time: 3:48.6
```

**Why this beats greedy:**
A greedy approach might put the fastest freestyle swimmer (Dave, 51.9) on free. But Dave is our best breaststroker! Hungarian sees the global picture.

### When to Use

| Scenario                       | Use Hungarian? | Why                                   |
| ------------------------------ | -------------- | ------------------------------------- |
| **Medley relay assignment**    | ✅ Yes          | Classic 4-to-4 assignment problem     |
| **Any 1-to-1 matching**        | ✅ Yes          | Optimal for assignment problems       |
| **Free relay assignment**      | ❌ No           | Simpler: just pick 4 fastest          |
| **Individual event selection** | ❌ No           | Not 1-to-1 (swimmer can do 2+ events) |
| **When order matters**         | ❌ No           | Hungarian doesn't consider sequence   |

### Pros & Cons

| Pros                        | Cons                                          |
| --------------------------- | --------------------------------------------- |
| ✅ Polynomial time O(n³)     | ❌ Only for 1-to-1 assignment                  |
| ✅ Guaranteed optimal        | ❌ Doesn't handle "swimmer does multiple legs" |
| ✅ No setup required (scipy) | ❌ Assumes all costs known                     |
| ✅ Fast for small n (< 100)  | ❌ Limited to square-ish matrices              |
| ✅ Well-understood algorithm |                                               |

### File Location

```
swim_ai_reflex/backend/services/relay_optimizer_service.py
  └─ Lines 251-347 (_optimize_medley_relay)
  └─ Uses: scipy.optimize.linear_sum_assignment
```

---

## 4. Monte Carlo Simulation

### What It Is

**Monte Carlo** simulation runs thousands of trials with random variation to produce probability distributions instead of single-point estimates.

For swim meets: Seed times ≠ actual times. Swimmers have variance. Monte Carlo answers "What's the probability Seton wins?"

### The Math

```
For each trial t = 1 to N:
  For each swimmer i:
    simulated_time[i,t] = seed_time[i] + ε    where ε ~ N(0, σ²)
    σ ≈ 0.5-1.5% of seed time

  Re-rank swimmers based on simulated times
  Calculate points for this simulation

Result:
  P(Seton wins) = count(seton_score > opponent_score) / N
  Expected points = mean(seton_scores)
  95% CI = [quantile(2.5%), quantile(97.5%)]
```

### How It Works in AquaForge

```python
# Location: swim_ai_reflex/backend/core/monte_carlo.py

def fast_monte_carlo_simulation(seton_df, opponent_df, trials=500, rules=None):
    seton_points_total = np.zeros(trials)
    opponent_points_total = np.zeros(trials)

    for event in events:
        base_times = event_df['time'].values

        # Generate variance (1.5% typical)
        sigmas = np.maximum(0.2, 0.005 * base_times)

        # Generate random times (vectorized for speed)
        noise = np.random.normal(0, 1, size=(trials, num_swimmers))
        sim_times = base_times + (noise * sigmas)

        # Re-rank for each trial
        sorted_indices = np.argsort(sim_times, axis=1)

        # Calculate points
        # ... (apply scoring rules)

    return {
        "seton_mean": np.mean(seton_points_total),
        "seton_std": np.std(seton_points_total),
        "seton_win_prob": np.mean(seton_points_total > opponent_points_total)
    }
```

### Example

**Input:** Seton vs Trinity, 500 Monte Carlo trials

**Output:**

```
Monte Carlo Simulation Results (500 trials):

Seton:
  Expected Points: 89.3 (std: 8.2)
  Range: [71, 112]
  95% Confidence: [75.1, 104.8]

Trinity:
  Expected Points: 67.8 (std: 7.5)
  Range: [52, 89]

Win Probability:
  Seton wins: 87.4%
  Trinity wins: 11.2%
  Tie: 1.4%

High-Variance Events (most uncertain):
  - Boys 50 Free: 3-way race for 1st (0.3s separating top 3)
  - Girls 100 Fly: Schroer vs Trinity's top (same seed time)
```

### When to Use

| Scenario                         | Use Monte Carlo? | Why                                   |
| -------------------------------- | ---------------- | ------------------------------------- |
| **Want confidence intervals**    | ✅ Yes            | Provides uncertainty quantification   |
| **Close projected meet**         | ✅ Yes            | Variance matters most when tight      |
| **Championship with many teams** | ✅ Yes            | Multi-team standings can flip         |
| **Single point estimate needed** | ❌ No             | Use deterministic projection          |
| **Real-time optimization**       | ⚠️ Depends        | Can be slow; use fewer trials         |
| **Risk assessment**              | ✅ Yes            | "What's our worst realistic outcome?" |

### Pros & Cons

| Pros                            | Cons                                                   |
| ------------------------------- | ------------------------------------------------------ |
| ✅ Quantifies uncertainty        | ❌ Computationally intensive (10K trials)               |
| ✅ Identifies high-risk events   | ❌ Requires variance model calibration                  |
| ✅ Probability-based decisions   | ❌ Randomness means slightly different results each run |
| ✅ Works with any scoring system | ❌ May be overkill for lopsided meets                   |
| ✅ Vectorized = fast in NumPy    |                                                        |

### File Location

```
swim_ai_reflex/backend/core/monte_carlo.py
  └─ fast_monte_carlo_simulation() - main function
  └─ Uses: numpy vectorized operations
```

---

## 5. Stackelberg Bilevel Optimization

### What It Is

**Stackelberg optimization** models a leader-follower game:

1. **Leader (Seton)** commits to a strategy first
2. **Follower (Opponent)** observes and responds optimally
3. Leader finds strategy that maximizes outcome even after follower's best response

This is MORE CONSERVATIVE than Nash equilibrium—it assumes the opponent will definitely counter you.

### The Math

```
BILEVEL OPTIMIZATION:

Level 1 (Leader's Problem):
  MAXIMIZE (over Seton's lineup x):   score(x, y*(x))

Level 2 (Follower's Problem):
  y*(x) = ARGMAX (over opponent lineup y):   opponent_score(x, y)

In other words: Find x such that even when opponent plays y*(x), Seton's score is maximized.
```

### How It Works in AquaForge

```python
# Location: swim_ai_reflex/backend/core/strategies/stackelberg_strategy.py

class StackelbergStrategy:
    def optimize(self, seton_roster, opponent_roster, ...):
        # PHASE 1: Generate candidate Seton lineups
        candidates = []
        candidates.append(self._generate_greedy_lineup(...))
        candidates.append(self._generate_lineup_resting(star_swimmer=...))
        candidates.extend(self._generate_random_lineups(count=20))

        # PHASE 2: For each candidate, compute opponent's best response
        scored_candidates = []
        for name, seton_lineup in candidates:
            opp_response = self._compute_opponent_response(
                seton_lineup, opponent_roster
            )

            score = self.score_matchup(seton_lineup, opp_response)
            scored_candidates.append((name, seton_lineup, score))

        # PHASE 3: Select lineup with best margin AFTER opponent counters
        best = max(scored_candidates, key=lambda x: x[2]['margin'])

        return best
```

### Example

**Scenario:** Seton has a dominant 50 Free swimmer (Daniel Sokban). Should we enter him?

**Stackelberg Analysis:**

| Candidate Lineup           | Opponent Response                         | Seton Points | Margin |
| -------------------------- | ----------------------------------------- | ------------ | ------ |
| Sokban in 50 Free          | Trinity moves Phillips (22.23) to counter | 85           | +14    |
| Sokban in 100 Free instead | Trinity spreads swimmers                  | 91           | +23    |
| Sokban in both             | Trinity stacks 50 Free                    | 88           | +17    |

**Decision:** Moving Sokban to 100 Free is Stackelberg-optimal because even when Trinity responds, our margin is best.

### When to Use

| Scenario                             | Use Stackelberg? | Why                                      |
| ------------------------------------ | ---------------- | ---------------------------------------- |
| **Opponent will definitely counter** | ✅ Yes            | Models optimal opponent response         |
| **High-stakes dual meet**            | ✅ Yes            | When you can't afford to be exploited    |
| **Opponent is strategic**            | ✅ Yes            | Assumes intelligent opponent             |
| **Opponent data limited**            | ❌ No             | Need roster to model responses           |
| **Championship**                     | ❌ No             | Opponents not targeting you specifically |
| **Need fast results**                | ❌ No             | Evaluates many candidates; slower        |

### Pros & Cons

| Pros                                    | Cons                                      |
| --------------------------------------- | ----------------------------------------- |
| ✅ Produces "unexploitable" strategies   | ❌ Very computationally expensive          |
| ✅ Conservative (assumes smart opponent) | ❌ May sacrifice optimality for robustness |
| ✅ Shows margin after opponent responds  | ❌ Requires good opponent modeling         |
| ✅ Reveals strategic insights            | ❌ Only for 1v1 scenarios                  |

### File Location

```
swim_ai_reflex/backend/core/strategies/stackelberg_strategy.py
  └─ StackelbergStrategy class
  └─ Uses: candidate generation + exhaustive evaluation
```

---

## 6. Heuristic/Greedy Algorithms

### What They Are

**Heuristics** are fast, approximate algorithms that produce "good enough" solutions without guaranteeing optimality. The main heuristic in AquaForge is **greedy assignment**.

### Greedy Algorithm

```
For each event in order of importance:
    Sort swimmers by time (fastest first)
    For each swimmer:
        If swimmer can legally be assigned (< 2 events, not fatigued):
            Assign swimmer to event
            Break (move to next event)
```

### How It Works in AquaForge

```python
# Location: swim_ai_reflex/backend/core/strategies/heuristic_strategy.py

class HeuristicStrategy:
    def optimize(self, roster, ...):
        assignments = {}
        event_counts = defaultdict(int)  # Track events per swimmer

        for event in sorted_events_by_importance:
            swimmers = roster[roster['event'] == event]
            swimmers = swimmers.sort_values('time')

            assigned = 0
            for _, swimmer in swimmers.iterrows():
                name = swimmer['swimmer']
                if event_counts[name] < 2 and assigned < 4:
                    assignments[(name, event)] = swimmer
                    event_counts[name] += 1
                    assigned += 1

        return assignments
```

### When to Use

| Scenario                           | Use Heuristic? | Why                              |
| ---------------------------------- | -------------- | -------------------------------- |
| **Gurobi unavailable**             | ✅ Yes          | Fallback when no license         |
| **Quick estimate needed**          | ✅ Yes          | Instant results                  |
| **Initial solution for iteration** | ✅ Yes          | Start point for Nash/Stackelberg |
| **Optimal solution required**      | ❌ No           | May miss better assignments      |
| **Complex constraints**            | ❌ No           | Hard to handle elegantly         |

### Pros & Cons

| Pros                           | Cons                                                   |
| ------------------------------ | ------------------------------------------------------ |
| ✅ Extremely fast (O(n log n))  | ❌ Not guaranteed optimal                               |
| ✅ No external dependencies     | ❌ May miss non-obvious strategies                      |
| ✅ Easy to understand/debug     | ❌ Order-dependent (different order → different result) |
| ✅ Always produces valid lineup | ❌ Doesn't consider trade-offs well                     |

---

## 🎯 Strategy Selection Matrix

### By Meet Type

| Meet Type             | Primary Strategy | Secondary | Monte Carlo? | Notes                            |
| --------------------- | ---------------- | --------- | ------------ | -------------------------------- |
| **Dual Meet**         | Nash + Gurobi    | Heuristic | Optional     | Nash for opponent modeling       |
| **VCAC Championship** | Gurobi           | Heuristic | Recommended  | Multi-team, no opponent modeling |
| **VISAA State**       | Gurobi           | Heuristic | Recommended  | High stakes, many teams          |
| **Practice Meet**     | Heuristic        | -         | No           | Quick estimate sufficient        |

### By Scenario

| Scenario                     | Best Strategy        | Why                           |
| ---------------------------- | -------------------- | ----------------------------- |
| Need provably optimal lineup | **Gurobi MILP**      | Guarantees global optimum     |
| Opponent will counter us     | **Nash Equilibrium** | Finds stable point            |
| High-stakes, need robustness | **Stackelberg**      | Assumes opponent intelligence |
| Optimal medley relay         | **Hungarian**        | Assignment problem            |
| Want probability of winning  | **Monte Carlo**      | Uncertainty quantification    |
| No Gurobi license            | **Heuristic**        | Fast fallback                 |
| Time-pressured decision      | **Heuristic**        | Instant results               |

### By Component

| Component                   | Algorithm             | Notes                                     |
| --------------------------- | --------------------- | ----------------------------------------- |
| Individual event assignment | Gurobi MILP           | Handles all constraints                   |
| Medley relay legs           | Hungarian             | Optimal stroke matching                   |
| Free relay                  | Greedy                | Simply pick 4 fastest                     |
| 400 Free trade-off          | Cost-benefit analysis | Compare relay pts vs individual sacrifice |
| Uncertainty analysis        | Monte Carlo           | Run after optimization                    |
| Opponent response modeling  | Nash or Stackelberg   | Stackelberg more conservative             |

---

## 🔄 Combined Strategy Patterns

### Pattern 1: Standard Dual Meet

```
1. Nash Equilibrium (8 iterations max)
   └─ Uses Gurobi at each step to optimize each side's lineup

2. Extract final lineups (Seton + Opponent)

3. Monte Carlo validation (optional, 500 trials)
   └─ Calculate win probability and confidence intervals

4. Relay Optimization
   └─ Hungarian for medley
   └─ Greedy for free relays
```

### Pattern 2: Championship Meet

```
1. Gurobi MILP for individual entries
   └─ Constraint: diving counts as individual, relay 3 penalty

2. Hungarian for medley relay

3. Greedy for 200 Free relay

4. 400 Free trade-off analysis
   └─ Compare relay points gained vs individual points lost

5. Monte Carlo simulation (recommended, 1000+ trials)
   └─ Multi-team standings probability
```

### Pattern 3: High-Stakes Dual Meet

```
1. Stackelberg optimization
   └─ Evaluate 25 candidate lineups
   └─ Compute opponent's best response to each
   └─ Select most robust

2. Compare to Nash result
   └─ If significantly different, investigate

3. Monte Carlo validation
   └─ Verify win probability > 80%
```

---

## 📁 File Reference

| Algorithm        | Primary File                              | Supporting Files                            |
| ---------------- | ----------------------------------------- | ------------------------------------------- |
| Nash Equilibrium | `services/optimization_service.py`        | `core/optimizer_utils.py`                   |
| Gurobi MILP      | `core/strategies/gurobi_strategy.py`      | `core/strategies/championship_strategy.py`  |
| Hungarian        | `services/relay_optimizer_service.py`     | Uses `scipy.optimize.linear_sum_assignment` |
| Monte Carlo      | `core/monte_carlo.py`                     | Uses `numpy`                                |
| Stackelberg      | `core/strategies/stackelberg_strategy.py` | -                                           |
| Heuristic        | `core/strategies/heuristic_strategy.py`   | -                                           |

---

## 6. Additional Advanced Strategies - Complete Reference

### 6.1 Stackelberg Game (Leader-Follower Model)

**What It Is:**

Stackelberg games model situations where one player (leader) moves first, then others (followers) react. Unlike Nash where everyone moves simultaneously, this captures sequential decision-making.

**Swim Meet Application:**

In many leagues, entries are submitted at different times:
- Seton submits entries Friday at 4pm
- Opponent sees Seton's entries and adjusts before 5pm deadline

**How It Could Work:**

```
1. Seton (leader) commits to a lineup
2. Opponent (follower) optimally reacts
3. Seton anticipates reaction when making initial choice
↓
Result: Seton's optimal "leader strategy"
```

**Example Scenario:**

```
SETON LEADER DECISION:

Option A: Put Smith in 100 Free (Smith's best event)
  → Opponent likely moves Jones to 100 Fly (avoiding Smith)
  → Seton wins 100 Free (+12 pts), loses 100 Fly (-6 pts)
  → Net: +6 points

Option B: Put Smith in 100 Fly (a "bluff")
  → Opponent keeps Jones in 100 Free
  → Smith beats Jones' backup in 100 Fly (+8 pts)
  → Seton's backup competitive in 100 Free (+4 pts)
  → Net: +12 points

STACKELBERG SAYS: Use Option B (strategic misdirection)
```

**When to Use:**

| Scenario                      | Use Stackelberg? | Why                                         |
| ----------------------------- | ---------------- | ------------------------------------------- |
| **You submit entries first**  | ✅ Yes            | You're the leader                           |
| **Close dual meet**           | ✅ Yes            | Strategic deception helps                   |
| **Championship (many teams)** | ❌ No             | Opponent isn't specifically reacting to you |
| **Unknown opponent**          | ❌ No             | Can't model their reaction                  |

**Pros and Cons:**

| ✅ Pros                               | ❌ Cons                           |
| ------------------------------------ | -------------------------------- |
| Models first-mover advantage         | Complex optimization (bilevel)   |
| Captures strategic timing            | Requires opponent response model |
| Can find non-obvious strategies      | Computationally expensive        |
| Better than Nash when you move first | Hard to verify correctness       |

**Recommendation:** � **MEDIUM PRIORITY** - Implement after core features. Valuable for dual meets where entry timing matters.

---

### 6.2 Hungarian Algorithm (Assignment Problem)

**What It Is:**

The Hungarian Algorithm solves the **assignment problem**: optimally matching N workers to N tasks to minimize/maximize total cost.

**Swim Meet Application:**

Perfect for **relay leg assignments** where each swimmer swims exactly one leg:

```
Problem: Assign 4 swimmers to 4 relay legs
         to MINIMIZE total relay time

         | Back | Breast | Fly | Free |
Alice    | 58.2 | 65.3   | 62.1| 54.8 |
Bob      | 55.1 | 68.9   | 59.3| 52.1 |
Carol    | 61.3 | 62.8   | 57.6| 55.2 |
Dave     | 63.5 | 61.1   | 65.8| 51.9 |
```

**How It Works in AquaForge:**

```python
# Already implemented in relay_optimizer_service.py
from scipy.optimize import linear_sum_assignment

def optimize_medley_relay(swimmer_times):
    cost_matrix = build_cost_matrix(swimmer_times)
    row_ind, col_ind = linear_sum_assignment(cost_matrix)
    return optimal_assignment(row_ind, col_ind)
```

**Example Output:**

```
HUNGARIAN OPTIMAL ASSIGNMENT:
  Backstroke: Bob (55.1s)   - Not his best, but globally optimal
  Breaststroke: Dave (61.1s) - His best stroke
  Butterfly: Carol (57.6s)   - Her best stroke
  Freestyle: Alice (54.8s)   - Not her best, but globally optimal

Total Time: 3:48.6

WHY THIS BEATS GREEDY:
Greedy would put Dave on Free (51.9s - his best)
But then Breaststroke has no good option
Hungarian sees the global picture
```

**When to Use:**

| Scenario                        | Use Hungarian? | Why                         |
| ------------------------------- | -------------- | --------------------------- |
| **Medley relay leg assignment** | ✅ Yes          | Classic 4×4 assignment      |
| **Swimmer-to-event pairing**    | ⚠️ Partial      | Only if 1 event per swimmer |
| **Multiple events per swimmer** | ❌ No           | Use ILP instead             |
| **Relay with swimmer overlap**  | ❌ No           | Use ILP for constraints     |

**Pros and Cons:**

| ✅ Pros                | ❌ Cons                   |
| --------------------- | ------------------------ |
| O(n³) polynomial time | Only 1-to-1 matching     |
| Guaranteed optimal    | Can't handle constraints |
| Simple to implement   | Doesn't consider fatigue |

**Recommendation:** ✅ **ALREADY IMPLEMENTED** - Used for medley relay optimization. Extend to consider exchange time variance.

---

### 6.3 Minimax Regret (Conservative Strategy)

**What It Is:**

Minimax Regret minimizes your **maximum possible regret** - the difference between what you chose and what would have been optimal in hindsight.

**Swim Meet Application:**

When facing uncertainty about opponent performance:

```
YOUR DECISION: 50 Free vs 100 Free for your top sprinter

Scenario A: Opponent swims fast
  50 Free outcome: Lose by 2 pts (regret = 8 pts vs if you'd moved him)
  100 Free outcome: Win by 1 pt (regret = 0)

Scenario B: Opponent swims slow
  50 Free outcome: Win by 6 pts (regret = 0)
  100 Free outcome: Win by 3 pts (regret = 3 pts vs 50 Free)

REGRET MATRIX:
          | 50 Free | 100 Free |
Scenario A|    8    |    0     |
Scenario B|    0    |    3     |
Max Regret|    8    |    3     | ← MINIMAX chooses 100 Free
```

**When to Use:**

| Scenario                      | Use Minimax? | Why                         |
| ----------------------------- | ------------ | --------------------------- |
| **Unknown opponent times**    | ✅ Yes        | Uncertainty handling        |
| **Championship (multi-team)** | ✅ Yes        | Many unpredictable outcomes |
| **You're the favorite**       | ✅ Yes        | Avoid catastrophic losses   |
| **You're the underdog**       | ❌ No         | Need aggressive risk-taking |

**Pros and Cons:**

| ✅ Pros                          | ❌ Cons                           |
| ------------------------------- | -------------------------------- |
| Robust to uncertainty           | May be too conservative          |
| Avoids catastrophic outcomes    | Ignores probability of scenarios |
| Simple to understand            | May leave points on table        |
| No probability estimates needed | Not optimal for risk-tolerance   |

**Recommendation:** ✅ **IMPLEMENT** as part of "Conservative Strategy" option.

---

### 6.4 Monte Carlo Simulation

**What It Is:**

Monte Carlo runs thousands of simulated meets with random performance variations to get probability distributions of outcomes.

**Swim Meet Application:**

```python
# Implemented in monte_carlo.py
def simulate_meet(entries, num_simulations=10000):
    results = []
    for i in range(num_simulations):
        # Add random variance to each time
        simulated_times = add_variance(entries)
        # Score the meet
        score = score_meet(simulated_times)
        results.append(score)
    
    return {
        "expected_score": mean(results),
        "confidence_interval": percentile(results, [2.5, 97.5]),
        "win_probability": sum(won(r) for r in results) / len(results)
    }
```

**Example Output:**

```
MONTE CARLO RESULTS (10,000 simulations):

Expected Score: 191.2 ± 15.3 points
95% Confidence Interval: [176, 206]
Win Probability: 73.1%
Podium (Top 3) Probability: 94.2%

HIGH VARIANCE EVENTS:
  - 100 Fly: ±8.5 points swing
  - 50 Free: ±6.2 points swing
  
LOW VARIANCE EVENTS:
  - 500 Free: ±2.1 points (domination)
  - 200 IM: ±1.8 points (clear outcomes)

RECOMMENDATION: Medium risk - focus on high-variance events
```

**When to Use:**

| Scenario                   | Use Monte Carlo? | Why                         |
| -------------------------- | ---------------- | --------------------------- |
| **Risk assessment needed** | ✅ Yes            | Quantifies uncertainty      |
| **Close meets**            | ✅ Yes            | Win probability crucial     |
| **Championship planning**  | ✅ Yes            | Multi-team dynamics         |
| **Quick "what-if"**        | ⚠️ Limited        | May be slow for interactive |

**Recommendation:** ✅ **IMPLEMENTED** - Core feature for championship mode.

---

### 6.5 Fatigue-Adjusted Performance Model

**What It Is:**

Models how swimmer performance degrades based on preceding events, event spacing, and cumulative meet load.

**Swim Meet Application:**

```python
# Implemented in fatigue_model.py
FATIGUE_COSTS = {
    "sprint": 0.5%,    # 50/100 events
    "middle": 1.0%,    # 200 events  
    "distance": 2.0%,  # 500+ events
    "im": 1.5%,        # IM events
}

def calculate_fatigue_penalty(previous_events, current_event):
    penalty = sum(FATIGUE_COSTS[e] for e in previous_events)
    
    if is_back_to_back(previous_events[-1], current_event):
        penalty *= 1.5  # Back-to-back multiplier
    
    # Recovery from rest time
    penalty -= rest_time * 0.001  # 0.1% per minute rest
    
    return min(penalty, 0.05)  # Cap at 5%
```

**Example Output:**

```
FATIGUE REPORT: Michael Zahorchak
Events: 200 IM → 100 Fly → 100 Free

Event 1: 200 IM
  Fatigue: 0% (first event)
  Adjusted Time: 2:05.00 (seed)

Event 2: 100 Fly  
  Previous fatigue: 1.5% (from 200 IM)
  Back-to-back: No
  Rest time: 35 min
  Adjusted Fatigue: 1.2%
  Adjusted Time: 56.67s (vs 56.00 seed)

Event 3: 100 Free
  Previous fatigue: 2.7% (200 IM + 100 Fly)
  Back-to-back: YES (with 100 Fly)
  Penalty multiplier: 1.5x
  Adjusted Time: 50.91s (vs 49.50 seed)

RISK ASSESSMENT: MEDIUM
  - 3 events with 100 Fly → 100 Free back-to-back
  - Consider moving 100 Free if possible
```

**When to Use:**

| Scenario                   | Use Fatigue? | Why                     |
| -------------------------- | ------------ | ----------------------- |
| **Multi-event swimmers**   | ✅ Yes        | Cumulative load matters |
| **Back-to-back decisions** | ✅ Yes        | Critical for accuracy   |
| **Single event swimmers**  | ❌ No         | No fatigue to model     |
| **Fresh lineup**           | ❌ No         | No accumulated fatigue  |

**Recommendation:** ✅ **IMPLEMENTED** - Essential for realistic predictions.

---

### 6.6 Bayesian Time Prediction

**What It Is:**

Bayesian inference updates swimmer time predictions as new information becomes available, combining prior knowledge with new evidence.

**Swim Meet Application:**

```
PRIOR: Swimmer's seed time = 25.50 (from October meet)

NEW EVIDENCE:
  - November practice splits: improving
  - Coach says "she's swimming great"
  - Recent taper started

POSTERIOR (Updated Prediction):
  Prior weight: 40% (season best is reliable)
  Evidence weight: 60% (recent improvement signs)
  
  Updated Time: 25.20 ± 0.3s
  Improvement Probability: 78%
```

**When to Use:**

| Scenario                      | Use Bayesian? | Why                       |
| ----------------------------- | ------------- | ------------------------- |
| **Outdated seed times**       | ✅ Yes         | Incorporate recent info   |
| **Freshmen/first season**     | ✅ Yes         | Limited historical data   |
| **Incorporating coach input** | ✅ Yes         | Subjective evidence works |
| **Championship peaks**        | ✅ Yes         | Taper effects modeled     |

**Recommendation:** 🔮 **FUTURE** - After core features, add for personalized predictions.

---

### 6.7 Multi-Objective Optimization (Pareto)

**What It Is:**

Optimizes multiple conflicting objectives simultaneously, showing trade-offs between them.

**Swim Meet Application:**

```
OBJECTIVES:
  1. Maximize points
  2. Minimize swimmer fatigue  
  3. Maximize consistency (low variance)

PARETO FRONTIER:
Strategy A: 195 pts, High fatigue, Medium variance
Strategy B: 188 pts, Low fatigue, Low variance
Strategy C: 191 pts, Medium fatigue, High variance

No single "best" - coach chooses based on priorities
```

**When to Use:**

| Scenario                     | Use Pareto? | Why                         |
| ---------------------------- | ----------- | --------------------------- |
| **Season management**        | ✅ Yes       | Balance performance vs rest |
| **High-stakes championship** | ⚠️ Maybe     | If fatigue is a concern     |
| **Single-meet focus**        | ❌ No        | Just maximize points        |

**Recommendation:** 🟡 **MEDIUM PRIORITY** - Good for strategic planning interface.

---

## 7. Strategy Decision Guide

### Quick Selection Matrix

| Your Situation             | Recommended Strategy     | Why                |
| -------------------------- | ------------------------ | ------------------ |
| Dual meet, close           | Nash + Monte Carlo       | Game theory + risk |
| Dual meet, you dominate    | Maximize Individual      | Lock in points     |
| Dual meet, you're underdog | Aggressive + Monte Carlo | Need variance      |
| Championship, favorite     | Conservative + Fatigue   | Protect position   |
| Championship, mid-pack     | Nash + Fatigue           | Strategic depth    |
| Championship, underdog     | Aggressive + Monte Carlo | Need high variance |
| Unknown opponent           | Minimax Regret           | Conservative       |
| First meet of season       | Monte Carlo              | Assess uncertainty |
| Peak championship          | All models               | Maximum insight    |

### Strategy Comparison

| Strategy            | Speed  | Accuracy   | Risk Insight | Multi-Team | Implemented    |
| ------------------- | ------ | ---------- | ------------ | ---------- | -------------- |
| Maximize Individual | ⚡ Fast | ⭐⭐⭐ Good   | ❌ None       | ✅ Yes      | ✅ Yes          |
| Nash Equilibrium    | 🐢 Slow | ⭐⭐⭐⭐ Great | ⭐⭐ Some      | ✅ Yes      | ✅ Yes          |
| Monte Carlo         | 🐢 Slow | ⭐⭐⭐ Good   | ⭐⭐⭐⭐⭐ Best   | ✅ Yes      | ✅ Yes          |
| Fatigue Model       | ⚡ Fast | ⭐⭐⭐⭐⭐ Best | ⭐⭐⭐ Good     | ✅ Yes      | ✅ Yes          |
| Stackelberg         | 🐢 Slow | ⭐⭐⭐⭐ Great | ⭐⭐⭐ Good     | ⚠️ Partial  | ❌ Planned      |
| Hungarian           | ⚡ Fast | ⭐⭐⭐⭐⭐ Best | ❌ None       | ✅ Yes      | ✅ Yes (relays) |
| Minimax Regret      | ⚡ Fast | ⭐⭐⭐ Good   | ⭐⭐⭐ Good     | ✅ Yes      | ❌ Planned      |
| Bayesian            | ⚡ Fast | ⭐⭐⭐⭐⭐ Best | ⭐⭐⭐ Good     | N/A        | ❌ Planned      |

---

## �📖 Further Reading

1. **Nash Equilibrium**: Nash, J. (1950). "Equilibrium Points in N-Person Games"
2. **Hungarian Algorithm**: Kuhn, H.W. (1955). "The Hungarian Method for the Assignment Problem"
3. **MILP**: Wolsey, L.A. (1998). "Integer Programming"
4. **Monte Carlo**: Metropolis, N. & Ulam, S. (1949). "The Monte Carlo Method"
5. **Stackelberg Games**: von Stackelberg, H. (1934). "Marktform und Gleichgewicht"
6. **Minimax Regret**: Savage, L.J. (1951). "The Theory of Statistical Decision"
7. **Bayesian Inference**: Gelman, A. et al. (2013). "Bayesian Data Analysis"

---

_Document created for AquaForge v1.0.0-next_  
_Last updated: January 18, 2026_
