"""
Live Tracker API Router

API endpoints for real-time meet tracking during championship meets.
"""

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from swim_ai_reflex.backend.services.live_meet_tracker import (
    LiveMeetTracker,
    create_live_tracker,
)

router = APIRouter(prefix="/live", tags=["live-tracking"])

# In-memory tracker instances (keyed by meet_name)
# In production, use Redis or database for persistence
_trackers: dict[str, LiveMeetTracker] = {}


# ============================================================================
# Request/Response Models
# ============================================================================


class InitializeMeetRequest(BaseModel):
    """Request to initialize a meet for live tracking."""

    meet_name: str = Field(..., description="Name of the meet")
    meet_profile: str = Field("vcac_championship", description="Meet rules profile")
    target_team: str = Field("SST", description="Team to focus analysis on")
    entries: list[dict] = Field(..., description="Psych sheet entries")


class RecordResultRequest(BaseModel):
    """Request to record a single result."""

    meet_name: str = Field(..., description="Meet identifier")
    event: str = Field(..., description="Event name (e.g., 'Boys 50 Free')")
    place: int = Field(..., ge=1, le=20, description="Finishing place")
    swimmer: str = Field(..., description="Swimmer name")
    team: str = Field(..., description="Team name/code")
    time: float = Field(..., description="Time in seconds or dive score")
    is_official: bool = Field(True, description="Whether result is official/scoring")


class RecordEventRequest(BaseModel):
    """Request to record all results for an event."""

    meet_name: str = Field(..., description="Meet identifier")
    event: str = Field(..., description="Event name")
    results: list[dict] = Field(..., description="List of result dicts")


class StandingsResponse(BaseModel):
    """Current standings with projections."""

    team_totals: dict[str, float]
    projected_remaining: dict[str, float]
    combined_totals: dict[str, float]
    events_completed: int
    events_remaining: int
    sorted_standings: list[dict]  # Sorted by points


class ClinchResponse(BaseModel):
    """Clinch scenario analysis."""

    target_team: str
    current_position: int
    scenarios: list[dict]


# ============================================================================
# Endpoints
# ============================================================================


@router.post("/initialize", status_code=status.HTTP_201_CREATED)
def initialize_meet(request: InitializeMeetRequest) -> dict:
    """
    Initialize a meet for live tracking.

    Creates a new tracker instance with psych sheet data for projections.
    """
    # Create tracker if not exists
    if request.meet_name in _trackers:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Meet '{request.meet_name}' already initialized. Use /reset to restart.",
        )

    tracker = create_live_tracker(meet_profile=request.meet_profile)
    tracker.set_psych_sheet(
        entries=request.entries,
        target_team=request.target_team,
        meet_name=request.meet_name,
    )

    _trackers[request.meet_name] = tracker

    return {
        "message": f"Meet '{request.meet_name}' initialized",
        "entry_count": len(request.entries),
        "teams_count": len(tracker.teams),
        "teams": list(tracker.teams),
    }


@router.post("/result")
def record_result(request: RecordResultRequest) -> dict:
    """
    Record a single result.

    Updates the tracker with one swimmer's result and recalculates standings.
    """
    tracker = _get_tracker(request.meet_name)

    result = tracker.record_result(
        event=request.event,
        place=request.place,
        swimmer=request.swimmer,
        team=request.team,
        time=request.time,
        is_official=request.is_official,
    )

    # Get updated standings
    standings = tracker.get_current_standings()

    return {
        "result": {
            "event": result.event,
            "place": result.place,
            "swimmer": result.swimmer,
            "team": result.team,
            "points": result.points,
            "timestamp": result.timestamp.isoformat(),
        },
        "event_complete": request.event in tracker.completed_events,
        "current_standings": {
            team: standings.team_totals.get(team, 0) for team in tracker.teams
        },
    }


@router.post("/event")
def record_event(request: RecordEventRequest) -> dict:
    """
    Record all results for an event at once.

    Bulk operation for entering complete event results.
    """
    tracker = _get_tracker(request.meet_name)

    results = tracker.record_event_results(event=request.event, results=request.results)

    return {
        "event": request.event,
        "results_recorded": len(results),
        "event_complete": True,
        "top_3": [
            {"place": r.place, "swimmer": r.swimmer, "team": r.team, "points": r.points}
            for r in sorted(results, key=lambda x: x.place)[:3]
        ],
    }


