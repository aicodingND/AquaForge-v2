"""
Optimization Router

Provides endpoints for swim meet lineup optimization.
"""

import logging
import time

from fastapi import APIRouter, HTTPException

from swim_ai_reflex.backend.api.models import (
    ErrorResponse,
    OptimizationRequest,
    OptimizationResponse,
)
from swim_ai_reflex.backend.utils.data_contracts import (
    normalize_roster,
    validate_team_entries,
)

router = APIRouter()
logger = logging.getLogger(__name__)


def _validate_request(request: OptimizationRequest, is_championship: bool):
    """Validate and normalize request data. Returns (seton_raw, seton_df, opponent_df, warnings)."""
    seton_raw = [dict(entry) for entry in request.seton_data]
    opponent_raw = (
        [dict(entry) for entry in request.opponent_data]
        if request.opponent_data
        else []
    )

    seton_result = validate_team_entries(
        seton_raw, team_type="seton", remove_duplicates=True
    )
    if seton_result.has_errors:
        error_detail = "; ".join(seton_result.error_messages())
        raise HTTPException(
            status_code=400, detail=f"Seton data validation failed: {error_detail}"
        )

    for warning in seton_result.warnings:
        logger.warning(f"Seton data warning: {warning.message}")
    logger.info(f"Seton validation: {seton_result.stats}")

    if not is_championship:
        if not opponent_raw:
            raise HTTPException(
                status_code=400, detail="Opponent team data is required for dual mode"
            )
        opponent_result = validate_team_entries(
            opponent_raw, team_type="opponent", remove_duplicates=True
        )
        if opponent_result.has_errors:
            error_detail = "; ".join(opponent_result.error_messages())
            raise HTTPException(
                status_code=400,
                detail=f"Opponent data validation failed: {error_detail}",
            )
        for warning in opponent_result.warnings:
            logger.warning(f"Opponent data warning: {warning.message}")
        logger.info(f"Opponent validation: {opponent_result.stats}")
    else:
        opponent_result = validate_team_entries([], team_type="opponent")
        opponent_result.entries = []

    seton_df = normalize_roster(seton_result.entries, team="seton")
    opponent_df = normalize_roster(opponent_result.entries, team="opponent")

    all_warnings = list(seton_result.warning_messages())
    if not is_championship:
        all_warnings.extend(opponent_result.warning_messages())

    return seton_raw, seton_df, opponent_df, all_warnings


