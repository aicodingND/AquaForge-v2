"""
Optimization Router

Provides endpoints for swim meet lineup optimization.
"""

import logging
import time
from typing import List

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
        # Check if this is championship mode (no opponent needed)
        is_championship = request.scoring_type in ["vcac_championship", "visaa_state"]
        logger.info(
            f"DEBUG: scoring_type={request.scoring_type}, is_championship={is_championship}"
        )
        logger.info(f"DEBUG: seton_data entries: {len(request.seton_data)}")
        logger.info(
            f"DEBUG: opponent_data entries: {len(request.opponent_data) if request.opponent_data else 0}"
        )

        # ============================================================
        # VALIDATION LAYER - Using centralized data_contracts module
        # ============================================================

        # Convert request data to raw dicts
        seton_raw = [dict(entry) for entry in request.seton_data]
        opponent_raw = (
            [dict(entry) for entry in request.opponent_data]
            if request.opponent_data
            else []
        )

        # Validate Seton data
        seton_result = validate_team_entries(
            seton_raw, team_type="seton", remove_duplicates=True
        )

        if seton_result.has_errors:
            error_detail = "; ".join(seton_result.error_messages())
            raise HTTPException(
                status_code=400, detail=f"Seton data validation failed: {error_detail}"
            )

        # Log any warnings
        for warning in seton_result.warnings:
            logger.warning(f"Seton data warning: {warning.message}")

        logger.info(f"Seton validation: {seton_result.stats}")

        # Validate Opponent data (only required for dual mode)
        if not is_championship:
            if not opponent_raw:
                raise HTTPException(
                    status_code=400,
                    detail="Opponent team data is required for dual mode",
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

            # Log warnings
            for warning in opponent_result.warnings:
                logger.warning(f"Opponent data warning: {warning.message}")

            logger.info(f"Opponent validation: {opponent_result.stats}")
        else:
            # Championship mode - create empty opponent result
            opponent_result = validate_team_entries([], team_type="opponent")
            opponent_result.entries = []

        # ============================================================
        # NORMALIZATION LAYER - Create typed DataFrames
        # ============================================================

        seton_df = normalize_roster(seton_result.entries, team="seton")
        opponent_df = normalize_roster(opponent_result.entries, team="opponent")

        # Collect all warnings for response
        all_warnings: List[str] = []
        all_warnings.extend(seton_result.warning_messages())
        if not is_championship:
            all_warnings.extend(opponent_result.warning_messages())

        # Import the optimization service
        from swim_ai_reflex.backend.services.optimization_service import (
            optimization_service,
        )

        logger.info(
            f"Starting optimization with {len(seton_df)} Seton entries, {len(opponent_df)} opponent entries"
        )
        logger.info(f"Using backend: {request.optimizer_backend}")

        # Map optimizer backend value
        method = (
            "heuristic" if request.optimizer_backend.value == "heuristic" else "gurobi"
        )

        # ===== CHAMPIONSHIP MODE: Use ChampionshipGurobiStrategy =====
        if is_championship:
            logger.info("Championship mode detected - using ChampionshipGurobiStrategy")
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

            # Import and run championship strategy
            from swim_ai_reflex.backend.core.strategies.championship_strategy import (
                ChampionshipGurobiStrategy,
            )

            strategy = ChampionshipGurobiStrategy(meet_profile=meet_profile)
            champ_result = strategy.optimize_entries(
                all_entries=entries,
                target_team="SST",  # Team CODE, not name - entries use SST not "Seton"
                time_limit=60,
            )

            # ===== NEW: Project full standings for ALL teams =====
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

                logger.info(
                    f"Converted {len(entries_for_projection)} entries for projection"
                )

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
                logger.info(
                    f"✅ Successfully projected standings for {num_standings} teams"
                )

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

        # ===== DUAL MEET MODE: Use standard optimization service =====
        else:
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
            return format_dual_meet_response(
                result=result,
                seton_score=seton_score,
                opponent_score=opponent_score,
                optimization_time_ms=optimization_time_ms,
                method=method,
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


@router.get("/optimize/backends")
async def list_backends():
    """
    List available optimization backends and their status.
    """
    backends = {
        "heuristic": {
            "available": True,
            "description": "Fast heuristic-based optimization",
            "recommended_for": "Quick results, large datasets",
        }
    }

    # Check Gurobi availability
    import importlib.util

    if importlib.util.find_spec("gurobipy") is not None:
        backends["gurobi"] = {
            "available": True,
            "description": "Optimal solution using integer programming",
            "recommended_for": "Best results, smaller datasets",
        }
    else:
        backends["gurobi"] = {
            "available": False,
            "description": "Gurobi optimizer (not installed)",
            "recommended_for": "N/A",
        }

    return {"backends": backends, "default": "heuristic"}
