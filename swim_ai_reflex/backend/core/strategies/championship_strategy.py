"""
Championship Gurobi Strategy

Extends the dual-meet Gurobi optimizer for multi-team championship meets.

Key differences from dual meets:
- Scoring against ALL teams, not just one opponent
- VCAC scoring: [32, 26, 24, 22, 20, 18, 14, 10, 8, 6, 4, 2] (places 1-12)
- Max 4 scorers per team per event
- Relay 3 (400 Free) counts as individual event
- Diving counts as 1 individual
"""

import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set

from swim_ai_reflex.backend.core.rules import get_meet_profile
from swim_ai_reflex.backend.services.constraint_validator import (
    get_blocked_events,
    normalize_event_name,
)


@dataclass
class ChampionshipEntry:
    """Single swimmer-event entry."""

    swimmer_name: str
    team: str
    event: str
    seed_time: float
    gender: str = ""
    grade: Optional[str] = None
    source: str = "unknown"


@dataclass
class ChampionshipOptimizationResult:
    """Result of championship entry optimization."""

    assignments: Dict[str, List[str]]  # {swimmer: [events]}
    total_points: float
    baseline_points: float
    improvement: float
    solve_time_ms: float
    status: str
    event_breakdown: Dict[str, float] = field(default_factory=dict)
    recommendations: List[str] = field(default_factory=list)


