import math
import random
from typing import Any, Dict, List, Tuple

import pandas as pd

from swim_ai_reflex.backend.core.optimizer_utils import (
    count_back_to_back_events,
    evaluate_seton_vs_opponent,
    validate_lineup_constraints,
)
from swim_ai_reflex.backend.core.strategies.base_strategy import BaseOptimizerStrategy


class HeuristicStrategy(BaseOptimizerStrategy):
    """
    Simulated Annealing based heuristic optimization strategy.
    Finds near-optimal lineups by exploring neighbor states.

    STRATEGIC FLEXIBILITY:
    - Swimmers can compete in 0, 1, or 2 individual events (no minimum)
    - The algorithm explores swaps to find optimal assignments
    - A swimmer may only swim 1 event if that maximizes team points
    """

    def optimize(
        self,
        seton_roster: pd.DataFrame,
        opponent_roster: pd.DataFrame,
        scoring_fn: Any,
        rules: Any,
        **kwargs,
    ) -> Tuple[pd.DataFrame, pd.DataFrame, Dict[str, float], List[Dict[str, Any]]]:
        """
        Run simulated annealing optimization.

        Kwargs:
            max_iters (int): Maximum iterations (default 1200)
            temp0 (float): Initial temperature (default 0.8)
            alpha (float): Weight for opponent score (default 1.0)
            progress_callback (callable): Function to report progress
            cancel_callback (callable): Function to check for cancellation
        """
        max_iters = kwargs.get("max_iters", 1200)
        temp0 = kwargs.get("temp0", 0.8)
        alpha = kwargs.get("alpha", 1.0)
        progress_callback = kwargs.get("progress_callback")
        cancel_callback = kwargs.get("cancel_callback")
        min_grade = kwargs.get("min_grade", 8)

        # Working copies - preserve original team names from input
        # This is critical for Nash iteration where roles swap
        current = seton_roster.copy().reset_index(drop=True)
        if "team" not in current.columns or current["team"].isna().all():
            current["team"] = "seton"
        opponent_best = opponent_roster.copy()
        if "team" not in opponent_best.columns or opponent_best["team"].isna().all():
            opponent_best["team"] = "opponent"

        # Validate initial
        is_valid, violations = validate_lineup_constraints(current, rules, min_grade)

        # Initial evaluation
        best = current.copy()
        best_score, best_totals, best_scored = evaluate_seton_vs_opponent(
            best, opponent_best, scoring_fn, alpha=alpha
        )

        # HARD CONSTRAINT: Check back-to-back violations
        b2b_violations = count_back_to_back_events(best)
        if b2b_violations > 0:
            best_score = -999999  # Completely invalid

        current_score = best_score
        history = []
        last_improvement_iter = 0
        reheat_count = 0
        temp = temp0
        cooling_rate = 0.995
        hall_of_fame = []

        for it in range(1, max_iters + 1):
            if cancel_callback and it % 10 == 0:
                cancel_callback()

            if progress_callback and it % 10 == 0:
                pct = 20 + int((it / max_iters) * 60)
                status_msg = f"Optimizing... Iteration {it}/{max_iters} | Best Score: {best_score:.1f}"
                try:
                    progress_callback(pct, status_msg)
                except Exception:
                    pass

            # Reheating
            if it - last_improvement_iter > 200:
                if len(hall_of_fame) < 3:
                    hall_of_fame.append(
                        {
                            "score": best_score,
                            "totals": best_totals.copy(),
                            "lineup": best.copy(),
                        }
                    )
                temp = temp0 * 0.5
                reheat_count += 1
                last_improvement_iter = it

            # Generate neighbor
            candidate = self._random_neighbor_swap(current, rules, min_grade)

            # Evaluate
            cand_score, cand_totals, cand_scored = evaluate_seton_vs_opponent(
                candidate, opponent_best, scoring_fn, alpha=alpha
            )

            # HARD CONSTRAINT: Reject any lineup with back-to-back violations
            b2b_violations = count_back_to_back_events(candidate)
            if b2b_violations > 0:
                # Skip this candidate entirely - don't accept it
                continue

            delta = cand_score - current_score

            # Accept logic
            if delta > 0 or (temp > 0 and random.random() < math.exp(delta / temp)):
                current = candidate
                current_score = cand_score

                if cand_score > best_score:
                    best = candidate.copy()
                    best_score = cand_score
                    best_totals = cand_totals
                    best_scored = cand_scored
                    last_improvement_iter = it
                    history.append(
                        {"iter": it, "score": best_score, "totals": best_totals}
                    )

            temp *= cooling_rate

        return best, best_scored, best_totals, history

    def _random_neighbor_swap(self, seton_df, rules, min_grade=8):
        """Internal helper to swap swimmers."""
        df = seton_df.copy()
        if df.empty:
            return df

        n_rows = len(df)
        max_attempts = 100

        for _ in range(max_attempts):
            i = random.randrange(n_rows)
            j = random.randrange(n_rows)

            if i == j:
                continue

            # Swap
            swimmer_i = df.at[i, "swimmer"]
            swimmer_j = df.at[j, "swimmer"]

            df.at[i, "swimmer"] = swimmer_j
            df.at[j, "swimmer"] = swimmer_i

            # Validate
            is_valid, _ = validate_lineup_constraints(df, rules, min_grade)

            if is_valid:
                return df
            else:
                # Revert
                df.at[i, "swimmer"] = swimmer_i
                df.at[j, "swimmer"] = swimmer_j

        return df
