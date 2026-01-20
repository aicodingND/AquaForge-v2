# AquaForge Meet Type Architecture

**Document Type:** Architecture Decision Record  
**Status:** PROPOSED  
**Created:** January 16, 2026  
**PRISM Confidence:** 85%

---

## 📋 Executive Summary

This document outlines the recommended architecture for overhauling AquaForge's dual meet and championship meet workflows. The key insight: **these are fundamentally different problems that share common infrastructure but require distinct processing pipelines**.

---

## 🎯 Problem Statement

The current AquaForge codebase mixes dual meet and championship logic in a single `optimization_service.py` file (680 lines). This has caused:

1. **The 270-0 Bug**: Scoring details mismatch due to mixing single-team and multi-team logic
2. **Incomplete Championship Mode**: Phase 3 (championship integration) remains "in progress"
3. **Maintenance Difficulty**: Changes to one mode risk breaking the other
4. **Testing Gaps**: No clear separation makes isolated testing difficult

---

## 🔄 The Fundamental Difference

| Aspect                | Dual Meet                         | Championship Meet               |
| --------------------- | --------------------------------- | ------------------------------- |
| **Number of Teams**   | 2 (head-to-head)                  | 6-8+ (multi-team)               |
| **Input Data**        | Two rosters (us vs them)          | Unified psych sheet (all teams) |
| **Optimization Goal** | Beat ONE opponent                 | Maximize team score vs field    |
| **Algorithm**         | Nash Equilibrium / Game Theory    | Entry Selection ILP             |
| **Scoring**           | 232 total points distributed      | Variable based on placements    |
| **User Flow**         | Single-step (upload → optimize)   | Multi-step wizard               |
| **Special Rules**     | Exhibition swimmers, back-to-back | Relay 3 penalty, diving slot    |

---

## 🏗️ Proposed Architecture: The Pipeline Pattern

### System Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         UNIFIED DATA INGESTION LAYER                         │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐ │
│  │ CSV Upload  │  │ PDF Parser  │  │ HY3/CL2     │  │ SwimCloud Scraper   │ │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └──────────┬──────────┘ │
│         └────────────────┴────────────────┴────────────────────┘             │
│                                    ▼                                         │
│         ┌────────────────────────────────────────────────────┐               │
│         │           DATA CONTRACTS & NORMALIZATION            │               │
│         │  • Event name normalization  • Time parsing         │               │
│         │  • Swimmer validation       • Grade validation     │               │
│         └─────────────────────────┬──────────────────────────┘               │
└───────────────────────────────────┼──────────────────────────────────────────┘
                                    ▼
         ┌──────────────────────────┴──────────────────────────┐
         │             MEET TYPE DETECTION / ROUTING            │
         │     meet_type: "dual" | "conference" | "state"       │
         └─────────────────────┬───────────────────────────────┘
                               │
          ┌────────────────────┼────────────────────┐
          ▼                    ▼                    ▼
 ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
 │  DUAL MEET      │  │  CONFERENCE     │  │  STATE CHAMP    │
 │  PIPELINE       │  │  CHAMPIONSHIP   │  │  PIPELINE       │
 │                 │  │  PIPELINE       │  │                 │
 │  • 2 teams      │  │  • VCAC rules   │  │  • VISAA rules  │
 │  • Nash/Gurobi  │  │  • R3 penalty   │  │  • Prelims/Finals│
 │  • 232 points   │  │  • Multi-team   │  │  • Multi-team   │
 └────────┬────────┘  └────────┬────────┘  └────────┬────────┘
          │                    │                    │
          ▼                    ▼                    ▼
 ┌─────────────────────────────────────────────────────────────┐
 │              COMMON RESULT FORMATTING & EXPORT               │
 │  • PDF reports  • Excel exports  • API responses            │
 └─────────────────────────────────────────────────────────────┘
