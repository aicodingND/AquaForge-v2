# AquaForge Championship Module - Strategic Implementation Roadmap

**Document:** Technical Implementation Plan  
**Target Event:** VCAC Championship (Feb 7, 2026)  
**Created:** January 15, 2026  
**Version:** 1.0

---

## 📋 Executive Summary

This roadmap outlines four integrated modules to extend AquaForge from dual-meet optimization to multi-team championship events. Each module builds on the previous, creating a comprehensive championship toolkit.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    AQUAFORGE CHAMPIONSHIP MODULE                        │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│   ┌─────────────┐     ┌─────────────┐     ┌─────────────┐              │
│   │   MODULE 1  │ ──► │   MODULE 2  │ ──► │   MODULE 3  │              │
│   │   Psych     │     │   Point     │     │   Entry     │              │
│   │   Sheet     │     │   Projection│     │   Selection │              │
│   │   Parser    │     │   Engine    │     │   Optimizer │              │
│   └─────────────┘     └─────────────┘     └──────┬──────┘              │
│                                                   │                     │
│                       ┌─────────────┐             │                     │
│                       │   MODULE 4  │ ◄───────────┘                     │
│                       │   Relay     │                                   │
│                       │   Optimizer │                                   │
│                       └─────────────┘                                   │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 🔧 Module 1: Psych Sheet Parser

### Purpose

Parse psych sheet PDFs/CSVs into structured data for all teams.

### Data Model

```python
@dataclass
class PsychSheetEntry:
    """Single swimmer-event entry from psych sheet."""
    swimmer_name: str
    team: str
    event: str
    seed_time: float  # in seconds (e.g., 25.43)
    seed_rank: int    # overall rank in this event
    is_diving: bool
    dive_score: Optional[float]


@dataclass
class MeetPsychSheet:
    """Complete psych sheet for a meet."""
    meet_name: str
    meet_date: date
    teams: List[str]
    entries: List[PsychSheetEntry]

    def get_event_entries(self, event: str) -> List[PsychSheetEntry]:
        """Get all entries for a specific event, sorted by seed time."""
        return sorted(
            [e for e in self.entries if e.event == event],
            key=lambda x: x.seed_time
        )

    def get_team_entries(self, team: str) -> List[PsychSheetEntry]:
        """Get all entries for a specific team."""
        return [e for e in self.entries if e.team == team]
```

### Input Formats to Support

| Format            | Source                        | Priority  |
| ----------------- | ----------------------------- | --------- |
| **CSV**           | Manual export from Hy-Tek     | 🔴 High   |
| **PDF**           | Official psych sheet          | 🟠 Medium |
| **SDIF**          | USA Swimming data interchange | 🟡 Future |
| **SwimCloud API** | Online database               | 🟡 Future |

### Implementation Plan

```python
# File: swim_ai_reflex/backend/services/psych_sheet_service.py

class PsychSheetParser:
    """Parse psych sheets from various formats."""

    def parse_csv(self, file_path: str) -> MeetPsychSheet:
        """
        Parse CSV format psych sheet.

        Expected columns:
        - Event, Swimmer, Team, SeedTime, Age, Grade
        """
        df = pd.read_csv(file_path)
        entries = []

        for _, row in df.iterrows():
            entries.append(PsychSheetEntry(
                swimmer_name=row['Swimmer'],
                team=row['Team'],
                event=row['Event'],
                seed_time=self._parse_time(row['SeedTime']),
                seed_rank=0,  # Will be calculated
                is_diving='diving' in row['Event'].lower(),
                dive_score=row.get('DiveScore')
            ))

        # Calculate ranks per event
        psych = MeetPsychSheet(
            meet_name=df.attrs.get('meet_name', 'Unknown'),
            meet_date=date.today(),
            teams=list(df['Team'].unique()),
            entries=entries
        )
        self._calculate_ranks(psych)
        return psych

    def parse_pdf(self, file_path: str) -> MeetPsychSheet:
        """Parse PDF psych sheet using OCR + pattern matching."""
        # Use pdfplumber or PyPDF2 for text extraction
        # Pattern match for: "1. Smith, John    Seton    25.43"
        pass

    def _parse_time(self, time_str: str) -> float:
        """Convert time string to seconds. Handles MM:SS.ss and SS.ss formats."""
        if pd.isna(time_str) or time_str == 'NT':
            return float('inf')  # No Time

        time_str = str(time_str).strip()
        if ':' in time_str:
            parts = time_str.split(':')
            return float(parts[0]) * 60 + float(parts[1])
        return float(time_str)
```

