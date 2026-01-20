# Meet Profile Configuration System

## Design for Easily Switchable Meet Types

**Created**: 2026-01-15  
**Status**: Design Document

---

## Current Architecture

The existing `rules.py` already has a good foundation:

```python
@dataclass
class MeetRules:
    name: str
    individual_points: List[int]
    relay_points: List[int]
    max_individual_events_per_swimmer: int
    max_total_events_per_swimmer: int
    max_entries_per_team_per_event: int
    max_relays_per_team_per_event: int
    max_scorers_per_team_individual: int
    max_scorers_per_team_relay: int
    min_scoring_grade: int = 8
```

Currently has: `VISAADualRules`, `VISAAChampRules`

---

## Proposed Solution: Meet Profile System

### 1. Add New Rule Classes in `rules.py`

```python
@dataclass
class SetonDualRules(MeetRules):
    """
    Seton Dual Meet Rules (from Coach Koehr):
    - Individual: Top 7 score [8, 6, 5, 4, 3, 2, 1]
    - Relay: Top 3 score [10, 5, 3]
    - 4 scoring entries per individual, 2 per relay
    """
    name: str = "Seton Dual Meet"
    individual_points: List[int] = field(default_factory=lambda: [8, 6, 5, 4, 3, 2, 1])
    relay_points: List[int] = field(default_factory=lambda: [10, 5, 3])
    max_individual_events_per_swimmer: int = 2
    max_total_events_per_swimmer: int = 4
    max_entries_per_team_per_event: int = 4  # varsity
    max_relays_per_team_per_event: int = 2   # A and B
    min_scoring_grade: int = 8  # 7th grade = exhibition
    max_scorers_per_team_individual: int = 4
    max_scorers_per_team_relay: int = 2


@dataclass
class VCACChampRules(MeetRules):
    """
    VCAC Conference Championship (Feb 7, 2026):
    - Individual: 32-26-24-22-20-18-14-10-8-6-4-2
    - Relay: 16-13-12-11-10-9-7-5-4-3-2-1
    - Individual worth MORE than relay!
    """
    name: str = "VCAC Championship"
    individual_points: List[int] = field(default_factory=lambda: [32, 26, 24, 22, 20, 18, 14, 10, 8, 6, 4, 2])
    relay_points: List[int] = field(default_factory=lambda: [16, 13, 12, 11, 10, 9, 7, 5, 4, 3, 2, 1])
    max_individual_events_per_swimmer: int = 2
    max_total_events_per_swimmer: int = 5  # 2 indiv + 3 relay, or complex with diving
    max_entries_per_team_per_event: int = 999  # unlimited
    max_relays_per_team_per_event: int = 2  # A and B
    min_scoring_grade: int = 8
    max_scorers_per_team_individual: int = 4
    max_scorers_per_team_relay: int = 2

    # VCAC specific
    diving_counts_as_individual: bool = True
    relay_free_count: int = 2  # first 2 relays don't count toward individual limit


@dataclass
class VISAAStateRules(MeetRules):
    """
    VISAA State Championship (Feb 12-14, 2026):
    - Championship Finals: 40-34-32-30...
    - Consolation Finals: 20-17-16-15...
    - Prelims/Finals format
    """
    name: str = "VISAA State Championship"
    # Championship finals scoring
    individual_points: List[int] = field(default_factory=lambda: [40, 34, 32, 30, 28, 26, 24, 22, 18, 14, 12, 10, 8, 6, 4, 2])
    relay_points: List[int] = field(default_factory=lambda: [40, 34, 32, 30, 28, 26, 24, 22, 18, 14, 12, 10, 8, 6, 4, 2])
    # Consolation finals scoring (places 9-16)
    consolation_individual_points: List[int] = field(default_factory=lambda: [20, 17, 16, 15, 14, 13, 12, 11, 9, 7, 6, 5, 4, 3, 2, 1])
    consolation_relay_points: List[int] = field(default_factory=lambda: [20, 17, 16, 15, 14, 13, 12, 11, 9, 7, 6, 5, 4, 3, 2, 1])

    max_individual_events_per_swimmer: int = 2
    max_total_events_per_swimmer: int = 4
    max_entries_per_team_per_event: int = 3
    max_relays_per_team_per_event: int = 2
    min_scoring_grade: int = 8
    max_scorers_per_team_individual: int = 16
    max_scorers_per_team_relay: int = 16

    # State-specific
    has_prelims_finals: bool = True
    no_exhibition: bool = True
```

