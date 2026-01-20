"""
Core Data Entities - Strict Pydantic Models for HyTek Data

These entities map directly to HyTek Team Manager database tables.
All validation is strict - no fuzzy matching or guessing.

Design Principles:
1. Every field must be a clear win or loss (no fuzzy workarounds)
2. Validation errors are raised, not silently fixed
3. Types match HyTek's data format exactly
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator


# =============================================================================
# Constants - HyTek stroke/distance codes
# =============================================================================

STROKE_CODES = {
    1: "Free",
    2: "Back",
    3: "Breast",
    4: "Fly",
    5: "IM",
}

VALID_DISTANCES = {25, 50, 100, 200, 400, 500, 800, 1000, 1500, 1650}
VALID_GRADES = {"FR", "SO", "JR", "SR", "8", "7", "6", "9", "10", "11", "12"}
COURSE_CODES = {"Y": "Yards", "S": "Short Course Meters", "L": "Long Course Meters"}


# =============================================================================
# Team Entity
# =============================================================================


class TeamEntity(BaseModel):
    """
    Maps to HyTek teams table.

    Example CSV row:
        TEAM,TCODE,TNAME,SHORT,...
        1,"SST","Seton Swimming","Seton",...
    """

    team_id: int = Field(gt=0, description="HyTek TEAM field")
    code: str = Field(min_length=1, max_length=10, description="HyTek TCODE field")
    name: str = Field(min_length=1, max_length=100, description="HyTek TNAME field")
    short_name: str = Field(max_length=30, description="HyTek SHORT field")
    state: str = Field(default="VA", max_length=2)
    team_type: str = Field(default="HS", max_length=10)

    @field_validator("code", "name", "short_name", mode="before")
    @classmethod
    def strip_and_validate(cls, v: str | None) -> str:
        if v is None:
            return ""
        return str(v).strip()


# =============================================================================
# Athlete Entity
# =============================================================================


class AthleteEntity(BaseModel):
    """
    Maps to HyTek athletes table.

    Example CSV row:
        ATHLETE,TEAM1,...,LAST,FIRST,...,SEX,BIRTH,...,CLASS,...
        2,1,...,"DOBAK","LAUREN",...,"F","03/08/84 00:00:00",...,"SR",...
    """

    athlete_id: int = Field(gt=0, description="HyTek ATHLETE field")
    team_id: int = Field(gt=0, description="HyTek TEAM1 field")
    last_name: str = Field(min_length=1, max_length=50)
    first_name: str = Field(min_length=1, max_length=50)
    sex: Literal["M", "F"]
    birth_date: date | None = None
    grade: str | None = Field(
        default=None, description="FR, SO, JR, SR, or grade number"
    )
    inactive: bool = Field(default=False)
    preferred_name: str | None = None

    @field_validator("last_name", "first_name", mode="before")
    @classmethod
    def strip_name(cls, v: str | None) -> str:
        if v is None or str(v).strip() == "":
            raise ValueError("Name cannot be empty")
        return str(v).strip()

    @field_validator("grade", mode="before")
    @classmethod
    def normalize_grade(cls, v: str | None) -> str | None:
        if v is None or str(v).strip() == "" or str(v).strip() == " ":
            return None
        grade = str(v).strip().upper()
        if grade in VALID_GRADES:
            return grade
        return None

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"

    @property
    def display_name(self) -> str:
        if self.preferred_name:
            return f"{self.preferred_name} {self.last_name}"
        return self.full_name


# =============================================================================
# Meet Entity
# =============================================================================


class MeetEntity(BaseModel):
    """
    Maps to HyTek meets table.

    Example CSV row:
        MEET,MNAME,START,END,...,COURSE,...,Location,...
        114,"SST vs FCS, Wakefield, WoL","12/02/05 00:00:00",...,"Y",...
    """

    meet_id: int = Field(gt=0, description="HyTek MEET field")
    name: str = Field(min_length=1, max_length=200)
    start_date: date
    end_date: date | None = None
    course: Literal["Y", "S", "L"] = Field(default="Y")
    location: str = Field(default="", max_length=200)
    altitude: int = Field(default=0, ge=0)

    @field_validator("name", "location", mode="before")
    @classmethod
    def strip_text(cls, v: str | None) -> str:
        if v is None:
            return ""
        return str(v).strip()

    @model_validator(mode="after")
    def validate_dates(self) -> "MeetEntity":
        if self.end_date and self.end_date < self.start_date:
            raise ValueError("end_date cannot be before start_date")
        return self

    @property
    def season(self) -> str:
        """Calculate season string (e.g., '2025-2026')."""
        year = self.start_date.year
        month = self.start_date.month
        if month >= 8:  # August or later = next year's season
            return f"{year}-{year + 1}"
        return f"{year - 1}-{year}"

    @property
    def course_name(self) -> str:
        return COURSE_CODES.get(self.course, "Unknown")


# =============================================================================
# Swim Result Entity
# =============================================================================


class SwimResultEntity(BaseModel):
    """
    Maps to HyTek results table.

    Time is stored internally as seconds (float) but can be created from
    hundredths (as stored in HyTek CSV).

    Example CSV row:
        MEET,ATHLETE,I_R,TEAM,SCORE,F_P,SPLIT,EX,ORIGIN,RESULT,...,DISTANCE,STROKE,...
        39,87,"I",1,19648,"F",0,,"C",1095,...,200,5,...
    """

    result_id: int | None = Field(
        default=None, description="HyTek RESULT ID for linking splits"
    )
    meet_id: int = Field(gt=0)
    athlete_id: int = Field(gt=0)
    result_type: Literal["I", "R"] = Field(description="I=Individual, R=Relay")
    time_seconds: float = Field(gt=0, description="Time in seconds")
    distance: int = Field(gt=0)
    stroke: int = Field(ge=1, le=5, description="1=Free, 2=Back, 3=Breast, 4=Fly, 5=IM")
    course: Literal["Y", "S", "L"] = Field(default="Y")
    place: int = Field(default=0, ge=0)
    points: float = Field(default=0.0, ge=0)
    is_exhibition: bool = Field(default=False)
    is_dq: bool = Field(default=False)
    dq_code: str | None = None
    dq_description: str | None = None

    @field_validator("distance", mode="before")
    @classmethod
    def validate_distance(cls, v: int) -> int:
        v = int(v)
        if v not in VALID_DISTANCES:
            raise ValueError(f"Invalid distance: {v}. Must be one of {VALID_DISTANCES}")
        return v

    @classmethod
    def from_hundredths(
        cls,
        meet_id: int,
        athlete_id: int,
        result_type: str,
        time_hundredths: int,
        distance: int,
        stroke: int,
        course: str = "Y",
        **kwargs,
    ) -> "SwimResultEntity":
        """Create from HyTek format (time in hundredths of seconds)."""
        return cls(
            meet_id=meet_id,
            athlete_id=athlete_id,
            result_type=result_type,
            time_seconds=time_hundredths / 100.0,
            distance=distance,
            stroke=stroke,
            course=course,
            **kwargs,
        )

    @property
    def event_name(self) -> str:
        """Generate event name like '100 Free' or '200 IM'."""
        stroke_name = STROKE_CODES.get(self.stroke, "Unknown")
        return f"{self.distance} {stroke_name}"

    @property
    def formatted_time(self) -> str:
        """Format time as MM:SS.ss or SS.ss."""
        if self.time_seconds >= 60:
            mins = int(self.time_seconds // 60)
            secs = self.time_seconds % 60
            return f"{mins}:{secs:05.2f}"
        return f"{self.time_seconds:.2f}"


# =============================================================================
# Relay Result Entity
# =============================================================================


class RelayResultEntity(BaseModel):
    """
    Maps to HyTek relays table.

    Example CSV row:
        RELAY,MEET,LO_HI,TEAM,LETTER,AGE_RANGE,SEX,ATH(1),ATH(2),ATH(3),ATH(4),...
        1142,47,99,1,"B",0,"M",93,98,103,99,...
    """

    relay_id: int = Field(gt=0)
    meet_id: int = Field(gt=0)
    team_id: int = Field(gt=0)
    letter: str = Field(min_length=1, max_length=1, description="A, B, C, etc.")
    sex: Literal["M", "F"]
    swimmers: list[int] = Field(min_length=4, max_length=8, description="Athlete IDs")
    distance: int = Field(gt=0)
    stroke: int = Field(ge=1, le=5)
    time_seconds: float | None = None

    @field_validator("swimmers", mode="before")
    @classmethod
    def filter_valid_swimmers(cls, v: list) -> list[int]:
        """Remove 0s and invalid IDs from swimmer list."""
        if not isinstance(v, list):
            raise ValueError("swimmers must be a list")

        valid = []
        for s in v:
            try:
                swimmer_id = int(s) if s else 0
                if swimmer_id > 0:
                    valid.append(swimmer_id)
            except (ValueError, TypeError):
                # Skip non-integer values silently
                continue

        if len(valid) < 4:
            raise ValueError(f"Relay must have at least 4 swimmers, got {len(valid)}")
        return valid

    @property
    def event_name(self) -> str:
        stroke_name = STROKE_CODES.get(self.stroke, "Unknown")
        return f"{self.distance} {stroke_name} Relay"


# =============================================================================
# Split Entity
# =============================================================================


class SplitEntity(BaseModel):
    """
    Maps to HyTek splits table.

    Example CSV row:
        SplitID,SplitIndex,Split,StrokeRate
        4893,2,2425,
    """

    split_id: int = Field(gt=0, description="Links to result ID")
    split_index: int = Field(ge=1, description="1=first split, 2=second, etc.")
    time_seconds: float = Field(gt=0)
    stroke_rate: float | None = None

    @classmethod
    def from_hundredths(
        cls,
        split_id: int,
        split_index: int,
        time_hundredths: int,
        stroke_rate: float | None = None,
    ) -> "SplitEntity":
        """Create from HyTek format (time in hundredths)."""
        return cls(
            split_id=split_id,
            split_index=split_index,
            time_seconds=time_hundredths / 100.0,
            stroke_rate=stroke_rate,
        )


# =============================================================================
# Diving Result Entity
# =============================================================================


class DivingResultEntity(BaseModel):
    """
    Diving result entity for scored dive events.
    """

    meet_id: int = Field(gt=0)
    athlete_id: int = Field(gt=0)
    score: float = Field(ge=0, description="Total dive score")
    place: int = Field(default=0, ge=0)
    points: float = Field(default=0.0, ge=0)
    event_name: str = Field(default="1M Diving")


# =============================================================================
# Validation Error Tracking
# =============================================================================


class ValidationError(BaseModel):
    """Track validation errors during import (logged, not silently fixed)."""

    source_file: str
    row_number: int
    field_name: str
    raw_value: str
    error_message: str
    timestamp: datetime = Field(default_factory=datetime.now)

    def __str__(self) -> str:
        return f"{self.source_file}:{self.row_number} - {self.field_name}: {self.error_message}"