@router.get("/standings/{meet_name}")
def get_standings(meet_name: str) -> StandingsResponse:
    """
    Get current standings combining actual and projected points.
    """
    tracker = _get_tracker(meet_name)
    standings = tracker.get_current_standings()

    # Sort standings
    sorted_standings = sorted(
        [
            {
                "team": team,
                "actual": standings.team_totals.get(team, 0),
                "projected": standings.projected_remaining.get(team, 0),
                "total": total,
            }
            for team, total in standings.combined_totals.items()
        ],
        key=lambda x: x["total"],
        reverse=True,
    )

    return StandingsResponse(
        team_totals=standings.team_totals,
        projected_remaining=standings.projected_remaining,
        combined_totals=standings.combined_totals,
        events_completed=standings.events_completed,
        events_remaining=standings.events_remaining,
        sorted_standings=sorted_standings,
    )


@router.get("/remaining/{meet_name}")
def get_remaining_points(meet_name: str) -> dict:
    """
    Get points still available in remaining events.
    """
    tracker = _get_tracker(meet_name)
    remaining = tracker.get_remaining_points()

    return {"meet_name": meet_name, "remaining_by_team": remaining}


@router.get("/clinch/{meet_name}/{target_team}")
def get_clinch_scenarios(meet_name: str, target_team: str) -> ClinchResponse:
    """
    Get clinch scenario analysis for a specific team.

    Shows what's needed to clinch each position and danger of being caught.
    """
    tracker = _get_tracker(meet_name)
    scenarios = tracker.get_clinch_scenarios(target_team)

    # Get current position
    standings = tracker.get_current_standings()
    sorted_teams = sorted(
        standings.combined_totals.items(), key=lambda x: x[1], reverse=True
    )
    current_pos = next(
        (i + 1 for i, (team, _) in enumerate(sorted_teams) if team == target_team), 0
    )

    return ClinchResponse(
        target_team=target_team,
        current_position=current_pos,
        scenarios=[
            {
                "position": s.target_position,
                "points_ahead": s.points_ahead,
                "points_behind": s.points_behind,
                "can_clinch": s.can_clinch,
                "requirements": s.clinch_requirements,
                "can_be_caught": s.can_be_caught,
                "dangers": s.danger_scenarios,
            }
            for s in scenarios
        ],
    )


@router.get("/swing/{meet_name}")
def get_swing_events(meet_name: str, target_team: str | None = "SST") -> dict:
    """
    Get remaining swing events with high scoring potential.
    """
    tracker = _get_tracker(meet_name)
    swing = tracker.get_swing_remaining(target_team)

    return {"meet_name": meet_name, "target_team": target_team, "swing_events": swing}


@router.get("/summary/{meet_name}")
def get_coach_summary(meet_name: str, target_team: str | None = "SST") -> dict:
    """
    Get formatted coach summary with standings and recommendations.
    """
    tracker = _get_tracker(meet_name)
    summary = tracker.generate_coach_summary(target_team)

    return {"meet_name": meet_name, "target_team": target_team, "summary": summary}


@router.get("/status/{meet_name}")
def get_event_status(meet_name: str) -> dict:
    """
    Get status of all events (completed, in_progress, upcoming).
    """
    tracker = _get_tracker(meet_name)
    status_map = tracker.get_event_status()

    # Group by status
    completed = [e for e, s in status_map.items() if s == "completed"]
    in_progress = [e for e, s in status_map.items() if s == "in_progress"]
    upcoming = [e for e, s in status_map.items() if s == "upcoming"]

    return {
        "meet_name": meet_name,
        "completed": completed,
        "in_progress": in_progress,
        "upcoming": upcoming,
        "progress": {
            "completed": len(completed),
            "total": len(tracker.EVENT_ORDER),
            "percent": round(len(completed) / len(tracker.EVENT_ORDER) * 100, 1),
        },
    }


@router.delete("/reset/{meet_name}")
def reset_meet(meet_name: str) -> dict:
    """
    Reset/delete a meet tracker.
    """
    if meet_name not in _trackers:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Meet '{meet_name}' not found",
        )

    del _trackers[meet_name]

    return {"message": f"Meet '{meet_name}' reset successfully"}


# ============================================================================
# Helper Functions
# ============================================================================


def _get_tracker(meet_name: str) -> LiveMeetTracker:
    """Get tracker instance or raise 404."""
    if meet_name not in _trackers:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Meet '{meet_name}' not initialized. Use POST /api/v1/live/initialize first.",
        )
    return _trackers[meet_name]
