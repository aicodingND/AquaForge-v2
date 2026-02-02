"""
Meet and Season Models

Pydantic models for meet scheduling and season planning.
"""

from datetime import date, datetime
from enum import Enum

from pydantic import BaseModel, Field


class MeetImportance(str, Enum):
    """Meet importance levels for optimization."""

    REGULAR = "regular"
    CONFERENCE = "conference"
    DIVISIONAL = "divisional"
    STATE = "state"
    CHAMPIONSHIP = "championship"


class ScheduledMeet(BaseModel):
    """A scheduled meet in the season."""

    meet_id: str = Field(..., description="Unique identifier")
    date: date
    opponent: str
    location: str = "TBD"

    # Importance affects optimization priorities
    importance: MeetImportance = MeetImportance.REGULAR
    importance_weight: float = Field(
        default=1.0, ge=0.1, le=2.0, description="Weight multiplier for this meet"
    )

    # Flags
    is_home: bool = True
    is_conference: bool = False
    is_championship: bool = False

    # Historical context
    last_result: str | None = None  # "W 105-75" or "L 85-95"
    historical_margin: float = Field(
        default=0.0, description="Avg point margin vs this opponent"
    )

    @property
    def days_until(self) -> int:
        """Days until this meet."""
        return (self.date - date.today()).days


class Season(BaseModel):
    """A complete swim season."""

    season_name: str = Field(..., description="e.g., '2025-2026 Boys'")
    start_date: date
    end_date: date

    meets: list[ScheduledMeet] = Field(default_factory=list)

    # Championship meet (special handling)
    championship_meet: ScheduledMeet | None = None

    # Season goals
    target_wins: int = Field(default=0, ge=0, description="Target number of wins")
    current_wins: int = Field(default=0, ge=0)
    current_losses: int = Field(default=0, ge=0)

    @property
    def upcoming_meets(self) -> list[ScheduledMeet]:
        """Get meets that haven't happened yet."""
        today = date.today()
        return sorted([m for m in self.meets if m.date >= today], key=lambda m: m.date)

    @property
    def next_meet(self) -> ScheduledMeet | None:
        """Get the next upcoming meet."""
        upcoming = self.upcoming_meets
        return upcoming[0] if upcoming else None

    @property
    def days_until_championship(self) -> int | None:
        """Days until championship meet."""
        if self.championship_meet:
            return self.championship_meet.days_until
        return None

    @property
    def win_rate(self) -> float:
        """Current win rate."""
        total = self.current_wins + self.current_losses
        return self.current_wins / total if total > 0 else 0.0


class SeasonGoals(BaseModel):
    """Strategic goals for the season."""

    # Win targets
    minimum_wins: int = Field(default=5, ge=0)
    target_wins: int = Field(default=8, ge=0)

    # Swimmer development
    develop_jv_in_regular_meets: bool = True
    rest_stars_before_championship: bool = True
    days_rest_before_championship: int = Field(default=7, ge=0)

    # Priority events (focus on these)
    priority_events: list[str] = Field(default_factory=list)

    # Specific swimmer goals
    swimmer_event_goals: dict = Field(
        default_factory=dict, description="e.g., {'John': {'100 Free': 'break 50s'}}"
    )


class SeasonPlan(BaseModel):
    """Output of season planning optimization."""

    season: str
    generated_at: datetime = Field(default_factory=datetime.now)

    # Per-meet recommendations
    meet_strategies: list[dict] = Field(default_factory=list)

    # Swimmer usage across season
    swimmer_load: dict = Field(
        default_factory=dict, description="Events per swimmer across season"
    )

    # Recommendations
    rest_recommendations: list[str] = Field(default_factory=list)
    jv_development_opportunities: list[str] = Field(default_factory=list)

    # Projected outcomes
    projected_wins: int = 0
    projected_losses: int = 0
    championship_readiness: float = Field(default=0.0, ge=0, le=1)