async def _run_championship_optimization(request, seton_raw, start_time):
    """Run championship mode optimization. Returns response dict."""
    # Get strategy preference from request (default: aqua for best results)
    strategy_type = getattr(request, "championship_strategy", "aqua")
    logger.info(f"Championship mode - using strategy: {strategy_type}")

    from swim_ai_reflex.backend.services.championship_formatter import (
        build_championship_entries,
        format_championship_response,
    )
    from swim_ai_reflex.backend.utils.data_contracts import parse_time

    # Converter function for championship entries (uses already-parsed times)
    def championship_time_converter(time_val):
        """Convert time value - entries are already parsed, just ensure float."""
        if isinstance(time_val, (int, float)):
            return float(time_val)
        result, _ = parse_time(time_val)
        return result if result else 9999.0

    # Convert validated entries to ChampionshipEntry format
    entries = build_championship_entries(seton_raw, championship_time_converter)

    # Determine meet profile
    meet_profile = (
        "vcac_championship"
        if request.scoring_type == "vcac_championship"
        else "visaa_state"
    )

    # ===== AQUA STRATEGY (RECOMMENDED) =====
    if strategy_type == "aqua":
        logger.info("Using AquaOptimizer for championship (2x better than Gurobi)")
        import pandas as pd

        from swim_ai_reflex.backend.core.rules import get_meet_profile
        from swim_ai_reflex.backend.core.strategies.aqua_optimizer import (
            AquaOptimizer,
            ScoringProfile,
        )

        # Get scoring profile and rules
        scoring_profile = (
            ScoringProfile.vcac_championship()
            if meet_profile == "vcac_championship"
            else ScoringProfile.visaa_championship()
        )

        # Get meet rules for scoring function
        rules = get_meet_profile(meet_profile)

        # Create scoring function from rules
        def scoring_fn(place: int, is_relay: bool = False) -> float:
            if place < 1 or place > len(rules.individual_points):
                return 0.0
            pts = rules.individual_points[place - 1]
            return pts * rules.relay_multiplier if is_relay else pts

        # Convert entries to DataFrame
        df = pd.DataFrame(
            [
                {
                    "swimmer": e.swimmer_name,
                    "event": e.event,
                    "time": e.seed_time,
                    "team": e.team,
                    "gender": getattr(e, "gender", ""),
                }
                for e in entries
            ]
        )

        # Split by team
        seton_df = df[df["team"].str.upper() == "SST"].copy()
        opponent_df = df[df["team"].str.upper() != "SST"].copy()

        logger.info(
            f"AquaOptimizer: {len(seton_df)} SST entries, {len(opponent_df)} opponent entries"
        )

        try:
            optimizer = AquaOptimizer(
                profile=scoring_profile,
                quality_mode="thorough",
                nash_iterations=5,
                use_championship_factors=request.use_championship_factors,
                locked_assignments=request.locked_assignments,
                excluded_swimmers=request.excluded_swimmers,
                time_overrides=request.time_overrides,
            )

            # Run optimization
            result = optimizer.optimize(
                seton_roster=seton_df,
                opponent_roster=opponent_df,
                scoring_fn=scoring_fn,
                rules=rules,
            )

            # Extract result - format: (seton_lineup, opp_lineup, scores_dict, details)
            if isinstance(result, tuple) and len(result) >= 3:
                seton_lineup = result[0]
                scores = result[2] if isinstance(result[2], dict) else {}
                seton_score = scores.get("seton_total", 0)

                # Create a compatible champ_result structure
                from dataclasses import dataclass

                @dataclass
                class AquaChampResult:
                    optimal_lineup: any
                    score: float
                    improvement: float
                    events: dict

                champ_result = AquaChampResult(
                    optimal_lineup=seton_lineup,
                    score=seton_score,
                    improvement=0,  # Could calculate vs baseline
                    events={},
                )

                logger.info(f"AquaOptimizer championship result: {seton_score} pts")
            else:
                raise ValueError(
                    f"Unexpected result format from AquaOptimizer: {type(result)}"
                )

        except Exception as e:
            logger.warning(f"AquaOptimizer failed, falling back to Gurobi: {e}")
            strategy_type = "gurobi"  # Fall through to Gurobi

    # ===== GUROBI STRATEGY (FALLBACK) =====
    if strategy_type == "gurobi":
        logger.info("Using ChampionshipGurobiStrategy")
        from swim_ai_reflex.backend.core.strategies.championship_strategy import (
            ChampionshipGurobiStrategy,
        )

        strategy = ChampionshipGurobiStrategy(meet_profile=meet_profile)
        champ_result = strategy.optimize_entries(
            all_entries=entries,
            target_team="SST",  # Team CODE, not name - entries use SST not "Seton"
            time_limit=60,
        )

    # ===== PROJECT STANDINGS FOR ALL TEAMS =====
    standings_projection = None
    try:
        from swim_ai_reflex.backend.services.championship.projection import (
            PointProjectionService,
        )

        logger.info(f"Projecting standings for {len(entries)} total entries")

        # Convert entries to dict format for projection service
        entries_for_projection = [
            {
                "swimmer": e.swimmer_name,
                "team": e.team,
                "event": e.event,
                "time": e.seed_time,
                "gender": e.gender,
                "grade": e.grade,
            }
            for e in entries
        ]

        logger.info(f"Converted {len(entries_for_projection)} entries for projection")

        # Log unique teams
        unique_teams = set(e["team"] for e in entries_for_projection)
        logger.info(f"Unique teams in entries: {unique_teams}")

        projection_service = PointProjectionService(meet_profile=meet_profile)
        projection_result = projection_service.project_standings(
            entries=entries_for_projection,
            target_team="SST",
            meet_name=f"Championship ({meet_profile})",
        )

        # Convert to dict for response
        standings_projection = projection_result.to_dict()

        num_standings = len(standings_projection.get("standings", []))
        logger.info(f"✅ Successfully projected standings for {num_standings} teams")

        if num_standings == 0:
            logger.warning("⚠️  Standings projection returned 0 teams!")
        else:
            # Log first few standings for verification
            for standing in standings_projection.get("standings", [])[:3]:
                logger.info(
                    f"   {standing.get('rank')}. {standing.get('team')}: {standing.get('points')} pts"
                )

    except Exception as e:
        logger.error(f"❌ Failed to project full standings: {e}", exc_info=True)
        # Continue without standings - optimization still works
        standings_projection = None

    # Format response using championship formatter
    return format_championship_response(
        champ_result=champ_result,
        entries=entries,
        optimization_time_ms=(time.time() - start_time) * 1000,
        standings_projection=standings_projection,
    )