class ChampionshipGurobiStrategy:
    """
    Gurobi-based optimization for championship meets.

    Extends dual-meet logic to handle:
    - Multiple competing teams
    - Championship scoring tables
    - 400FR individual slot penalty
    - Diver integration
    """

    def __init__(self, meet_profile: str = "vcac_championship"):
        self.rules = get_meet_profile(meet_profile)
        self.points_table = self.rules.individual_points
        self.relay_points = self.rules.relay_points
        self.max_scorers = self.rules.max_scorers_per_team_individual

    def optimize_entries(
        self,
        all_entries: List[ChampionshipEntry],
        target_team: str,
        divers: Optional[Set[str]] = None,
        relay_1_swimmers: Optional[Set[str]] = None,  # 200 Medley
        relay_2_swimmers: Optional[Set[str]] = None,  # 200 Free
        relay_3_swimmers: Optional[Set[str]] = None,  # 400 Free
        time_limit: int = 60,
    ) -> ChampionshipOptimizationResult:
        """
        Optimize individual event entries for target team.

        Args:
            all_entries: All entries from unified psych sheet
            target_team: Team to optimize (e.g., "SST")
            divers: Set of swimmer names who are divers (counts as 1 individual)
            relay_1_swimmers: Set of swimmers on 200 Medley Relay
            relay_2_swimmers: Set of swimmers on 200 Free Relay
            relay_3_swimmers: Set of swimmers on 400 Free Relay (VCAC: costs 1 individual)
            time_limit: Gurobi solve time limit in seconds

        Returns:
            ChampionshipOptimizationResult with optimal assignments
        """
        import time

        start_time = time.time()

        divers = divers or set()
        relay_1_swimmers = relay_1_swimmers or set()
        relay_2_swimmers = relay_2_swimmers or set()
        relay_3_swimmers = relay_3_swimmers or set()

        try:
            # Setup Gurobi license
            self._setup_gurobi_license()
            import gurobipy as gp
            from gurobipy import GRB
        except ImportError:
            raise ImportError("Gurobi not installed. Please install gurobipy.")

        # Filter to individual events only
        individual_entries = [
            e
            for e in all_entries
            if "relay" not in e.event.lower() and "diving" not in e.event.lower()
        ]

        # Get target team entries
        team_entries = [
            e for e in individual_entries if e.team.upper() == target_team.upper()
        ]

        if not team_entries:
            return ChampionshipOptimizationResult(
                assignments={},
                total_points=0,
                baseline_points=0,
                improvement=0,
                solve_time_ms=0,
                status="failed",
                recommendations=["No entries found for target team"],
            )

        # Extract unique swimmers and events for target team
        swimmers = sorted(set(e.swimmer_name for e in team_entries))
        events = sorted(set(e.event for e in individual_entries))

        # Build lookup: (swimmer, event) -> entry
        swimmer_event_lookup: Dict[tuple, ChampionshipEntry] = {}
        for e in team_entries:
            swimmer_event_lookup[(e.swimmer_name, e.event)] = e

        # Calculate expected points for each (swimmer, event) pair
        point_matrix = self._build_point_matrix(
            individual_entries, swimmers, events, target_team
        )

        # Create Gurobi model
        m = gp.Model("ChampionshipOptimization")
        m.setParam("OutputFlag", 0)
        m.setParam("TimeLimit", time_limit)

        # Decision variables: x[swimmer, event] = 1 if swimmer swims event
        x = m.addVars(swimmers, events, vtype=GRB.BINARY, name="x")

        # CONSTRAINTS

        # 1. Can only assign swimmer to event if they have a seed time
        for s in swimmers:
            for e in events:
                if (s, e) not in swimmer_event_lookup:
                    m.addConstr(x[s, e] == 0, name=f"no_time_{s}_{e}")

        # 2. Max individual events per swimmer (VCAC: 2)
        # Adjusted for divers and relay-3 swimmers
        for s in swimmers:
            # Base limit is 2 individual events
            limit = 2

            # Divers get 1 fewer slot
            if s in divers:
                limit -= 1

            # 400 Free Relay swimmers get 1 fewer slot (VCAC rule)
            if s in relay_3_swimmers:
                limit -= 1

            limit = max(0, limit)  # Can't go negative

            m.addConstr(
                gp.quicksum(x[s, e] for e in events) <= limit, name=f"max_indiv_{s}"
            )

        # 3. No back-to-back events (STANDARD RULE - including relay leg blocking)
        # Use normalized event names for comparison

        # 3a. Individual <-> Individual blocking
        for s in swimmers:
            swimmer_events = [e for e in events if (s, e) in swimmer_event_lookup]

            for event1 in swimmer_events:
                # Get blocked events for this event
                blocked = get_blocked_events(event1)

                for event2 in swimmer_events:
                    if event1 == event2:
                        continue

                    # Normalize both event names (strips gender prefixes)
                    norm_event2 = normalize_event_name(event2)

                    if norm_event2 in blocked:
                        m.addConstr(
                            x[s, event1] + x[s, event2] <= 1,
                            name=f"no_b2b_{s}_{event1[:10]}_{event2[:10]}",
                        )

        # 3b. Individual <-> Relay blocking
        # Map relays to their event names
        relay_map = {
            "200 Medley Relay": relay_1_swimmers,
            "200 Free Relay": relay_2_swimmers,
            "400 Free Relay": relay_3_swimmers,
        }

        for relay_name, relay_participants in relay_map.items():
            # Get blocked events if one swims THIS relay (what comes AFTER relay)
            blocked_after = get_blocked_events(relay_name)

            # Find events that would BLOCK this relay (what comes BEFORE relay)
            # This is inverse lookup - easier to just check all events

            for s in swimmers:
                if s not in relay_participants:
                    continue

                swimmer_events = [e for e in events if (s, e) in swimmer_event_lookup]

                for ind_event in swimmer_events:
                    norm_ind = normalize_event_name(ind_event)

                    # CASE 1: Individual Event BLOCKS Relay (Ind -> Relay)
                    # e.g. 50 Free immediately before diving (not applicable to relays generally)
                    # or 100 Breast before 400 Free Relay
                    if relay_name in get_blocked_events(norm_ind):
                        m.addConstr(
                            x[s, ind_event] == 0,
                            name=f"block_pre_relay_{s}_{ind_event}",
                        )

                    # CASE 2: Relay BLOCKS Individual Event (Relay -> Ind)
                    # e.g. 200 Medley Relay blocks 200 Free
                    if norm_ind in blocked_after:
                        m.addConstr(
                            x[s, ind_event] == 0,
                            name=f"block_post_relay_{s}_{ind_event}",
                        )

        # OBJECTIVE: Maximize expected points
        m.setObjective(
            gp.quicksum(
                point_matrix.get((s, e), 0) * x[s, e] for s in swimmers for e in events
            ),
            GRB.MAXIMIZE,
        )

        # Solve
        m.optimize()

        solve_time_ms = (time.time() - start_time) * 1000

        if m.Status == GRB.OPTIMAL or m.Status == GRB.TIME_LIMIT:
            # Extract solution
            assignments: Dict[str, List[str]] = {}
            event_breakdown: Dict[str, float] = {}

            for s in swimmers:
                assigned_events = []
                for e in events:
                    if x[s, e].X > 0.5:
                        assigned_events.append(e)
                        event_breakdown[e] = event_breakdown.get(
                            e, 0
                        ) + point_matrix.get((s, e), 0)

                if assigned_events:
                    assignments[s] = assigned_events

            total_points = -m.ObjVal if m.ObjVal else 0
            total_points = abs(total_points) if total_points < 0 else m.ObjVal

            # Calculate baseline (what we'd get with default top-2 by seed)
            baseline = self._calculate_baseline_points(
                team_entries, individual_entries, target_team
            )

            return ChampionshipOptimizationResult(
                assignments=assignments,
                total_points=total_points,
                baseline_points=baseline,
                improvement=total_points - baseline,
                solve_time_ms=solve_time_ms,
                status="optimal" if m.Status == GRB.OPTIMAL else "time_limit",
                event_breakdown=event_breakdown,
                recommendations=self._generate_recommendations(
                    assignments, divers, relay_3_swimmers
                ),
            )
        else:
            return ChampionshipOptimizationResult(
                assignments={},
                total_points=0,
                baseline_points=0,
                improvement=0,
                solve_time_ms=solve_time_ms,
                status="failed",
                recommendations=[f"Gurobi failed with status {m.Status}"],
            )

    def _setup_gurobi_license(self):
        """Configure Gurobi license from env vars or file."""
        if not os.environ.get("WLSACCESSID"):
            base_dir = os.getcwd()
            possible_paths = [
                os.path.join(base_dir, "gurobi.lic"),
                os.path.join(base_dir, "swim_ai_reflex", "gurobi.lic"),
                "/app/gurobi.lic",
            ]
            for path in possible_paths:
                if os.path.exists(path):
                    os.environ["GRB_LICENSE_FILE"] = path
                    break

    def _build_point_matrix(
        self,
        all_entries: List[ChampionshipEntry],
        swimmers: List[str],
        events: List[str],
        target_team: str,
    ) -> Dict[tuple, float]:
        """
        Build expected points matrix for each (swimmer, event) pair.

        Points depend on predicted placement against ALL competitors.
        """
        point_matrix: Dict[tuple, float] = {}

        for event in events:
            # Get all entries for this event, sorted by seed time
            event_entries = sorted(
                [e for e in all_entries if e.event == event and e.seed_time > 0],
                key=lambda x: x.seed_time,
            )

            # Calculate expected points for each target team swimmer
            for swimmer in swimmers:
                # Find this swimmer's entry
                swimmer_entry = None
                swimmer_rank = 0
                team_scorers_ahead = 0

                for i, entry in enumerate(event_entries):
                    if (
                        entry.swimmer_name == swimmer
                        and entry.team.upper() == target_team.upper()
                    ):
                        swimmer_entry = entry
                        swimmer_rank = i + 1  # 1-indexed
                        break
                    elif entry.team.upper() == target_team.upper():
                        team_scorers_ahead += 1

                if swimmer_entry is None:
                    continue

                # Check if this swimmer would score (max 4 per team)
                if team_scorers_ahead >= self.max_scorers:
                    point_matrix[(swimmer, event)] = 0.0
                else:
                    # Get points for this placement
                    if swimmer_rank <= len(self.points_table):
                        point_matrix[(swimmer, event)] = float(
                            self.points_table[swimmer_rank - 1]
                        )
                    else:
                        point_matrix[(swimmer, event)] = 0.0

        return point_matrix

    def _calculate_baseline_points(
        self,
        team_entries: List[ChampionshipEntry],
        all_entries: List[ChampionshipEntry],
        target_team: str,
    ) -> float:
        """Calculate points with greedy best-2-per-swimmer approach."""
        # Group by swimmer
        swimmer_entries: Dict[str, List[ChampionshipEntry]] = {}
        for e in team_entries:
            if e.swimmer_name not in swimmer_entries:
                swimmer_entries[e.swimmer_name] = []
            swimmer_entries[e.swimmer_name].append(e)

        # For each swimmer, take their best 2 entries by expected points
        baseline = 0.0

        for swimmer, entries in swimmer_entries.items():
            # Calculate expected points for each entry
            entry_points = []
            for entry in entries:
                # Simple rank-based points (ignoring team scorer limits for baseline)
                event_entries = sorted(
                    [
                        e
                        for e in all_entries
                        if e.event == entry.event and e.seed_time > 0
                    ],
                    key=lambda x: x.seed_time,
                )
                rank = next(
                    (
                        i + 1
                        for i, e in enumerate(event_entries)
                        if e.swimmer_name == swimmer
                        and e.team.upper() == target_team.upper()
                    ),
                    999,
                )
                if rank <= len(self.points_table):
                    entry_points.append((entry, self.points_table[rank - 1]))
                else:
                    entry_points.append((entry, 0))

            # Take top 2
            entry_points.sort(key=lambda x: -x[1])
            for _, pts in entry_points[:2]:
                baseline += pts

        return baseline

    def _generate_recommendations(
        self,
        assignments: Dict[str, List[str]],
        divers: Set[str],
        relay_3_swimmers: Set[str],
    ) -> List[str]:
        """Generate coaching recommendations based on optimization."""
        recs = []

        # Count event usage
        for swimmer, events in assignments.items():
            if swimmer in divers:
                recs.append(
                    f"🏊 {swimmer} (diver): {len(events)} individual events assigned"
                )
            if swimmer in relay_3_swimmers:
                recs.append(
                    f"🔄 {swimmer} (400FR): {len(events)} individual events (relay-3 penalty applied)"
                )

        # Flag swimmers with only 1 event (might be worth reviewing)
        single_event_swimmers = [
            s
            for s, e in assignments.items()
            if len(e) == 1 and s not in divers and s not in relay_3_swimmers
        ]
        if single_event_swimmers:
            recs.append(
                f"⚠️ {len(single_event_swimmers)} swimmers assigned only 1 event - review for opportunities"
            )

        return recs


