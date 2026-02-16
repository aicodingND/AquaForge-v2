"""
Championship Gurobi Strategy

Extends the dual-meet Gurobi optimizer for multi-team championship meets.
Adapts scoring tables and constraints from the meet profile (MeetRules).

Supported meet profiles:
- vcac_championship: 12-place, relay 2x, Relay 3 = individual slot
- visaa_state: 16-place, relay 2x, Relay 3 = regular relay (no penalty)
- visaa_championship: 16-place consolation scoring

Key features:
- Scoring tables loaded from MeetRules (not hardcoded)
- Relay 3 penalty adapts via rules.relay_3_counts_as_individual
- Max scorers per team per event from rules.max_scorers_per_team_individual
- Diving counts as 1 individual slot
"""

import bisect
import os
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from swim_ai_reflex.backend.core.attrition_model import AttritionRates
from swim_ai_reflex.backend.core.championship_factors import (
    ChampionshipFactors,
    adjust_time,
)
from swim_ai_reflex.backend.core.rules import get_meet_profile
from swim_ai_reflex.backend.services.constraint_validator import (
    get_blocked_events,
    normalize_event_name,
)

if TYPE_CHECKING:
    pass


@dataclass
class ChampionshipEntry:
    """Single swimmer-event entry."""

    swimmer_name: str
    team: str
    event: str
    seed_time: float
    gender: str = ""
    grade: str | None = None
    source: str = "unknown"


@dataclass
class ChampionshipOptimizationResult:
    """Result of championship entry optimization."""

    assignments: dict[str, list[str]]  # {swimmer: [events]}
    total_points: float
    baseline_points: float
    improvement: float
    solve_time_ms: float
    status: str
    event_breakdown: dict[str, float] = field(default_factory=dict)
    recommendations: list[str] = field(default_factory=list)


