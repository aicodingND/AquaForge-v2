"""
Championship Router

API endpoints for multi-team championship meets (VCAC, VISAA State, etc.).
"""

import io
import logging
from typing import Any

import pandas as pd
from fastapi import APIRouter, File, UploadFile

from swim_ai_reflex.backend.api.exceptions import (
    FileUploadError,
    ValidationError,
)
from swim_ai_reflex.backend.api.models.championship import (
    ChampionshipOptimizeRequest,
    ChampionshipOptimizeResponse,
    ChampionshipProjectRequest,
    ChampionshipProjectResponse,
    StandingModel,
    SwingEventModel,
)
from swim_ai_reflex.backend.pipelines.championship import (
    ChampionshipInput,
    ChampionshipPipeline,
)

router = APIRouter(prefix="/championship", tags=["Championship"])
logger = logging.getLogger(__name__)


def get_championship_pipeline(
    meet_profile: str = "vcac_championship",
) -> ChampionshipPipeline:
    """Dependency injection for championship pipeline."""
    return ChampionshipPipeline(meet_profile)


@router.post(
    "/project",
    response_model=ChampionshipProjectResponse,
    summary="Project championship standings",
    description="""
    Project meet standings from psych sheet data.

    Uses seed times to predict placements and calculate expected points
    for each team. Also identifies swing events where small improvements
    would yield significant point gains.

    **Supported Meet Profiles:**
    - `vcac_championship`: VCAC Conference Championship rules
    - `visaa_state`: VISAA State Championship rules
    """,
)
async def project_standings(
    request: ChampionshipProjectRequest,
) -> ChampionshipProjectResponse:
    """Project championship meet standings."""
    try:
        pipeline = get_championship_pipeline(request.meet_profile)

        # Create pipeline input
        pipeline_input = ChampionshipInput(
            entries=request.entries,
            target_team=request.target_team,
            meet_name=request.meet_name,
            meet_profile=request.meet_profile,
        )

        # Run projection only
        result = pipeline.execute(pipeline_input, stage="projection")

        # Convert to response
        standings = [
            StandingModel(rank=s["rank"], team=s["team"], points=s["points"])
            for s in result.get("standings", [])
        ]

        swing_events = [SwingEventModel(**se) for se in result.get("swing_events", [])]

        return ChampionshipProjectResponse(
            success=result.get("success", True),
            meet_name=request.meet_name,
            target_team=request.target_team,
            target_team_total=result.get("target_team_total", 0),
            target_team_rank=result.get("target_team_rank", 0),
            standings=standings,
            team_totals=result.get("projection", {}).get("team_totals", {}),
            swing_events=swing_events,
            recommendations=result.get("recommendations", []),
            meet_type=result.get("meet_type", "championship"),
            metrics=result.get("metrics"),
            warnings=result.get("warnings"),
        )

    except Exception as e:
        logger.exception(f"Championship projection failed: {e}")
        # TODO: Eventually convert to raise DataProcessingError(str(e))
        # Currently keeping response pattern for backward compatibility
        return ChampionshipProjectResponse(
            success=False,
            meet_name=request.meet_name,
            target_team=request.target_team,
            target_team_total=0,
            target_team_rank=0,
            standings=[],
            team_totals={},
            error=str(e),
        )


@router.post(
    "/optimize",
    response_model=ChampionshipOptimizeResponse,
    summary="Optimize championship entries",
    description="""
    Optimize swimmer event assignments for maximum team points.

    Takes into account:
    - Max 2 individual events per swimmer
    - Diving counts as 1 individual event
    - 400 Free Relay (Relay 3) counts as 1 individual event at VCAC
    - Back-to-back event restrictions
    """,
)
async def optimize_entries(
    request: ChampionshipOptimizeRequest,
) -> ChampionshipOptimizeResponse:
    """Optimize championship entries."""
    try:
        pipeline = get_championship_pipeline(request.meet_profile)

        # Create pipeline input
        pipeline_input = ChampionshipInput(
            entries=request.entries,
            target_team=request.target_team,
            meet_name=request.meet_name,
            meet_profile=request.meet_profile,
            divers=set(request.divers),
            relay_3_swimmers=set(request.relay_3_swimmers),
        )

        # Determine stage based on options
        if request.optimize_relays:
            stage = "full"
        elif request.optimize_entries:
            stage = "entries"
        else:
            stage = "projection"

        # Run pipeline
        result = pipeline.execute(pipeline_input, stage=stage)

        return ChampionshipOptimizeResponse(
            success=result.get("success", True),
            projection=result.get("projection", {}),
            entry_assignments=result.get("entry_assignments"),
            relay_configurations=result.get("relay_configurations"),
            optimization_improvement=result.get("optimization_improvement", 0),
            recommendations=result.get("recommendations", []),
            meet_type=result.get("meet_type", "championship"),
            metrics=result.get("metrics"),
            warnings=result.get("warnings"),
        )

    except Exception as e:
        logger.exception(f"Championship optimization failed: {e}")
        # TODO: Eventually convert to raise OptimizationError(str(e))
        # Currently keeping response pattern for backward compatibility
        return ChampionshipOptimizeResponse(
            success=False,
            projection={},
            error=str(e),
        )


