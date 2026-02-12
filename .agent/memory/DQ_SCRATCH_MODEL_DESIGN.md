# DQ/Scratch Probability Model — Design Specification

## Status: DESIGN COMPLETE — Ready for Implementation

## Problem Statement

The optimizer currently treats all seed entries as certain completions. In reality,
swimmers may DQ (disqualification), DNS (did not start/scratch), or DNF (did not
finish), creating scoring volatility the optimizer doesn't account for.

From empirical analysis of 25,830 entries across 52 championship meets:
- Seed accuracy has a 77.9% flip rate (significant position changes)
- 50 Free has "low" confidence tier (most volatile event)
- DQ/DNS events shift points to other teams unexpectedly

## Data Infrastructure Assessment

### What Exists
| Component | Status | Location |
|-----------|--------|----------|
| `is_dq` field in MDB parser | **Parsed** | `hytek_mdb_parser.py:544-547` — detects "DQ", "D", "DSQ" from `Fin_stat` |
| `is_dq` in DB model | **Stored** | `db_models.py:216` — `Entry.is_dq: bool` |
| `is_dns` in DB model | **Schema ready** | `db_models.py:217` — `Entry.is_dns: bool` (NOT populated yet) |
| `dq_code` in DB model | **Schema ready** | `db_models.py:218` — `Entry.dq_code: str` (NOT populated) |
| `is_exhibition` flag | **Parsed** | `hytek_mdb_parser.py:541` — from `Fin_exh` |
| DQ filtering in backtest | **Active** | `counterfactual_backtest.py:87` — `WHERE en.is_dq = 0` |
| DQ filtering in bias calc | **Active** | `historical_backtest.py:51` — `AND en.is_dq = 0` |
| Platform adapter statuses | **Recognized** | `platform_adapters.py:235` — "NT", "NS", "DQ", "SCR", "X" → 9999.99 |
| Monte Carlo time variance | **Active** | Two engines: `core/monte_carlo.py` (dual), `championship/monte_carlo.py` (champ) |
| Historical MDB databases | **~100 files** | `data/organized/hytek_databases/` — 2003-2025 span |

### What's Missing
1. **DNS inference from MDB**: Entry has `seed_time` but no `finals_time` and not DQ → DNS
2. **Historical DQ/DNS rate aggregation**: No code calculates rates from the 100+ MDBs
3. **Attrition modeling in Monte Carlo**: Simulators model time variance but not swimmer dropout
4. **Risk-weighted scoring in optimizer**: All entries treated as equally certain

## Proposed Architecture

### Phase 1: Data Extraction & DNS Inference (prerequisite)
**Effort: ~2 hours | Files: 2**

#### 1a. Enhance MDB Parser DNS Inference
In `hytek_mdb_parser.py`, after DQ detection (line 547), add:

```python
# DNS inference: has seed time, no finals time, not DQ → Did Not Start
is_dns = (
    seed_time is not None
    and finals_time is None
    and not is_dq
    and place is None  # No place awarded
)
```

Set `ParsedEntry.is_dns = is_dns` and propagate through ETL pipeline.

#### 1b. Aggregate Historical Rates Script
New script: `scripts/compute_dq_dns_rates.py`

Query the SQLite DB for all entries across all ingested meets:

```sql
SELECT
    ev.event_name,
    m.meet_type,
    COUNT(*) as total_entries,
    SUM(CASE WHEN en.is_dq = 1 THEN 1 ELSE 0 END) as dq_count,
    SUM(CASE WHEN en.is_dns = 1 THEN 1 ELSE 0 END) as dns_count,
    SUM(CASE WHEN en.finals_time IS NULL AND en.is_dq = 0 THEN 1 ELSE 0 END) as no_result_count
FROM entries en
JOIN events ev ON en.event_id = ev.id
JOIN meets m ON ev.meet_id = m.id
WHERE ev.is_relay = 0
GROUP BY ev.event_name, m.meet_type
HAVING total_entries >= 20
```

Output: `data/dq_dns_rates.json` with structure:

```json
{
  "global_dq_rate": 0.023,
  "global_dns_rate": 0.045,
  "by_event": {
    "50 Free": { "dq_rate": 0.010, "dns_rate": 0.030, "n": 1850 },
    "100 Fly": { "dq_rate": 0.040, "dns_rate": 0.050, "n": 920 }
  },
  "by_meet_type": {
    "championship": { "dq_rate": 0.020, "dns_rate": 0.060 },
    "dual": { "dq_rate": 0.025, "dns_rate": 0.035 }
  }
}
```

### Phase 2: Attrition Rate Module
**Effort: ~1.5 hours | Files: 1**

New module: `swim_ai_reflex/backend/core/attrition_model.py`