### Deliverables

- [ ] `PsychSheetEntry` and `MeetPsychSheet` data models
- [ ] CSV parser with column mapping
- [ ] Time string parser (handles MM:SS.ss, SS.ss, NT)
- [ ] PDF parser (text extraction + regex patterns)
- [ ] API endpoint: `POST /api/psych-sheet/upload`
- [ ] Frontend component: Psych sheet upload + preview

### Estimated Effort: 2-3 days

---

## 🎯 Module 2: Point Projection Engine

### Purpose

Given psych sheet data, calculate expected points for each swimmer/team.

### Core Algorithm

```
For each event:
  1. Get all entries sorted by seed time
  2. Predict final placement (seed order for timed finals)
  3. Apply scoring rules: VCAC = [32, 26, 24, 22, 20, 18, 14, 10, 8, 6, 4, 2]
  4. Apply team constraints: max 4 scorers per team per event
  5. Calculate expected points per swimmer
```

### Implementation

```python
# File: swim_ai_reflex/backend/services/point_projection_service.py

from swim_ai_reflex.backend.core.rules import get_meet_profile

class PointProjectionEngine:
    """Calculate expected points from psych sheet data."""

    def __init__(self, meet_profile: str = "vcac_championship"):
        self.rules = get_meet_profile(meet_profile)

    def project_event_points(
        self,
        psych: MeetPsychSheet,
        event: str
    ) -> Dict[str, List[Dict]]:
        """
        Project points for a single event.

        Returns: {
            'Seton': [
                {'swimmer': 'John Smith', 'predicted_place': 2, 'points': 26},
                {'swimmer': 'Mike Jones', 'predicted_place': 5, 'points': 20},
            ],
            'Trinity': [...],
            ...
        }
        """
        entries = psych.get_event_entries(event)
        is_relay = 'relay' in event.lower()
        points_table = self.rules.relay_points if is_relay else self.rules.individual_points
        max_scorers = self.rules.max_scorers_per_team_relay if is_relay else self.rules.max_scorers_per_team_individual

        results = defaultdict(list)
        team_scorer_count = defaultdict(int)

        for place, entry in enumerate(entries, 1):
            team = normalize_team_name(entry.team)

            # Check if team can still score
            if team_scorer_count[team] < max_scorers:
                points = points_table[place - 1] if place <= len(points_table) else 0
                team_scorer_count[team] += 1
            else:
                points = 0  # Exhibition (exceeds scorer limit)

            results[team].append({
                'swimmer': entry.swimmer_name,
                'seed_time': entry.seed_time,
                'predicted_place': place,
                'points': points,
                'scoring': points > 0
            })

        return dict(results)

    def project_full_meet(
        self,
        psych: MeetPsychSheet,
        target_team: str = "Seton"
    ) -> Dict:
        """
        Project points for entire meet.

        Returns comprehensive projection with:
        - Total points per team
        - Points breakdown by event
        - Swing events (where small improvements = big gains)
        """
        event_projections = {}
        team_totals = defaultdict(float)

        # Get all unique events
        events = list(set(e.event for e in psych.entries))

        for event in events:
            proj = self.project_event_points(psych, event)
            event_projections[event] = proj

            # Accumulate team totals
            for team, swimmers in proj.items():
                team_totals[team] += sum(s['points'] for s in swimmers)

        # Identify swing events for target team
        swing_events = self._identify_swing_events(
            event_projections, target_team
        )

        return {
            'team_totals': dict(team_totals),
            'target_team_total': team_totals.get(normalize_team_name(target_team), 0),
            'event_projections': event_projections,
            'swing_events': swing_events,
            'standings': sorted(team_totals.items(), key=lambda x: -x[1])
        }

    def _identify_swing_events(
        self,
        projections: Dict,
        target_team: str
    ) -> List[Dict]:
        """
        Find events where small time improvements = significant point gains.

        A "swing event" is where:
        - Target team swimmer is close to a better placement
        - Moving up 1-2 places gains 4+ points
        """
        swing_events = []
        target = normalize_team_name(target_team)

        for event, teams in projections.items():
            if target not in teams:
                continue

            for swimmer in teams[target]:
                place = swimmer['predicted_place']
                current_points = swimmer['points']

                # Check if moving up 1 place gains significant points
                if place > 1:
                    better_place = place - 1
                    # Calculate points at better place (simplified)
                    points_table = self.rules.individual_points
                    potential_points = points_table[better_place - 1] if better_place <= len(points_table) else 0
                    point_gain = potential_points - current_points

                    if point_gain >= 4:  # Significant gain
                        swing_events.append({
                            'event': event,
                            'swimmer': swimmer['swimmer'],
                            'current_place': place,
                            'target_place': better_place,
                            'current_points': current_points,
                            'potential_points': potential_points,
                            'point_gain': point_gain
                        })

        # Sort by potential point gain (descending)
        return sorted(swing_events, key=lambda x: -x['point_gain'])
```

