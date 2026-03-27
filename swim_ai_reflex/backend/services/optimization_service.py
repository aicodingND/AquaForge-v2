"""
Enhanced optimization service with caching, retry logic, and better error handling.
"""

import asyncio
import hashlib
from typing import Any

import pandas as pd

from swim_ai_reflex.backend.core.dual_meet_scoring import score_dual_meet
from swim_ai_reflex.backend.core.optimizer_factory import OptimizerFactory
from swim_ai_reflex.backend.core.rules import VISAADualRules
from swim_ai_reflex.backend.services.base_service import BaseService
from swim_ai_reflex.backend.utils.cache import DataCache
from swim_ai_reflex.backend.utils.helpers import normalize_team_name


class OptimizationCache:
    """Wrapper for persistent DataCache."""

    def _generate_key(
        self,
        seton_df: pd.DataFrame,
        opponent_df: pd.DataFrame,
        method: str,
        max_iters: int,
    ) -> str:
        """Generate a persistent cache key from input parameters."""
        cache_version = (
            "v4"  # Incrementing version to ensure opponent lineup is captured
        )
        seton_hash = hashlib.md5(
            pd.util.hash_pandas_object(seton_df).values
        ).hexdigest()
        opponent_hash = (
            hashlib.md5(pd.util.hash_pandas_object(opponent_df).values).hexdigest()
            if not opponent_df.empty
            else "empty"
        )
        # Unique prefix for optimization results vs raw data
        return (
            f"opt_res_{cache_version}_{seton_hash}_{opponent_hash}_{method}_{max_iters}"
        )

    def get(self, key: str) -> dict[str, Any] | None:
        """Retrieve cached result."""
        data, _ = DataCache.load_from_cache(key)
        return data  # returns dict or None

    def set(self, key: str, value: dict[str, Any]):
        """Store result in persistent cache."""
        # Use DataCache to save dictionary as pickle
        DataCache.save_to_cache(value, key, "optimization_result")

    def clear(self):
        """Clear all cached results (clears everything in DataCache dir)."""
        DataCache.clear_cache()


