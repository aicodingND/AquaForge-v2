---
name: Championship Mode
description: Multi-team championship optimization strategies and workflows
triggers:
  - championship optimization
  - multi-team scoring
  - VCAC championship
  - VISAA states
---

# Championship Mode Skill 🏆

Use this skill for multi-team championship meets (VCAC, VISAA States).

---

## Championship vs Dual Meet

| Aspect    | Dual Meet         | Championship           |
| --------- | ----------------- | ---------------------- |
| Teams     | 2                 | 6-20+                  |
| Opponent  | Known, single     | Field of competitors   |
| Algorithm | Nash Equilibrium  | Entry Selection ILP    |
| Strategy  | Beat ONE opponent | Maximize against field |
| Points    | Head-to-head      | Placement against all  |

---

## VCAC Championship Specifics

### Scoring (Top 12 Score)

**Individual:** 32-26-24-22-20-18-14-10-8-6-4-2  
**Relay:** 16-13-12-11-10-9-7-5-4-3-2-1

### The Relay 3 Rule (CRITICAL)

⚠️ **400 Free Relay counts as 1 individual event slot!**

```python
def calculate_effective_individual(swimmer):
    """VCAC: Relay 3 counts as individual slot."""
    individual_used = swim_individual_count + (1 if is_diver else 0)
    relay_penalty = max(0, relay_count - 2)  # Only relay 3 costs
    return individual_used + relay_penalty
```

### Valid Entry Combinations (VCAC)

| Swim | Dive | Relays | Valid? | Notes                 |
| ---- | ---- | ------ | ------ | --------------------- |
| 2    | No   | 2      | ✅      | Standard max          |
| 1    | Yes  | 2      | ✅      | Diver with 1 swim     |
| 2    | No   | 3      | ❌      | Relay 3 = 3 effective |
| 1    | No   | 3      | ✅      | Relay 3 specialist    |
| 0    | Yes  | 3      | ✅      | Diver + Relay 3 only  |

---

## Championship Optimization Workflow

### Phase 1: Project Points

```python
# Use PointProjectionEngine
from swim_ai_reflex.backend.core.scoring.point_projection import PointProjectionEngine

engine = PointProjectionEngine(scoring_type='vcac')
projections = engine.project_points(psych_sheet, target_team='SST')
```

### Phase 2: Entry Selection

```python
# Use ChampionshipGurobiStrategy
from swim_ai_reflex.backend.core.strategies.championship_strategy import ChampionshipGurobiStrategy

strategy = ChampionshipGurobiStrategy()
optimal_entries = strategy.optimize(
    psych_sheet=psych_sheet,
    target_team='SST',  # Use team CODE, not full name!
    constraints={
        'max_individual': 2,
        'relay_3_counts': True,
        'diving_counts': True
    }
)
```

### Phase 3: Relay Optimization

```python
# Optimize relay assignments
from swim_ai_reflex.backend.core.relay.optimizer import RelayOptimizer

relay_opt = RelayOptimizer()
relays = relay_opt.assign_relays(
    swimmers=optimal_entries.selected_swimmers,
    relay_events=['200 Medley Relay', '200 Free Relay', '400 Free Relay']
)
```

### Phase 4: Trade-off Analysis

```python
# 400 FR trade-off analysis
from swim_ai_reflex.backend.core.strategies.relay_tradeoff import Relay400TradeoffAnalyzer

analyzer = Relay400TradeoffAnalyzer()
tradeoff = analyzer.analyze(
    psych_sheet=psych_sheet,
    target_team='SST',
    projected_score=projections['total']
)
```

---

## Strategic Decision Points

### Decision 1: Who goes in 400 FR?

The 400 Free Relay consumes an individual slot. Evaluate:

**Good 400 FR candidates:**
- Swimmers already at 1 individual event
- Strong 100 Free split times
- Not critical for other individual events

**Avoid for 400 FR:**
- Swimmers with 2 high-scoring individual events
- Divers (already using a slot)

### Decision 2: Exhibition Strategy

Championship meets MAY limit exhibition. If allowed:
- Use exhibition for experience
- Don't waste varsity slots on non-scorers
- 7-8 graders always exhibition

### Decision 3: Event Concentration

| Team Depth                | Strategy                                 |
| ------------------------- | ---------------------------------------- |
| Deep (many good swimmers) | Spread entries across events             |
| Thin (few standouts)      | Concentrate best swimmers in best events |

---

## API Integration

### Endpoint: `/api/v2/championship`

```http
POST /api/v2/championship/optimize
Content-Type: application/json

{
    "psych_sheet": [...],
    "target_team": "SST",
    "scoring_type": "vcac",
    "include_relay_tradeoff": true
}
```

### Response:
```json
{
    "status": "success",
    "projected_score": 254,
    "optimal_entries": [...],
    "relay_assignments": {...},
    "tradeoff_analysis": {...}
}
```

---

## Common Gotchas

1. **Use team CODE ("SST"), not full name ("Seton")**
   - `ChampionshipGurobiStrategy` filters by `e.team.upper() == target_team.upper()`

2. **Championship has no "opponent"**
   - Don't show "X vs 0" in UI
   - Display "Projected Score: X"

3. **VCAC uses top 4 scorers per event**
   - Not top 3 like dual meets

4. **Multiple psych sheet sources**
   - SwimCloud scraped data
   - Coach-provided spreadsheets
   - Meet-specific psych sheets
   - **Merge and deduplicate!**

---

## Integration with PRISM

For complex championship strategy, invoke PRISM:

```
/prism Optimize championship entries for VCAC, balancing 
individual event strength against relay needs, considering 
the 400 FR trade-off
```

---

_Skill: championship-mode | Version: 1.0_