### Output Example

```json
{
  "team_totals": {
    "seton": 512,
    "trinity": 487,
    "oakcrest": 423,
    "fredericksburg": 312,
    "immanuel": 298,
    "jpii": 267
  },
  "target_team_total": 512,
  "standings": [
    ["seton", 512],
    ["trinity", 487],
    ["oakcrest", 423]
  ],
  "swing_events": [
    {
      "event": "Boys 50 Free",
      "swimmer": "Mike Johnson",
      "current_place": 4,
      "target_place": 3,
      "current_points": 22,
      "potential_points": 24,
      "point_gain": 6
    }
  ]
}
```

### Deliverables

- [ ] `PointProjectionEngine` class
- [ ] Event-level point projection
- [ ] Full meet projection with standings
- [ ] Swing event identification
- [ ] API endpoint: `GET /api/projection/{meet_id}`
- [ ] Frontend: Point projection dashboard

### Estimated Effort: 2-3 days

---

## 🏊 Module 3: Entry Selection Optimizer

### Purpose

Determine optimal event assignments for each swimmer to maximize team points.

### Problem Formulation

This is a **Generalized Assignment Problem (GAP)** with additional constraints.

```
MAXIMIZE: Σ (expected_points[swimmer, event] × assigned[swimmer, event])

SUBJECT TO:
  - Each swimmer assigned ≤ 2 individual events
  - Each swimmer assigned ≤ 3 relays (or constraint with penalty)
  - Diving counts as 1 individual event
  - Relay 3 counts as 1 individual event (VCAC rule)
  - Each event has ≤ 4 scoring Seton swimmers
```

### Algorithm Options

| Algorithm                            | Pros                                  | Cons                           | Recommendation  |
| ------------------------------------ | ------------------------------------- | ------------------------------ | --------------- |
| **Integer Linear Programming (ILP)** | Optimal solution, handles constraints | May be slow for large problems | ✅ Primary      |
| **Greedy Heuristic**                 | Fast, simple                          | May miss optimal               | ✅ Fallback     |
| **Genetic Algorithm**                | Good for complex constraints          | Non-deterministic              | 🟡 Future       |
| **Hungarian Algorithm**              | Classic assignment                    | Doesn't handle all constraints | ❌ Not suitable |