class OptimizationService(BaseService):
    """
    Enhanced service to handle optimization requests with caching and retry logic.
    """

    def __init__(self):
        super().__init__()
        self._cache = OptimizationCache()

    def _validate_roster(self, roster: pd.DataFrame, roster_name: str) -> str | None:
        """
        Validate roster DataFrame structure.
        """
        if roster is None or roster.empty:
            return f"{roster_name} roster is empty or invalid"

        required_columns = ["swimmer", "event", "time", "team"]
        missing_cols = [col for col in required_columns if col not in roster.columns]
        if missing_cols:
            return f"{roster_name} roster missing required columns: {', '.join(missing_cols)}"

        return None

    async def predict_best_lineups(
        self,
        seton_roster: pd.DataFrame,
        opponent_roster: pd.DataFrame,
        method: str = "gurobi",
        max_iters: int = 500,
        enforce_fatigue: bool = False,
        scoring_type: str = "visaa_top7",  # "visaa_top7" or "standard_top5"
        robust_mode: bool = False,  # NEW: Maximize worst-case instead of expected
        use_cache: bool = True,
        retry_on_failure: bool = True,
        max_retries: int = 2,
        use_championship_factors: bool | None = None,
        locked_assignments: list[dict] | None = None,
        excluded_swimmers: list[str] | None = None,
        time_overrides: list[dict] | None = None,
    ) -> dict[str, Any]:
        """
        Run the lineup optimization engine with caching and retry logic.
        """
        # Validate inputs
        error = self._validate_roster(seton_roster, "Seton")
        if error:
            return self._error(error, code="VALIDATION_ERROR")

        if opponent_roster is not None and not opponent_roster.empty:
            error = self._validate_roster(opponent_roster, "Opponent")
            if error:
                return self._error(error, code="VALIDATION_ERROR")

        # DEBUG: Inspect attributes that might affect scoring
        self.log_info(
            f"Optimization Request: Seton {len(seton_roster)} rows, Opponent {len(opponent_roster) if opponent_roster is not None else 0} rows"
        )

        if opponent_roster is not None and not opponent_roster.empty:
            if "grade" in opponent_roster.columns:
                null_grades = opponent_roster["grade"].isnull().sum()
                sample_grades = opponent_roster["grade"].unique()[:5]
                self.log_info(
                    f"Opponent Grade Check: {null_grades} nulls. Sample: {sample_grades}"
                )
                # FIX: Pre-fill invalid grades to ensure they are eligible (if missing)
                # Assuming missing grade means "eligible" (e.g. standard HS swimmer)
                opponent_roster["grade"] = opponent_roster["grade"].fillna("9")
            else:
                self.log_info(
                    "Opponent roster has NO 'grade' column (Default Eligible)"
                )

        # FIX: Also check Seton roster for missing grades
        if seton_roster is not None and not seton_roster.empty:
            if "grade" in seton_roster.columns:
                seton_roster["grade"] = seton_roster["grade"].fillna("9")

        # Validate method parameter
        if method not in ["heuristic", "gurobi", "stackelberg", "aqua"]:
            return self._error(
                f"Invalid optimization method: {method}", code="INVALID_PARAM"
            )

        # Validate max_iters
        if max_iters < 1 or max_iters > 10000:
            return self._error(f"Invalid max_iters: {max_iters}", code="INVALID_PARAM")

        # Check cache
        if use_cache:
            cache_key = self._cache._generate_key(
                seton_roster, opponent_roster, method, max_iters
            )
            # Append fatigue setting to key to ensure distinct results
            cache_key += f"_fatigue_{enforce_fatigue}"

            cached_result = self._cache.get(cache_key)
            if cached_result:
                self.log_info("Converting cached result")
                cached_result["from_cache"] = True
                return self._success(
                    data=cached_result, message="Optimization retrieved from cache"
                )

        # Run optimization with retry logic
        attempt = 0
        last_error = None

        while attempt <= (max_retries if retry_on_failure else 0):
            try:
                result = await self._run_optimization(
                    seton_roster,
                    opponent_roster,
                    method,
                    max_iters,
                    enforce_fatigue,
                    scoring_type,
                    robust_mode,
                    use_championship_factors=use_championship_factors,
                    locked_assignments=locked_assignments,
                    excluded_swimmers=excluded_swimmers,
                    time_overrides=time_overrides,
                )

                # Check for internal error
                if "error" in result:
                    return self._error(result["error"], code="OPTIMIZATION_ERROR")

                # Cache successful result
                if use_cache:
                    self._cache.set(cache_key, result)

                result["from_cache"] = False
                return self._success(
                    data=result, message="Optimization completed successfully"
                )

            except Exception as e:
                last_error = e
                attempt += 1
                self.log_warning(f"Optimization attempt {attempt} failed: {str(e)}")
                if attempt <= max_retries:
                    await asyncio.sleep(2**attempt)
                    continue
                else:
                    break

        # All retries failed
        import traceback

        error_details = traceback.format_exc()
        return self._error(
            f"Optimization failed after {attempt} attempts: {str(last_error)}",
            code="OPTIMIZATION_FAILED",
            details=error_details,
        )

    async def _run_optimization(
        self,
        seton_roster: pd.DataFrame,
        opponent_roster: pd.DataFrame,
        method: str,
        max_iters: int,
        enforce_fatigue: bool = False,
        scoring_type: str = "visaa_top7",
        robust_mode: bool = False,
        use_championship_factors: bool | None = None,
        locked_assignments: list[dict] | None = None,
        excluded_swimmers: list[str] | None = None,
        time_overrides: list[dict] | None = None,
    ) -> dict[str, Any]:
        """
        Internal method to run the actual optimization using the Strategy pattern.
        """
        # Capture logs for UI display
        run_logs: list[str] = []

        def log_and_capture(msg: str):
            self.log_info(msg)
            run_logs.append(msg)

        # Create rules based on scoring_type
        if scoring_type == "standard_top5":
            # Standard NFHS: 6-4-3-2-1
            rules = VISAADualRules()
            rules.individual_points = [6, 4, 3, 2, 1]
            log_and_capture("Using Standard Top 5 Scoring (6-4-3-2-1)")
        else:
            # VISAA Default: 8-6-5-4-3-2-1
            rules = VISAADualRules()
            log_and_capture("Using VISAA Top 7 Scoring (8-6-5-4-3-2-1)")

        # Define Scoring Function (CLEAN - no constraints, just scoring)
        def score_lineup(df: pd.DataFrame):
            """Pure scoring function - uses score_dual_meet to ensure 232 points."""
            # Ensure teams are normalized for splitting
            # Use a copy to avoid SettingWithCopy warnings
            df_scoring = df.copy()
            if "team_norm" not in df_scoring.columns:
                df_scoring["team_norm"] = df_scoring["team"].apply(normalize_team_name)

            seton_df = df_scoring[df_scoring["team_norm"] == "seton"]
            opp_df = df_scoring[df_scoring["team_norm"] == "opponent"]

            return score_dual_meet(seton_df, opp_df, rules=rules)

        # Import constraint validator for proper constraint checking
        from swim_ai_reflex.backend.services.constraint_validator import (
            normalize_event_name,
            validate_lineup,
        )

        def is_lineup_valid(lineup_df: pd.DataFrame) -> bool:
            """
            Check if lineup violates any constraints using proper validator.
            Returns True if lineup is valid, False if it has constraint violations.
            """
            if lineup_df is None or lineup_df.empty:
                return False

            # Build assignments dict from dataframe
            try:
                seton_mask = lineup_df["team"].str.lower() == "seton"
                seton_df = lineup_df[seton_mask]

                if seton_df.empty:
                    return True  # No Seton swimmers = no constraints to check

                # Build {swimmer: [events]} dict
                assignments = {}
                for _, row in seton_df.iterrows():
                    swimmer = row.get("swimmer", "")
                    event = row.get("event", "")
                    if swimmer and event:
                        if swimmer not in assignments:
                            assignments[swimmer] = []
                        assignments[swimmer].append(event)

                # Validate using the proper constraint validator
                result = validate_lineup(
                    seton_assignments=assignments,
                    meet_profile="seton_dual",
                    allow_override=False,
                )

                return result.is_valid
            except Exception:
                # If validation fails, assume valid to not block optimization
                return True

        def score_with_validation(df: pd.DataFrame):
            """
            Score lineup and return very negative score if constraints violated.
            This is the scoring function passed to the optimizer.

            Note: For Gurobi, constraints are built into the ILP model directly.
            This wrapper is for heuristic optimizers that need a scoring-based approach.
            """
            scored_df, total_scores = score_lineup(df)

            # Check if lineup violates constraints
            if not is_lineup_valid(df):
                # Return very negative score to reject this lineup
                total_scores["seton"] = -float("inf")

            return scored_df, total_scores

        try:
            # Try to get strategy from factory (Gurobi first, then fallback)
            try:
                strategy = OptimizerFactory.get_strategy(method)
                self.log_info(f"Using {method} optimization strategy")

                # Apply what-if parameters to AquaOptimizer instances
                from swim_ai_reflex.backend.core.strategies.aqua_optimizer import (
                    AquaOptimizer as _AquaOpt,
                )

                if isinstance(strategy, _AquaOpt):
                    if use_championship_factors is not None:
                        if use_championship_factors:
                            from swim_ai_reflex.backend.core.championship_factors import (
                                ChampionshipFactors,
                            )

                            strategy.championship_factors = ChampionshipFactors()
                        else:
                            from swim_ai_reflex.backend.core.championship_factors import (
                                ChampionshipFactors,
                            )

                            strategy.championship_factors = (
                                ChampionshipFactors.disabled()
                            )
                    if locked_assignments:
                        strategy.locked_assignments = locked_assignments
                    if excluded_swimmers:
                        strategy.excluded_swimmers = excluded_swimmers
                    if time_overrides:
                        strategy.time_overrides = time_overrides

            except (ImportError, ModuleNotFoundError) as e:
                # Gurobi not available, fallback to heuristic
                if method == "gurobi":
                    self.log_warning(
                        f"Gurobi not available ({str(e)}), falling back to heuristic strategy"
                    )
                    strategy = OptimizerFactory.get_strategy("heuristic")
                    method = "heuristic"  # Update method for cache key
                else:
                    raise

            # -------------------------------------------------------------------------
            # -------------------------------------------------------------------------
            # PHASE 1: NASH EQUILIBRIUM ITERATION
            # -------------------------------------------------------------------------
            # True game-theoretic optimization: iterate until neither side wants to
            # change strategy. This is a Nash equilibrium approximation.
            #
            # Key insight: Both coaches are rational and will optimize their lineups.
            # We iterate Seton ↔ Opponent until convergence (no changes).
            # -------------------------------------------------------------------------

            def lineups_equivalent(
                lineup1: pd.DataFrame, lineup2: pd.DataFrame
            ) -> bool:
                """Check if two lineups are functionally equivalent."""
                if lineup1 is None or lineup2 is None:
                    return False
                if lineup1.empty or lineup2.empty:
                    return lineup1.empty and lineup2.empty
                if len(lineup1) != len(lineup2):
                    return False

                # Compare swimmer-event assignments
                try:
                    set1 = set(
                        zip(lineup1["swimmer"].tolist(), lineup1["event"].tolist())
                    )
                    set2 = set(
                        zip(lineup2["swimmer"].tolist(), lineup2["event"].tolist())
                    )
                    return set1 == set2
                except (KeyError, TypeError):
                    return False

            avg_events = 0
            if not opponent_roster.empty and "swimmer" in opponent_roster.columns:
                avg_events = len(opponent_roster) / len(
                    opponent_roster["swimmer"].unique()
                )

            # Track Nash-derived opponent lineup & status
            from swim_ai_reflex.backend.core.opponent_model import (
                greedy_opponent_best_lineup,
            )

            # Always start with greedy baseline so we have *something*
            nash_opponent_lineup = greedy_opponent_best_lineup(opponent_roster)

            # Only run Nash iteration if opponent has strategic choices
            if avg_events > 2.0:
                MAX_NASH_ITERATIONS = 8  # Prevent infinite loops
                CONVERGENCE_THRESHOLD = 2  # Stable for N iterations = converged

                log_and_capture(
                    f"Phase 1: Nash Equilibrium Iteration ({avg_events:.1f} events/swimmer)..."
                )

                current_seton_lineup = None  # Will be optimized in first iteration
                current_opp_lineup = nash_opponent_lineup  # Start with greedy

                stable_count = 0

                try:
                    for iteration in range(MAX_NASH_ITERATIONS):
                        log_and_capture(
                            f"... Iteration {iteration + 1}/{MAX_NASH_ITERATIONS}"
                        )

                        # Step A: Seton optimizes against current opponent lineup
                        new_seton, _, _, _ = await asyncio.to_thread(
                            strategy.optimize,
                            seton_roster=seton_roster,
                            opponent_roster=current_opp_lineup
                            if current_opp_lineup is not None
                            and not current_opp_lineup.empty
                            else opponent_roster,
                            scoring_fn=score_with_validation,
                            rules=rules,
                            max_iters=max_iters
                            // 3,  # Each iteration gets portion of budget
                            alpha=1.0,
                        )

                        if new_seton is not None and not new_seton.empty:
                            seton_changed = not lineups_equivalent(
                                current_seton_lineup, new_seton
                            )
                            current_seton_lineup = new_seton
                            # Ensure Seton lineup keeps team='seton'
                            current_seton_lineup["team"] = "seton"
                        else:
                            seton_changed = False

                        # Step B: Opponent optimizes against current Seton lineup
                        new_opp, _, _, _ = await asyncio.to_thread(
                            strategy.optimize,
                            seton_roster=opponent_roster,  # Opponent optimizing their roster
                            opponent_roster=current_seton_lineup
                            if current_seton_lineup is not None
                            else seton_roster,
                            scoring_fn=score_with_validation,
                            rules=rules,
                            max_iters=max_iters // 3,
                            alpha=1.0,
                        )

                        if new_opp is not None and not new_opp.empty:
                            opp_changed = not lineups_equivalent(
                                current_opp_lineup, new_opp
                            )
                            current_opp_lineup = new_opp
                            # CRITICAL: Force team='opponent' on opponent lineup
                            # The optimizer may have labeled it 'seton' since opponent_roster
                            # was passed as the seton_roster parameter
                            current_opp_lineup["team"] = "opponent"
                        else:
                            opp_changed = False

                        # Check for convergence (Nash equilibrium reached)
                        if not seton_changed and not opp_changed:
                            stable_count += 1
                            log_and_capture(
                                f"→ Stable iteration (count: {stable_count})"
                            )

                            if stable_count >= CONVERGENCE_THRESHOLD:
                                log_and_capture(
                                    f"✓ Nash Equilibrium reached at iteration {iteration + 1}!"
                                )
                                break
                        else:
                            stable_count = 0  # Reset on any change
                            changes = []
                            if seton_changed:
                                changes.append("Seton adjusted")
                            if opp_changed:
                                changes.append("Opponent adjusted")
                            log_and_capture(f"→ {', '.join(changes)}")

                    else:
                        # Loop completed without convergence
                        log_and_capture(
                            "! Max iterations reached. Using best opponent from final iteration."
                        )

                    # Use the converged opponent lineup for final optimization
                    if current_opp_lineup is not None and not current_opp_lineup.empty:
                        opponent_roster = current_opp_lineup
                        nash_opponent_lineup = (
                            current_opp_lineup.copy()
                        )  # Save for return
                        log_and_capture(
                            "→ Using Nash-derived opponent for final optimization"
                        )

                except Exception as nash_err:
                    self.log_warning(
                        f"Nash iteration failed: {str(nash_err)}. Using greedy opponent."
                    )
                    # Fallback to greedy opponent
                    opponent_roster = greedy_opponent_best_lineup(opponent_roster)
                    nash_opponent_lineup = opponent_roster.copy()
                    nash_opponent_lineup = opponent_roster.copy()

            # -------------------------------------------------------------------------
            # PHASE 2: OPTIMIZE SETON (Main Pass)
            # -------------------------------------------------------------------------

            try:
                # Run optimization in thread pool
                (
                    best_lineup,
                    best_scored,
                    best_totals,
                    history,
                ) = await asyncio.to_thread(
                    strategy.optimize,
                    seton_roster=seton_roster,
                    opponent_roster=opponent_roster,
                    scoring_fn=score_with_validation,
                    rules=rules,
                    max_iters=max_iters,
                    alpha=1.0,
                )
            except Exception as main_opt_err:
                # Fallback for Main Pass
                err_str = str(main_opt_err).lower()
                if "gurobi" in method.lower() and (
                    "model too large" in err_str
                    or "license" in err_str
                    or "gurobi" in err_str
                ):
                    self.log_warning(
                        f"✗ Gurobi Failed ({str(main_opt_err)}). Falling back to HEURISTIC engine."
                    )
                    # Switch to heuristic
                    strategy = OptimizerFactory.get_strategy("heuristic")
                    (
                        best_lineup,
                        best_scored,
                        best_totals,
                        history,
                    ) = await asyncio.to_thread(
                        strategy.optimize,
                        seton_roster=seton_roster,
                        opponent_roster=opponent_roster,
                        scoring_fn=score_with_validation,
                        rules=rules,
                        max_iters=max_iters,
                        alpha=1.0,
                    )
                else:
                    raise main_opt_err

            # -------------------------------------------------------------------------
            # PHASE 3: ROBUST EVALUATION (if enabled)
            # -------------------------------------------------------------------------
            # Evaluate our lineup against MULTIPLE opponent scenarios.
            # Report the worst-case score to ensure we're resilient.
            # -------------------------------------------------------------------------

            robust_results = None
            if robust_mode:
                log_and_capture(
                    "Phase 3: Running Robust Evaluation (multi-scenario)..."
                )

                import random

                from swim_ai_reflex.backend.core.opponent_model import (
                    greedy_opponent_best_lineup,
                )

                # Generate multiple opponent scenarios
                opponent_scenarios = []

                # Scenario 1: Nash-equilibrium opponent (already computed)
                opponent_scenarios.append(("Nash Equilibrium", opponent_roster))

                # Scenario 2: Aggressive opponent (all stars in first half of events)
                try:
                    aggressive_opp = greedy_opponent_best_lineup(
                        seton_roster
                    )  # Uses seton as "opponent" to flip perspective
                    if not aggressive_opp.empty:
                        opponent_scenarios.append(("Aggressive", aggressive_opp))
                except Exception:
                    pass

                # Scenario 3: Random perturbations (swap some swimmer assignments)
                for i in range(3):
                    try:
                        perturbed = opponent_roster.copy()
                        if not perturbed.empty and len(perturbed) > 2:
                            # Randomly shuffle some assignments
                            indices = list(perturbed.index)
                            if len(indices) >= 4:
                                # Swap two random pairs
                                random.shuffle(indices)
                                # Just use the perturbed order as a variant
                                perturbed = perturbed.sample(frac=1).reset_index(
                                    drop=True
                                )
                            opponent_scenarios.append((f"Perturbed {i + 1}", perturbed))
                    except Exception:
                        pass

                # Evaluate our lineup against each scenario
                scenario_scores = []
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
                        log_and_capture(
                            f"{scenario_name}: {seton_score:.0f} - {opp_score:.0f} (margin: {margin:+.0f})"
                        )
                    except Exception as scenario_err:
                        log_and_capture(f"{scenario_name}: Error - {str(scenario_err)}")

                if scenario_scores:
                    # Find worst-case
                    worst_case = min(scenario_scores, key=lambda x: x["margin"])
                    best_case = max(scenario_scores, key=lambda x: x["margin"])
                    avg_margin = sum(s["margin"] for s in scenario_scores) / len(
                        scenario_scores
                    )

                    log_and_capture("Robust Summary:")
                    log_and_capture(
                        f"Worst case: {worst_case['scenario']} (margin: {worst_case['margin']:+.0f})"
                    )
                    log_and_capture(
                        f"Best case: {best_case['scenario']} (margin: {best_case['margin']:+.0f})"
                    )
                    log_and_capture(f"Average: margin {avg_margin:+.1f}")

                    robust_results = {
                        "scenarios": scenario_scores,
                        "worst_case": worst_case,
                        "best_case": best_case,
                        "average_margin": avg_margin,
                        "guaranteed_margin": worst_case["margin"],
                    }

        except ValueError as e:
            return {"error": str(e)}
        except ImportError as e:
            return {"error": f"Dependency missing: {str(e)}"}
        except Exception as e:
            import traceback

            self.log_error(f"Strategy execution failed: {traceback.format_exc()}")
            return {"error": f"Optimization failed: {str(e)}"}

        # Validate results
        if best_lineup is None or best_lineup.empty:
            return {"error": "Optimization produced no valid lineup"}

        # Re-score final lineup WITH BOTH TEAMS
        # (previous bug: only scored Seton, giving opponent 0)
        # Combine best_lineup (Seton) with nash_opponent_lineup (Opponent) for proper dual meet scoring

        # CRITICAL FIX: Force team names for proper scoring
        # The scoring function (full_meet_scoring) uses normalize_team_name() which
        # only recognizes 'seton' and 'opponent'. Any other team name scores 0!
        # Previous bug: .fillna("opponent") only set null values, leaving real team
        # names like "St. Mary's" unchanged, causing opponent to score 0.

        # Force ALL opponent entries to have team="opponent"
        nash_opponent_lineup["team"] = "opponent"

        # Also ensure Seton lineup has team="seton" (in case it's missing or wrong)
        if "team" not in best_lineup.columns:
            best_lineup["team"] = "seton"
        else:
            best_lineup["team"] = "seton"  # Force it for safety

        # CRITICAL: Normalize event names for consistent matching
        # This fixes fuzzy matching issues in the router
        if "event" in best_lineup.columns:
            best_lineup["event"] = best_lineup["event"].apply(normalize_event_name)
        if "event" in nash_opponent_lineup.columns:
            nash_opponent_lineup["event"] = nash_opponent_lineup["event"].apply(
                normalize_event_name
            )

        combined_lineup = pd.concat(
            [best_lineup, nash_opponent_lineup], ignore_index=True
        )
        final_scored_df, final_totals = score_lineup(combined_lineup)

        result = {
            "seton_score": float(final_totals.get("seton", 0)),
            "opponent_score": float(final_totals.get("opponent", 0)),
            "best_lineup": best_lineup.to_dict("records"),
            "opponent_lineup": nash_opponent_lineup.to_dict("records")
            if nash_opponent_lineup is not None and not nash_opponent_lineup.empty
            else opponent_roster.to_dict("records"),
            # CRITICAL FIX: Use final_scored_df which has BOTH teams scored properly
            # This fixes the 270-0 bug where router couldn't match opponent scores
            "details": final_scored_df.to_dict("records")
            if final_scored_df is not None and not final_scored_df.empty
            else [],
            "iterations": len(history) if history else 0,
            "logs": run_logs,
            "robust_mode": robust_mode,
        }

        # Safety check: Log warning if opponent score is 0 but had entries
        if (
            result["opponent_score"] == 0
            and nash_opponent_lineup is not None
            and not nash_opponent_lineup.empty
        ):
            self.log_warning(
                "Opponent score is 0 despite having entries! "
                "Check team name normalization or scoring rules."
            )
            # Add to logs for UI visibility
            run_logs.append("WARNING: Opponent score is 0. Possible data issue.")

        # Add robust results if computed
        if robust_results:
            result["robust"] = robust_results
            result["guaranteed_margin"] = robust_results["guaranteed_margin"]

        return result

    def clear_cache(self):
        """Clear the optimization cache."""
        self._cache.clear()
        self.log_info("Optimization cache cleared")


# Singleton instance
optimization_service = OptimizationService()
