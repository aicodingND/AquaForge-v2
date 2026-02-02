"""
Stackelberg Optimization Strategy

Implements bilevel optimization where:
- Seton (leader) commits to a lineup
- Opponent (follower) responds optimally
- We find the Seton lineup that maximizes score after opponent's best response

This is computationally expensive but produces "unexploitable" lineups.
"""

from typing import Any

import pandas as pd

from swim_ai_reflex.backend.core.scoring import EVENT_ORDER
from swim_ai_reflex.backend.core.strategies.base_strategy import BaseOptimizerStrategy


class StackelbergStrategy(BaseOptimizerStrategy):
    """
    Bilevel Stackelberg optimization:
    - Level 1 (Leader/Seton): Find lineup that maximizes score after opponent response
    - Level 2 (Follower/Opponent): Given Seton's lineup, find optimal counter

    This is the gold standard for game-theoretic optimization but is
    significantly slower than Nash or standard methods.
    """

    def __init__(self, max_candidates: int = 25, time_limit: int = 60):
        """
        Args:
            max_candidates: Maximum number of Seton lineups to evaluate deeply
            time_limit: Per-candidate time limit for opponent optimization
        """
        self.max_candidates = max_candidates
        self.time_limit = time_limit

    def optimize(
        self,
        seton_roster: pd.DataFrame,
        opponent_roster: pd.DataFrame,
        scoring_fn: Any,
        rules: Any,
        **kwargs,
    ) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, float], list[dict[str, Any]]]:
        """
        Run Stackelberg bilevel optimization.

        Returns:
            - best_seton_lineup: The Stackelberg-optimal Seton lineup
            - scored_result: The scored result with opponent's best response
            - totals: Score totals
            - history: Optimization history with all candidates evaluated
        """
        history = []

        # Data prep
        seton_df = seton_roster.copy().reset_index(drop=True)
        opponent_df = opponent_roster.copy().reset_index(drop=True)

        if "team" not in seton_df.columns:
            seton_df["team"] = "seton"
        if "team" not in opponent_df.columns:
            opponent_df["team"] = "opponent"

        # Get events
        available_events = set(seton_df["event"].unique())
        events = [e for e in EVENT_ORDER if e in available_events]
        if not events:
            events = sorted(list(available_events))

        [e for e in events if "Relay" not in e]

        # =========================================================================
        # PHASE 1: Generate candidate Seton lineups
        # =========================================================================
        # We use a combination of:
        # 1. Greedy best-per-event
        # 2. Random valid permutations
        # 3. Strategic variations (rest star swimmers, etc.)

        candidates = []

        # Candidate 1: Greedy (fastest swimmer per event)
        greedy_lineup = self._generate_greedy_lineup(seton_df, events, rules)
        if not greedy_lineup.empty:
            candidates.append(("Greedy", greedy_lineup))

        # Candidate 2-5: Variations where we rest star swimmers in different events
        star_swimmers = self._identify_star_swimmers(seton_df, top_n=3)
        for i, star in enumerate(star_swimmers[:3]):
            variant = self._generate_lineup_resting(
                seton_df, events, rules, rest_swimmer=star
            )
            if not variant.empty:
                candidates.append((f"Rest-{star[:10]}", variant))

        # Candidates 6-25: Random valid permutations
        random_candidates = self._generate_random_lineups(
            seton_df, events, rules, count=self.max_candidates - len(candidates)
        )
        for i, lineup in enumerate(random_candidates):
            candidates.append((f"Random-{i + 1}", lineup))

        history.append(
            {"phase": "candidate_generation", "candidates_found": len(candidates)}
        )

        # =========================================================================
        # PHASE 2: Compute opponent's best response to each candidate
        # =========================================================================
        # For each Seton lineup, run opponent optimization

        scored_candidates = []

        for name, seton_lineup in candidates:
            try:
                # Compute opponent's optimal response to this Seton lineup
                opp_response = self._compute_opponent_response(
                    seton_lineup=seton_lineup,
                    opponent_roster=opponent_df,
                    events=events,
                    rules=rules,
                    scoring_fn=scoring_fn,
                )

                # Score the matchup
                scored_df, totals = scoring_fn(
                    pd.concat([seton_lineup, opp_response], ignore_index=True)
                )

                seton_score = totals.get("seton", 0)
                opp_score = totals.get("opponent", 0)
                margin = seton_score - opp_score

                scored_candidates.append(
                    {
                        "name": name,
                        "seton_lineup": seton_lineup,
                        "opponent_response": opp_response,
                        "scored_df": scored_df,
                        "totals": totals,
                        "seton_score": seton_score,
                        "opp_score": opp_score,
                        "margin": margin,
                    }
                )

                history.append(
                    {
                        "phase": "opponent_response",
                        "candidate": name,
                        "seton_score": seton_score,
                        "opponent_score": opp_score,
                        "margin": margin,
                    }
                )

            except Exception as e:
                history.append(
                    {"phase": "opponent_response", "candidate": name, "error": str(e)}
                )

        # =========================================================================
        # PHASE 3: Select Stackelberg-optimal lineup
        # =========================================================================
        # The best lineup is the one with the highest margin AFTER opponent counters

        if not scored_candidates:
            # Fallback to greedy if all failed
            return greedy_lineup, pd.DataFrame(), {"seton": 0, "opponent": 0}, history

        # Find best margin (Stackelberg equilibrium)
        best = max(scored_candidates, key=lambda x: x["margin"])

        history.append(
            {
                "phase": "final_selection",
                "best_candidate": best["name"],
                "best_margin": best["margin"],
                "all_margins": [(c["name"], c["margin"]) for c in scored_candidates],
            }
        )

        return (best["seton_lineup"], best["scored_df"], best["totals"], history)

    def _generate_greedy_lineup(
        self, roster: pd.DataFrame, events: list[str], rules: Any
    ) -> pd.DataFrame:
        """Generate lineup by greedily picking fastest swimmer per event."""
        lineup_rows = []
        swimmer_events = {}  # Track events per swimmer

        for event in events:
            event_swimmers = roster[roster["event"] == event].sort_values(
                "time", ascending=True
            )
            assigned = 0
            max_per_event = (
                4 if "Relay" not in event else rules.max_relays_per_team_per_event
            )

            for _, row in event_swimmers.iterrows():
                swimmer = row["swimmer"]
                current_count = swimmer_events.get(swimmer, 0)

                # Check constraints
                is_individual = "Relay" not in event
                individual_count = sum(
                    1
                    for e in swimmer_events.get(swimmer + "_events", [])
                    if "Relay" not in e
                )

                if current_count >= rules.max_total_events_per_swimmer:
                    continue
                if (
                    is_individual
                    and individual_count >= rules.max_individual_events_per_swimmer
                ):
                    continue
                if assigned >= max_per_event:
                    break

                lineup_rows.append(row.to_dict())
                swimmer_events[swimmer] = current_count + 1
                swimmer_events[swimmer + "_events"] = swimmer_events.get(
                    swimmer + "_events", []
                ) + [event]
                assigned += 1

        return (
            pd.DataFrame(lineup_rows)
            if lineup_rows
            else pd.DataFrame(columns=roster.columns)
        )

    def _identify_star_swimmers(
        self, roster: pd.DataFrame, top_n: int = 3
    ) -> list[str]:
        """Identify top swimmers by average time percentile across events."""
        if roster.empty or "swimmer" not in roster.columns:
            return []

        # Calculate z-scores per event, then average per swimmer
        swimmer_scores = {}

        for swimmer in roster["swimmer"].unique():
            swimmer_rows = roster[roster["swimmer"] == swimmer]
            percentiles = []

            for _, row in swimmer_rows.iterrows():
                event = row["event"]
                time = row["time"]
                event_times = roster[roster["event"] == event]["time"]
                if len(event_times) > 1:
                    # Lower percentile = faster
                    percentile = (event_times < time).mean()
                    percentiles.append(percentile)

            if percentiles:
                swimmer_scores[swimmer] = sum(percentiles) / len(percentiles)

        # Sort by lowest percentile (fastest)
        sorted_swimmers = sorted(swimmer_scores.items(), key=lambda x: x[1])
        return [s[0] for s in sorted_swimmers[:top_n]]

    def _generate_lineup_resting(
        self, roster: pd.DataFrame, events: list[str], rules: Any, rest_swimmer: str
    ) -> pd.DataFrame:
        """Generate lineup where a specific swimmer is rested (not assigned)."""
        filtered_roster = roster[roster["swimmer"] != rest_swimmer]
        return self._generate_greedy_lineup(filtered_roster, events, rules)

    def _generate_random_lineups(
        self, roster: pd.DataFrame, events: list[str], rules: Any, count: int
    ) -> list[pd.DataFrame]:
        """Generate random valid lineups by shuffling swimmer priorities."""
        lineups = []

        for _ in range(count):
            # Shuffle the roster order (changes greedy priority)
            shuffled = roster.sample(frac=1).reset_index(drop=True)
            lineup = self._generate_greedy_lineup(shuffled, events, rules)
            if not lineup.empty:
                lineups.append(lineup)

        return lineups

    def _compute_opponent_response(
        self,
        seton_lineup: pd.DataFrame,
        opponent_roster: pd.DataFrame,
        events: list[str],
        rules: Any,
        scoring_fn: Any,
    ) -> pd.DataFrame:
        """
        Compute opponent's optimal response to a given Seton lineup.

        This is the "inner" optimization in bilevel programming.
        Opponent wants to maximize their score given Seton's lineup is fixed.
        """
        # For now, use enhanced greedy that considers Seton's entries
        # A full implementation would use Gurobi here too

        lineup_rows = []
        swimmer_events = {}

        # Analyze Seton's lineup per event
        seton_per_event = {}
        for _, row in seton_lineup.iterrows():
            event = row["event"]
            if event not in seton_per_event:
                seton_per_event[event] = []
            seton_per_event[event].append(row["time"])

        for event in events:
            seton_times = sorted(seton_per_event.get(event, []))
            event_swimmers = opponent_roster[opponent_roster["event"] == event].copy()

            if event_swimmers.empty:
                continue

            # Calculate "value" = expected points based on beating Seton swimmers
            def calc_value(time):
                # How many Seton swimmers would this opponent beat?
                beats = sum(1 for t in seton_times if time < t)
                # Rough point value (1st=8, 2nd=6, etc.)
                return beats * 2  # Simple heuristic

            event_swimmers["value"] = event_swimmers["time"].apply(calc_value)
            event_swimmers = event_swimmers.sort_values("value", ascending=False)

            assigned = 0
            max_per_event = (
                4 if "Relay" not in event else rules.max_relays_per_team_per_event
            )

            for _, row in event_swimmers.iterrows():
                swimmer = row["swimmer"]
                current_count = swimmer_events.get(swimmer, 0)

                is_individual = "Relay" not in event
                individual_count = sum(
                    1
                    for e in swimmer_events.get(swimmer + "_events", [])
                    if "Relay" not in e
                )

                if current_count >= rules.max_total_events_per_swimmer:
                    continue
                if (
                    is_individual
                    and individual_count >= rules.max_individual_events_per_swimmer
                ):
                    continue
                if assigned >= max_per_event:
                    break

                row_dict = row.to_dict()
                row_dict.pop("value", None)  # Remove temporary column
                lineup_rows.append(row_dict)
                swimmer_events[swimmer] = current_count + 1
                swimmer_events[swimmer + "_events"] = swimmer_events.get(
                    swimmer + "_events", []
                ) + [event]
                assigned += 1

        result = (
            pd.DataFrame(lineup_rows)
            if lineup_rows
            else pd.DataFrame(columns=opponent_roster.columns)
        )
        if "team" not in result.columns and not result.empty:
            result["team"] = "opponent"
        return result
