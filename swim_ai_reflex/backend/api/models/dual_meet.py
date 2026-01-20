"""
Dual Meet API Models

Pydantic models for dual meet request/response validation.
"""

from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field, field_validator


class SwimmerEntryModel(BaseModel):
    """A single swimmer entry."""

    swimmer: str = Field(..., description="Swimmer's name")
    event: str = Field(..., description="Event name")
    time: Union[float, str] = Field(..., description="Time in seconds or string format")
    grade: Optional[int] = Field(None, description="Grade level (7-12)")
    is_exhibition: Optional[bool] = Field(False, description="Exhibition swimmer")

    @field_validator("swimmer")
    @classmethod
    def validate_swimmer(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Swimmer name cannot be empty")
        return v.strip()

    @field_validator("event")
    @classmethod
    def validate_event(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Event cannot be empty")
        return v.strip()


class TeamRosterModel(BaseModel):
    """Team roster with entries."""

    team_name: str = Field(..., description="Team name")
    entries: List[SwimmerEntryModel] = Field(..., description="List of swimmer entries")

    @field_validator("team_name")
    @classmethod
    def validate_team_name(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Team name cannot be empty")
        return v.strip()


class DualMeetOptions(BaseModel):
    """Options for dual meet optimization."""

    method: str = Field(
        "gurobi", description="Optimization method: gurobi, nash, heuristic"
    )
    max_iters: int = Field(1000, description="Maximum iterations")
    enforce_fatigue: bool = Field(False, description="Apply fatigue penalties")
    scoring_type: str = Field("visaa_top7", description="Scoring type")

    @field_validator("method")
    @classmethod
    def validate_method(cls, v: str) -> str:
        allowed = {"gurobi", "nash", "heuristic"}
        if v.lower() not in allowed:
            raise ValueError(f"Method must be one of: {allowed}")
        return v.lower()


class DualMeetRequest(BaseModel):
    """Request for dual meet optimization."""

    our_team: TeamRosterModel = Field(..., description="Our team roster")
    opponent: TeamRosterModel = Field(..., description="Opponent team roster")
    options: Optional[DualMeetOptions] = Field(
        default_factory=DualMeetOptions, description="Optimization options"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "our_team": {
                    "team_name": "Seton",
                    "entries": [
                        {
                            "swimmer": "John Smith",
                            "event": "100 Free",
                            "time": 52.34,
                            "grade": 11,
                        },
                        {
                            "swimmer": "Jane Doe",
                            "event": "50 Free",
                            "time": 26.12,
                            "grade": 10,
                        },
                    ],
                },
                "opponent": {
                    "team_name": "Trinity",
                    "entries": [
                        {
                            "swimmer": "Bob Jones",
                            "event": "100 Free",
                            "time": 53.01,
                            "grade": 12,
                        },
                    ],
                },
                "options": {"method": "gurobi", "enforce_fatigue": False},
            }
        }
    }


class EventBreakdownModel(BaseModel):
    """Breakdown for a single event."""

    event: str
    our_points: float
    opponent_points: float
    entries: List[Dict[str, Any]]


class DualMeetResponse(BaseModel):
    """Response from dual meet optimization."""

    success: bool = Field(..., description="Whether optimization succeeded")
    our_score: float = Field(..., description="Our team's score")
    opponent_score: float = Field(..., description="Opponent's score")
    total_points: float = Field(..., description="Total points (should be 232)")
    winner: str = Field(..., description="Winning team name")
    is_valid: bool = Field(..., description="Whether total is valid (232)")

    baseline_score: Optional[float] = Field(
        None, description="Score before optimization"
    )
    optimized_score: Optional[float] = Field(
        None, description="Score after optimization"
    )
    improvement: Optional[float] = Field(None, description="Point improvement")
    method_used: Optional[str] = Field(None, description="Optimization method used")

    event_breakdown: List[EventBreakdownModel] = Field(
        default_factory=list, description="Per-event scoring breakdown"
    )
    recommendations: List[str] = Field(
        default_factory=list, description="Coaching recommendations"
    )
    details: Optional[List[Dict[str, Any]]] = Field(
        None, description="Detailed lineup entries"
    )

    # Metrics
    meet_type: str = Field("dual", description="Meet type")
    metrics: Optional[Dict[str, Any]] = Field(None, description="Performance metrics")
    warnings: Optional[List[str]] = Field(None, description="Validation warnings")
    error: Optional[str] = Field(None, description="Error message if failed")

    model_config = {
        "json_schema_extra": {
            "example": {
                "success": True,
                "our_score": 135,
                "opponent_score": 97,
                "total_points": 232,
                "winner": "Seton",
                "is_valid": True,
                "improvement": 5,
                "recommendations": ["Consider moving Smith to 50 Free"],
            }
        }
    }
