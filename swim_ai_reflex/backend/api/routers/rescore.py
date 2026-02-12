"""
Rescore Router - Fast re-scoring of modified lineups without full optimization.
Used for what-if scenarios and lineup editor.
"""

from __future__ import annotations

import logging
from typing import Any

import pandas as pd
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from swim_ai_reflex.backend.core.rules import get_rules
from swim_ai_reflex.backend.core.scoring import full_meet_scoring
from swim_ai_reflex.backend.services.advanced_analytics_service import (
    AdvancedAnalyticsService,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["rescore"])


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------


class RescoreEntry(BaseModel):
    swimmer: str
    event: str
    time: float
    team: str
    grade: int | None = None
    is_relay: bool = False


class RescoreRequest(BaseModel):
    entries: list[RescoreEntry]
    meet_type: str = Field(default="dual", description="'dual' or 'champ'")


class SwingAnalysisRequest(BaseModel):
    entries: list[RescoreEntry]
    meet_type: str = Field(default="dual")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _entries_to_dataframe(entries: list[RescoreEntry]) -> pd.DataFrame:
    """Convert a list of ``RescoreEntry`` models into the DataFrame format
    expected by ``full_meet_scoring``.
    """
    rows = []
    for e in entries:
        rows.append(
            {
                "swimmer": e.swimmer,
                "event": e.event,
                "time": e.time,
                "team": e.team,
                "grade": e.grade if e.grade is not None else 10,
                "is_relay": e.is_relay,
                "is_diving": False,
            }
        )
    return pd.DataFrame(rows)


def _build_event_breakdown(scored_df: pd.DataFrame) -> list[dict[str, Any]]:
    """Build a per-event breakdown from a scored DataFrame."""
    breakdown: list[dict[str, Any]] = []
    for event_name, event_group in scored_df.groupby("event"):
        swimmers = []
        for _, row in event_group.sort_values("place").iterrows():
            swimmers.append(
                {
                    "swimmer": row["swimmer"],
                    "team": row["team"],
                    "time": float(row["time"]),
                    "place": int(row["place"]),
                    "points": float(row["points"]),
                }
            )
        breakdown.append(
            {
                "event": event_name,
                "swimmers": swimmers,
            }
        )
    return breakdown


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/rescore")
async def rescore_lineup(request: RescoreRequest) -> dict[str, Any]:
    """
    Fast re-score a lineup.  No optimisation -- just scoring.
    Used by the lineup editor for instant feedback.
    """
    if not request.entries:
        raise HTTPException(status_code=400, detail="entries list must not be empty")

    try:
        rules = get_rules(request.meet_type)
        df = _entries_to_dataframe(request.entries)
        scored_df, totals = full_meet_scoring(df, rules, validate=False)

        event_breakdown = _build_event_breakdown(scored_df)

        return {
            "seton_score": totals.get("seton", 0.0),
            "opponent_score": totals.get("opponent", 0.0),
            "margin": round(totals.get("seton", 0.0) - totals.get("opponent", 0.0), 2),
            "meet_type": request.meet_type,
            "events": event_breakdown,
        }
    except Exception as exc:
        logger.exception("Rescore failed")
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/swing-analysis")
async def get_swing_analysis(request: SwingAnalysisRequest) -> dict[str, Any]:
    """
    Get point swing analysis for a scored lineup.

    Steps:
    1. Score the lineup using the requested meet rules.
    2. Run ``point_swing_analysis`` to find per-event swing opportunities.
    3. Run ``generate_coaching_summary`` for a high-level overview.
    4. Return both.
    """
    if not request.entries:
        raise HTTPException(status_code=400, detail="entries list must not be empty")

    try:
        rules = get_rules(request.meet_type)
        df = _entries_to_dataframe(request.entries)
        scored_df, totals = full_meet_scoring(df, rules, validate=False)

        analytics_svc = AdvancedAnalyticsService()
        swing = analytics_svc.point_swing_analysis(scored_df, totals, rules)
        summary = analytics_svc.generate_coaching_summary(swing, totals)

        return {
            "seton_score": totals.get("seton", 0.0),
            "opponent_score": totals.get("opponent", 0.0),
            "swing_analysis": swing,
            "coaching_summary": summary,
        }
    except Exception as exc:
        logger.exception("Swing analysis failed")
        raise HTTPException(status_code=500, detail=str(exc))
