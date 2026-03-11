"""
Historical Data API Router

Exposes imported Hy-Tek meet data: teams, seasons, meets, swimmers,
scouting reports, head-to-head matchups, and DB stats.
"""

import logging
from datetime import date, datetime
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func
from sqlmodel import col, select

from swim_ai_reflex.backend.persistence.database import get_session
from swim_ai_reflex.backend.persistence.db_models import (
    Entry,
    Event,
    ImportLog,
    Meet,
    MeetTeam,
    RelayEntry,
    Season,
    Split,
    Swimmer,
    SwimmerTeamSeason,
    Team,
)
from swim_ai_reflex.backend.persistence.sqlite_repository import SQLiteRepository

router = APIRouter()
logger = logging.getLogger(__name__)


# =============================================================================
# Response Models
# =============================================================================


class TeamSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: int
    name: str
    short_name: str | None = None
    conference: str | None = None
    is_user_team: bool = False


class SeasonSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: int
    name: str


class TeamDetail(TeamSummary):
    division: str | None = None
    state: str = "VA"
    seasons: list[SeasonSummary] = Field(default_factory=list)
    meet_count: int = 0


class MeetTeamScore(BaseModel):
    model_config = ConfigDict(extra="forbid")
    team_id: int
    team_name: str
    final_score: float | None = None
    is_home: bool = False


class MeetSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: int
    name: str
    meet_date: date
    season_id: int | None = None
    season_name: str | None = None
    meet_type: str = "dual"
    location: str | None = None
    pool_course: str = "25Y"
    teams: list[MeetTeamScore] = Field(default_factory=list)


class EntryResult(BaseModel):
    model_config = ConfigDict(extra="forbid")
    swimmer_id: int | None = None
    swimmer_name: str | None = None
    team_name: str | None = None
    seed_time: float | None = None
    finals_time: float | None = None
    place: int | None = None
    points: float = 0.0
    is_dq: bool = False
    is_exhibition: bool = False


class EventResult(BaseModel):
    model_config = ConfigDict(extra="forbid")
    event_id: int
    event_name: str
    event_number: int | None = None
    gender: str | None = None
    is_relay: bool = False
    event_category: str | None = None
    entries: list[EntryResult] = Field(default_factory=list)


class MeetDetail(MeetSummary):
    events: list[EventResult] = Field(default_factory=list)
    entry_count: int = 0


class SwimmerSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: int
    first_name: str
    last_name: str
    full_name: str
    gender: str | None = None


class SwimmerBestTime(BaseModel):
    model_config = ConfigDict(extra="forbid")
    event_name: str
    best_time: float
    mean_time: float | None = None
    sample_size: int = 1


class SwimmerProfile(SwimmerSummary):
    seasons: list[dict[str, Any]] = Field(default_factory=list)
    bests: list[SwimmerBestTime] = Field(default_factory=list)
    total_entries: int = 0


class TimeRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")
    time: float
    seed_time: float | None = None
    place: int | None = None
    points: float = 0.0
    event: str
    meet: str
    meet_date: str
    meet_type: str


class ProgressionRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")
    event: str
    season: str
    best_time: float
    mean_time: float | None = None
    sample_size: int = 1


class HeadToHeadRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")
    meet: str
    date: str
    team_a_score: float | None = None
    team_b_score: float | None = None


class HeadToHeadResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    team_a: TeamSummary
    team_b: TeamSummary
    records: list[HeadToHeadRecord] = Field(default_factory=list)
    team_a_wins: int = 0
    team_b_wins: int = 0
    draws: int = 0


class RosterEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")
    swimmer_id: int
    name: str
    gender: str | None = None
    grade: int | None = None
    events: list[dict[str, Any]] = Field(default_factory=list)


class DbStats(BaseModel):
    model_config = ConfigDict(extra="forbid")
    total_teams: int
    total_swimmers: int
    total_meets: int
    total_entries: int
    total_relay_entries: int
    total_splits: int
    total_seasons: int
    total_imports: int


class ImportLogEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: int
    source_path: str
    source_type: str | None = None
    import_date: datetime
    records_imported: int = 0
    records_skipped: int = 0
    status: str = "pending"


class ProspectiveChampRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    team_ids: list[int] = Field(..., min_length=2, description="Team IDs to include")
    season_id: int = Field(..., description="Season to pull best times from")
    seton_team_id: int | None = Field(
        None, description="Your team ID (for lineup detail and Stackelberg)"
    )
    method: str = Field(
        default="gurobi", description="projection|nash|aquaopt|gurobi|stackelberg_champ"
    )
    time_metric: str = Field(
        default="best_time", description="best_time|recent_time|mean_time"
    )
    gurobi_time_limit: int = Field(
        default=10, ge=1, le=60, description="Gurobi time limit per team (seconds)"
    )
    max_candidates: int = Field(
        default=15, ge=1, le=50, description="Stackelberg: candidate lineups"
    )
    top_n_opponents: int = Field(
        default=10, ge=1, le=20, description="Stackelberg: top opponents to re-optimize"
    )


class TeamStanding(BaseModel):
    model_config = ConfigDict(extra="forbid")
    team_name: str
    score: float
    rank: int


class EventLineupEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")
    event: str
    swimmers: list[str]


class ProspectiveChampResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    standings: list[TeamStanding]
    seton_lineup: list[EventLineupEntry] | None = None
    method: str
    status: str
    optimization_time_ms: int
    team_count: int
    swimmer_count: int
    event_count: int
    season_name: str
    time_metric: str


# =============================================================================
# Helper Functions
# =============================================================================


def _round_time(t: float | None) -> float | None:
    """Round a swim time to 2 decimal places, handling None."""
    if t is None:
        return None
    return round(t, 2)


def _compute_bests_from_entries(session, swimmer_id: int) -> list[dict]:
    """Compute all-time bests per event from entries (fallback when swimmer_bests is empty)."""
    stmt = (
        select(
            Event.event_name,
            func.min(Entry.finals_time).label("best_time"),
            func.avg(Entry.finals_time).label("mean_time"),
            func.count(Entry.id).label("sample_size"),
        )
        .join(Event, Entry.event_id == Event.id)
        .where(Entry.swimmer_id == swimmer_id)
        .where(Entry.finals_time.is_not(None))
        .where(Event.is_relay == False)  # noqa: E712
        .group_by(Event.event_name)
        .order_by(func.min(Entry.finals_time))
    )
    rows = session.exec(stmt).all()
    return [
        {
            "event_name": row.event_name,
            "best_time": round(row.best_time, 2),
            "mean_time": round(row.mean_time, 2) if row.mean_time else None,
            "sample_size": row.sample_size,
        }
        for row in rows
    ]


def _compute_progression_from_entries(session, swimmer_id: int) -> list[dict]:
    """Compute season-over-season bests from entries (fallback when swimmer_bests is empty)."""
    stmt = (
        select(
            Event.event_name,
            Season.name.label("season_name"),
            func.min(Entry.finals_time).label("best_time"),
            func.avg(Entry.finals_time).label("mean_time"),
            func.count(Entry.id).label("sample_size"),
        )
        .join(Event, Entry.event_id == Event.id)
        .join(Meet, Event.meet_id == Meet.id)
        .join(Season, Meet.season_id == Season.id)
        .where(Entry.swimmer_id == swimmer_id)
        .where(Entry.finals_time.is_not(None))
        .where(Event.is_relay == False)  # noqa: E712
        .group_by(Event.event_name, Season.name)
        .order_by(Season.name, Event.event_name)
    )
    rows = session.exec(stmt).all()
    return [
        {
            "event": row.event_name,
            "season": row.season_name,
            "best_time": round(row.best_time, 2),
            "mean_time": round(row.mean_time, 2) if row.mean_time else None,
            "sample_size": row.sample_size,
        }
        for row in rows
    ]


def _compute_team_bests(session, team_id: int, season_id: int) -> dict[int, list[dict]]:
    """Compute best times per swimmer for a team in a season."""
    stmt = (
        select(
            Entry.swimmer_id,
            Event.event_name,
            func.min(Entry.finals_time).label("best_time"),
            func.avg(Entry.finals_time).label("mean_time"),
            func.count(Entry.id).label("sample_size"),
        )
        .join(Event, Entry.event_id == Event.id)
        .join(Meet, Event.meet_id == Meet.id)
        .join(
            SwimmerTeamSeason,
            (SwimmerTeamSeason.swimmer_id == Entry.swimmer_id)
            & (SwimmerTeamSeason.team_id == team_id)
            & (SwimmerTeamSeason.season_id == season_id),
        )
        .where(Meet.season_id == season_id)
        .where(Entry.finals_time.is_not(None))
        .where(Event.is_relay == False)  # noqa: E712
        .group_by(Entry.swimmer_id, Event.event_name)
        .order_by(Entry.swimmer_id, func.min(Entry.finals_time))
    )
    rows = session.exec(stmt).all()
    result: dict[int, list[dict]] = {}
    for row in rows:
        if row.swimmer_id not in result:
            result[row.swimmer_id] = []
        result[row.swimmer_id].append(
            {
                "event": row.event_name,
                "best_time": round(row.best_time, 2),
                "mean_time": round(row.mean_time, 2) if row.mean_time else None,
                "sample_size": row.sample_size,
            }
        )
    return result


