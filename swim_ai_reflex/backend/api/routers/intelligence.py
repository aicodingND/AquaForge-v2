"""
Intelligence API Router

Endpoints for swim intelligence analysis:
- Trajectory prediction (time improvement/decline trends)
- Psychological profiling (clutch performance, consistency)
- Coach tendency analysis (lineup pattern prediction)
- LLM-powered strategy advice
"""

import logging

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from swim_ai_reflex.backend.intelligence.coach_tendency import (
    coach_tendency_analyzer,
)
from swim_ai_reflex.backend.intelligence.psychological import (
    PsychologicalProfile,
    psychological_profiler,
)
from swim_ai_reflex.backend.intelligence.trajectory import (
    trajectory_predictor,
)
from swim_ai_reflex.backend.models.opponent import CoachTendency
from swim_ai_reflex.backend.services.intelligence_service import (
    get_swimmer_name,
    get_swimmer_profile_data,
    get_swimmer_time_records,
    get_team_meet_results,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/intelligence")


# ==================== Request/Response Models ====================


class TrajectoryResponse(BaseModel):
    success: bool
    swimmer_id: int
    swimmer_name: str
    trajectories: list[dict]
    event_count: int


class PsychologicalResponse(BaseModel):
    success: bool
    swimmer_id: int
    swimmer_name: str
    profile: dict


class CoachTendencyResponse(BaseModel):
    success: bool
    team_name: str
    tendency: dict
    meet_count: int


class LLMAdviceRequest(BaseModel):
    seton_roster: list[dict]
    opponent_roster: list[dict]
    meet_context: dict | None = None


class LLMAdviceResponse(BaseModel):
    success: bool
    available: bool
    recommendation: str
    confidence: float
    rationale: str
    key_insights: list[str]
    tactical_adjustments: list[str]
    risk_level: str


# ==================== Endpoints ====================


@router.get("/trajectory/{swimmer_id}", response_model=TrajectoryResponse)
async def get_trajectory(
    swimmer_id: int,
    event: str | None = Query(None, description="Filter to specific event"),
):
    """Analyze a swimmer's performance trajectory over time.

    Returns trend analysis, improvement rate, plateau detection,
    and predicted future times.
    """
    swimmer_name = get_swimmer_name(swimmer_id)
    if not swimmer_name:
        raise HTTPException(status_code=404, detail="Swimmer not found")

    time_records = get_swimmer_time_records(swimmer_id, event_name=event)

    if not time_records:
        return TrajectoryResponse(
            success=True,
            swimmer_id=swimmer_id,
            swimmer_name=swimmer_name,
            trajectories=[],
            event_count=0,
        )

    # Group records by event
    events: dict[str, list] = {}
    for record in time_records:
        events.setdefault(record.event, []).append(record)

    # Analyze each event's trajectory
    trajectories = []
    for event_name, records in events.items():
        trajectory = trajectory_predictor.analyze_trajectory(
            swimmer=swimmer_name,
            event=event_name,
            times=records,
        )
        trajectories.append(trajectory.model_dump(mode="json"))

    return TrajectoryResponse(
        success=True,
        swimmer_id=swimmer_id,
        swimmer_name=swimmer_name,
        trajectories=trajectories,
        event_count=len(trajectories),
    )


@router.get("/psychological/{swimmer_id}", response_model=PsychologicalResponse)
async def get_psychological_profile(swimmer_id: int):
    """Build a psychological performance profile for a swimmer.

    Analyzes clutch performance, consistency, rivalry effects,
    and home/away patterns.
    """
    swimmer_name = get_swimmer_name(swimmer_id)
    if not swimmer_name:
        raise HTTPException(status_code=404, detail="Swimmer not found")

    meet_results, swimmer_times = get_swimmer_profile_data(swimmer_id)

    if not swimmer_times:
        return PsychologicalResponse(
            success=True,
            swimmer_id=swimmer_id,
            swimmer_name=swimmer_name,
            profile=PsychologicalProfile(
                swimmer=swimmer_name, sample_size=0, confidence=0.0
            ).model_dump(),
        )

    profile = psychological_profiler.build_profile(
        swimmer=swimmer_name,
        meet_results=meet_results,
        swimmer_times=swimmer_times,
    )

    return PsychologicalResponse(
        success=True,
        swimmer_id=swimmer_id,
        swimmer_name=swimmer_name,
        profile=profile.model_dump(),
    )


@router.get("/coach-tendency/{team_name}", response_model=CoachTendencyResponse)
async def get_coach_tendency(
    team_name: str,
    coach_name: str | None = Query(None, description="Coach name if known"),
):
    """Analyze coaching patterns for an opponent team.

    Discovers lineup tendencies, star swimmer placement patterns,
    relay resting habits, and predictability score.
    """
    meet_results = get_team_meet_results(team_name)

    if not meet_results:
        return CoachTendencyResponse(
            success=True,
            team_name=team_name,
            tendency=CoachTendency(
                coach_name=coach_name or "Unknown",
                team_name=team_name,
                sample_size=0,
                confidence=0.0,
            ).model_dump(mode="json"),
            meet_count=0,
        )

    tendency = coach_tendency_analyzer.analyze_history(
        past_meets=meet_results,
        team_name=team_name,
        coach_name=coach_name,
    )

    return CoachTendencyResponse(
        success=True,
        team_name=team_name,
        tendency=tendency.model_dump(mode="json"),
        meet_count=len(meet_results),
    )


@router.post("/llm-advice", response_model=LLMAdviceResponse)
async def get_llm_advice(request: LLMAdviceRequest):
    """Get AI-powered strategy advice for a matchup.

    Uses LLM (when configured with OPENAI_API_KEY) to analyze
    lineup matchups and suggest tactical decisions. Falls back
    to rule-based analysis when LLM is unavailable.
    """
    from swim_ai_reflex.backend.intelligence.llm_advisor import LLMStrategyAdvisor

    advisor = LLMStrategyAdvisor()

    recommendation = advisor.analyze_lineup_strategy(
        seton_roster=request.seton_roster,
        opponent_roster=request.opponent_roster,
        meet_context=request.meet_context,
    )

    return LLMAdviceResponse(
        success=True,
        available=advisor.available,
        recommendation=recommendation.recommendation,
        confidence=recommendation.confidence,
        rationale=recommendation.rationale,
        key_insights=recommendation.key_insights,
        tactical_adjustments=recommendation.tactical_adjustments,
        risk_level=recommendation.risk_level,
    )
