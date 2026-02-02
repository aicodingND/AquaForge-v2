# Championship Advanced Strategies Implementation Plan

**Status**: Planning Phase
**Created**: 2026-01-18
**Objective**: Incorporate Nash Equilibrium and advanced game theory into championship optimization

---

## Executive Summary

This plan extends the championship optimization system to include:

1. **Nash Equilibrium Strategy** - Multi-team game theory optimization
2. **Monte Carlo Simulation** - Probabilistic outcome modeling
3. **Scenario Analysis** - What-if testing for different team strategies
4. **Risk Assessment** - Variance and confidence intervals
5. **Interactive Strategy Selection** - Intuitive UI for coaches

---

## Phase 1: Nash Equilibrium for Multi-Team Championships

### Concept

In a championship meet with N teams, each team's optimal strategy depends on what other teams do. Nash Equilibrium finds the stable state where no team can improve by unilaterally changing their strategy.

### Mathematical Model

```
For teams T = {T1, T2, ..., TN}:
- Each team Ti has strategy space Si (possible event assignments)
- Payoff function Pi(s1, s2, ..., sN) = points scored by Ti
- Nash Equilibrium: No team can improve Pi by changing si alone
```

### Implementation Approach

```python
class NashEquilibriumStrategy:
    """
    Multi-team Nash Equilibrium optimization.

    Finds stable lineup configurations where no team has incentive
    to unilaterally change their assignments.
    """

    def __init__(self, all_teams_entries, meet_profile):
        self.teams = self._group_by_team(all_teams_entries)
        self.meet_profile = meet_profile

    def find_equilibrium(self, max_iterations=100):
        """
        Iterative best-response algorithm:
        1. Start with seed-time based assignments
        2. For each team, optimize given other teams' current strategies
        3. Repeat until convergence (no team wants to change)
        """
        current_strategies = self._initialize_strategies()

        for iteration in range(max_iterations):
            improved = False

            for team in self.teams:
                # Optimize this team given others' strategies
                new_strategy = self._best_response(
                    team,
                    current_strategies
                )

                if new_strategy != current_strategies[team]:
                    current_strategies[team] = new_strategy
                    improved = True

            if not improved:
                # Reached Nash Equilibrium
                break

        return current_strategies
```

### Use Cases

**Scenario 1: Close Championship Race**
- 3 teams within 20 points of each other
- Nash Equilibrium shows: "If Team A puts their star in 100 Free, Team B should respond with 100 Fly"
- Helps coaches anticipate opponent strategies

**Scenario 2: Strategic Event Selection**
- Team has swimmer who could do 50 Free OR 100 Free
- Nash analysis: "100 Free is less contested, choose that"

### Pros & Cons

**Pros:**
- Accounts for competitive dynamics
- Finds stable, defensible strategies
- Helps with strategic planning

**Cons:**
- Computationally expensive (O(N * iterations))
- Requires accurate opponent data
- May not converge if no equilibrium exists
- Assumes rational opponents

---

## Phase 2: Monte Carlo Simulation

### Concept

Simulate thousands of meet scenarios with performance variance to get probability distributions of outcomes.

### Implementation

```python
class MonteCarloSimulator:
    """
    Probabilistic meet outcome simulation.
    """

    def simulate_meet(
        self,
        assignments,
        num_simulations=10000,
        variance_model="historical"
    ):
        """
        Run N simulations with:
        - Time variance (swimmers don't always hit seed times)
        - DQ probability
        - Relay exchange variance
        """
        results = []

        for _ in range(num_simulations):
            # Sample times from distribution
            simulated_times = self._sample_times(
                assignments,
                variance_model
            )

            # Score this simulation
            scores = self._score_simulation(simulated_times)
            results.append(scores)

        # Analyze results
        return {
            "expected_score": np.mean(results),
            "confidence_95": np.percentile(results, [2.5, 97.5]),
            "win_probability": np.mean(results > threshold),
            "risk_score": np.std(results),
        }
```

### Variance Models

1. **Historical Variance**: Based on past performance data
2. **Seed Time Confidence**: Faster seeds = lower variance
3. **Event-Specific**: Sprints more consistent than distance

### UI Display

```
Projected Score: 191 points
├─ Expected: 191 ± 15 points (95% CI: 176-206)
├─ Win Probability: 78%
├─ Risk Level: Medium
└─ Recommendation: Conservative strategy suggested
```

---

## Phase 3: Scenario Analysis

### Concept

Allow coaches to test "what-if" scenarios interactively.

### Features

```typescript
interface ScenarioAnalysis {
  baseline: OptimizationResult;
  scenarios: {
    "if_swimmer_X_improves_by_1s": OptimizationResult;
    "if_relay_team_changes": OptimizationResult;
    "if_opponent_strategy_changes": OptimizationResult;
  };
  recommendations: string[];
}
```

### Example Scenarios

1. **"What if our 50 Freestyler drops 0.5 seconds?"**
   - Re-run optimization with improved time
   - Show point gain: "+8 points, moves from 3rd to 1st"

2. **"What if we rest our star for relays?"**
   - Remove from individual events
   - Show trade-off: "-12 individual, +18 relay = +6 net"

3. **"What if Trinity puts their best swimmer in 100 Free?"**
   - Adjust opponent strategy
   - Show impact: "We drop from 1st to 2nd in that event, -6 points"

---

## Phase 4: Strategy Comparison Matrix

### Visual Comparison

