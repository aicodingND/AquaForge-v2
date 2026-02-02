from typing import Any

import pandas as pd

from swim_ai_reflex.backend.core.optimizer_utils import evaluate_seton_vs_opponent
from swim_ai_reflex.backend.core.scoring import EVENT_ORDER
from swim_ai_reflex.backend.core.strategies.base_strategy import BaseOptimizerStrategy

# Optional: Probabilistic scoring (Phase 1 enhancement)
try:
    from swim_ai_reflex.backend.intelligence.time_distribution import (
        expected_points_with_uncertainty,
    )

    HAS_PROBABILISTIC = True
except ImportError:
    HAS_PROBABILISTIC = False


class GurobiStrategy(BaseOptimizerStrategy):
    """
    Exact optimization strategy using Gurobi MIP solver.
    Requires gurobipy installed and a valid license.
    """

    def optimize(
        self,
        seton_roster: pd.DataFrame,
        opponent_roster: pd.DataFrame,
        scoring_fn: Any,
        rules: Any,
        **kwargs,
    ) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, float], list[dict[str, Any]]]:
        """
        Run Gurobi optimization.
        """
        try:
            import os

            # Gurobi WLS (Web License Service) can be configured via environment variables:
            # WLSACCESSID, WLSSECRET, LICENSEID - Gurobi reads these automatically
            # If not set via env, fall back to license file
            if not os.environ.get("WLSACCESSID"):
                base_dir = os.getcwd()
                possible_paths = [
                    os.path.join(base_dir, "gurobi.lic"),
                    os.path.join(base_dir, "swim_ai_reflex", "gurobi.lic"),
                    "/app/gurobi.lic",  # Docker path
                ]
                for path in possible_paths:
                    if os.path.exists(path):
                        os.environ["GRB_LICENSE_FILE"] = path
                        break

            import gurobipy as gp
            from gurobipy import GRB
        except ImportError:
            raise ImportError("Gurobi not installed. Please install gurobipy.")

        alpha = kwargs.get("alpha", 1.0)
        time_limit = kwargs.get("time_limit", 30)

        # Data Prep - preserve original team names from input
        # This is critical for Nash iteration where roles swap
        seton_df = seton_roster.copy().reset_index(drop=True)
        opponent_df = opponent_roster.copy().reset_index(drop=True)
        if "team" not in seton_df.columns or seton_df["team"].isna().all():
            seton_df["team"] = "seton"
        if "team" not in opponent_df.columns or opponent_df["team"].isna().all():
            opponent_df["team"] = "opponent"

        # Create opponent's best lineup using greedy model
        # (Gurobi-vs-Gurobi gives incorrect results because both optimize independently)
        from swim_ai_reflex.backend.core.opponent_model import (
            greedy_opponent_best_lineup,
        )

        opponent_best = greedy_opponent_best_lineup(opponent_df)
        opponent_best["team"] = "opponent"

        # Events setup
        available_events = set(seton_df["event"].unique())
        events = [e for e in EVENT_ORDER if e in available_events]
        if not events:
            events = sorted(list(available_events))

        {e: i for i, e in enumerate(events)}
        swimmers = seton_df["swimmer"].unique().tolist()

        # Initialize Model
        m = gp.Model("SwimLineup")
        m.setParam("OutputFlag", 0)
        m.setParam("TimeLimit", time_limit)

        # Variables
        x = m.addVars(swimmers, events, vtype=GRB.BINARY, name="x")

        # Constraints
        # NOTE: All constraints are MAXIMUMS - swimmers can strategically swim fewer events
        # A swimmer may swim 0, 1, or 2 individual events based on what maximizes team points

        # 1. Total events (MAXIMUM - no minimum required)
        for s in swimmers:
            m.addConstr(
                x.sum(s, "*") <= rules.max_total_events_per_swimmer,
                name=f"max_total_{s}",
            )

        # 2. Individual events (MAXIMUM - swimmers can swim 0, 1, or 2)
        individual_events = [e for e in events if "Relay" not in e]
        for s in swimmers:
            m.addConstr(
                gp.quicksum(x[s, e] for e in individual_events)
                <= rules.max_individual_events_per_swimmer,
                name=f"max_indiv_{s}",
            )

        # 3. Team entries per event - Try to fill up to 4 swimmers (dual meet standard)
        for e in events:
            if "Relay" in e:
                # Relays: typically 2-3 entries
                limit = rules.max_relays_per_team_per_event
                m.addConstr(x.sum("*", e) <= limit, name=f"max_team_{e}")
            else:
                # Individual events: up to 4 swimmers
                # Note: Some events may not have 4 available swimmers
                m.addConstr(x.sum("*", e) <= 4, name=f"max_4_{e}")

        # 4. No Back-to-Back
        for s in swimmers:
            for i in range(len(events) - 1):
                e1 = events[i]
                e2 = events[i + 1]
                m.addConstr(x[s, e1] + x[s, e2] <= 1, name=f"no_b2b_{s}_{i}")

        # -------------------------------------------------------------------------
        # Objective Calculation - PROPER DUAL MEET SCORING SIMULATION
        # -------------------------------------------------------------------------
        # KEY RULES (VISAA):
        # - Grades 8-12 are SCORING eligible
        # - Grades 7 and below are EXHIBITION (can place but earn 0 points)
        # - When exhibition swimmer places, points "slide down" to next scorer
        # - Only top 7 places score: [8, 6, 5, 4, 3, 2, 1]
        # - Each team limited to 3 scorers per event
        # -------------------------------------------------------------------------

        INDIVIDUAL_POINTS = [8, 6, 5, 4, 3, 2, 1]  # Places 1-7
        RELAY_POINTS = [8, 4, 2]  # Places 1-3
        MIN_SCORING_GRADE = 8
        MAX_SCORERS_PER_TEAM = 4

        def calculate_scoring_position(swimmer_time, swimmer_grade, event_entries):
            """
            Calculate the actual *scoring* position, not just raw finish position.

            Exhibition swimmers (grade < 8) don't count toward scoring positions.
            So if an exhibition swimmer finishes 3rd, the 4th-place finisher
            gets 3rd-place points.

            Args:
                swimmer_time: This swimmer's time
                swimmer_grade: This swimmer's grade (7 and below = exhibition)
                event_entries: List of dicts with 'time', 'grade', 'team' for all swimmers

            Returns:
                scoring_position: 1-7 for scorers, or 0 if exhibition/no points
            """
            # Exhibition swimmers always get 0 points
            # Safely convert grade to int (may be string from data sources)
            try:
                grade_int = int(swimmer_grade) if swimmer_grade is not None else 12
            except (ValueError, TypeError):
                grade_int = 12  # Default to scoring if conversion fails

            if grade_int < MIN_SCORING_GRADE:
                return 0

            # Sort all entries by time (fastest first)
            sorted_entries = sorted(event_entries, key=lambda x: x.get("time", 999))

            # Count how many SCORING swimmers finished ahead of this swimmer
            scoring_ahead = 0
            seton_scorers_ahead = 0

            for entry in sorted_entries:
                entry_time = entry.get("time", 999)
                entry_grade_raw = entry.get(
                    "grade", 12
                )  # Default to scoring if unknown
                # Safely convert entry_grade to int
                try:
                    entry_grade = (
                        int(entry_grade_raw) if entry_grade_raw is not None else 12
                    )
                except (ValueError, TypeError):
                    entry_grade = 12
                entry_team = entry.get("team", "").lower()

                # Stop when we reach this swimmer's time
                if entry_time >= swimmer_time:
                    break

                # Only count scoring-eligible swimmers
                if entry_grade >= MIN_SCORING_GRADE:
                    scoring_ahead += 1
                    if "seton" in entry_team:
                        seton_scorers_ahead += 1

            # This swimmer's scoring position (1-indexed)
            scoring_position = scoring_ahead + 1

            # Check team scorer limit (only top 3 from each team score)
            if seton_scorers_ahead >= MAX_SCORERS_PER_TEAM:
                return 0  # Already have 3 Seton scorers ahead

            return scoring_position

        # -------------------------------------------------------------------------
        # EVENT IMPORTANCE WEIGHTING
        # -------------------------------------------------------------------------
        # Close events matter MORE than blowouts. If we're guaranteed to win or
        # lose an event by a large margin, strategic decisions there have less
        # impact. Focus optimizer on "swing" events.
        #
        # Importance = 1.0 / (1.0 + relative_margin)
        # - Close race (0.5% margin) → importance ≈ 0.99
        # - Moderate gap (5% margin) → importance ≈ 0.67
        # - Blowout (20% margin) → importance ≈ 0.33
        # -------------------------------------------------------------------------

        event_importance = {}

        for e in events:
            # Get best Seton time for this event
            seton_event = seton_df[seton_df["event"] == e]
            opp_event = opponent_best[opponent_best["event"] == e]

            if seton_event.empty or opp_event.empty:
                event_importance[e] = 1.0  # Default to full importance
                continue

            seton_best_time = seton_event["time"].min()
            opp_best_time = opp_event["time"].min()

            # Calculate relative margin (how far apart are the teams?)
            avg_time = (seton_best_time + opp_best_time) / 2
            time_diff = abs(seton_best_time - opp_best_time)
            relative_margin = time_diff / avg_time if avg_time > 0 else 0

            # Importance: higher for close races, lower for blowouts
            # Scale factor of 3.0 makes 10% margin → ~0.77 importance
            importance = 1.0 / (1.0 + relative_margin * 3.0)

            # Clamp between 0.3 and 1.0 (never fully ignore an event)
            event_importance[e] = max(0.3, min(1.0, importance))

        obj_coeffs = {}

        # Check if roster has std_dev data for probabilistic scoring
        use_probabilistic = (
            HAS_PROBABILISTIC
            and "std_dev" in seton_df.columns
            and seton_df["std_dev"].notna().any()
        )

        for s in swimmers:
            for e in events:
                row = seton_df[(seton_df["swimmer"] == s) & (seton_df["event"] == e)]
                if row.empty:
                    m.addConstr(x[s, e] == 0)
                    continue

                time = row.iloc[0]["time"]
                grade_raw = row.iloc[0].get(
                    "grade", 12
                )  # Default to scoring if unknown
                # Safely convert grade to int (may be string from data sources)
                try:
                    grade = int(grade_raw) if grade_raw is not None else 12
                except (ValueError, TypeError):
                    grade = 12  # Default to scoring if conversion fails
                is_relay = "Relay" in e
                is_exhibition = grade < MIN_SCORING_GRADE

                # Build opponent times for this event
                opp_event = opponent_best[opponent_best["event"] == e]

                if use_probabilistic:
                    # PROBABILISTIC MODE: Use expected points with uncertainty
                    swimmer_std = row.iloc[0].get("std_dev", 0.5)

                    # Build opponent time distributions
                    opponent_times = []
                    for _, opp_row in opp_event.iterrows():
                        opp_std = (
                            opp_row.get("std_dev", 0.5)
                            if "std_dev" in opp_event.columns
                            else 0.5
                        )
                        opponent_times.append((opp_row["time"], opp_std))

                    seton_points = expected_points_with_uncertainty(
                        swimmer_mean=time,
                        swimmer_std=swimmer_std,
                        opponent_times=opponent_times,
                        is_relay=is_relay,
                        is_exhibition=is_exhibition,
                    )
                else:
                    # DETERMINISTIC MODE: Original scoring simulation
                    event_entries = []
                    for _, opp_row in opp_event.iterrows():
                        event_entries.append(
                            {
                                "time": opp_row["time"],
                                "grade": opp_row.get("grade", 12),
                                "team": "opponent",
                            }
                        )

                    scoring_pos = calculate_scoring_position(time, grade, event_entries)

                    if scoring_pos == 0:
                        seton_points = 0.1
                    else:
                        points_table = RELAY_POINTS if is_relay else INDIVIDUAL_POINTS
                        if scoring_pos <= len(points_table):
                            seton_points = points_table[scoring_pos - 1]
                        else:
                            seton_points = 0

                # Apply event importance weighting
                importance = event_importance.get(e, 1.0)
                weighted_points = seton_points * importance

                obj_coeffs[s, e] = weighted_points

        m.setObjective(
            gp.quicksum(
                x[s, e] * obj_coeffs.get((s, e), 0) for s in swimmers for e in events
            ),
            GRB.MAXIMIZE,
        )

        m.optimize()

        if m.Status == GRB.OPTIMAL:
            rows = []
            for s in swimmers:
                for e in events:
                    if x[s, e].X > 0.5:
                        original_row = (
                            seton_df[
                                (seton_df["swimmer"] == s) & (seton_df["event"] == e)
                            ]
                            .iloc[0]
                            .to_dict()
                        )
                        rows.append(original_row)

            best_seton = (
                pd.DataFrame(rows)
                if rows
                else pd.DataFrame(columns=seton_roster.columns)
            )

            # Use dual_meet_scoring to ensure all 232 points are distributed
            try:
                from swim_ai_reflex.backend.core.dual_meet_scoring import (
                    score_dual_meet,
                )

                # Score using dual meet rules (ensures 232 points total)
                best_scored, best_totals = score_dual_meet(best_seton, opponent_best)

                return best_seton, best_scored, best_totals, []
            except ImportError:
                # Fallback to old scoring if dual_meet_scoring not available
                _, best_totals, best_scored = evaluate_seton_vs_opponent(
                    best_seton, opponent_best, scoring_fn, alpha
                )
                return best_seton, best_scored, best_totals, []

        else:
            # Fallback
            return seton_roster, pd.DataFrame(), {"seton": 0, "opponent": 0}, []

    def _optimize_single_team(
        self,
        roster_df: pd.DataFrame,
        rules: Any,
        gp: Any,
        GRB: Any,
        time_limit: int = 15,
    ) -> pd.DataFrame:
        """
        Optimize a single team's lineup using Gurobi.
        Maximizes team's expected points while respecting constraints.
        """
        if roster_df.empty:
            return roster_df

        df = roster_df.copy().reset_index(drop=True)
        events = df["event"].unique().tolist()
        swimmers = df["swimmer"].unique().tolist()

        # Create model
        m = gp.Model("TeamLineup")
        m.setParam("OutputFlag", 0)
        m.setParam("TimeLimit", time_limit)

        # Variables
        x = m.addVars(
            [(s, e) for s in swimmers for e in events], vtype=GRB.BINARY, name="x"
        )

        # Constraints
        # 1. Max 2 individual events per swimmer
        individual_events = [e for e in events if "Relay" not in e]
        for s in swimmers:
            m.addConstr(
                gp.quicksum(x[s, e] for e in individual_events if (s, e) in x) <= 2
            )

        # 2. Max 4 swimmers per event
        for e in events:
            m.addConstr(gp.quicksum(x[s, e] for s in swimmers if (s, e) in x) <= 4)

        # 3. Can only assign swimmer to event if they have a time for it
        for s in swimmers:
            for e in events:
                if len(df[(df["swimmer"] == s) & (df["event"] == e)]) == 0:
                    if (s, e) in x:
                        m.addConstr(x[s, e] == 0)

        # Objective: maximize expected points (faster times = more points)
        obj_coeffs = {}
        for s in swimmers:
            for e in events:
                row = df[(df["swimmer"] == s) & (df["event"] == e)]
                if not row.empty:
                    time = row.iloc[0]["time"]
                    # Estimate points based on relative speed (faster = higher coefficient)
                    # Simple heuristic: use inverse of normalized time
                    all_times = df[df["event"] == e]["time"]
                    if len(all_times) > 0:
                        min_time = all_times.min()
                        coeff = min_time / time if time > 0 else 0
                        obj_coeffs[s, e] = coeff * 8  # Scale to approximate point value
                    else:
                        obj_coeffs[s, e] = 0

        m.setObjective(
            gp.quicksum(
                x[s, e] * obj_coeffs.get((s, e), 0)
                for s in swimmers
                for e in events
                if (s, e) in x
            ),
            GRB.MAXIMIZE,
        )

        m.optimize()

        # Extract solution
        if m.Status == GRB.OPTIMAL:
            rows = []
            for s in swimmers:
                for e in events:
                    if (s, e) in x and x[s, e].X > 0.5:
                        original_row = (
                            df[(df["swimmer"] == s) & (df["event"] == e)]
                            .iloc[0]
                            .to_dict()
                        )
                        rows.append(original_row)
            return (
                pd.DataFrame(rows) if rows else pd.DataFrame(columns=roster_df.columns)
            )
        else:
            # Fallback to greedy if Gurobi fails
            from swim_ai_reflex.backend.core.opponent_model import (
                greedy_opponent_best_lineup,
            )

            return greedy_opponent_best_lineup(roster_df)
