"""
Championship API Models

Pydantic models for championship meet request/response validation.
"""

from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field, field_validator


class PsychSheetEntryModel(BaseModel):
    """A single psych sheet entry."""

    swimmer: str = Field(..., alias="swimmer_name", description="Swimmer's name")
    team: str = Field(..., description="Team name")
    event: str = Field(..., description="Event name")
    seed_time: Optional[Union[float, str]] = Field(
        None, description="Seed time in seconds"
    )
    time: Optional[Union[float, str]] = Field(None, description="Alternate time field")
    grade: Optional[int] = Field(12, description="Grade level")
    gender: Optional[str] = Field("M", description="Gender (M/F)")
    is_diving: Optional[bool] = Field(False, description="Is diving event")
    dive_score: Optional[float] = Field(None, description="Dive score")

    @field_validator("swimmer", mode="before")
    @classmethod
    def normalize_swimmer(cls, v: str) -> str:
        if not v or not str(v).strip():
            raise ValueError("Swimmer name cannot be empty")
        return str(v).strip()

    def get_time(self) -> Optional[float]:
        """Get the time from either field."""
        return self.seed_time or self.time

    model_config = {"populate_by_name": True}


class StandingModel(BaseModel):
    """Team standing in projected results."""

    rank: int = Field(..., description="Team rank")
    team: str = Field(..., description="Team name")
    points: float = Field(..., description="Projected points")


class SwingEventModel(BaseModel):
    """A swing event opportunity."""

    event: str
    swimmer: str
    team: str
    current_place: int
    target_place: int
    current_points: float
    potential_points: float
    point_gain: float
    time_gap: float


class ChampionshipProjectRequest(BaseModel):
    """Request for championship point projection."""

    entries: List[Dict[str, Any]] = Field(..., description="All psych sheet entries")
    target_team: str = Field("Seton", description="Team to focus analysis on")
    meet_name: str = Field("Championship", description="Meet name")
    meet_profile: str = Field("vcac_championship", description="Rules profile")

    model_config = {
        "json_schema_extra": {
            "example": {
                "entries": [
                    {
                        "swimmer_name": "John Smith",
                        "team": "Seton",
                        "event": "100 Free",
                        "seed_time": 52.34,
                        "grade": 11,
                    }
                ],
                "target_team": "Seton",
                "meet_name": "VCAC Championship 2026",
            }
        }
    }


class EventProjectionModel(BaseModel):
    """Projection for a single event."""

    event: str
    team_points: Dict[str, float]
    entries: List[Dict[str, Any]]


class ChampionshipProjectResponse(BaseModel):
    """Response from championship point projection."""

    success: bool = Field(..., description="Whether projection succeeded")
    meet_name: str = Field(..., description="Meet name")
    target_team: str = Field(..., description="Target team")
    target_team_total: float = Field(..., description="Target team projected points")
    target_team_rank: int = Field(..., description="Target team projected rank")

    standings: List[StandingModel] = Field(..., description="Projected standings")
    team_totals: Dict[str, float] = Field(..., description="Points per team")
    swing_events: List[SwingEventModel] = Field(
        default_factory=list, description="Swing event opportunities"
    )
    event_projections: Optional[Dict[str, EventProjectionModel]] = Field(
        None, description="Per-event projections"
    )
    recommendations: List[str] = Field(
        default_factory=list, description="Coaching recommendations"
    )

    # Metadata
    meet_type: str = Field("championship", description="Meet type")
    metrics: Optional[Dict[str, Any]] = Field(None, description="Performance metrics")
    warnings: Optional[List[str]] = Field(None, description="Validation warnings")
    error: Optional[str] = Field(None, description="Error message if failed")


class ChampionshipOptimizeRequest(BaseModel):
    """Request for championship entry optimization."""

    entries: List[Dict[str, Any]] = Field(..., description="All psych sheet entries")
    target_team: str = Field("Seton", description="Team to optimize")
    meet_name: str = Field("Championship", description="Meet name")
    meet_profile: str = Field("vcac_championship", description="Rules profile")

    # Constraint inputs
    divers: List[str] = Field(
        default_factory=list, description="Swimmers who are diving"
    )
    relay_3_swimmers: List[str] = Field(
        default_factory=list, description="Swimmers swimming the 400 Free Relay"
    )

    # Options
    optimize_entries: bool = Field(True, description="Run entry optimization")
    optimize_relays: bool = Field(False, description="Run relay optimization")


class ChampionshipOptimizeResponse(BaseModel):
    """Response from championship entry optimization."""

    success: bool
    projection: Dict[str, Any] = Field(..., description="Projected standings")
    entry_assignments: Optional[Dict[str, List[str]]] = Field(
        None, description="Optimized swimmer-event assignments"
    )
    relay_configurations: Optional[Dict[str, Any]] = Field(
        None, description="Optimized relay configurations"
    )
    optimization_improvement: float = Field(0, description="Point improvement")
    recommendations: List[str] = Field(default_factory=list)

    # Metadata
    meet_type: str = Field("championship")
    metrics: Optional[Dict[str, Any]] = None
    warnings: Optional[List[str]] = None
    error: Optional[str] = None