### Implementation: ILP Approach

```python
# File: swim_ai_reflex/backend/services/entry_optimizer_service.py

from scipy.optimize import milp, LinearConstraint, Bounds
import numpy as np

class EntrySelectionOptimizer:
    """
    Optimize swimmer event assignments for maximum team points.
    Uses Mixed Integer Linear Programming (MILP).
    """

    def __init__(self, meet_profile: str = "vcac_championship"):
        self.rules = get_meet_profile(meet_profile)
        self.projection_engine = PointProjectionEngine(meet_profile)

    def optimize(
        self,
        psych: MeetPsychSheet,
        team: str = "Seton"
    ) -> Dict:
        """
        Find optimal event assignments for team swimmers.

        Returns: {
            'assignments': {
                'John Smith': ['200 Free', '100 Free'],
                'Mike Jones': ['100 Fly'],
                ...
            },
            'total_points': 512,
            'improvement_over_current': 23
        }
        """
        # Get team swimmers and available events
        team_entries = psych.get_team_entries(team)
        swimmers = list(set(e.swimmer_name for e in team_entries))
        events = list(set(e.event for e in team_entries if 'relay' not in e.event.lower()))

        n_swimmers = len(swimmers)
        n_events = len(events)

        # Decision variables: x[i,j] = 1 if swimmer i assigned to event j
        # Flatten to 1D: index = i * n_events + j
        n_vars = n_swimmers * n_events

        # Objective: maximize expected points
        # c[i,j] = expected points if swimmer i does event j
        c = np.zeros(n_vars)
        for i, swimmer in enumerate(swimmers):
            for j, event in enumerate(events):
                c[i * n_events + j] = self._get_expected_points(
                    psych, swimmer, event, team
                )

        # We want to MAXIMIZE, but milp MINIMIZES, so negate
        c = -c

        # Constraints
        constraints = []

        # 1. Each swimmer does at most 2 individual events
        for i in range(n_swimmers):
            # Sum of x[i, :] <= 2
            A_row = np.zeros(n_vars)
            A_row[i * n_events:(i + 1) * n_events] = 1
            constraints.append(LinearConstraint(A_row.reshape(1, -1), -np.inf, 2))

        # 2. Each event has at most 4 Seton scorers
        # (This is a soft constraint - extras just don't score)
        # For true optimization, we could limit entries, but
        # actually we want unlimited entries, just cap scoring
        # So this constraint is not needed for entry selection

        # Variable bounds: binary (0 or 1)
        bounds = Bounds(lb=0, ub=1)
        integrality = np.ones(n_vars)  # All variables are integers

        # Solve
        result = milp(
            c=c,
            constraints=constraints,
            bounds=bounds,
            integrality=integrality
        )

        if result.success:
            # Parse solution
            assignments = defaultdict(list)
            x = result.x.round()  # Binary solution

            for i, swimmer in enumerate(swimmers):
                for j, event in enumerate(events):
                    if x[i * n_events + j] > 0.5:
                        assignments[swimmer].append(event)

            return {
                'assignments': dict(assignments),
                'total_points': -result.fun,  # Negate back
                'status': 'optimal'
            }
        else:
            return {
                'assignments': {},
                'total_points': 0,
                'status': 'failed',
                'message': result.message
            }

    def _get_expected_points(
        self,
        psych: MeetPsychSheet,
        swimmer: str,
        event: str,
        team: str
    ) -> float:
        """Calculate expected points for swimmer in event."""
        # Get swimmer's seed time for this event
        entries = psych.get_event_entries(event)

        swimmer_entry = None
        for e in entries:
            if e.swimmer_name == swimmer and e.team == team:
                swimmer_entry = e
                break

        if not swimmer_entry:
            return 0  # Swimmer not entered in this event

        # Predict placement
        place = swimmer_entry.seed_rank

        # Get points for this placement
        points_table = self.rules.individual_points
        if place <= len(points_table):
            return points_table[place - 1]
        return 0


class GreedyEntryOptimizer:
    """
    Fast greedy heuristic for entry selection.
    Use when ILP is too slow or for quick estimates.
    """

    def optimize(self, psych: MeetPsychSheet, team: str = "Seton") -> Dict:
        """
        Greedy algorithm:
        1. Calculate points per event for each swimmer
        2. Sort by marginal value (points / event slot used)
        3. Greedily assign highest value first
        4. Respect constraints
        """
        team_entries = psych.get_team_entries(team)

        # Calculate value of each (swimmer, event) pair
        swimmer_event_values = []
        for entry in team_entries:
            if 'relay' in entry.event.lower():
                continue

            value = self._calculate_value(entry, psych)
            swimmer_event_values.append({
                'swimmer': entry.swimmer_name,
                'event': entry.event,
                'value': value
            })

        # Sort by value descending
        swimmer_event_values.sort(key=lambda x: -x['value'])

        # Greedy assignment
        assignments = defaultdict(list)
        swimmer_events_used = defaultdict(int)

        for item in swimmer_event_values:
            swimmer = item['swimmer']
            event = item['event']

            # Check constraint: max 2 individual events
            if swimmer_events_used[swimmer] < 2:
                assignments[swimmer].append(event)
                swimmer_events_used[swimmer] += 1

        # Calculate total points
        total_points = sum(
            item['value'] for item in swimmer_event_values
            if item['event'] in assignments.get(item['swimmer'], [])
        )

        return {
            'assignments': dict(assignments),
            'total_points': total_points,
            'status': 'heuristic'
        }
```

