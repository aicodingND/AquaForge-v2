"""
Qualifying Standards Router

Endpoints for checking championship qualifying status.

NOTE: This module imports ChampionshipPlanner from
swim_ai_reflex.backend.services.championship_planner. On this codebase,
the Mac version uses swim_ai_reflex.backend.services.championship/ (a package).
If ChampionshipPlanner is not found, ensure the correct import path is set
for your environment.
"""

import logging
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

# NOTE: The Windows codebase uses services.championship_planner (single file).
# The Mac codebase may use services.championship.planner or similar.
# Adjust this import if needed for your environment.
try:
    from swim_ai_reflex.backend.services.championship_planner import ChampionshipPlanner
except ImportError:
    try:
        from swim_ai_reflex.backend.services.championship.planner import (
            ChampionshipPlanner,  # type: ignore[assignment]
        )
    except ImportError:
        ChampionshipPlanner = None  # type: ignore[assignment,misc]

router = APIRouter()
logger = logging.getLogger(__name__)


class SwimmerTimeEntry(BaseModel):
    """Swimmer entry with event times."""

    swimmer: str
    event: str
    time: float
    grade: int = 12


class QualifyingCheckRequest(BaseModel):
    """Request to check qualifying status."""

    swimmers: list[SwimmerTimeEntry]
    level: str = Field(
        default="state", description="Qualifying level: state, regional, or national"
    )


class QualifyingStatusResponse(BaseModel):
    """Response with qualifying status for all swimmers."""

    swimmers: list[dict[str, Any]]
    summary: dict[str, int]


@router.post("/qualifying/check", response_model=QualifyingStatusResponse)
async def check_qualifying_status(request: QualifyingCheckRequest):
    """
    Check which swimmers have met qualifying standards.

    Groups by swimmer and returns status for each event.
    """
    if ChampionshipPlanner is None:
        raise HTTPException(
            status_code=501,
            detail="ChampionshipPlanner not available. Check import paths.",
        )

    try:
        planner = ChampionshipPlanner()

        # Group entries by swimmer
        swimmer_times: dict[str, dict[str, Any]] = {}

        for entry in request.swimmers:
            if entry.swimmer not in swimmer_times:
                swimmer_times[entry.swimmer] = {"grade": entry.grade, "events": {}}
            swimmer_times[entry.swimmer]["events"][entry.event] = entry.time

        # Check qualifying status for each swimmer
        swimmers_status: list[dict[str, Any]] = []
        total_qualified = 0
        total_close = 0
        total_needs_work = 0

        for swimmer_name, data in swimmer_times.items():
            status = planner.check_qualifying_status(
                swimmer_times=data["events"], level=request.level
            )

            # Format qualifications for frontend
            qualifications: list[dict[str, Any]] = []

            for q in status["qualified"]:
                qualifications.append(
                    {
                        "event": q["event"],
                        "best_time": q["time"],
                        "standard": q["standard"],
                        "status": "qualified",
                        "gap": -q["margin"],  # Negative = under standard
                    }
                )
                total_qualified += 1

            for q in status["close"]:
                qualifications.append(
                    {
                        "event": q["event"],
                        "best_time": q["time"],
                        "standard": q["standard"],
                        "status": "close",
                        "gap": q["gap"],
                    }
                )
                total_close += 1

            for q in status["needs_improvement"]:
                qualifications.append(
                    {
                        "event": q["event"],
                        "best_time": q["time"],
                        "standard": q["standard"],
                        "status": "needs_work",
                        "gap": q["gap"],
                    }
                )
                total_needs_work += 1

            swimmers_status.append(
                {
                    "swimmer": swimmer_name,
                    "grade": data["grade"],
                    "qualifications": qualifications,
                }
            )

        return QualifyingStatusResponse(
            swimmers=swimmers_status,
            summary={
                "total_qualified": total_qualified,
                "total_close": total_close,
                "total_needs_work": total_needs_work,
            },
        )

    except Exception as e:
        logger.error(f"Qualifying check failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/qualifying/standards/{level}")
async def get_qualifying_standards(level: str = "state"):
    """
    Get qualifying time standards for a specific level.
    """
    if ChampionshipPlanner is None:
        raise HTTPException(
            status_code=501,
            detail="ChampionshipPlanner not available. Check import paths.",
        )

    try:
        planner = ChampionshipPlanner()
        standards = planner.qualifying_standards.get(level, [])

        return {
            "level": level,
            "standards": [
                {"event": s.event, "time_standard": s.time_standard, "level": s.level}
                for s in standards
            ],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