async def _run_dual_optimization(request, seton_df, opponent_df, method, start_time):
    """Run dual meet optimization. Returns response dict."""
    # Import the optimization service
    from swim_ai_reflex.backend.services.optimization_service import (
        optimization_service,
    )

    logger.info(
        f"Starting optimization with {len(seton_df)} Seton entries, {len(opponent_df)} opponent entries"
    )
    logger.info(f"Using backend: {method}")

    # Import the formatter
    from swim_ai_reflex.backend.utils.response_formatter import (
        format_dual_meet_response,
    )

    # Run optimization using the correct method (async)
    result = await optimization_service.predict_best_lineups(
        seton_roster=seton_df,
        opponent_roster=opponent_df,
        method=method,
        max_iters=100,
        enforce_fatigue=request.enforce_fatigue,
        scoring_type=request.scoring_type,
        robust_mode=request.robust_mode,
        use_championship_factors=request.use_championship_factors,
        locked_assignments=request.locked_assignments,
        excluded_swimmers=request.excluded_swimmers,
        time_overrides=request.time_overrides,
    )

    # Calculate timing
    optimization_time_ms = (time.time() - start_time) * 1000

    # Extract scores from result - structure is result["data"]["seton_score"]
    seton_score = 0
    opponent_score = 0

    if result.get("success"):
        data = result.get("data", {})
        seton_score = data.get("seton_score", 0)
        opponent_score = data.get("opponent_score", 0)

    # Use the new centralized formatter
    response = format_dual_meet_response(
        result=result,
        seton_score=seton_score,
        opponent_score=opponent_score,
        optimization_time_ms=optimization_time_ms,
        method=method,
    )

    # Auto-save run for historical comparison
    try:
        import json as _json

        from swim_ai_reflex.backend.persistence.sqlite_repository import (
            SQLiteRepository,
        )

        repo = SQLiteRepository()
        await repo.save_meet(
            {
                "meet_id": f"opt_{int(time.time())}",
                "opponent": getattr(request, "opponent_team_name", None) or "Opponent",
                "our_score": seton_score,
                "opponent_score": opponent_score,
                "lineup_json": _json.dumps(result.get("data", {}), default=str),
            }
        )
    except Exception as e:
        logger.debug(f"Failed to persist optimization run: {e}")

    return response


