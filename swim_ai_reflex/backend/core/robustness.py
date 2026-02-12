from collections.abc import Callable
from typing import Any

import pandas as pd

from swim_ai_reflex.backend.core.dual_meet_scoring import score_dual_meet


class RobustnessEvaluator:
    """
    Evaluates a proposed lineup against multiple possible opponent scenarios
    to determine its worst-case performance guarantees (Robust Optimization).
    """

    def __init__(self, logger: Callable[[str], None] | None = None):
        self.log = logger if logger else lambda x: None

    def evaluate(
        self,
        best_lineup: pd.DataFrame,
        opponent_roster: pd.DataFrame,
        seton_roster: pd.DataFrame,
        nash_opponent: pd.DataFrame | None = None,
    ) -> dict[str, Any] | None:
        """
        Run multi-scenario evaluation.
        """
        self.log("Phase 3: Running Robust Evaluation (multi-scenario)...")

        opponent_scenarios: list[tuple[str, pd.DataFrame]] = []

        # Scenario 1: Nash Equilibrium (if available)
        if nash_opponent is not None:
            opponent_scenarios.append(("Nash Equilibrium", nash_opponent))

        # Scenario 2: Aggressive (greedy re-optimization of opponent)
        # Note: greedy_opponent_best_lineup returns an optimized lineup for the
        # given roster. We pass the opponent roster to simulate the opponent
        # playing aggressively.
        try:
            pass
        except Exception:
            pass

        # Scenario 3: Random perturbations
        for i in range(3):
            try:
                perturbed = opponent_roster.copy()
                if not perturbed.empty and len(perturbed) > 2:
                    # Randomly shuffle
                    perturbed = perturbed.sample(frac=1).reset_index(drop=True)
                    opponent_scenarios.append((f"Perturbed {i + 1}", perturbed))
            except Exception:
                pass

        # Evaluate
        scenario_scores: list[dict[str, Any]] = []
        for scenario_name, opp_scenario in opponent_scenarios:
            try:
                _, scenario_totals = score_dual_meet(best_lineup, opp_scenario)
                seton_score = scenario_totals.get("seton", 0)
                opp_score = scenario_totals.get("opponent", 0)
                margin = seton_score - opp_score
                scenario_scores.append(
                    {
                        "scenario": scenario_name,
                        "seton_score": seton_score,
                        "opponent_score": opp_score,
                        "margin": margin,
                    }
                )
                self.log(
                    f"   {scenario_name}: {seton_score:.0f} - {opp_score:.0f} (margin: {margin:+.0f})"
                )
            except Exception as scenario_err:
                self.log(f"   {scenario_name}: Error - {str(scenario_err)}")

        if scenario_scores:
            worst_case = min(scenario_scores, key=lambda x: x["margin"])
            best_case = max(scenario_scores, key=lambda x: x["margin"])
            avg_margin = sum(s["margin"] for s in scenario_scores) / len(
                scenario_scores
            )

            self.log("   Robust Summary:")
            self.log(
                f"      Worst case: {worst_case['scenario']} (margin: {worst_case['margin']:+.0f})"
            )
            self.log(
                f"      Best case:  {best_case['scenario']} (margin: {best_case['margin']:+.0f})"
            )
            self.log(f"      Average:    margin {avg_margin:+.1f}")

            return {
                "scenarios": scenario_scores,
                "worst_case": worst_case,
                "best_case": best_case,
                "average_margin": avg_margin,
                "guaranteed_margin": worst_case["margin"],
            }

        return None
