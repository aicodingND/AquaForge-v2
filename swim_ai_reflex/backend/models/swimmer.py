"""
Swimmer Models - Pydantic schemas for swimmer data.

These models are designed for:
1. Current Reflex app usage
2. Future FastAPI migration (ready-to-use request/response schemas)
"""

from datetime import date
from typing import List, Optional

from pydantic import BaseModel, Field


class SwimmerTime(BaseModel):
    """
    Represents a swimmer's time in an event with uncertainty quantification.

    Instead of treating times as fixed values, we model them as distributions
    to account for natural variance in performance.
    """

    swimmer: str = Field(..., description="Swimmer's name")
    event: str = Field(..., description="Event name (e.g., '100 Free')")
    team: str = Field(default="seton", description="Team identifier")
    grade: int = Field(default=12, ge=7, le=12, description="Grade level (7-12)")

    # Time distribution
    mean_time: float = Field(..., gt=0, description="Expected/average time in seconds")
    std_dev: float = Field(
        default=0.5, ge=0, description="Standard deviation in seconds"
    )
    best_time: Optional[float] = Field(default=None, description="Season best time")
    recent_time: Optional[float] = Field(
        default=None, description="Average of last 3 meets"
    )

    # Metadata
    confidence: float = Field(
        default=0.8, ge=0, le=1, description="Data quality score (0-1)"
    )
    sample_size: int = Field(
        default=1, ge=1, description="Number of times used to calculate stats"
    )

    def __init__(self, **data):
        # If best_time not provided, use mean_time
        if data.get("best_time") is None:
            data["best_time"] = data.get("mean_time")
        if data.get("recent_time") is None:
            data["recent_time"] = data.get("mean_time")
        super().__init__(**data)

    @property
    def time(self) -> float:
        """Backward compatibility: return mean_time as 'time'."""
        return self.mean_time

    def expected_range(self, sigmas: float = 1.0) -> tuple[float, float]:
        """Return expected time range at given confidence level."""
        return (
            self.mean_time - sigmas * self.std_dev,
            self.mean_time + sigmas * self.std_dev,
        )

    def probability_under(self, threshold: float) -> float:
        """Probability of swimming faster than threshold."""
        from scipy import stats

        if self.std_dev == 0:
            return 1.0 if self.mean_time < threshold else 0.0
        z = (threshold - self.mean_time) / self.std_dev
        return stats.norm.cdf(z)


class SwimmerProfile(BaseModel):
    """
    Complete profile of a swimmer with all their events.
    """

    swimmer: str
    team: str
    grade: int
    events: List[SwimmerTime] = Field(default_factory=list)

    # Psychological factors (Phase 6)
    clutch_factor: float = Field(
        default=1.0, ge=0, le=2, description="Performance multiplier under pressure"
    )
    consistency: float = Field(
        default=0.8, ge=0, le=1, description="How consistent (low variance)"
    )


class TimeRecord(BaseModel):
    """
    A single recorded time from a meet.
    Used for building historical data and calculating distributions.
    """

    swimmer: str
    event: str
    time: float
    meet_date: date
    meet_name: str
    is_official: bool = True

    # Conditions that may affect time
    altitude: Optional[float] = None  # Feet above sea level
    pool_length: str = "25Y"  # 25Y, 25M, 50M


class RosterEntry(BaseModel):
    """
    Simple roster entry for backward compatibility with existing code.
    Can be converted to/from SwimmerTime.
    """

    swimmer: str
    event: str
    time: float
    team: str = "seton"
    grade: int = 12

    def to_swimmer_time(self, std_dev: float = 0.5) -> SwimmerTime:
        """Convert to SwimmerTime with uncertainty."""
        return SwimmerTime(
            swimmer=self.swimmer,
            event=self.event,
            team=self.team,
            grade=self.grade,
            mean_time=self.time,
            std_dev=std_dev,
        )

    @classmethod
    def from_swimmer_time(cls, st: SwimmerTime) -> "RosterEntry":
        """Convert from SwimmerTime (loses uncertainty info)."""
        return cls(
            swimmer=st.swimmer,
            event=st.event,
            time=st.mean_time,
            team=st.team,
            grade=st.grade,
        )