```
| Strategy         | Projected | Risk  | Complexity | Best For          |
| ---------------- | --------- | ----- | ---------- | ----------------- |
| Maximize Indiv   | 191 pts   | Low   | Simple     | Most teams        |
| Nash Equilibrium | 198 pts   | Med   | Complex    | Competitive meets |
| Monte Carlo      | 191±15    | Known | Medium     | Risk assessment   |
| Balanced         | 195 pts   | Med   | Medium     | Flexible teams    |
| Conservative     | 178 pts   | Low   | Simple     | Young teams       |
| Aggressive       | 203 pts   | High  | Complex    | Championship push |
```

---

## Phase 5: UI/UX Enhancements

### New Championship Optimization Page

```
┌─────────────────────────────────────────────────────────┐
│  Championship Optimization                               │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  📊 Meet: VCAC Championship 2026                        │
│  👥 Teams: 6 teams, 142 total entries                   │
│  🎯 Target: Seton (SST)                                 │
│                                                          │
├─────────────────────────────────────────────────────────┤
│  Strategy Selection                                      │
│                                                          │
│  ○ Maximize Individual Events (Recommended) ⚡          │
│    Fast, reliable optimization of individual events     │
│    Best for: Most teams, first-time users              │
│                                                          │
│  ○ Nash Equilibrium (Advanced) 🎯                       │
│    Multi-team game theory optimization                  │
│    Best for: Competitive meets, strategic planning     │
│    ⚠️  Requires opponent entry data                     │
│                                                          │
│  ○ Monte Carlo Simulation (Risk Analysis) 📈            │
│    Probabilistic outcome modeling                       │
│    Best for: Understanding variance and risk            │
│                                                          │
│  [Show All Strategies →]                                │
│                                                          │
├─────────────────────────────────────────────────────────┤
│  Advanced Options                                        │
│                                                          │
│  ☑ Include back-to-back events                         │
│  ☑ Optimize relay lineups                              │
│  ☐ Conservative (avoid fatigue)                        │
│  ☐ Aggressive (maximize points)                        │
│                                                          │
│  Simulation Count: [10,000] ▼                           │
│  Confidence Level: [95%] ▼                              │
│                                                          │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  [Run Optimization]  [Compare Strategies]               │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

### Results Display

```
┌─────────────────────────────────────────────────────────┐
│  Optimization Results                                    │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  Strategy: Maximize Individual Events                   │
│                                                          │
│  📊 Projected Score                                     │
│  ┌────────────────────────────────────────────────┐    │
│  │  191 points                                     │    │
│  │  Individual Events Only                         │    │
│  └────────────────────────────────────────────────┘    │
│                                                          │
│  🏆 Full Meet Projection                                │
│  ┌────────────────────────────────────────────────┐    │
│  │  1. Seton         234 pts  ⭐ (You)            │    │
│  │  2. Trinity       218 pts                       │    │
│  │  3. Immanuel      205 pts                       │    │
│  │  4. Oakcrest      192 pts                       │    │
│  │  5. Fredericksburg 178 pts                      │    │
│  │  6. O'Connell     165 pts                       │    │
│  └────────────────────────────────────────────────┘    │
│                                                          │
│  💡 Key Insights                                        │
│  • Your strongest events: 50 Free (+32), 100 Fly (+26) │
│  • Swing events: 3 opportunities for +10 points        │
│  • Competitive events: 100 Free (6 teams within 2s)    │
│                                                          │
│  [View Event Breakdown] [Export Results] [Try Another] │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

---

## Implementation Timeline

### Week 1: Foundation
- [x] Create strategy definitions module
- [x] Add /strategies API endpoint
- [ ] Create strategy selection UI component
- [ ] Add strategy comparison view

### Week 2: Nash Equilibrium
- [ ] Implement best-response algorithm
- [ ] Add convergence detection
- [ ] Create multi-team optimizer
- [ ] Add Nash strategy to UI

### Week 3: Monte Carlo
- [ ] Implement variance models
- [ ] Add simulation engine
- [ ] Create probability distributions
- [ ] Add risk visualization to UI

### Week 4: Integration & Polish
- [ ] Integrate all strategies
- [ ] Add scenario analysis
- [ ] Create comparison matrix
- [ ] User testing and refinement

---

## Success Metrics

1. **Performance**: Nash equilibrium converges in < 10 seconds
2. **Accuracy**: Monte Carlo predictions within 10% of actual results
3. **Usability**: 80% of users understand strategy differences
4. **Adoption**: 50% of users try advanced strategies

---

## Technical Considerations

### Nash Equilibrium Challenges

1. **Convergence**: May not always reach equilibrium
   - Solution: Set max iterations, return best found

2. **Computational Cost**: O(N teams × M iterations)
   - Solution: Parallel processing, caching

3. **Data Requirements**: Need opponent entries
   - Solution: Graceful degradation if data missing

### Monte Carlo Challenges

1. **Variance Modeling**: Need historical data
   - Solution: Use conservative defaults, learn over time

2. **Simulation Speed**: 10,000 runs must be fast
   - Solution: Vectorized numpy operations

---

## Next Steps

1. **User Review**: Get feedback on strategy definitions
2. **Prototype**: Build Nash equilibrium proof-of-concept
3. **Test**: Validate with historical meet data
4. **Iterate**: Refine based on coach feedback

---

## Questions for User

1. Do you have historical meet data for variance modeling?
2. Priority: Nash Equilibrium or Monte Carlo first?
3. Should we support custom variance models?
4. Any other game theory concepts to consider?