```

---

## 📂 Proposed File Structure

```
swim_ai_reflex/backend/
├── api/
│   ├── routers/
│   │   ├── dual_meet.py           # NEW: POST /api/dual-meet/optimize
│   │   ├── championship.py        # NEW: /api/championship/* endpoints
│   │   ├── optimization.py        # DEPRECATE: Keep for backwards compat
│   │   ├── data.py                # KEEP
│   │   ├── export.py              # KEEP
│   │   └── health.py              # KEEP
│   └── models/
│       ├── dual_meet.py           # NEW: DualMeetRequest/Response
│       ├── championship.py        # NEW: ChampionshipRequest/Response
│       └── models.py              # KEEP: Shared models
├── pipelines/                     # NEW DIRECTORY
│   ├── __init__.py
│   ├── base.py                    # Abstract MeetPipeline class
│   ├── dual_meet.py               # DualMeetPipeline
│   └── championship.py            # ChampionshipPipeline
├── services/
│   ├── dual_meet/                 # NEW SUBDIRECTORY
│   │   ├── __init__.py
│   │   ├── nash_optimizer.py      
│   │   ├── gurobi_optimizer.py    
│   │   └── scoring.py             
│   ├── championship/              # NEW SUBDIRECTORY
│   │   ├── __init__.py
│   │   ├── psych_sheet.py         
│   │   ├── point_projection.py    
│   │   ├── entry_optimizer.py     
│   │   └── relay_optimizer.py     
│   └── shared/                    # NEW SUBDIRECTORY
│       ├── __init__.py
│       ├── validation.py          # Unified MeetDataValidator
│       ├── normalization.py       
│       └── cache.py               
└── core/
    ├── rules.py                   # KEEP: All meet rule classes
    └── ...
```

---

## 📡 API Design

### Dual Meet Endpoints

```http
POST /api/dual-meet/optimize
Content-Type: application/json

{
  "our_team": {
    "team_name": "Seton",
    "entries": [
      {"swimmer": "John Smith", "event": "100 Free", "time": 52.34, "grade": 11},
      ...
    ]
  },
  "opponent": {
    "team_name": "Trinity",
    "entries": [...]
  },
  "options": {
    "method": "gurobi",
    "enforce_fatigue": true
  }
}

Response: {
  "our_score": 135,
  "opponent_score": 97,
  "total_points": 232,
  "event_breakdown": [
    {
      "event": "200 Medley Relay",
      "our_points": 10,
      "opponent_points": 5,
      "details": [...]
    },
    ...
  ],
  "lineup": {...},
  "recommendations": [
    "Consider moving Smith to 50 Free for +2 points"
  ]
}
```

### Championship Endpoints

```http
POST /api/championship/load
Content-Type: multipart/form-data

file: <psych_sheet.csv>
meet_profile: "vcac_championship"

Response: {
  "session_id": "abc-123",
  "meet_name": "VCAC Championship 2026",
  "teams": ["Seton", "Trinity", "Oakcrest", ...],
  "entry_count": 997,
  "events": [...]
}
```

```http
GET /api/championship/{session_id}/project?target_team=Seton

Response: {
  "standings": [
    {"rank": 1, "team": "Seton", "projected_points": 1202},
    {"rank": 2, "team": "Trinity", "projected_points": 1087},
    ...
  ],
  "swing_events": [
    {"event": "Girls 50 Free", "swimmer": "Jane Doe", "point_gain": 6},
    ...
  ],
  "event_projections": {...}
}
```

```http
POST /api/championship/{session_id}/optimize-entries

{
  "target_team": "Seton",
  "divers": ["John Doe"],
  "relay_3_swimmers": ["Jane Smith", "Mike Jones"]
}

Response: {
  "assignments": {
    "John Doe": ["Diving"],
    "Jane Smith": ["100 Free"],
    ...
  },
  "total_points": 1215,
  "improvement_over_baseline": 13,
  "constraints_satisfied": true
}
```

```http
POST /api/championship/{session_id}/optimize-relays

{
  "target_team": "Seton",
  "entry_assignments": {...}
}