### Deliverables

- [ ] `EntrySelectionOptimizer` with ILP solver
- [ ] `GreedyEntryOptimizer` as fast fallback
- [ ] Diver constraint handling (diving = 1 individual)
- [ ] Relay 3 constraint handling (costs individual slot)
- [ ] API endpoint: `POST /api/optimize/entries`
- [ ] Frontend: Entry assignment UI with drag-drop

### Estimated Effort: 3-5 days

---

## 🔄 Module 4: Relay Configuration Optimizer

### Purpose

Optimize A and B relay compositions for maximum points.

### VCAC Relay Specifics

| Relay            | Type      | Legs                       |
| ---------------- | --------- | -------------------------- |
| 200 Medley Relay | Medley    | Back → Breast → Fly → Free |
| 200 Free Relay   | Freestyle | Free × 4                   |
| 400 Free Relay   | Freestyle | Free × 4                   |

**Key constraints:**

- Both A and B relays score
- Relay 3 (400 Free) counts as individual event
- Swimmer can only swim each relay once

### Algorithm: Two-Stage Optimization

```
STAGE 1: Determine who SHOULD swim relays
  - Consider individual event commitments
  - Check for relay 3 penalty
  - Identify "relay-only" swimmers (weak in individual)

STAGE 2: Optimize leg assignments within each relay
  - Medley: Assign by specialty (back, breast, fly, free)
  - Free: Balance speed across legs
```

### Implementation

