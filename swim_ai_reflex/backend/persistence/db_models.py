"""
SQLModel Table Definitions - AquaForge Historical Data Platform

Normalized relational schema covering:
- Organizations (teams, seasons)
- People (swimmers, identity resolution)
- Competitions (meets, events)
- Performance (entries, relays)
- Analytics (swimmer_bests, qualifying_times)
- ETL (import_logs)
"""

import json
from datetime import date, datetime

from sqlmodel import Field, Relationship, SQLModel

# =============================================================================
# Organizations
# =============================================================================


class Team(SQLModel, table=True):
    __tablename__ = "teams"

    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    short_name: str | None = None
    aliases_json: str | None = Field(default=None, description="JSON array of aliases")
    conference: str | None = None
    division: str | None = None
    state: str = Field(default="VA")
    is_user_team: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    swimmer_seasons: list["SwimmerTeamSeason"] = Relationship(back_populates="team")
    meet_teams: list["MeetTeam"] = Relationship(back_populates="team")

    @property
    def aliases(self) -> list[str]:
        if self.aliases_json:
            return json.loads(self.aliases_json)
        return []

    @aliases.setter
    def aliases(self, value: list[str]):
        self.aliases_json = json.dumps(value)


class Season(SQLModel, table=True):
    __tablename__ = "seasons"

    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(unique=True, index=True)  # "2025-2026"
    start_date: date | None = None
    end_date: date | None = None

    # Relationships
    meets: list["Meet"] = Relationship(back_populates="season")
    swimmer_seasons: list["SwimmerTeamSeason"] = Relationship(back_populates="season")


# =============================================================================
# People
# =============================================================================


class Swimmer(SQLModel, table=True):
    __tablename__ = "swimmers"

    id: int | None = Field(default=None, primary_key=True)
    first_name: str = Field(index=True)
    last_name: str = Field(index=True)
    middle_initial: str | None = None
    gender: str | None = Field(default=None, description="M or F")
    birth_year: int | None = None
    usa_swimming_id: str | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    team_seasons: list["SwimmerTeamSeason"] = Relationship(back_populates="swimmer")
    entries: list["Entry"] = Relationship(back_populates="swimmer")
    aliases: list["SwimmerAlias"] = Relationship(back_populates="swimmer")
    bests: list["SwimmerBest"] = Relationship(back_populates="swimmer")

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"


class SwimmerAlias(SQLModel, table=True):
    __tablename__ = "swimmer_aliases"

    id: int | None = Field(default=None, primary_key=True)
    swimmer_id: int = Field(foreign_key="swimmers.id", index=True)
    alias_name: str = Field(unique=True, index=True)
    source: str | None = None  # "hytek_mdb", "manual", "fuzzy_match"

    # Relationships
    swimmer: Swimmer | None = Relationship(back_populates="aliases")


class SwimmerTeamSeason(SQLModel, table=True):
    __tablename__ = "swimmer_team_seasons"

    id: int | None = Field(default=None, primary_key=True)
    swimmer_id: int = Field(foreign_key="swimmers.id", index=True)
    team_id: int = Field(foreign_key="teams.id", index=True)
    season_id: int = Field(foreign_key="seasons.id", index=True)
    grade: int | None = None
    is_active: bool = Field(default=True)

    # Relationships
    swimmer: Swimmer | None = Relationship(back_populates="team_seasons")
    team: Team | None = Relationship(back_populates="swimmer_seasons")
    season: Season | None = Relationship(back_populates="swimmer_seasons")


# =============================================================================
# Competitions
# =============================================================================


class Meet(SQLModel, table=True):
    __tablename__ = "meets"

    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    meet_date: date = Field(index=True)
    meet_end_date: date | None = None
    season_id: int | None = Field(default=None, foreign_key="seasons.id")
    location: str | None = None
    city: str | None = None
    state: str | None = None
    pool_course: str = Field(default="25Y")  # 25Y, 25M, 50M
    num_lanes: int | None = None
    meet_type: str = Field(
        default="dual"
    )  # dual, invitational, conference, championship, time_trial, exhibition
    ind_max_scorers: int | None = None  # max individual scorers per team
    relay_max_scorers: int | None = None  # max relay scorers per team
    hytek_db_path: str | None = None  # source .mdb file path
    source_file: str | None = None  # file used for import
    notes: str | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    season: Season | None = Relationship(back_populates="meets")
    events: list["Event"] = Relationship(back_populates="meet")
    meet_teams: list["MeetTeam"] = Relationship(back_populates="meet")


