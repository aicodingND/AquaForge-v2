"""
Models package init.

Production-ready Pydantic models for AquaForge.
"""

from swim_ai_reflex.backend.models.swimmer import (
    SwimmerTime,
    SwimmerProfile,
    TimeRecord,
    RosterEntry,
)

from swim_ai_reflex.backend.models.opponent import (
    CoachTendency,
    HistoricalLineup,
    OpponentProfile,
    MeetResult,
)

from swim_ai_reflex.backend.models.meet import (
    MeetImportance,
    ScheduledMeet,
    Season,
    SeasonGoals,
    SeasonPlan,
)

__all__ = [
    # Swimmer models
    "SwimmerTime",
    "SwimmerProfile", 
    "TimeRecord",
    "RosterEntry",
    # Opponent models
    "CoachTendency",
    "HistoricalLineup",
    "OpponentProfile",
    "MeetResult",
    # Meet models
    "MeetImportance",
    "ScheduledMeet",
    "Season",
    "SeasonGoals",
    "SeasonPlan",
]