```python
@dataclass
class AttritionRates:
    """Per-event DQ/DNS probabilities for scoring adjustment."""
    enabled: bool
    dq_rates: dict[str, float]    # event → P(DQ)
    dns_rates: dict[str, float]   # event → P(DNS)
    default_dq: float = 0.023     # fallback global rate
    default_dns: float = 0.045    # fallback global rate

    @classmethod
    def from_json(cls, path: str) -> "AttritionRates": ...

    @classmethod
    def disabled(cls) -> "AttritionRates": ...

    def combined_attrition(self, event: str) -> float:
        """P(swimmer doesn't score) = P(DQ) + P(DNS)"""
        return self.dq_rate(event) + self.dns_rate(event)

    def expected_value_factor(self, event: str) -> float:
        """Discount factor: 1 - P(attrition) for expected value scoring."""
        return 1.0 - self.combined_attrition(event)
```

### Phase 3: Integration Points (3 paths)
**Effort: ~3 hours | Files: 3**

#### 3a. Monte Carlo Integration (highest value)
In `championship/monte_carlo.py` `_simulate_event()`:

```python
# Before time variance, stochastically drop swimmers
if self.attrition and np.random.random() < self.attrition.combined_attrition(event):
    continue  # Swimmer doesn't score this trial
```

This naturally produces wider confidence intervals and more realistic outcome
distributions. A swimmer with 4% DQ risk on 100 Fly will be absent from ~4%
of simulated meets, reducing their expected point contribution.

#### 3b. Point Projection Integration (medium value)
In `championship/projection.py` `_project_event()`:

```python
# After scoring, discount projected points by attrition probability
projected.expected_points *= attrition.expected_value_factor(event_name)
```

This reduces the projected score for events where swimmers are more likely to
DQ or scratch, giving coaches a more realistic projection.

#### 3c. Optimizer Scoring Integration (strategic value)
In `aqua_optimizer.py` or `championship_strategy.py`:

The optimizer can use attrition rates to prefer lower-risk assignments when
point margins are tight:

```python
# Risk-adjusted score = raw_points × (1 - attrition_rate)
# This naturally penalizes high-DQ events like 100 Fly (4% DQ)
# vs low-DQ events like 50 Free (1% DQ)
risk_score = base_score * attrition.expected_value_factor(event)
```

For Gurobi ILP: modify the point matrix coefficients.
For Aqua beam search: adjust the scoring function.

## Hierarchical Rate Model (Bayesian-inspired)

The rates should be computed hierarchically for best accuracy:

```
Level 1: Global baseline     → P(DQ) = 2.3%  (all events, all meets)
Level 2: Per-event           → P(DQ | 100 Fly) = 4.0%
Level 3: Per-swimmer-event   → P(DQ | swimmer=X, event=100 Fly) = 8.0%
```

For swimmers with enough history (N >= 5 entries in event), use their personal
rate. Otherwise, fall back to event-level, then global. This avoids overfitting
to single incidents while capturing repeat-DQ swimmers.

Implementation: weighted blend:
```python
def blended_rate(swimmer_rate, swimmer_n, event_rate, min_n=5):
    """Shrink swimmer estimate toward event prior."""
    weight = min(swimmer_n / min_n, 1.0)
    return weight * swimmer_rate + (1 - weight) * event_rate
```

## Expected Impact

| Metric | Current | With Attrition Model |
|--------|---------|---------------------|
| Monte Carlo CI width | ±15-25 pts | ±18-30 pts (more realistic) |
| Projection accuracy | ~90.7% top-12 | Better calibration for borderline |
| Optimizer risk awareness | None | Prefers low-DQ assignments |
| Coach decision support | Time-only | DQ risk flagging per assignment |

## Implementation Order

1. **Phase 1b first** — Run the rate aggregation script on existing DB data
   (even without DNS inference, DQ data is already there)
2. **Phase 1a** — Add DNS inference to parser, re-ingest a few key MDBs
3. **Phase 2** — Build the `AttritionRates` module
4. **Phase 3a** — Wire into Monte Carlo (biggest bang-for-buck)
5. **Phase 3b** — Wire into projections
6. **Phase 3c** — Wire into optimizer scoring (most complex)

## Dependencies

- Requires 100+ ingested MDB databases in SQLite
- `is_dq` already populated from parser
- `is_dns` needs parser enhancement + re-ingestion
- No new Python packages needed (numpy, pandas already available)

## Risks & Mitigations

| Risk | Mitigation |
|------|-----------|
| Low DQ sample size per swimmer | Hierarchical model shrinks toward event prior |
| DNS inference inaccuracy | Conservative: only flag DNS when seed_time exists AND no finals_time AND no DQ |
| Over-penalizing strong swimmers who had 1 DQ | Minimum N threshold (5) before using personal rate |
| Championship vs dual meet rate differences | Separate rate tables by meet_type |