```python
# File: swim_ai_reflex/backend/services/relay_optimizer_service.py

@dataclass
class RelayLeg:
    swimmer: str
    stroke: str  # 'back', 'breast', 'fly', 'free'
    split_time: float


@dataclass
class RelayConfiguration:
    relay_name: str  # '200 Medley Relay', '200 Free Relay', '400 Free Relay'
    team_designation: str  # 'A' or 'B'
    legs: List[RelayLeg]
    predicted_time: float
    predicted_place: int
    predicted_points: int


class RelayOptimizer:
    """Optimize relay configurations for maximum team points."""

    def __init__(self, meet_profile: str = "vcac_championship"):
        self.rules = get_meet_profile(meet_profile)

    def optimize_relays(
        self,
        psych: MeetPsychSheet,
        individual_assignments: Dict[str, List[str]],
        team: str = "Seton"
    ) -> Dict[str, List[RelayConfiguration]]:
        """
        Optimize all relay configurations.

        Args:
            psych: Psych sheet with all times
            individual_assignments: {swimmer: [event1, event2]} from entry optimizer
            team: Target team name

        Returns: {
            '200 Medley Relay': [A_config, B_config],
            '200 Free Relay': [A_config, B_config],
            '400 Free Relay': [A_config, B_config] or None if skipping
        }
        """
        results = {}

        # Get all team swimmers and their times
        team_swimmers = self._get_swimmer_times(psych, team)

        # Track who can swim relays (considering individual commitments)
        available_for_relay = self._get_relay_availability(
            team_swimmers, individual_assignments
        )

        # Optimize each relay
        results['200 Medley Relay'] = self._optimize_medley_relay(
            team_swimmers, available_for_relay, psych, '200 Medley Relay'
        )

        results['200 Free Relay'] = self._optimize_free_relay(
            team_swimmers, available_for_relay, psych, '200 Free Relay', 50
        )

        # 400 Free Relay - check if it's worth it (costs individual slots!)
        results['400 Free Relay'] = self._optimize_400_free_with_penalty(
            team_swimmers, available_for_relay, individual_assignments, psych
        )

        return results

    def _optimize_medley_relay(
        self,
        swimmers: Dict[str, Dict[str, float]],  # {swimmer: {stroke: time}}
        available: Set[str],
        psych: MeetPsychSheet,
        relay_name: str
    ) -> List[RelayConfiguration]:
        """
        Optimize medley relay using Hungarian algorithm.

        Strokes: Back → Breast → Fly → Free
        Objective: Minimize total relay time
        """
        strokes = ['100 Back', '100 Breast', '100 Fly', '100 Free']
        available_list = list(available)

        # Build cost matrix: cost[swimmer][stroke] = time
        n = len(available_list)
        cost_matrix = np.full((n, 4), np.inf)

        for i, swimmer in enumerate(available_list):
            for j, stroke in enumerate(strokes):
                if swimmer in swimmers and stroke in swimmers[swimmer]:
                    cost_matrix[i, j] = swimmers[swimmer][stroke]

        # Use Hungarian algorithm for A relay (best 4)
        from scipy.optimize import linear_sum_assignment
        row_ind, col_ind = linear_sum_assignment(cost_matrix)

        # Build A relay
        a_legs = []
        a_swimmers_used = set()
        for i, j in zip(row_ind, col_ind):
            if cost_matrix[i, j] < np.inf and len(a_legs) < 4:
                a_legs.append(RelayLeg(
                    swimmer=available_list[i],
                    stroke=strokes[j].split()[1].lower(),  # 'back', 'breast', etc.
                    split_time=cost_matrix[i, j]
                ))
                a_swimmers_used.add(available_list[i])

        a_time = sum(leg.split_time for leg in a_legs)
        a_place, a_points = self._predict_relay_placement(psych, relay_name, a_time)

        a_config = RelayConfiguration(
            relay_name=relay_name,
            team_designation='A',
            legs=a_legs,
            predicted_time=a_time,
            predicted_place=a_place,
            predicted_points=a_points
        )

        # Build B relay with remaining swimmers
        remaining = [s for s in available_list if s not in a_swimmers_used]
        b_config = self._build_b_relay(remaining, swimmers, strokes, relay_name, psych)

        return [a_config, b_config]

    def _optimize_400_free_with_penalty(
        self,
        swimmers: Dict,
        available: Set[str],
        individual_assignments: Dict[str, List[str]],
        psych: MeetPsychSheet
    ) -> List[RelayConfiguration]:
        """
        Decide whether to swim 400 Free Relay.

        VCAC Rule: Relay 3 counts as individual event slot!

        Trade-off:
        - 400 relay might score 16 pts (1st) to 1 pt (12th)
        - But swimmers on it lose an individual slot
        - May be worth skipping if swimmers need individual events
        """
        # Calculate value of swimming 400 relay
        best_400_config = self._optimize_free_relay(
            swimmers, available, psych, '400 Free Relay', 100
        )

        relay_points = best_400_config[0].predicted_points + best_400_config[1].predicted_points

        # Calculate opportunity cost
        # For each swimmer on relay, what individual points would they forfeit?
        opportunity_cost = 0
        for leg in best_400_config[0].legs + best_400_config[1].legs:
            swimmer = leg.swimmer
            current_events = individual_assignments.get(swimmer, [])

            # If swimmer already has 2 events, they'd have to drop one
            if len(current_events) >= 2:
                # Find their lowest-value event
                min_value = min(
                    self._get_event_value(psych, swimmer, e)
                    for e in current_events
                )
                opportunity_cost += min_value

        # Decision: swim 400 relay if net positive
        net_value = relay_points - opportunity_cost

        if net_value < 0:
            # Skip 400 relay - not worth it
            return None

        return best_400_config
```