### 2. Create Profile Registry

```python
# In rules.py or new file: meet_profiles.py

MEET_PROFILES = {
    "seton_dual": SetonDualRules,
    "vcac_championship": VCACChampRules,
    "visaa_state": VISAAStateRules,
    "visaa_dual": VISAADualRules,
    "visaa_championship": VISAAChampRules,
}

def get_meet_profile(profile_name: str) -> MeetRules:
    """Get a meet profile by name."""
    if profile_name not in MEET_PROFILES:
        available = list(MEET_PROFILES.keys())
        raise ValueError(f"Unknown profile '{profile_name}'. Available: {available}")
    return MEET_PROFILES[profile_name]()

def list_profiles() -> List[str]:
    """List all available meet profiles."""
    return list(MEET_PROFILES.keys())
```

### 3. Update optimization_service.py

Change:

```python
def predict_best_lineups(
    self,
    seton_roster: pd.DataFrame,
    opponent_roster: pd.DataFrame,
    method: str = "gurobi",
    max_iters: int = 50,
    enforce_fatigue: bool = False,
    scoring_type: str = "visaa_top7",  # OLD
    ...
)
```

To:

```python
def predict_best_lineups(
    self,
    seton_roster: pd.DataFrame,
    opponent_roster: pd.DataFrame,
    method: str = "gurobi",
    max_iters: int = 50,
    enforce_fatigue: bool = False,
    meet_profile: str = "seton_dual",  # NEW
    ...
)
```

### 4. Frontend UI (Next.js)

Add a dropdown selector:

```tsx
// In optimization page component
const MEET_PROFILES = [
  { value: "seton_dual", label: "Dual Meet (Seton Standard)" },
  { value: "vcac_championship", label: "VCAC Championship (Feb 7)" },
  { value: "visaa_state", label: "VISAA State Championship (Feb 12-14)" },
];

<Select
  label="Meet Type"
  value={meetProfile}
  onChange={(e) => setMeetProfile(e.target.value)}
>
  {MEET_PROFILES.map((p) => (
    <Option key={p.value} value={p.value}>
      {p.label}
    </Option>
  ))}
</Select>;
```

---

## Configuration Storage

### Option A: Settings in `localStorage` (Frontend)

- Persist last-used profile
- No backend changes needed

### Option B: Config file (Backend)

Create `.aquaforge/config.yaml`:

```yaml
default_meet_profile: seton_dual
last_used: vcac_championship
custom_profiles:
  # Users could define custom profiles here
```

### Option C: Database (Future)

- Store per-user preferences
- Requires auth implementation

**Recommendation**: Start with Option A (localStorage) for simplicity.

---

## Implementation Steps

### Sprint 1: Backend Profile System

1. [ ] Add new rule classes to `rules.py`
2. [ ] Create `MEET_PROFILES` registry
3. [ ] Update `optimization_service.py` to accept `meet_profile` parameter
4. [ ] Add API endpoint to list available profiles

### Sprint 2: Frontend Integration

1. [ ] Add profile dropdown to optimization page
2. [ ] Store selection in localStorage
3. [ ] Pass profile to API calls

### Sprint 3: Testing

1. [ ] Unit tests for each profile
2. [ ] E2E test switching between profiles
3. [ ] Verify scoring calculations match documentation

---

## Validation

Each profile should be validated against known scoring:

```python
def test_seton_dual_scoring():
    rules = SetonDualRules()
    assert rules.individual_points == [8, 6, 5, 4, 3, 2, 1]
    assert rules.relay_points == [10, 5, 3]
    assert rules.max_scorers_per_team_individual == 4

def test_vcac_championship_scoring():
    rules = VCACChampRules()
    assert rules.individual_points[0] == 32  # 1st place = 32
    assert rules.relay_points[0] == 16       # 1st place = 16 (NOT 32!)
```

---

## Summary

This approach:

1. ✅ Uses existing `MeetRules` dataclass pattern
2. ✅ Easy to add new profiles (just create new class)
3. ✅ Single dropdown in UI to switch
4. ✅ Settings persist without affecting other profiles
5. ✅ Validates scoring at profile level
