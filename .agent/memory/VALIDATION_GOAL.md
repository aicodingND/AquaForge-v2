# Central Validation Goal: Optimizer Must Beat Coach

**Every feature, fix, and refactor must serve this goal.**
If the core optimization doesn't produce better lineups than a coach working manually,
all supporting features (live tracker, analytics, exports) provide zero value.

---

## Validation Framework

### 1. Pre-Work Check
Before starting any task, ask:
> "Does this improve the optimizer's ability to find better lineups?"

If NO — deprioritize unless it's a direct user request.
If YES — proceed, and validate with backtest after.

### 2. Post-Change Backtest
After any change to scoring, rules, constraints, or optimizer logic:

```bash
# Run the canonical backtest
source .venv/bin/activate
python scripts/compare_coach_vs_optimizer.py

# Verify delta is positive (optimizer > coach)
python scripts/backtest_meet_512.py
```

**Pass criteria**: Optimizer seed-scored total > Coach seed-scored total (currently +112 pts).

### 3. Scoring Rule Validation
After any change to `rules.py` or `scoring.py`:

```bash
python -m pytest tests/test_scoring_constraints.py -v
```

**Pass criteria**: All 38 tests pass, no regression in point tables or constraint enforcement.

### 4. Constraint Validation
After any change to entry limits or max-events logic:

```bash
python -m pytest tests/test_constraint_validator.py tests/test_entry_optimizer.py -v
```

**Pass criteria**: No swimmer exceeds 2 individual events, no swimmer exceeds 4 total events.

---

## Backtest Baseline (Meet 512 — VCAC Regular Season Championship)

### Seed-Time Comparison (Apples-to-Apples)

| Team   | Coach (seed) | Optimizer (seed) | Delta   |
|--------|-------------|-----------------|---------|
| Boys   | 103 pts     | 140 pts         | **+37** |
| Girls  | 56 pts      | 131 pts         | **+75** |
| **Total** | **159 pts** | **271 pts** | **+112 (+70%)** |

### Where the Optimizer Found Points the Coach Missed

| Swimmer | Coach Assignment | Optimizer Assignment | Delta |
|---------|-----------------|---------------------|-------|
| Rafael De Micoli | 50 Free + 100 Breast (0 pts) | 200 Free (16 pts, 1st seed) | +16 |
| Therese Paradise | 500 Free + 50 Free (4 pts) | 100 Breast + 100 Fly (19 pts) | +15 |
| Penny Kramer | Not entered | 200 Free (12 pts, 3rd seed) | +12 |
| Philomena Kay | 200 Free + 50 Free (0 pts) | 100 Breast + 200 IM (12 pts) | +12 |
| Patrick Kay | 100 Free + 100 Back (14 pts) | 100 Back + 500 Free (19 pts) | +5 |

### What Makes the Optimizer Better

1. **Exhaustive search**: 10,000+ lineup permutations vs coach's ~50 mental scenarios
2. **Global optimization**: Considers team-wide point maximization, not per-swimmer
3. **Constraint enforcement**: Mathematically guarantees no rule violations
4. **Opponent modeling**: Nash equilibrium anticipates counter-strategies
5. **Hidden opportunities**: Found 4 scoring-eligible swimmers coach didn't enter

### What the Coach Still Does Better

1. **Race-day knowledge**: Who's injured, who's peaking, who's nervous
2. **Taper effect**: Actual race-day score was 529 pts (3.3x seed projection)
3. **Relay composition**: Leg selection based on relay-specific splits
4. **Strategic timing**: Holding back in prelims, saving energy for finals

---

## Seed Accuracy Empirical Analysis (2026-02-12)

**Source**: 25,830 swim entries across 52 championship meets parsed from HyTek MDBs.
**Script**: `scripts/analyze_seed_accuracy.py`

### Key Findings

| Metric | Value | Implication |
|--------|-------|-------------|
| Avg time drop | +1.12s (+1.01%) | Swimmers are consistently faster at meets than seeds |
| Swam faster | 58.6% | Majority improve, but 41% go slower — variance is real |
| Exact placement flip | 77.9% | Seeds don't predict specific finishing positions |
| Top-3 stability | 80.6% | Top seeds reliably win — highest-point assignments are safe |
| Top-12 stability | 90.7% | Scoring positions are very stable — optimizer's core approach works |
| Avg flip magnitude | 2.5 places | When flips happen, they're moderate (not catastrophic) |

### Event-Specific Variance (most/least predictable)

| Event | Flip Rate | Notes |
|-------|-----------|-------|
| 200 IM | 64.9% | Most predictable — complex event rewards consistent swimmers |
| 500 Free | 68.2% | Distance = stable |
| 50 Back | 91.0% | Least predictable — sprint + specialty = high variance |
| 50 Breast | 88.0% | Sprint specialty events flip frequently |

### Grade-Based Drop (all grades improve similarly)

| Grade | Avg Drop % | Note |
|-------|-----------|------|
| 7 | +1.71% | Slight edge but small sample |
| 8-12 | +1.4-2.5% | Uniform — no grade-specific model needed |

### Actionable Conclusions

1. **Championship adjustment factor: 0.99** (multiply seed times by 0.99 for 1% speed-up)
2. **Apply uniformly** — no need for per-grade or per-event adjustment models
3. **Optimizer's seed-based approach is validated** — 91% top-12 stability means assignments hold where points are highest
4. **Sensitivity focus**: Events with >85% flip rate (50 Back, 50 Breast, 50 Fly) need wider confidence intervals for coach review

---

## Improvement Roadmap (Ordered by Impact on Core Goal)

### High Impact (Directly Improves Lineup Quality)
1. **Championship speed-up factor (0.99x)** — Apply 1% uniform adjustment to seed times *(validated by empirical analysis)*
2. **Relay-aware optimization** — Joint relay+individual optimization (not sequential)
3. **Historical performance weighting** — Recent meets weighted higher than season bests
4. **DQ/scratch probability** — Account for swimmers who historically DQ or scratch

### Medium Impact (Improves Decision Quality)
5. **Sensitivity analysis** — Show which placements are "close calls" for coach override
6. **What-if scenarios** — Let coach lock specific assignments, re-optimize rest
7. **Confidence intervals** — Show range of expected outcomes, not point estimates

### Low Impact (Supporting Features)
8. Live tracking, email reports, analytics dashboards
9. Training plan generation, video analysis
10. Multi-coach collaboration

---

## Decision Heuristic

When choosing what to work on:

```
IF task improves seed accuracy → DO IT FIRST
ELIF task improves constraint enforcement → DO IT SECOND
ELIF task improves search quality → DO IT THIRD
ELIF task improves UX → DO IT IF TIME PERMITS
ELSE → SKIP
```