### Relay Strategy Matrix

| Situation                                     | Recommendation                             |
| --------------------------------------------- | ------------------------------------------ |
| Star swimmer has 2 strong individual events   | Skip 400 relay or use on A relay only      |
| Swimmer mediocre in individual, fast in relay | Use on all 3 relays                        |
| Diver who can swim                            | 0-1 relays (diving + swim = 2 indiv slots) |
| Deep team with many swimmers                  | Stack A relay, competitive B relay         |
| Weak team, few swimmers                       | May need to skip B relays                  |

### Deliverables

- [ ] `RelayOptimizer` class
- [ ] Medley relay optimization (Hungarian algorithm)
- [ ] Free relay optimization
- [ ] 400 Free Relay trade-off analysis
- [ ] Integration with entry optimizer
- [ ] API endpoint: `POST /api/optimize/relays`
- [ ] Frontend: Relay configuration tool

### Estimated Effort: 3-4 days

---

## 📅 Implementation Timeline

```
Week 1 (Jan 20-24, 2026):
├── Module 1: Psych Sheet Parser [2-3 days]
│   ├── Day 1: Data models, CSV parser
│   ├── Day 2: PDF parser, API endpoint
│   └── Day 3: Frontend upload component
│
└── Module 2: Point Projection [2-3 days]
    ├── Day 3-4: Projection engine
    └── Day 5: Swing event identification, API

Week 2 (Jan 27-31, 2026):
├── Module 3: Entry Optimizer [3-5 days]
│   ├── Day 1-2: ILP formulation
│   ├── Day 3: Greedy fallback
│   └── Day 4-5: VCAC constraints, testing
│
└── Module 4: Relay Optimizer [2-3 days]
    ├── Day 4-5: Medley/Free optimization
    └── Day 6: 400 relay trade-off

Week 3 (Feb 3-7, 2026):
├── Integration Testing [2 days]
├── Frontend Polish [1-2 days]
└── VCAC Championship [Feb 7] 🏆
```

---

## 🚀 Quick Wins (Can Do Now)

Even before full implementation, we can use:

1. **VCACChampRules** ✅ - Already implemented
2. **is_valid_entry()** ✅ - Constraint validation ready
3. **Manual psych sheet analysis** - Export to spreadsheet
4. **Point projection by hand** - Use scoring tables

---

## 📚 References

1. [Linear Programming for Swim Meet Optimization](https://umich.edu) - Classic paper on swimmer assignment
2. [Hungarian Algorithm for Medley Relays](https://sciencedirect.com) - Optimal stroke assignment
3. [USA Swimming SDIF Format](https://usaswimming.org) - Data interchange standard
4. [Hy-Tek Meet Manager](https://hytek.active.com) - Standard meet management software

---

_Document generated by AquaForge AI Development Team_
_January 15, 2026_
