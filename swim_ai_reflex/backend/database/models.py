from datetime import datetime

from sqlmodel import Field, Relationship, SQLModel


class Team(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(index=True, unique=True)
    code: str | None = None

    swimmers: list["Swimmer"] = Relationship(back_populates="team")


class Meet(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    date: datetime
    location: str | None = None
    profile_type: str | None = "standard"  # e.g., "visaa_championship", "vcac"

    entries: list["EventEntry"] = Relationship(back_populates="meet")
    backtest_results: list["BacktestResult"] = Relationship(back_populates="meet")


class Swimmer(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    gender: str | None = None
    graduation_year: int | None = None

    team_id: int | None = Field(default=None, foreign_key="team.id")
    team: Team | None = Relationship(back_populates="swimmers")

    entries: list["EventEntry"] = Relationship(back_populates="swimmer")


class EventEntry(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    event_name: str
    seed_time: float
    actual_time: float | None = None
    points: float | None = None
    rank: int | None = None

    meet_id: int = Field(foreign_key="meet.id")
    meet: Meet | None = Relationship(back_populates="entries")

    swimmer_id: int = Field(foreign_key="swimmer.id")
    swimmer: Swimmer | None = Relationship(back_populates="entries")


class BacktestResult(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    ai_score: float
    coach_score: float
    actual_score: float
    rank_accuracy: float

    meet_id: int = Field(foreign_key="meet.id")
    meet: Meet | None = Relationship(back_populates="backtest_results")

    details: str | None = None  # JSON string for extra details