class MeetTeam(SQLModel, table=True):
    """Link table: which teams competed in a meet, with final scores."""

    __tablename__ = "meet_teams"

    id: int | None = Field(default=None, primary_key=True)
    meet_id: int = Field(foreign_key="meets.id", index=True)
    team_id: int = Field(foreign_key="teams.id", index=True)
    final_score: float | None = None
    is_home: bool = Field(default=False)

    # Relationships
    meet: Meet | None = Relationship(back_populates="meet_teams")
    team: Team | None = Relationship(back_populates="meet_teams")


class Event(SQLModel, table=True):
    __tablename__ = "events"

    id: int | None = Field(default=None, primary_key=True)
    meet_id: int = Field(foreign_key="meets.id", index=True)
    event_number: int | None = None  # 1-22 for standard HS order
    event_name: str = Field(index=True)  # "200 Medley Relay", "100 Free"
    event_distance: int | None = None  # 200, 100, 50, 500
    event_stroke: str | None = None  # Free, Back, Breast, Fly, IM, Medley
    gender: str | None = None  # M, F, X
    is_relay: bool = Field(default=False)
    is_diving: bool = Field(default=False)
    event_category: str | None = Field(
        default=None,
        description="standard, championship, jv, novice, non_standard, unknown",
    )

    # Relationships
    meet: Meet | None = Relationship(back_populates="events")
    entries: list["Entry"] = Relationship(back_populates="event")
    relay_entries: list["RelayEntry"] = Relationship(back_populates="event")


# =============================================================================
# Performance
# =============================================================================


class Entry(SQLModel, table=True):
    """Individual swimmer performance in a specific event at a meet."""

    __tablename__ = "entries"

    id: int | None = Field(default=None, primary_key=True)
    event_id: int = Field(foreign_key="events.id", index=True)
    swimmer_id: int = Field(foreign_key="swimmers.id", index=True)
    team_id: int | None = Field(default=None, foreign_key="teams.id")
    seed_time: float | None = None  # seconds
    finals_time: float | None = None  # seconds (NULL if DNS/DQ)
    heat: int | None = None
    lane: int | None = None
    place: int | None = None
    points: float = Field(default=0.0)
    is_exhibition: bool = Field(default=False)
    is_dq: bool = Field(default=False)
    is_dns: bool = Field(default=False)
    dq_code: str | None = None
    course: str | None = None  # Y, L, S per entry (from Fin_course)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    event: Event | None = Relationship(back_populates="entries")
    swimmer: Swimmer | None = Relationship(back_populates="entries")


class RelayEntry(SQLModel, table=True):
    __tablename__ = "relay_entries"

    id: int | None = Field(default=None, primary_key=True)
    event_id: int = Field(foreign_key="events.id", index=True)
    team_id: int = Field(foreign_key="teams.id")
    relay_letter: str = Field(default="A")  # A, B, C
    seed_time: float | None = None
    finals_time: float | None = None
    heat: int | None = None
    lane: int | None = None
    place: int | None = None
    points: float = Field(default=0.0)
    is_exhibition: bool = Field(default=False)
    is_dq: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    event: Event | None = Relationship(back_populates="relay_entries")
    legs: list["RelayLeg"] = Relationship(back_populates="relay_entry")


class RelayLeg(SQLModel, table=True):
    __tablename__ = "relay_legs"

    id: int | None = Field(default=None, primary_key=True)
    relay_entry_id: int = Field(foreign_key="relay_entries.id", index=True)
    swimmer_id: int = Field(foreign_key="swimmers.id")
    leg_order: int  # 1-4
    split_time: float | None = None  # individual leg split

    # Relationships
    relay_entry: RelayEntry | None = Relationship(back_populates="legs")