class ChampionshipGurobiStrategy:
    """
    Gurobi-based optimization for championship meets.

    Extends dual-meet logic to handle:
    - Multiple competing teams
    - Championship scoring tables
    - 400FR individual slot penalty
    - Diver integration
    """

    def __init__(
        self,
        meet_profile: str = "vcac_championship",
        championship_factors: ChampionshipFactors | None = None,
        attrition: AttritionRates
        | None = None,  # accepted but unused (zero optimization impact)
    ):
        self.rules = get_meet_profile(meet_profile)
        self.points_table = self.rules.individual_points
        self.relay_points = self.rules.relay_points
        self.max_scorers = self.rules.max_scorers_per_team_individual

        # Championship adjustment factors
        if championship_factors is not None:
            self.factors = championship_factors
        else:
            self.factors = ChampionshipFactors()

    def optimize_entries(
        self,
        all_entries: list[ChampionshipEntry],
        target_team: str,
        divers: set[str] | None = None,
        relay_1_swimmers: set[str] | None = None,  # 200 Medley
        relay_2_swimmers: set[str] | None = None,  # 200 Free
        relay_3_swimmers: set[str] | None = None,  # 400 Free
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
        swimmer_event_lookup: dict[tuple, ChampionshipEntry] = {}
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

        # 2. Max individual events per swimmer
        # Adjusted for divers and relay-3 swimmers (meet-type aware)
        relay_3_penalty = getattr(self.rules, "relay_3_counts_as_individual", False)
        for s in swimmers:
            # Base limit is 2 individual events
            limit = 2

            # Divers get 1 fewer slot
            if s in divers:
                limit -= 1

            # 400 Free Relay costs 1 individual slot ONLY at meets where it counts
            # (e.g., VCAC yes, VISAA State no)
            if relay_3_penalty and s in relay_3_swimmers:
                limit -= 1

            limit = max(0, limit)  # Can't go negative

            m.addConstr(
                gp.quicksum(x[s, e] for e in events) <= limit, name=f"max_indiv_{s}"
            )

        # 3. Max entries per team per event
        # Note: max_scorers limits how many SCORE, but entries can exceed this.
        # The point_matrix already accounts for placement among teammates.
        # Use max_entries (unlimited at VISAA = 999) not max_scorers (4).
        max_entries = getattr(self.rules, "max_entries_per_team_per_event", 4)
        for e in events:
            m.addConstr(
                gp.quicksum(x[s, e] for s in swimmers) <= max_entries,
                name=f"max_entries_{e}",
            )

        # 4. No back-to-back events (STANDARD RULE - including relay leg blocking)
        # Use normalized event names for comparison

        # 4a. Individual <-> Individual blocking
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

        # 4b. Individual <-> Relay blocking
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
            # Extract assignment from solution
            assignments: dict[str, list[str]] = {}

            for s in swimmers:
                assigned_events = []
                for e in events:
                    if x[s, e].X > 0.5:
                        assigned_events.append(e)

                if assigned_events:
                    assignments[s] = assigned_events

            # Re-score using accurate placement (accounts for teammates)
            total_points, event_breakdown = self._rescore_solution(
                assignments, all_entries, target_team
            )

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
        all_entries: list[ChampionshipEntry],
        swimmers: list[str],
        events: list[str],
        target_team: str,
    ) -> dict[tuple, float]:
        """
        Build expected points matrix for each (swimmer, event) pair.

        Uses opponent-only ranking (rank among non-target-team entries)
        as the optimization objective.  This is slightly optimistic
        (ignores teammate rank depression) but ensures the optimizer
        fills all available event slots rather than leaving them empty.

        The per-team scorer limit (max 4 per event) is enforced as a
        Gurobi constraint.  After solving, the result is re-scored
        using accurate placement in _rescore_solution().
        """
        point_matrix: dict[tuple, float] = {}

        for event in events:
            # Sort opponent entries for binary-search ranking
            # Apply championship adjustment (empirical speed-up factor)
            opponent_times = sorted(
                adjust_time(e.seed_time, event, self.factors)
                for e in all_entries
                if e.event == event
                and e.seed_time > 0
                and e.team.upper() != target_team.upper()
            )

            # Target team entries for this event (also adjusted)
            team_event_times = {
                e.swimmer_name: adjust_time(e.seed_time, event, self.factors)
                for e in all_entries
                if e.event == event
                and e.seed_time > 0
                and e.team.upper() == target_team.upper()
            }

            for swimmer in swimmers:
                seed_time = team_event_times.get(swimmer)
                if seed_time is None:
                    continue

                # Rank among opponents (best-case: only target-team swimmer)
                opponents_faster = bisect.bisect_left(opponent_times, seed_time)
                placement = opponents_faster + 1

                if placement <= len(self.points_table):
                    raw_pts = float(self.points_table[placement - 1])
                    point_matrix[(swimmer, event)] = raw_pts
                else:
                    point_matrix[(swimmer, event)] = 0.0

        return point_matrix

    def _rescore_solution(
        self,
        assignments: dict[str, list[str]],
        all_entries: list[ChampionshipEntry],
        target_team: str,
    ) -> tuple[float, dict[str, float]]:
        """
        Re-score an assignment using accurate placement (all entries
        considered, including assigned teammates).

        Returns (total_points, event_breakdown).
        """
        # Build set of assigned (swimmer, event) pairs
        assigned = set()
        for swimmer, evts in assignments.items():
            for evt in evts:
                assigned.add((swimmer, evt))

        total_points = 0.0
        event_breakdown: dict[str, float] = {}

        events = sorted(set(evt for _, evts in assignments.items() for evt in evts))

        for event in events:
            # Opponent entries
            opp = [
                e
                for e in all_entries
                if e.event == event
                and e.seed_time > 0
                and e.team.upper() != target_team.upper()
            ]
            # Assigned target-team entries
            team = [
                e
                for e in all_entries
                if e.event == event
                and e.seed_time > 0
                and e.team.upper() == target_team.upper()
                and (e.swimmer_name, event) in assigned
            ]

            # Combine and sort by championship-adjusted seed time
            combined = sorted(
                opp + team,
                key=lambda e: adjust_time(e.seed_time, event, self.factors),
            )

            # Assign points (12-place scoring, max 4 scorers per team)
            team_scorers = 0
            event_pts = 0.0
            for i, entry in enumerate(combined):
                if i >= len(self.points_table):
                    break  # No more scoring places
                if entry.team.upper() == target_team.upper():
                    if team_scorers < self.max_scorers:
                        event_pts += self.points_table[i]
                        team_scorers += 1

            event_breakdown[event] = event_pts
            total_points += event_pts

        return total_points, event_breakdown

    def _calculate_baseline_points(
        self,
        team_entries: list[ChampionshipEntry],
        all_entries: list[ChampionshipEntry],
        target_team: str,
    ) -> float:
        """Calculate points with greedy best-2-per-swimmer approach.

        Assigns each swimmer their 2 highest-value events (by opponent-only
        rank), then re-scores the resulting lineup accurately.
        """
        # Pre-compute opponent times for fast ranking
        opp_times_by_event: dict[str, list[float]] = {}
        for e in all_entries:
            if e.seed_time > 0 and e.team.upper() != target_team.upper():
                opp_times_by_event.setdefault(e.event, []).append(e.seed_time)
        for evt in opp_times_by_event:
            opp_times_by_event[evt].sort()

        # Group by swimmer
        swimmer_entries: dict[str, list[ChampionshipEntry]] = {}
        for e in team_entries:
            swimmer_entries.setdefault(e.swimmer_name, []).append(e)

        # For each swimmer, pick their best 2 events by opponent-only rank
        baseline_assignments: dict[str, list[str]] = {}

        for swimmer, entries in swimmer_entries.items():
            entry_scores = []
            for entry in entries:
                opp_times = opp_times_by_event.get(entry.event, [])
                rank = bisect.bisect_left(opp_times, entry.seed_time) + 1
                pts = (
                    self.points_table[rank - 1] if rank <= len(self.points_table) else 0
                )
                entry_scores.append((entry.event, pts))

            entry_scores.sort(key=lambda x: -x[1])
            top_events = [evt for evt, pts in entry_scores[:2] if pts > 0]
            if top_events:
                baseline_assignments[swimmer] = top_events

        # Re-score the baseline lineup accurately
        baseline, _ = self._rescore_solution(
            baseline_assignments, all_entries, target_team
        )
        return baseline

    def _generate_recommendations(
        self,
        assignments: dict[str, list[str]],
        divers: set[str],
        relay_3_swimmers: set[str],
    ) -> list[str]:
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


__all__ = [
    "ChampionshipEntry",
    "ChampionshipOptimizationResult",
    "ChampionshipGurobiStrategy",
]