Response: {
  "relays": {
    "200 Medley Relay A": {
      "legs": ["Back: Smith", "Breast: Jones", "Fly: Williams", "Free: Brown"],
      "predicted_time": "1:45.23",
      "predicted_place": 1,
      "predicted_points": 16
    },
    ...
  },
  "400fr_analysis": {
    "recommendation": "SWIM",
    "relay_points_gained": 16,
    "individual_points_lost": 8,
    "net_benefit": 8
  }
}
```

---

## 🧩 Key Interfaces

### Pipeline Base Class

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Generic, TypeVar

TInput = TypeVar('TInput')
TResult = TypeVar('TResult')

@dataclass
class ValidationResult:
    valid: bool
    errors: list[str]
    warnings: list[str]

class MeetPipeline(ABC, Generic[TInput, TResult]):
    """Base class for all meet type pipelines."""
    
    @abstractmethod
    def validate_input(self, data: TInput) -> ValidationResult:
        """Validate input data against meet rules."""
        pass
    
    @abstractmethod
    def run(self, data: TInput, **options) -> TResult:
        """Execute the main pipeline logic."""
        pass
    
    @abstractmethod
    def format_response(self, result: TResult) -> dict:
        """Format result for API response."""
        pass
```

### Dual Meet Pipeline

```python
@dataclass
class DualMeetInput:
    our_team: TeamRoster
    opponent: TeamRoster
    method: str = "gurobi"
    enforce_fatigue: bool = False

@dataclass
class DualMeetResult:
    our_score: float
    opponent_score: float
    lineup: pd.DataFrame
    event_breakdown: list[dict]
    recommendations: list[str]

class DualMeetPipeline(MeetPipeline[DualMeetInput, DualMeetResult]):
    def validate_input(self, data: DualMeetInput) -> ValidationResult:
        # Validate both rosters have required columns
        # Validate event names are recognized
        # Validate times are parseable
        pass
    
    def run(self, data: DualMeetInput, **options) -> DualMeetResult:
        # 1. Normalize event names
        # 2. Apply constraints (back-to-back, 2-event limit)
        # 3. Run Nash/Gurobi optimization
        # 4. Score the lineup
        # 5. Generate recommendations
        pass
```

### Championship Pipeline

```python
@dataclass
class ChampionshipInput:
    psych_sheet: MeetPsychSheet
    target_team: str
    divers: set[str] = field(default_factory=set)
    relay_3_swimmers: set[str] = field(default_factory=set)

@dataclass  
class ChampionshipResult:
    standings: list[dict]
    entry_assignments: dict[str, list[str]]
    relay_configurations: dict[str, list[dict]]
    total_points: float
    swing_events: list[dict]
    recommendations: list[str]

class ChampionshipPipeline(MeetPipeline[ChampionshipInput, ChampionshipResult]):
    def project_standings(self, psych_sheet: MeetPsychSheet) -> list[dict]:
        """Pure projection - no optimization."""
        pass
    
    def optimize_entries(self, data: ChampionshipInput) -> dict[str, list[str]]:
        """Optimize swimmer-event assignments."""
        # Use Gurobi ILP to maximize points
        # Respect: 2 individual limit, diving counts, relay 3 penalty
        pass
    
    def optimize_relays(
        self, 
        psych_sheet: MeetPsychSheet,
        entry_assignments: dict[str, list[str]]
    ) -> dict:
        """Optimize relay compositions."""
        # Hungarian algorithm for medley
        # Speed-balanced for free relays
        # 400FR trade-off analysis
        pass
```

---

## 🔧 Shared Services

### MeetDataValidator