class Split(SQLModel, table=True):
    """Individual split times within an event (50-yard increments)."""

    __tablename__ = "splits"

    id: int | None = Field(default=None, primary_key=True)
    event_id: int = Field(foreign_key="events.id", index=True)
    swimmer_id: int | None = Field(default=None, foreign_key="swimmers.id", index=True)
    relay_entry_id: int | None = Field(default=None, foreign_key="relay_entries.id")
    split_number: int  # 1, 2, 3, 4... (cumulative split index)
    split_time: float  # cumulative time in seconds at this split point
    round_code: str = Field(default="F")  # F=finals, P=prelims, S=semis


class DualMeetPairing(SQLModel, table=True):
    """Which teams are paired in a dual meet (from Dualteams table)."""

    __tablename__ = "dual_meet_pairings"

    id: int | None = Field(default=None, primary_key=True)
    meet_id: int = Field(foreign_key="meets.id", index=True)
    team_a_id: int = Field(foreign_key="teams.id")
    team_b_id: int = Field(foreign_key="teams.id")
    gender: str | None = None  # M, F


# =============================================================================
# Analytics (Materialized / Computed)
# =============================================================================


class SwimmerBest(SQLModel, table=True):
    """Pre-computed best/mean/recent times per swimmer per event per season."""

    __tablename__ = "swimmer_bests"

    id: int | None = Field(default=None, primary_key=True)
    swimmer_id: int = Field(foreign_key="swimmers.id", index=True)
    event_name: str = Field(index=True)  # Normalized: "100 Free" (no gender prefix)
    season_id: int | None = Field(default=None, foreign_key="seasons.id")
    best_time: float
    mean_time: float | None = None
    std_dev: float | None = None
    recent_time: float | None = None  # avg of last 3
    sample_size: int = Field(default=1)
    improvement_pct: float | None = None  # vs previous season
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    swimmer: Swimmer | None = Relationship(back_populates="bests")


class QualifyingTime(SQLModel, table=True):
    """VISAA qualifying standards by event/gender/level."""

    __tablename__ = "qualifying_times"

    id: int | None = Field(default=None, primary_key=True)
    event_name: str  # "100 Free"
    gender: str  # M or F
    time_standard: float  # seconds
    level: str  # "state", "regional", "consideration"
    season: str  # "2025-2026"


# =============================================================================
# ETL Tracking
# =============================================================================


class ImportLog(SQLModel, table=True):
    """Track imported files for idempotency."""

    __tablename__ = "import_logs"

    id: int | None = Field(default=None, primary_key=True)
    source_path: str = Field(index=True)
    source_type: str | None = None  # hytek_mdb, pdf, csv, xlsx
    import_date: datetime = Field(default_factory=datetime.utcnow)
    records_imported: int = Field(default=0)
    records_skipped: int = Field(default=0)
    errors_json: str | None = None  # JSON array of error messages
    status: str = Field(default="pending")  # pending, running, success, failed
    checksum: str | None = Field(default=None, index=True)  # file hash

    @property
    def errors(self) -> list[str]:
        if self.errors_json:
            return json.loads(self.errors_json)
        return []

    @errors.setter
    def errors(self, value: list[str]):
        self.errors_json = json.dumps(value)


# =============================================================================
# Optimization History
# =============================================================================


class OptimizationRun(SQLModel, table=True):
    """Historical record of optimization runs for backtesting."""

    __tablename__ = "optimization_runs"

    id: int | None = Field(default=None, primary_key=True)
    meet_id: int | None = Field(default=None, foreign_key="meets.id")
    run_date: datetime = Field(default_factory=datetime.utcnow)
    optimizer_type: str = Field(default="gurobi")  # gurobi, heuristic, stackelberg
    home_score: float = Field(default=0.0)
    away_score: float = Field(default=0.0)
    lineup_json: str | None = None  # Full lineup as JSON
    config_json: str | None = None  # Optimizer config as JSON
    notes: str | None = None
