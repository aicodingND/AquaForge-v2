"""
Opponent Intelligence Models

Pydantic models for tracking and predicting opponent behavior.
"""

from datetime import datetime

from pydantic import BaseModel, Field


class CoachTendency(BaseModel):
    """
    Patterns discovered about an opponent coach's lineup decisions.

    These patterns are learned from historical data and used to
    predict how the opponent will likely respond.
    """

    coach_name: str = Field(..., description="Coach's name")
    team_name: str = Field(..., description="Team name")

    # Pattern probabilities (0 = never, 1 = always)
    rests_stars_in_relays: float = Field(
        default=0.3,
        ge=0,
        le=1,
        description="Probability of resting star swimmers in relay events",
    )
    front_loads_lineup: float = Field(
        default=0.5,
        ge=0,
        le=1,
        description="Probability of putting best swimmers in early events",
    )
    predictable_star_placement: float = Field(
        default=0.7,
        ge=0,
        le=1,
        description="Probability of using same lineup pattern repeatedly",
    )
    adapts_to_opponent: float = Field(
        default=0.3,
        ge=0,
        le=1,
        description="Probability of changing lineup based on matchup",
    )
    uses_exhibition_strategically: float = Field(
        default=0.4,
        ge=0,
        le=1,
        description="Probability of strategic exhibition placement",
    )

    # Specific patterns
    favorite_events_for_stars: list[str] = Field(
        default_factory=list,
        description="Events where coach typically places star swimmers",
    )
    avoided_events: list[str] = Field(
        default_factory=list, description="Events coach tends to concede"
    )

    # Metadata
    sample_size: int = Field(default=0, ge=0, description="Number of meets analyzed")
    last_updated: datetime = Field(default_factory=datetime.now)
    confidence: float = Field(
        default=0.5, ge=0, le=1, description="Confidence in predictions"
    )

    def to_dict(self) -> dict:
        """Convert to dictionary for storage."""
        return self.model_dump()

    @classmethod
    def from_dict(cls, data: dict) -> "CoachTendency":
        """Create from dictionary."""
        return cls(**data)


class HistoricalLineup(BaseModel):
    """A historical lineup from a past meet."""

    meet_date: datetime
    opponent: str
    event: str
    swimmer: str
    time: float
    place: int
    points: int
    was_exhibition: bool = False


class OpponentProfile(BaseModel):
    """Complete profile of an opponent team."""

    team_name: str
    coach_name: str | None = None

    # Current roster (this season)
    roster: list[dict] = Field(default_factory=list)

    # Historical data
    historical_lineups: list[HistoricalLineup] = Field(default_factory=list)

    # Computed tendencies
    tendency: CoachTendency | None = None

    # Performance stats
    win_rate_vs_seton: float = Field(default=0.5, ge=0, le=1)
    avg_margin: float = Field(
        default=0.0, description="Average point margin (+ = they win)"
    )

    # Metadata
    last_meet_date: datetime | None = None
    total_meets: int = 0


class MeetResult(BaseModel):
    """Result of a dual meet for historical tracking."""

    meet_id: str
    date: datetime
    opponent_team: str

    # Scores
    seton_score: float
    opponent_score: float

    # Full lineups (for pattern analysis)
    seton_lineup: list[dict]
    opponent_lineup: list[dict]

    # Metadata
    location: str = "Unknown"
    meet_type: str = "regular"  # regular, conference, championship

    @property
    def winner(self) -> str:
        """Who won this meet."""
        if self.seton_score > self.opponent_score:
            return "seton"
        elif self.opponent_score > self.seton_score:
            return self.opponent_team
        else:
            return "tie"

    @property
    def margin(self) -> float:
        """Seton's margin (positive = Seton win)."""
        return self.seton_score - self.opponent_score