# =============================================================================
# Stats & Dashboard
# =============================================================================


@router.get("/historical/stats", response_model=DbStats)
async def get_db_stats():
    """Get summary statistics for the historical database."""
    try:
        with get_session() as session:
            return DbStats(
                total_teams=session.exec(select(func.count(Team.id))).one(),
                total_swimmers=session.exec(select(func.count(Swimmer.id))).one(),
                total_meets=session.exec(select(func.count(Meet.id))).one(),
                total_entries=session.exec(select(func.count(Entry.id))).one(),
                total_relay_entries=session.exec(
                    select(func.count(RelayEntry.id))
                ).one(),
                total_splits=session.exec(select(func.count(Split.id))).one(),
                total_seasons=session.exec(select(func.count(Season.id))).one(),
                total_imports=session.exec(select(func.count(ImportLog.id))).one(),
            )
    except Exception as e:
        logger.error(f"Failed to get DB stats: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# Teams & Seasons
# =============================================================================


@router.get("/historical/teams", response_model=list[TeamSummary])
async def list_teams(
    search: str | None = Query(None, description="Filter by name (case-insensitive)"),
):
    """List all teams, optionally filtered by name."""
    try:
        with get_session() as session:
            stmt = select(Team).order_by(Team.name)
            if search:
                stmt = stmt.where(Team.name.ilike(f"%{search}%"))
            teams = session.exec(stmt).all()
            return [
                TeamSummary(
                    id=t.id,
                    name=t.name,
                    short_name=t.short_name,
                    conference=t.conference,
                    is_user_team=t.is_user_team,
                )
                for t in teams
            ]
    except Exception as e:
        logger.error(f"Failed to list teams: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/historical/seasons", response_model=list[SeasonSummary])
async def list_seasons():
    """List all seasons, newest first."""
    try:
        with get_session() as session:
            seasons = session.exec(
                select(Season).order_by(col(Season.name).desc())
            ).all()
            return [SeasonSummary(id=s.id, name=s.name) for s in seasons]
    except Exception as e:
        logger.error(f"Failed to list seasons: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/historical/teams/{team_id}", response_model=TeamDetail)
async def get_team_detail(team_id: int):
    """Get team detail with seasons played and meet count."""
    try:
        with get_session() as session:
            team = session.get(Team, team_id)
            if not team:
                raise HTTPException(status_code=404, detail="Team not found")

            # Seasons this team has swimmers in
            season_rows = session.exec(
                select(Season)
                .join(SwimmerTeamSeason, SwimmerTeamSeason.season_id == Season.id)
                .where(SwimmerTeamSeason.team_id == team_id)
                .distinct()
                .order_by(col(Season.name).desc())
            ).all()

            # Meet count
            meet_count = session.exec(
                select(func.count(MeetTeam.id)).where(MeetTeam.team_id == team_id)
            ).one()

            return TeamDetail(
                id=team.id,
                name=team.name,
                short_name=team.short_name,
                conference=team.conference,
                is_user_team=team.is_user_team,
                division=team.division,
                state=team.state,
                seasons=[SeasonSummary(id=s.id, name=s.name) for s in season_rows],
                meet_count=meet_count,
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get team detail: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# Meets
# =============================================================================


@router.get("/historical/meets")
async def list_meets(
    season_id: int | None = Query(None),
    team_id: int | None = Query(None),
    meet_type: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """List meets with optional filters and pagination."""
    try:
        with get_session() as session:
            stmt = select(Meet)
            count_stmt = select(func.count(Meet.id))

            if season_id is not None:
                stmt = stmt.where(Meet.season_id == season_id)
                count_stmt = count_stmt.where(Meet.season_id == season_id)
            if meet_type is not None:
                stmt = stmt.where(Meet.meet_type == meet_type)
                count_stmt = count_stmt.where(Meet.meet_type == meet_type)
            if team_id is not None:
                stmt = stmt.join(MeetTeam, Meet.id == MeetTeam.meet_id).where(
                    MeetTeam.team_id == team_id
                )
                count_stmt = count_stmt.join(
                    MeetTeam, Meet.id == MeetTeam.meet_id
                ).where(MeetTeam.team_id == team_id)

            total = session.exec(count_stmt).one()
            offset = (page - 1) * page_size
            stmt = (
                stmt.order_by(col(Meet.meet_date).desc())
                .offset(offset)
                .limit(page_size)
            )
            meets = session.exec(stmt).all()

            items = []
            for meet in meets:
                meet_teams = session.exec(
                    select(MeetTeam, Team)
                    .join(Team, MeetTeam.team_id == Team.id)
                    .where(MeetTeam.meet_id == meet.id)
                ).all()

                season_name = None
                if meet.season_id:
                    season = session.get(Season, meet.season_id)
                    season_name = season.name if season else None

                items.append(
                    MeetSummary(
                        id=meet.id,
                        name=meet.name,
                        meet_date=meet.meet_date,
                        season_id=meet.season_id,
                        season_name=season_name,
                        meet_type=meet.meet_type,
                        location=meet.location,
                        pool_course=meet.pool_course,
                        teams=[
                            MeetTeamScore(
                                team_id=mt.team_id,
                                team_name=team.name,
                                final_score=mt.final_score,
                                is_home=mt.is_home,
                            )
                            for mt, team in meet_teams
                        ],
                    ).model_dump()
                )

            return {
                "items": items,
                "total": total,
                "page": page,
                "page_size": page_size,
                "has_more": offset + page_size < total,
            }
    except Exception as e:
        logger.error(f"Failed to list meets: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/historical/meets/{meet_id}", response_model=MeetDetail)
async def get_meet_detail(meet_id: int):
    """Get full meet detail with events and entry results."""
    try:
        with get_session() as session:
            meet = session.get(Meet, meet_id)
            if not meet:
                raise HTTPException(status_code=404, detail="Meet not found")

            # Teams
            meet_teams = session.exec(
                select(MeetTeam, Team)
                .join(Team, MeetTeam.team_id == Team.id)
                .where(MeetTeam.meet_id == meet_id)
            ).all()

            season_name = None
            if meet.season_id:
                season = session.get(Season, meet.season_id)
                season_name = season.name if season else None

            # Events with entries
            events = session.exec(
                select(Event)
                .where(Event.meet_id == meet_id)
                .order_by(Event.event_number, Event.id)
            ).all()

            event_results = []
            total_entries = 0
            for event in events:
                entries = session.exec(
                    select(Entry, Swimmer)
                    .join(Swimmer, Entry.swimmer_id == Swimmer.id)
                    .where(Entry.event_id == event.id)
                    .order_by(Entry.place, Entry.finals_time)
                ).all()

                total_entries += len(entries)

                # Get team names for entries
                entry_list = []
                for entry, swimmer in entries:
                    team_name = None
                    if entry.team_id:
                        team = session.get(Team, entry.team_id)
                        team_name = team.name if team else None

                    entry_list.append(
                        EntryResult(
                            swimmer_id=swimmer.id,
                            swimmer_name=swimmer.full_name,
                            team_name=team_name,
                            seed_time=_round_time(entry.seed_time),
                            finals_time=_round_time(entry.finals_time),
                            place=entry.place,
                            points=entry.points,
                            is_dq=entry.is_dq,
                            is_exhibition=entry.is_exhibition,
                        )
                    )

                event_results.append(
                    EventResult(
                        event_id=event.id,
                        event_name=event.event_name,
                        event_number=event.event_number,
                        gender=event.gender,
                        is_relay=event.is_relay,
                        event_category=event.event_category,
                        entries=entry_list,
                    )
                )

            return MeetDetail(
                id=meet.id,
                name=meet.name,
                meet_date=meet.meet_date,
                season_id=meet.season_id,
                season_name=season_name,
                meet_type=meet.meet_type,
                location=meet.location,
                pool_course=meet.pool_course,
                teams=[
                    MeetTeamScore(
                        team_id=mt.team_id,
                        team_name=team.name,
                        final_score=mt.final_score,
                        is_home=mt.is_home,
                    )
                    for mt, team in meet_teams
                ],
                events=event_results,
                entry_count=total_entries,
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get meet detail: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# Swimmers
# =============================================================================


@router.get("/historical/swimmers")
async def list_swimmers(
    team_id: int | None = Query(None),
    season_id: int | None = Query(None),
    name: str | None = Query(None, description="Search by first or last name"),
    gender: str | None = Query(None, description="M or F"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
):
    """Search/list swimmers with optional filters and pagination."""
    try:
        with get_session() as session:
            stmt = select(Swimmer)
            count_stmt = select(func.count(Swimmer.id))

            if name:
                name_filter = Swimmer.first_name.ilike(
                    f"%{name}%"
                ) | Swimmer.last_name.ilike(f"%{name}%")
                stmt = stmt.where(name_filter)
                count_stmt = count_stmt.where(name_filter)

            if gender:
                stmt = stmt.where(Swimmer.gender == gender.upper())
                count_stmt = count_stmt.where(Swimmer.gender == gender.upper())

            if team_id is not None or season_id is not None:
                stmt = stmt.join(
                    SwimmerTeamSeason,
                    SwimmerTeamSeason.swimmer_id == Swimmer.id,
                )
                count_stmt = count_stmt.join(
                    SwimmerTeamSeason,
                    SwimmerTeamSeason.swimmer_id == Swimmer.id,
                )
                if team_id is not None:
                    stmt = stmt.where(SwimmerTeamSeason.team_id == team_id)
                    count_stmt = count_stmt.where(SwimmerTeamSeason.team_id == team_id)
                if season_id is not None:
                    stmt = stmt.where(SwimmerTeamSeason.season_id == season_id)
                    count_stmt = count_stmt.where(
                        SwimmerTeamSeason.season_id == season_id
                    )

            total = session.exec(count_stmt).one()
            offset = (page - 1) * page_size
            stmt = (
                stmt.order_by(Swimmer.last_name, Swimmer.first_name)
                .offset(offset)
                .limit(page_size)
            )
            swimmers = session.exec(stmt).all()

            items = [
                SwimmerSummary(
                    id=s.id,
                    first_name=s.first_name,
                    last_name=s.last_name,
                    full_name=s.full_name,
                    gender=s.gender,
                ).model_dump()
                for s in swimmers
            ]

            return {
                "items": items,
                "total": total,
                "page": page,
                "page_size": page_size,
                "has_more": offset + page_size < total,
            }
    except Exception as e:
        logger.error(f"Failed to list swimmers: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/historical/swimmers/{swimmer_id}", response_model=SwimmerProfile)
async def get_swimmer_profile(swimmer_id: int):
    """Get swimmer profile with seasons and computed best times."""
    try:
        with get_session() as session:
            swimmer = session.get(Swimmer, swimmer_id)
            if not swimmer:
                raise HTTPException(status_code=404, detail="Swimmer not found")

            # Seasons
            sts_rows = session.exec(
                select(SwimmerTeamSeason, Team, Season)
                .join(Team, SwimmerTeamSeason.team_id == Team.id)
                .join(Season, SwimmerTeamSeason.season_id == Season.id)
                .where(SwimmerTeamSeason.swimmer_id == swimmer_id)
                .order_by(col(Season.name).desc())
            ).all()

            seasons = [
                {
                    "season_name": season.name,
                    "team_name": team.name,
                    "team_id": team.id,
                    "grade": sts.grade,
                }
                for sts, team, season in sts_rows
            ]

            # Bests (computed from entries since swimmer_bests is empty)
            bests_data = _compute_bests_from_entries(session, swimmer_id)
            bests = [
                SwimmerBestTime(
                    event_name=b["event_name"],
                    best_time=b["best_time"],
                    mean_time=b["mean_time"],
                    sample_size=b["sample_size"],
                )
                for b in bests_data
            ]

            # Total entries
            total_entries = session.exec(
                select(func.count(Entry.id)).where(Entry.swimmer_id == swimmer_id)
            ).one()

            return SwimmerProfile(
                id=swimmer.id,
                first_name=swimmer.first_name,
                last_name=swimmer.last_name,
                full_name=swimmer.full_name,
                gender=swimmer.gender,
                seasons=seasons,
                bests=bests,
                total_entries=total_entries,
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get swimmer profile: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/historical/swimmers/{swimmer_id}/times", response_model=list[TimeRecord])
async def get_swimmer_times(
    swimmer_id: int,
    event_name: str | None = Query(None, description="Filter by event name"),
):
    """Get all recorded times for a swimmer, optionally filtered by event."""
    try:
        repo = SQLiteRepository()
        data = repo.get_swimmer_times(swimmer_id, event_name)
        return [
            TimeRecord(
                time=round(d["time"], 2),
                seed_time=_round_time(d.get("seed_time")),
                place=d.get("place"),
                points=d.get("points", 0.0),
                event=d["event"],
                meet=d["meet"],
                meet_date=d["meet_date"],
                meet_type=d["meet_type"],
            )
            for d in data
        ]
    except Exception as e:
        logger.error(f"Failed to get swimmer times: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/historical/swimmers/{swimmer_id}/progression",
    response_model=list[ProgressionRecord],
)
async def get_swimmer_progression(swimmer_id: int):
    """Get season-over-season progression for a swimmer, computed from entries."""
    try:
        with get_session() as session:
            # Verify swimmer exists
            swimmer = session.get(Swimmer, swimmer_id)
            if not swimmer:
                raise HTTPException(status_code=404, detail="Swimmer not found")

            data = _compute_progression_from_entries(session, swimmer_id)
            return [
                ProgressionRecord(
                    event=d["event"],
                    season=d["season"],
                    best_time=d["best_time"],
                    mean_time=d["mean_time"],
                    sample_size=d["sample_size"],
                )
                for d in data
            ]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get swimmer progression: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# Scouting & Head-to-Head
# =============================================================================


@router.get("/historical/scouting/head-to-head", response_model=HeadToHeadResponse)
async def get_head_to_head(
    team_a_id: int = Query(..., description="First team ID"),
    team_b_id: int = Query(..., description="Second team ID"),
):
    """Get historical head-to-head results between two teams."""
    try:
        with get_session() as session:
            team_a = session.get(Team, team_a_id)
            team_b = session.get(Team, team_b_id)
            if not team_a:
                raise HTTPException(
                    status_code=404, detail=f"Team {team_a_id} not found"
                )
            if not team_b:
                raise HTTPException(
                    status_code=404, detail=f"Team {team_b_id} not found"
                )

        repo = SQLiteRepository()
        records = repo.get_head_to_head(team_a_id, team_b_id)

        wins_a = sum(
            1
            for r in records
            if r.get("team_a_score")
            and r.get("team_b_score")
            and r["team_a_score"] > r["team_b_score"]
        )
        wins_b = sum(
            1
            for r in records
            if r.get("team_a_score")
            and r.get("team_b_score")
            and r["team_b_score"] > r["team_a_score"]
        )
        draws = sum(
            1
            for r in records
            if r.get("team_a_score")
            and r.get("team_b_score")
            and r["team_a_score"] == r["team_b_score"]
        )

        return HeadToHeadResponse(
            team_a=TeamSummary(
                id=team_a.id,
                name=team_a.name,
                short_name=team_a.short_name,
                conference=team_a.conference,
                is_user_team=team_a.is_user_team,
            ),
            team_b=TeamSummary(
                id=team_b.id,
                name=team_b.name,
                short_name=team_b.short_name,
                conference=team_b.conference,
                is_user_team=team_b.is_user_team,
            ),
            records=[
                HeadToHeadRecord(
                    meet=r["meet"],
                    date=r["date"],
                    team_a_score=r.get("team_a_score"),
                    team_b_score=r.get("team_b_score"),
                )
                for r in records
            ],
            team_a_wins=wins_a,
            team_b_wins=wins_b,
            draws=draws,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get head-to-head: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/historical/scouting/{team_id}")
async def get_scouting_report(
    team_id: int,
    season_id: int | None = Query(
        None, description="Season to scout (default: latest)"
    ),
):
    """Get scouting report for a team: roster with computed best times."""
    try:
        with get_session() as session:
            team = session.get(Team, team_id)
            if not team:
                raise HTTPException(status_code=404, detail="Team not found")

            # Find season: use provided or latest for this team
            if season_id is None:
                latest = session.exec(
                    select(Season)
                    .join(SwimmerTeamSeason, SwimmerTeamSeason.season_id == Season.id)
                    .where(SwimmerTeamSeason.team_id == team_id)
                    .order_by(col(Season.name).desc())
                    .limit(1)
                ).first()
                if not latest:
                    return {
                        "team": TeamSummary(
                            id=team.id,
                            name=team.name,
                            short_name=team.short_name,
                            conference=team.conference,
                            is_user_team=team.is_user_team,
                        ).model_dump(),
                        "season": None,
                        "roster": [],
                        "swimmer_count": 0,
                    }
                season_id = latest.id
                season_name = latest.name
            else:
                season = session.get(Season, season_id)
                season_name = season.name if season else "Unknown"

            # Get roster
            sts_rows = session.exec(
                select(SwimmerTeamSeason, Swimmer)
                .join(Swimmer, SwimmerTeamSeason.swimmer_id == Swimmer.id)
                .where(SwimmerTeamSeason.team_id == team_id)
                .where(SwimmerTeamSeason.season_id == season_id)
                .order_by(Swimmer.last_name, Swimmer.first_name)
            ).all()

            # Compute bests for all swimmers in this team/season
            team_bests = _compute_team_bests(session, team_id, season_id)

            roster = []
            for sts, swimmer in sts_rows:
                bests = team_bests.get(swimmer.id, [])
                roster.append(
                    RosterEntry(
                        swimmer_id=swimmer.id,
                        name=swimmer.full_name,
                        gender=swimmer.gender,
                        grade=sts.grade,
                        events=bests,
                    ).model_dump()
                )

            return {
                "team": TeamSummary(
                    id=team.id,
                    name=team.name,
                    short_name=team.short_name,
                    conference=team.conference,
                    is_user_team=team.is_user_team,
                ).model_dump(),
                "season": {"id": season_id, "name": season_name},
                "roster": roster,
                "swimmer_count": len(roster),
            }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get scouting report: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/historical/roster/{team_id}", response_model=list[RosterEntry])
async def get_team_roster(
    team_id: int,
    season_id: int = Query(..., description="Season ID"),
):
    """Get team roster for a season with best times."""
    try:
        repo = SQLiteRepository()
        data = repo.get_team_roster(team_id, season_id)
        return [
            RosterEntry(
                swimmer_id=d["swimmer_id"],
                name=d["name"],
                gender=d.get("gender"),
                grade=d.get("grade"),
                events=d.get("events", []),
            )
            for d in data
        ]
    except Exception as e:
        logger.error(f"Failed to get team roster: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/historical/scouting/{team_id}/optimizer-data")
async def get_optimizer_data(
    team_id: int,
    season: str | None = Query(None, description="Season name (e.g. 2025-2026)"),
):
    """Get team data formatted for the optimizer (SwimmerEntry format).

    Returns scouting data ready to use as opponent_data in optimization
    requests, eliminating the need for file upload.
    """
    try:
        from swim_ai_reflex.backend.services.scouting_service import (
            get_team_roster_for_optimizer,
        )

        entries = get_team_roster_for_optimizer(team_id=team_id, season_name=season)

        if not entries:
            raise HTTPException(
                status_code=404,
                detail="No scouting data found for this team/season",
            )

        return {
            "success": True,
            "team_id": team_id,
            "entry_count": len(entries),
            "swimmer_count": len(set(e["swimmer"] for e in entries)),
            "events": sorted(set(e["event"] for e in entries)),
            "data": entries,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get optimizer data: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/historical/scouted-teams")
async def list_scouted_teams(
    season: str | None = Query(None, description="Season name filter"),
):
    """List all teams with scouting data in the database."""
    try:
        from swim_ai_reflex.backend.services.scouting_service import (
            list_scouted_teams as _list_teams,
        )

        teams = _list_teams(season_name=season)
        return {"teams": teams, "count": len(teams)}
    except Exception as e:
        logger.error(f"Failed to list scouted teams: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# Import Logs
# =============================================================================


@router.get("/historical/imports")
async def list_imports(
    status: str | None = Query(None, description="Filter by status"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
):
    """List import log entries with optional status filter and pagination."""
    try:
        with get_session() as session:
            stmt = select(ImportLog)
            count_stmt = select(func.count(ImportLog.id))

            if status:
                stmt = stmt.where(ImportLog.status == status)
                count_stmt = count_stmt.where(ImportLog.status == status)

            total = session.exec(count_stmt).one()
            offset = (page - 1) * page_size
            stmt = (
                stmt.order_by(col(ImportLog.import_date).desc())
                .offset(offset)
                .limit(page_size)
            )
            logs = session.exec(stmt).all()

            items = [
                ImportLogEntry(
                    id=log.id,
                    source_path=log.source_path,
                    source_type=log.source_type,
                    import_date=log.import_date,
                    records_imported=log.records_imported,
                    records_skipped=log.records_skipped,
                    status=log.status,
                ).model_dump()
                for log in logs
            ]

            return {
                "items": items,
                "total": total,
                "page": page,
                "page_size": page_size,
                "has_more": offset + page_size < total,
            }
    except Exception as e:
        logger.error(f"Failed to list imports: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# BACKTEST
# =============================================================================


@router.post("/historical/meets/{meet_id}/backtest")
async def backtest_meet(
    meet_id: int,
    team_a_id: int = Query(..., description="Team A (your team) ID"),
    team_b_id: int = Query(..., description="Team B (opponent) ID"),
    optimizer: str = Query(
        "heuristic", description="Optimizer: heuristic, gurobi, stackelberg"
    ),
    max_iters: int = Query(
        0, ge=0, le=500, description="Optimizer iterations (0 = projection only)"
    ),
):
    """
    Run a historical backtest: score seed times, optionally run optimizer,
    compare predicted vs actual results.
    """
    try:
        from swim_ai_reflex.backend.utils.historical_backtest import run_backtest

        result = await run_backtest(
            meet_id=meet_id,
            team_a_id=team_a_id,
            team_b_id=team_b_id,
            optimizer=optimizer,
            max_iters=max_iters,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Backtest failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/historical/backtestable-meets")
async def list_backtestable_meets(
    min_entries: int = Query(20, ge=1, description="Minimum entries required"),
):
    """List meets suitable for backtesting (2+ teams with scored entries)."""
    try:
        from swim_ai_reflex.backend.utils.historical_backtest import (
            list_backtestable_meets as _list_meets,
        )

        meets = _list_meets(min_entries=min_entries)
        return {"meets": meets, "total": len(meets)}
    except Exception as e:
        logger.error(f"Failed to list backtestable meets: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# Prospective Championship Optimizer
# =============================================================================


@router.post(
    "/historical/championship/optimize", response_model=ProspectiveChampResponse
)
async def optimize_prospective_championship(request: ProspectiveChampRequest):
    """
    Optimize a prospective championship meet using team rosters from the database.

    Assembles rosters from swimmer_bests table, filters to championship events,
    and runs championship strategy optimization.
    """
    import time as time_mod

    # NOTE: championship_strategy may be located in core/ or services/championship/
    # depending on the codebase version. Adjust the import as needed.
    from swim_ai_reflex.backend.core.championship_strategy import (
        run_championship_strategy,
    )
    from swim_ai_reflex.backend.core.rules import VISAAChampRules
    from swim_ai_reflex.backend.utils.prospective_optimizer import (
        build_championship_roster,
        validate_season,
        validate_teams,
    )

    VALID_METHODS = {
        "projection",
        "greedy",
        "nash",
        "aquaopt",
        "gurobi",
        "stackelberg_champ",
    }

    try:
        start_time = time_mod.time()

        if request.method not in VALID_METHODS:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid method '{request.method}'. Must be one of: {sorted(VALID_METHODS)}",
            )

        if len(request.team_ids) > 30:
            raise HTTPException(status_code=400, detail="Maximum 30 teams allowed")

        with get_session() as session:
            # Validate inputs
            team_map = validate_teams(session, request.team_ids)
            season_name = validate_season(session, request.season_id)

            # Build roster DataFrame
            all_entries = build_championship_roster(
                session=session,
                team_ids=request.team_ids,
                season_id=request.season_id,
                time_metric=request.time_metric,
            )

        if all_entries.empty:
            raise HTTPException(
                status_code=404,
                detail="No swimmer data found for specified teams/season",
            )

        # Build kwargs for championship strategy
        kwargs: dict[str, Any] = {"gurobi_time_limit": request.gurobi_time_limit}
        seton_team_name = None

        if request.seton_team_id:
            seton_team_name = team_map.get(request.seton_team_id)
            if not seton_team_name:
                raise HTTPException(
                    status_code=400,
                    detail=f"seton_team_id {request.seton_team_id} must be in team_ids",
                )

        if request.method == "stackelberg_champ":
            if not seton_team_name:
                raise HTTPException(
                    status_code=400,
                    detail="seton_team_id required for stackelberg_champ method",
                )
            kwargs["seton_team_name"] = seton_team_name
            kwargs["max_candidates"] = request.max_candidates
            kwargs["top_n_opponents"] = request.top_n_opponents

        # Run championship strategy
        result = run_championship_strategy(
            all_entries=all_entries,
            rules=VISAAChampRules(),
            time_col="time",
            method=request.method,
            **kwargs,
        )

        # Format standings
        standings = [
            TeamStanding(team_name=team, score=score, rank=i + 1)
            for i, (team, score) in enumerate(result["standings"])
        ]

        # Extract seton lineup if requested
        seton_lineup = None
        if seton_team_name and result.get("team_lineups"):
            lineup_df = result["team_lineups"].get(seton_team_name)
            if lineup_df is not None and not lineup_df.empty:
                events_grouped = (
                    lineup_df.groupby("event")["swimmer"].apply(list).to_dict()
                )
                seton_lineup = [
                    EventLineupEntry(event=evt, swimmers=swimmers)
                    for evt, swimmers in sorted(events_grouped.items())
                ]

        optimization_time_ms = int((time_mod.time() - start_time) * 1000)

        return ProspectiveChampResponse(
            standings=standings,
            seton_lineup=seton_lineup,
            method=result["method"],
            status=result.get("status", "ok"),
            optimization_time_ms=optimization_time_ms,
            team_count=len(all_entries["team"].unique()),
            swimmer_count=len(all_entries["swimmer"].unique()),
            event_count=len(all_entries["event"].unique()),
            season_name=season_name,
            time_metric=request.time_metric,
        )

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(
            f"Prospective championship optimization failed: {e}", exc_info=True
        )
        raise HTTPException(status_code=500, detail=str(e))