```python
class MeetDataValidator:
    """Unified validation for all meet types."""
    
    def validate_swimmer_entry(self, entry: dict) -> ValidationResult:
        """Validate a single swimmer entry has required fields."""
        errors = []
        if 'swimmer' not in entry or not entry['swimmer']:
            errors.append("Missing swimmer name")
        if 'event' not in entry:
            errors.append("Missing event")
        if 'time' not in entry:
            errors.append("Missing time")
        return ValidationResult(valid=len(errors) == 0, errors=errors, warnings=[])
    
    def validate_event_names(
        self, 
        entries: list[dict], 
        rules: MeetRules
    ) -> ValidationResult:
        """Validate all event names are recognized."""
        unknown_events = []
        for entry in entries:
            event = normalize_event_name(entry.get('event', ''))
            if event not in rules.event_order:
                unknown_events.append(event)
        # ...
    
    def validate_constraints(
        self,
        swimmer_events: dict[str, list[str]],
        rules: MeetRules
    ) -> ValidationResult:
        """Validate swimmer doesn't exceed event limits."""
        # Check 2-individual limit
        # Check back-to-back constraints
        # Check fatigue implications
        pass
```

---

## 📋 Implementation Plan

### Phase 1: Pipeline Foundation (1 day)
- [ ] Create `pipelines/` directory
- [ ] Implement `base.py` with abstract classes
- [ ] Create stub implementations for dual and championship

### Phase 2: Extract Dual Meet Pipeline (2-3 days)
- [ ] Create `services/dual_meet/` directory
- [ ] Extract Nash optimizer from strategies
- [ ] Extract Gurobi optimizer from strategies
- [ ] Create `DualMeetPipeline` class
- [ ] Create `/api/dual-meet/optimize` endpoint
- [ ] Add deprecation to old `/api/optimize` endpoint
- [ ] Add tests for dual meet pipeline

### Phase 3: Build Championship Pipeline (3-4 days)
- [ ] Create `services/championship/` directory
- [ ] Complete `ChampionshipPipeline` class
- [ ] Integrate existing psych sheet service
- [ ] Integrate point projection service
- [ ] Integrate entry optimizer service
- [ ] Integrate relay optimizer service
- [ ] Create `/api/championship/*` endpoints
- [ ] Add tests for championship pipeline

### Phase 4: Unified Validation (1 day)
- [ ] Create `services/shared/validation.py`
- [ ] Implement `MeetDataValidator`
- [ ] Refactor both pipelines to use validator
- [ ] Add validation tests

### Phase 5: Testing & Documentation (1-2 days)
- [ ] Create `tests/dual_meet/` directory
- [ ] Create `tests/championship/` directory
- [ ] Add E2E integration tests
- [ ] Update API documentation
- [ ] Update KNOWLEDGE_BASE.md

**Total Estimated Effort: 8-11 days**

---

## ✅ Success Criteria

| Criterion                            | Verification Method                                   |
| ------------------------------------ | ----------------------------------------------------- |
| Dual meet works as before            | Run existing test suite, all pass                     |
| Championship completes full workflow | E2E test: upload → project → optimize → export        |
| Clear separation in codebase         | No cross-imports between dual_meet/ and championship/ |
| Test coverage ≥80% per mode          | pytest --cov                                          |
| API backwards compatible             | Old endpoint still works with deprecation warning     |

---

## 🐛 Known Risks

| Risk                                      | Mitigation                                     |
| ----------------------------------------- | ---------------------------------------------- |
| Breaking existing dual meet functionality | Keep old endpoint, thorough regression testing |
| Championship optimization too slow        | Profile Gurobi solve time, add time limits     |
| Frontend not ready for separate flows     | Can launch backend first, frontend follows     |
| Data format inconsistencies               | Unified validation layer catches early         |

---

## 📚 References

- [KNOWLEDGE_BASE.md](./KNOWLEDGE_BASE.md) - Domain rules
- [CHAMPIONSHIP_MODULE_ROADMAP.md](./CHAMPIONSHIP_MODULE_ROADMAP.md) - Original module plan
- [E2E_DATAFLOW_FIXES_SUMMARY.md](./E2E_DATAFLOW_FIXES_SUMMARY.md) - Recent fixes

---

_Last Updated: January 16, 2026_  
_PRISM Analysis Version: 1.0_