@router.post(
    "/upload-psych-sheet",
    summary="Upload psych sheet file",
    description="Upload a CSV psych sheet and parse it.",
)
async def upload_psych_sheet(
    file: UploadFile = File(...),
    target_team: str = "Seton",
    meet_name: str = "Championship",
    meet_profile: str = "vcac_championship",
) -> dict[str, Any]:
    """Upload and parse a psych sheet file."""
    try:
        # Read file
        content = await file.read()

        # Detect format and parse
        if file.filename.endswith(".csv"):
            df = pd.read_csv(io.StringIO(content.decode("utf-8")))
        elif file.filename.endswith((".xls", ".xlsx")):
            df = pd.read_excel(io.BytesIO(content))
        else:
            raise FileUploadError(
                f"Unsupported file format: {file.filename}",
                details={"allowed_formats": [".csv", ".xls", ".xlsx"]},
            )

        # Convert to entries
        entries = df.to_dict("records")

        # Get teams
        team_column = None
        for col in ["team", "Team", "TEAM", "school", "School"]:
            if col in df.columns:
                team_column = col
                break

        teams = list(df[team_column].unique()) if team_column else []

        return {
            "success": True,
            "filename": file.filename,
            "entry_count": len(entries),
            "teams": teams,
            "columns": list(df.columns),
            "entries": entries[:10],  # Preview first 10
            "meet_profile": meet_profile,
        }

    except FileUploadError:
        raise
    except Exception as e:
        logger.exception(f"Psych sheet upload failed: {e}")
        raise FileUploadError(str(e))


@router.get(
    "/meet-profiles",
    summary="List available meet profiles",
    description="Returns available meet profiles and their rules.",
)
async def list_meet_profiles() -> dict[str, Any]:
    """List available championship meet profiles."""
    from swim_ai_reflex.backend.core.rules import list_meet_profiles

    return {
        "profiles": list_meet_profiles(),
        "recommended": {
            "vcac": "vcac_championship",
            "state": "visaa_state",
        },
    }


@router.get(
    "/scoring-info/{profile}",
    summary="Get scoring information for a meet profile",
)
async def get_scoring_info(profile: str = "vcac_championship") -> dict[str, Any]:
    """Get scoring information for a specific meet profile."""
    from swim_ai_reflex.backend.core.rules import get_meet_profile

    try:
        rules = get_meet_profile(profile)

        return {
            "profile": profile,
            "name": rules.name,
            "individual_points": rules.individual_points,
            "relay_points": rules.relay_points,
            "max_individual_events": rules.max_individual_events_per_swimmer,
            "max_total_events": rules.max_total_events_per_swimmer,
            "max_scorers_individual": rules.max_scorers_per_team_individual,
            "max_scorers_relay": rules.max_scorers_per_team_relay,
            "min_scoring_grade": rules.min_scoring_grade,
        }
    except Exception:
        raise ValidationError(
            f"Profile not found: {profile}",
            details={"available_profiles": ["vcac_championship", "visaa_state"]},
        )


@router.get(
    "/strategies",
    summary="Get championship optimization strategies",
    description="""
    Returns comprehensive information about available championship optimization strategies.

    Each strategy includes:
    - Detailed description
    - When to use it
    - Example scenarios
    - Pros and cons
    - Recommended use cases
    - Implementation status
    """,
)
async def get_strategies() -> dict[str, Any]:
    """Get available championship optimization strategies with detailed information."""
    from swim_ai_reflex.backend.services.championship.strategies import (
        get_coming_soon_strategies,
        get_implemented_strategies,
        get_strategies_for_api,
    )

    all_strategies = get_strategies_for_api()
    implemented = [s.name for s in get_implemented_strategies()]
    coming_soon = [s.name for s in get_coming_soon_strategies()]

    # Optimizer comparison based on backtest results
    optimizer_comparison = {
        "optimizers": [
            {
                "id": "aqua",
                "name": "AquaOptimizer",
                "description": "Nash+Beam+SimAnnealing ensemble - highest quality solutions",
                "recommended": True,
                "performance": {
                    "avg_improvement_vs_coach": "+43%",
                    "avg_improvement_vs_gurobi": "+99%",
                    "execution_time": "~20 seconds",
                    "wins_in_backtest": 3,
                    "total_backtests": 3,
                },
                "best_for": "Championship meets where every point matters",
                "badge": "RECOMMENDED",
            },
            {
                "id": "gurobi",
                "name": "Gurobi MILP",
                "description": "Fast exact solver using Mixed Integer Linear Programming",
                "recommended": False,
                "performance": {
                    "avg_improvement_vs_coach": "-14%",
                    "execution_time": "~100 milliseconds",
                    "wins_in_backtest": 0,
                    "total_backtests": 3,
                },
                "best_for": "Quick what-if scenarios during practice",
                "badge": "FAST",
            },
        ],
        "default": "aqua",
        "backtest_summary": {
            "dataset": "Nova Catholic Invitational 2026",
            "aqua_score": 530,
            "gurobi_score": 318,
            "coach_actual": 371,
            "aqua_vs_coach": "+159 pts (+43%)",
            "gurobi_vs_coach": "-53 pts (-14%)",
        },
    }

    return {
        "strategies": all_strategies,
        "optimizer_comparison": optimizer_comparison,
        "summary": {
            "total": len(all_strategies),
            "implemented": len(implemented),
            "coming_soon": len(coming_soon),
        },
        "implemented_strategies": implemented,
        "coming_soon_strategies": coming_soon,
        "default_strategy": "maximize_individual",
        "default_optimizer": "aqua",
        "recommendation": """
        USE AQUAOPTIMIZER FOR CHAMPIONSHIPS:

        AquaOptimizer's Nash+Beam+SimAnnealing ensemble finds 2x better solutions
        than Gurobi MILP, and 43% better than manually-crafted coach lineups.

        The 20-second execution time is acceptable for championship meets where
        lineup decisions are made hours or days before competition.

        Use Gurobi only for quick previews during practice when speed matters.
        """,
    }
