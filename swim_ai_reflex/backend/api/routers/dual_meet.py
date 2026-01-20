"""
Dual Meet Router

API endpoints for dual meet (2-team head-to-head) optimization.
"""

import logging
from typing import Any, Dict

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException

from swim_ai_reflex.backend.api.models.dual_meet import (
    DualMeetRequest,
    DualMeetResponse,
)
from swim_ai_reflex.backend.pipelines.dual_meet import (
    DualMeetInput,
    DualMeetPipeline,
)

router = APIRouter(prefix="/dual-meet", tags=["Dual Meet"])
logger = logging.getLogger(__name__)


def get_dual_meet_pipeline() -> DualMeetPipeline:
    """Dependency injection for dual meet pipeline."""
    return DualMeetPipeline()


@router.post(
    "/optimize",
    response_model=DualMeetResponse,
    summary="Optimize dual meet lineup",
    description="""
    Optimize lineup for a head-to-head dual meet.
    
    Takes rosters for both teams and returns the optimal lineup
    with scoring predictions and recommendations.
    
    **Optimization Methods:**
    - `gurobi`: Integer programming (most accurate, requires Gurobi license)
    - `nash`: Nash equilibrium game theory
    - `heuristic`: Fast greedy algorithm
    
    **Scoring:**
    - Individual: Top 7 score [8, 6, 5, 4, 3, 2, 1]
    - Relays: Top 3 score [10, 5, 3]
    - Total: 232 points
    """,
)
async def optimize_dual_meet(
    request: DualMeetRequest,
    pipeline: DualMeetPipeline = Depends(get_dual_meet_pipeline),
) -> DualMeetResponse:
    """Run dual meet optimization."""
    try:
        # Convert Pydantic models to DataFrames
        our_entries = [entry.model_dump() for entry in request.our_team.entries]
        opp_entries = [entry.model_dump() for entry in request.opponent.entries]

        our_roster = pd.DataFrame(our_entries)
        opponent_roster = pd.DataFrame(opp_entries)

        # Create pipeline input
        pipeline_input = DualMeetInput(
            our_roster=our_roster,
            opponent_roster=opponent_roster,
            our_team=request.our_team.team_name,
            opponent_team=request.opponent.team_name,
        )

        # Get options
        options = request.options or {}
        if hasattr(options, "model_dump"):
            options = options.model_dump()

        # Run pipeline
        result = pipeline.execute(
            pipeline_input,
            method=options.get("method", "gurobi"),
            max_iters=options.get("max_iters", 1000),
            enforce_fatigue=options.get("enforce_fatigue", False),
        )

        # Convert to response
        return DualMeetResponse(**result)

    except Exception as e:
        logger.exception(f"Dual meet optimization failed: {e}")
        return DualMeetResponse(
            success=False,
            our_score=0,
            opponent_score=0,
            total_points=0,
            winner="",
            is_valid=False,
            error=str(e),
        )


@router.post(
    "/validate",
    summary="Validate dual meet data",
    description="Validate team rosters without running full optimization.",
)
async def validate_dual_meet(
    request: DualMeetRequest,
    pipeline: DualMeetPipeline = Depends(get_dual_meet_pipeline),
) -> Dict[str, Any]:
    """Validate dual meet input data."""
    try:
        our_entries = [entry.model_dump() for entry in request.our_team.entries]
        opp_entries = [entry.model_dump() for entry in request.opponent.entries]

        our_roster = pd.DataFrame(our_entries)
        opponent_roster = pd.DataFrame(opp_entries)

        pipeline_input = DualMeetInput(
            our_roster=our_roster,
            opponent_roster=opponent_roster,
            our_team=request.our_team.team_name,
            opponent_team=request.opponent.team_name,
        )

        validation = pipeline.validate_input(pipeline_input)

        return {
            "valid": validation.valid,
            "errors": validation.errors,
            "warnings": validation.warnings,
            "our_team": {
                "name": request.our_team.team_name,
                "entry_count": len(request.our_team.entries),
            },
            "opponent": {
                "name": request.opponent.team_name,
                "entry_count": len(request.opponent.entries),
            },
        }

    except Exception as e:
        logger.exception(f"Validation failed: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get(
    "/scoring-info",
    summary="Get dual meet scoring information",
    description="Returns the scoring rules for dual meets.",
)
async def get_scoring_info() -> Dict[str, Any]:
    """Get dual meet scoring information."""
    return {
        "meet_type": "dual",
        "total_points": 232,
        "events": 8,
        "individual_scoring": {
            "places": 7,
            "points": [8, 6, 5, 4, 3, 2, 1],
            "points_per_event": 29,
        },
        "relay_scoring": {
            "places": 3,
            "points": [10, 5, 3],
        },
        "rules": {
            "max_individual_events": 2,
            "max_total_events": 4,
            "min_scoring_grade": 9,
            "exhibition_grades": [7, 8],
        },
    }