class ScenarioSimulator:
    """
    Run what-if scenarios for championship strategy.
    """

    def __init__(self, optimizer: ChampionshipGurobiStrategy):
        self.optimizer = optimizer

    def simulate_entry_change(
        self,
        all_entries: List[ChampionshipEntry],
        target_team: str,
        swimmer: str,
        old_events: List[str],
        new_events: List[str],
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Simulate moving a swimmer from one set of events to another.

        Returns comparison showing point impact.
        """
        # Create modified entries
        modified_entries = []

        for entry in all_entries:
            if (
                entry.swimmer_name == swimmer
                and entry.team.upper() == target_team.upper()
            ):
                # Check if this event should be included
                if entry.event in new_events:
                    modified_entries.append(entry)
                # Skip events being removed
            else:
                modified_entries.append(entry)

        # Run both optimizations
        original_result = self.optimizer.optimize_entries(
            all_entries, target_team, **kwargs
        )
        modified_result = self.optimizer.optimize_entries(
            modified_entries, target_team, **kwargs
        )

        return {
            "swimmer": swimmer,
            "old_events": old_events,
            "new_events": new_events,
            "original_points": original_result.total_points,
            "modified_points": modified_result.total_points,
            "delta": modified_result.total_points - original_result.total_points,
            "recommendation": "✅ MAKE CHANGE"
            if modified_result.total_points > original_result.total_points
            else "❌ KEEP CURRENT",
        }

    def simulate_scratch(
        self,
        all_entries: List[ChampionshipEntry],
        target_team: str,
        swimmer: str,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Simulate a swimmer scratching from the meet entirely.

        Useful for injury/illness scenarios.
        """
        # Remove swimmer from entries
        modified_entries = [
            e
            for e in all_entries
            if not (e.swimmer_name == swimmer and e.team.upper() == target_team.upper())
        ]

        original_result = self.optimizer.optimize_entries(
            all_entries, target_team, **kwargs
        )
        modified_result = self.optimizer.optimize_entries(
            modified_entries, target_team, **kwargs
        )

        return {
            "swimmer": swimmer,
            "scenario": "SCRATCHED",
            "original_points": original_result.total_points,
            "modified_points": modified_result.total_points,
            "point_loss": original_result.total_points - modified_result.total_points,
            "impact": "HIGH"
            if (original_result.total_points - modified_result.total_points) > 20
            else "MEDIUM"
            if (original_result.total_points - modified_result.total_points) > 10
            else "LOW",
        }

    def simulate_time_improvement(
        self,
        all_entries: List[ChampionshipEntry],
        target_team: str,
        swimmer: str,
        event: str,
        new_time: float,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Simulate a swimmer dropping time in an event.
        """
        original_time = None
        modified_entries = []

        for entry in all_entries:
            if (
                entry.swimmer_name == swimmer
                and entry.event == event
                and entry.team.upper() == target_team.upper()
            ):
                original_time = entry.seed_time
                # Create modified entry
                modified_entries.append(
                    ChampionshipEntry(
                        swimmer_name=entry.swimmer_name,
                        team=entry.team,
                        event=entry.event,
                        seed_time=new_time,
                        gender=entry.gender,
                        grade=entry.grade,
                        source="simulation",
                    )
                )
            else:
                modified_entries.append(entry)

        original_result = self.optimizer.optimize_entries(
            all_entries, target_team, **kwargs
        )
        modified_result = self.optimizer.optimize_entries(
            modified_entries, target_team, **kwargs
        )

        return {
            "swimmer": swimmer,
            "event": event,
            "original_time": original_time,
            "new_time": new_time,
            "time_drop": original_time - new_time if original_time else 0,
            "original_points": original_result.total_points,
            "modified_points": modified_result.total_points,
            "point_gain": modified_result.total_points - original_result.total_points,
        }


class Relay400TradeoffAnalyzer:
    """
    Analyze the trade-off of swimming the 400 Free Relay at VCAC.

    VCAC Rule: Relay 3 (400 Free) counts as 1 individual event.

    This means swimmers on the 400FR lose an individual slot, so we need
    to compare:
    - Points gained from faster 400FR
    - Points lost from giving up an individual event
    """

    def __init__(self, meet_profile: str = "vcac_championship"):
        self.rules = get_meet_profile(meet_profile)
        self.optimizer = ChampionshipGurobiStrategy(meet_profile)

    def analyze_400fr_decision(
        self,
        all_entries: List[ChampionshipEntry],
        target_team: str,
        potential_400fr_swimmers: List[str],
        split_times: Dict[str, float],  # swimmer -> 100 free split time
    ) -> Dict[str, Any]:
        """
        Analyze whether to swim the 400 Free Relay and who should be on it.

        Args:
            all_entries: All meet entries
            target_team: Team to analyze
            potential_400fr_swimmers: Swimmers being considered for 400FR
            split_times: Each swimmer's projected 100 free split

        Returns:
            Analysis with recommendation
        """
        # Calculate points WITHOUT 400FR (swimmers keep individual slots)
        result_without_400 = self.optimizer.optimize_entries(
            all_entries,
            target_team,
            relay_3_swimmers=set(),  # No one loses a slot
        )

        # Calculate points WITH 400FR (swimmers lose individual slots)
        result_with_400 = self.optimizer.optimize_entries(
            all_entries, target_team, relay_3_swimmers=set(potential_400fr_swimmers)
        )

        # Estimate 400FR relay points (simplified - based on total time)
        total_split = sum(
            split_times.get(s, 60.0) for s in potential_400fr_swimmers[:4]
        )
        estimated_400fr_points = self._estimate_relay_points(total_split)

        # Net analysis
        individual_cost = result_without_400.total_points - result_with_400.total_points
        net_gain = estimated_400fr_points - individual_cost

        # Per-swimmer analysis
        swimmer_analysis = []
        for swimmer in potential_400fr_swimmers:
            # What individual points does this swimmer lose?
            with_swimmer = self.optimizer.optimize_entries(
                all_entries, target_team, relay_3_swimmers=set()
            )
            without_swimmer = self.optimizer.optimize_entries(
                all_entries, target_team, relay_3_swimmers={swimmer}
            )
            individual_loss = with_swimmer.total_points - without_swimmer.total_points

            swimmer_analysis.append(
                {
                    "swimmer": swimmer,
                    "split_time": split_times.get(swimmer, 0),
                    "individual_points_lost": individual_loss,
                    "value_for_relay": "HIGH"
                    if individual_loss < 10
                    else "MEDIUM"
                    if individual_loss < 20
                    else "LOW",
                }
            )

        # Sort by value (lower individual loss = better for relay)
        swimmer_analysis.sort(key=lambda x: x["individual_points_lost"])

        return {
            "points_without_400fr": result_without_400.total_points,
            "points_with_400fr": result_with_400.total_points,
            "estimated_400fr_relay_points": estimated_400fr_points,
            "individual_cost": individual_cost,
            "net_gain": net_gain,
            "recommendation": "✅ SWIM 400FR" if net_gain > 0 else "❌ SKIP 400FR",
            "swimmer_analysis": swimmer_analysis,
            "suggested_lineup": [s["swimmer"] for s in swimmer_analysis[:4]],
        }

    def _estimate_relay_points(self, total_time: float) -> float:
        """Estimate relay points based on time. Placeholder - needs real opponent data."""
        # Simplified: assume ~3:30 is 1st place, ~4:00 is 8th
        if total_time < 210:  # 3:30
            return self.rules.relay_points[0]  # 1st
        elif total_time < 220:  # 3:40
            return self.rules.relay_points[1]  # 2nd
        elif total_time < 230:  # 3:50
            return self.rules.relay_points[3]  # 4th
        elif total_time < 240:  # 4:00
            return self.rules.relay_points[5]  # 6th
        else:
            return self.rules.relay_points[7] if len(self.rules.relay_points) > 7 else 0