@router.post(
    "/optimize",
    response_model=OptimizationResponse,
    responses={400: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
)
async def optimize_lineup(request: OptimizationRequest):
    """
    Run lineup optimization for a swim meet.

    This endpoint accepts team data and optimization parameters,
    then returns the optimal lineup assignments.

    Args:
        request: Optimization request with team data and parameters

    Returns:
        Optimization results with scores and lineup assignments
    """
    start_time = time.time()

    try:
        is_championship = request.scoring_type in ["vcac_championship", "visaa_state"]
        logger.info(
            f"Optimization request: scoring_type={request.scoring_type}, is_championship={is_championship}"
        )

        seton_raw, seton_df, opponent_df, warnings = _validate_request(
            request, is_championship
        )
        method = request.optimizer_backend.value

        if is_championship:
            return await _run_championship_optimization(request, seton_raw, start_time)
        else:
            return await _run_dual_optimization(
                request, seton_df, opponent_df, method, start_time
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Optimization failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Optimization failed: {str(e)}")


@router.post("/optimize/preview")
async def preview_optimization(request: OptimizationRequest):
    """
    Get a quick preview of optimization without full computation.

    Useful for validating data before running full optimization.
    """
    try:
        # Validate and provide statistics about the input data
        seton_swimmers = set()
        seton_events = set()
        for entry in request.seton_data:
            seton_swimmers.add(entry.get("swimmer", "Unknown"))
            seton_events.add(entry.get("event", "Unknown"))

        opponent_swimmers = set()
        opponent_events = set()
        for entry in request.opponent_data:
            opponent_swimmers.add(entry.get("swimmer", "Unknown"))
            opponent_events.add(entry.get("event", "Unknown"))

        return {
            "valid": True,
            "seton": {
                "swimmer_count": len(seton_swimmers),
                "entry_count": len(request.seton_data),
                "events": list(seton_events),
            },
            "opponent": {
                "swimmer_count": len(opponent_swimmers),
                "entry_count": len(request.opponent_data),
                "events": list(opponent_events),
            },
            "common_events": list(seton_events & opponent_events),
            "optimizer": request.optimizer_backend.value,
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/optimize/compare")
async def compare_backends(request: OptimizationRequest):
    """
    Run optimization with multiple backends and compare results.

    Useful for validating AquaOptimizer against Gurobi or comparing strategies.
    Returns timing, scores, and confidence metrics for each backend.
    """
    import time

    # Backends to compare
    backends_to_test = ["aqua", "heuristic"]

    # Add Gurobi if available
    import importlib.util

    if importlib.util.find_spec("gurobipy") is not None:
        backends_to_test.append("gurobi")

    results = {}

    for backend in backends_to_test:
        start_time = time.time()
        try:
            # Create modified request with this backend

            # Use the optimization service
            from swim_ai_reflex.backend.services.optimization_service import (
                optimization_service,
            )
            from swim_ai_reflex.backend.utils.data_contracts import (
                normalize_roster,
                validate_team_entries,
            )

            # Convert request data
            seton_raw = [dict(entry) for entry in request.seton_data]
            opponent_raw = (
                [dict(entry) for entry in request.opponent_data]
                if request.opponent_data
                else []
            )

            seton_result = validate_team_entries(
                seton_raw, team_type="seton", remove_duplicates=True
            )
            opponent_result = validate_team_entries(
                opponent_raw, team_type="opponent", remove_duplicates=True
            )

            seton_df = normalize_roster(seton_result.entries, team="seton")
            opponent_df = normalize_roster(opponent_result.entries, team="opponent")

            # Run optimization
            result = await optimization_service.predict_best_lineups(
                seton_roster=seton_df,
                opponent_roster=opponent_df,
                method=backend,
                max_iters=100,
                enforce_fatigue=request.enforce_fatigue,
                scoring_type=request.scoring_type,
                robust_mode=request.robust_mode,
            )

            elapsed_ms = (time.time() - start_time) * 1000

            seton_score = 0
            opponent_score = 0
            if result.get("success"):
                data = result.get("data", {})
                seton_score = data.get("seton_score", 0)
                opponent_score = data.get("opponent_score", 0)

            results[backend] = {
                "success": result.get("success", False),
                "seton_score": seton_score,
                "opponent_score": opponent_score,
                "margin": seton_score - opponent_score,
                "time_ms": round(elapsed_ms, 1),
                "error": None,
            }

        except Exception as e:
            results[backend] = {
                "success": False,
                "seton_score": 0,
                "opponent_score": 0,
                "margin": 0,
                "time_ms": (time.time() - start_time) * 1000,
                "error": str(e),
            }

    # Analysis
    best_backend = max(
        [k for k, v in results.items() if v["success"]],
        key=lambda k: results[k]["margin"],
        default=None,
    )

    return {
        "results": results,
        "best_backend": best_backend,
        "backends_tested": backends_to_test,
        "recommendation": f"Use '{best_backend}' for best margin"
        if best_backend
        else "No successful backends",
    }


@router.get("/optimize/backends")
async def list_backends():
    """
    List available optimization backends and their status.
    """
    import importlib.util

    # Check Gurobi availability
    gurobi_available = importlib.util.find_spec("gurobipy") is not None

    backends = {
        "aqua": {
            "available": True,
            "description": "AquaOptimizer - Custom zero-cost optimizer with BeamSearch + SimulatedAnnealing",
            "recommended_for": "All use cases (recommended default)",
            "license": "None required",
        },
        "highs": {
            "available": True,
            "description": "HiGHS - Free open-source MIP solver with exact optimal solutions",
            "recommended_for": "When exact MIP solutions are needed without license",
            "license": "MIT (free)",
        },
        "heuristic": {
            "available": True,
            "description": "Fast greedy heuristic for quick results",
            "recommended_for": "Quick previews, large datasets",
            "license": "None required",
        },
        "gurobi": {
            "available": gurobi_available,
            "description": "Gurobi - Commercial MIP solver (requires license)",
            "recommended_for": "Legacy compatibility or when Gurobi is already licensed",
            "license": f"{'Active' if gurobi_available else 'Not installed'} ($10K+)",
        },
        "stackelberg": {
            "available": True,
            "description": "Game-theoretic bilevel optimization",
            "recommended_for": "Strategic analysis, opponent modeling",
            "license": "None required",
        },
    }

    return {"backends": backends, "default": "aqua", "recommended": "aqua"}


@router.get("/optimize/history")
async def get_optimization_history(opponent: str | None = None, limit: int = 10):
    """Get recent optimization runs for historical comparison."""
    try:
        from swim_ai_reflex.backend.persistence.sqlite_repository import (
            SQLiteRepository,
        )

        repo = SQLiteRepository()
        if opponent:
            runs = await repo.get_meets_by_opponent(opponent)
        else:
            runs = await repo.get_recent_meets(limit=limit)

        return {"runs": runs, "count": len(runs)}
    except Exception as e:
        logger.warning(f"History fetch failed: {e}")
        return {"runs": [], "count": 0}
