"""
SQLite Repository - Persistent storage implementation.

Implements MeetRepository (backward compat) plus new historical query methods.

NOTE: Imports from swim_ai_reflex.backend.models.opponent (CoachTendency,
MeetResult, OpponentProfile) -- these models may not exist on Mac yet.
If import fails, the MeetRepository interface methods will need updating.
"""

import json
from datetime import datetime

from sqlalchemy import func
from sqlmodel import Session, col, select

from swim_ai_reflex.backend.persistence.database import engine, init_db
from swim_ai_reflex.backend.persistence.db_models import (
    Entry,
    Event,
    ImportLog,
    Meet,
    MeetTeam,
    OptimizationRun,
    Season,
    Swimmer,
    SwimmerBest,
    SwimmerTeamSeason,
    Team,
)
from swim_ai_reflex.backend.persistence.repository import MeetRepository

# NOTE: These models may not exist on Mac yet — guard import
try:
    from swim_ai_reflex.backend.models.opponent import (  # noqa: F401
        CoachTendency,
        MeetResult,
        OpponentProfile,
    )

    _HAS_OPPONENT_MODELS = True
except ImportError:
    _HAS_OPPONENT_MODELS = False


class SQLiteRepository(MeetRepository):
    """
    Persistent repository backed by SQLite (or PostgreSQL via DATABASE_URL).
    Implements the existing MeetRepository interface for backward compatibility,
    plus new methods for historical data queries.
    """

    def __init__(self):
        init_db()

    def _session(self) -> Session:
        return Session(engine)

    # =========================================================================
    # MeetRepository interface (backward compat)
    # =========================================================================

    async def save_meet(self, meet) -> str:
        with self._session() as session:
            run = OptimizationRun(
                run_date=meet.date,
                optimizer_type="recorded",
                home_score=meet.seton_score,
                away_score=meet.opponent_score,
                lineup_json=json.dumps(
                    {
                        "meet_id": meet.meet_id,
                        "opponent": meet.opponent_team,
                        "location": meet.location,
                        "meet_type": meet.meet_type,
                        "seton_lineup": meet.seton_lineup,
                        "opponent_lineup": meet.opponent_lineup,
                    }
                ),
            )
            session.add(run)
            session.commit()
            return meet.meet_id

    async def get_meet(self, meet_id: str):
        if not _HAS_OPPONENT_MODELS:
            return None
        with self._session() as session:
            stmt = select(OptimizationRun).where(
                OptimizationRun.lineup_json.contains(meet_id)
            )
            run = session.exec(stmt).first()
            if not run or not run.lineup_json:
                return None
            data = json.loads(run.lineup_json)
            return MeetResult(
                meet_id=data.get("meet_id", meet_id),
                date=run.run_date,
                opponent_team=data.get("opponent", "Unknown"),
                seton_score=run.home_score,
                opponent_score=run.away_score,
                seton_lineup=data.get("seton_lineup", []),
                opponent_lineup=data.get("opponent_lineup", []),
                location=data.get("location", "Unknown"),
                meet_type=data.get("meet_type", "regular"),
            )

    async def get_meets_by_opponent(self, opponent: str) -> list:
        if not _HAS_OPPONENT_MODELS:
            return []
        with self._session() as session:
            stmt = select(OptimizationRun).where(
                OptimizationRun.lineup_json.contains(opponent)
            )
            runs = session.exec(stmt).all()
            results = []
            for run in runs:
                if not run.lineup_json:
                    continue
                data = json.loads(run.lineup_json)
                if data.get("opponent", "").lower() == opponent.lower():
                    results.append(
                        MeetResult(
                            meet_id=data.get("meet_id", ""),
                            date=run.run_date,
                            opponent_team=data["opponent"],
                            seton_score=run.home_score,
                            opponent_score=run.away_score,
                            seton_lineup=data.get("seton_lineup", []),
                            opponent_lineup=data.get("opponent_lineup", []),
                            location=data.get("location", "Unknown"),
                            meet_type=data.get("meet_type", "regular"),
                        )
                    )
            return results

    async def get_recent_meets(self, limit: int = 10) -> list:
        if not _HAS_OPPONENT_MODELS:
            return []
        with self._session() as session:
            stmt = (
                select(OptimizationRun)
                .order_by(col(OptimizationRun.run_date).desc())
                .limit(limit)
            )
            runs = session.exec(stmt).all()
            results = []
            for run in runs:
                if not run.lineup_json:
                    continue
                data = json.loads(run.lineup_json)
                results.append(
                    MeetResult(
                        meet_id=data.get("meet_id", ""),
                        date=run.run_date,
                        opponent_team=data.get("opponent", "Unknown"),
                        seton_score=run.home_score,
                        opponent_score=run.away_score,
                        seton_lineup=data.get("seton_lineup", []),
                        opponent_lineup=data.get("opponent_lineup", []),
                        location=data.get("location", "Unknown"),
                        meet_type=data.get("meet_type", "regular"),
                    )
                )
            return results

    async def get_meets_in_range(
        self, start_date: datetime, end_date: datetime
    ) -> list:
        if not _HAS_OPPONENT_MODELS:
            return []
        with self._session() as session:
            stmt = select(OptimizationRun).where(
                OptimizationRun.run_date >= start_date,
                OptimizationRun.run_date <= end_date,
            )
            runs = session.exec(stmt).all()
            results = []
            for run in runs:
                if not run.lineup_json:
                    continue
                data = json.loads(run.lineup_json)
                results.append(
                    MeetResult(
                        meet_id=data.get("meet_id", ""),
                        date=run.run_date,
                        opponent_team=data.get("opponent", "Unknown"),
                        seton_score=run.home_score,
                        opponent_score=run.away_score,
                        seton_lineup=data.get("seton_lineup", []),
                        opponent_lineup=data.get("opponent_lineup", []),
                        location=data.get("location", "Unknown"),
                        meet_type=data.get("meet_type", "regular"),
                    )
                )
            return results

    async def save_tendency(self, tendency) -> None:
        pass

    async def get_tendency(self, team_name: str):
        return None

    async def get_all_tendencies(self) -> list:
        return []

    async def save_opponent(self, profile) -> None:
        with self._session() as session:
            team = session.exec(
                select(Team).where(func.lower(Team.name) == profile.team_name.lower())
            ).first()
            if not team:
                team = Team(name=profile.team_name)
                session.add(team)
                session.commit()

    async def get_opponent(self, team_name: str):
        if not _HAS_OPPONENT_MODELS:
            return None
        with self._session() as session:
            team = session.exec(
                select(Team).where(func.lower(Team.name) == team_name.lower())
            ).first()
            if not team:
                return None
            return OpponentProfile(team_name=team.name)

    async def list_opponents(self) -> list[str]:
        with self._session() as session:
            teams = session.exec(
                select(Team).where(Team.is_user_team == False)  # noqa: E712
            ).all()
            return [t.name for t in teams]

    # =========================================================================
    # New Historical Query Methods
    # =========================================================================

    def get_or_create_team(self, name: str, session: Session | None = None) -> Team:
        """Get team by name or create it."""
        own_session = session is None
        if own_session:
            session = self._session()
        try:
            team = session.exec(
                select(Team).where(func.lower(Team.name) == name.lower())
            ).first()
            if not team:
                # Check aliases
                alias_match = session.exec(
                    select(Team).where(Team.aliases_json.contains(name))
                ).first()
                if alias_match:
                    return alias_match
                team = Team(name=name)
                session.add(team)
                session.commit()
                session.refresh(team)
            return team
        finally:
            if own_session:
                session.close()

    def get_or_create_season(self, name: str, session: Session | None = None) -> Season:
        """Get season by name (e.g., '2025-2026') or create it."""
        own_session = session is None
        if own_session:
            session = self._session()
        try:
            season = session.exec(select(Season).where(Season.name == name)).first()
            if not season:
                season = Season(name=name)
                session.add(season)
                session.commit()
                session.refresh(season)
            return season
        finally:
            if own_session:
                session.close()

    def get_swimmer_times(
        self, swimmer_id: int, event_name: str | None = None
    ) -> list[dict]:
        """Get all recorded times for a swimmer, optionally filtered by event."""
        with self._session() as session:
            stmt = (
                select(Entry, Event, Meet)
                .join(Event, Entry.event_id == Event.id)
                .join(Meet, Event.meet_id == Meet.id)
                .where(Entry.swimmer_id == swimmer_id)
                .where(Entry.finals_time.is_not(None))
            )
            if event_name:
                stmt = stmt.where(Event.event_name == event_name)
            stmt = stmt.order_by(Meet.meet_date)

            results = session.exec(stmt).all()
            return [
                {
                    "time": entry.finals_time,
                    "seed_time": entry.seed_time,
                    "place": entry.place,
                    "points": entry.points,
                    "event": event.event_name,
                    "meet": meet.name,
                    "meet_date": meet.meet_date.isoformat(),
                    "meet_type": meet.meet_type,
                }
                for entry, event, meet in results
            ]

    def get_swimmer_progression(self, swimmer_id: int) -> list[dict]:
        """Get season-over-season best times per event."""
        with self._session() as session:
            bests = session.exec(
                select(SwimmerBest, Season)
                .join(Season, SwimmerBest.season_id == Season.id)
                .where(SwimmerBest.swimmer_id == swimmer_id)
                .order_by(Season.name, SwimmerBest.event_name)
            ).all()
            return [
                {
                    "event": best.event_name,
                    "season": season.name,
                    "best_time": best.best_time,
                    "mean_time": best.mean_time,
                    "std_dev": best.std_dev,
                    "sample_size": best.sample_size,
                    "improvement_pct": best.improvement_pct,
                }
                for best, season in bests
            ]

    def get_head_to_head(self, team_a_id: int, team_b_id: int) -> list[dict]:
        """Get historical head-to-head results between two teams."""
        with self._session() as session:
            stmt = (
                select(Meet, MeetTeam)
                .join(MeetTeam, Meet.id == MeetTeam.meet_id)
                .where(MeetTeam.team_id.in_([team_a_id, team_b_id]))
                .order_by(Meet.meet_date)
            )
            rows = session.exec(stmt).all()

            meets_map: dict[int, dict] = {}
            for meet, mt in rows:
                if meet.id not in meets_map:
                    meets_map[meet.id] = {"meet": meet, "scores": {}}
                meets_map[meet.id]["scores"][mt.team_id] = mt.final_score

            results = []
            for mid, data in meets_map.items():
                if team_a_id in data["scores"] and team_b_id in data["scores"]:
                    results.append(
                        {
                            "meet": data["meet"].name,
                            "date": data["meet"].meet_date.isoformat(),
                            "team_a_score": data["scores"].get(team_a_id),
                            "team_b_score": data["scores"].get(team_b_id),
                        }
                    )
            return results

    def get_team_roster(self, team_id: int, season_id: int) -> list[dict]:
        """Get team roster for a season with best times."""
        with self._session() as session:
            stmt = (
                select(SwimmerTeamSeason, Swimmer)
                .join(Swimmer, SwimmerTeamSeason.swimmer_id == Swimmer.id)
                .where(SwimmerTeamSeason.team_id == team_id)
                .where(SwimmerTeamSeason.season_id == season_id)
                .where(SwimmerTeamSeason.is_active == True)  # noqa: E712
                .order_by(Swimmer.last_name, Swimmer.first_name)
            )
            rows = session.exec(stmt).all()

            roster = []
            for sts, swimmer in rows:
                bests = session.exec(
                    select(SwimmerBest)
                    .where(SwimmerBest.swimmer_id == swimmer.id)
                    .where(SwimmerBest.season_id == season_id)
                ).all()

                roster.append(
                    {
                        "swimmer_id": swimmer.id,
                        "name": swimmer.full_name,
                        "gender": swimmer.gender,
                        "grade": sts.grade,
                        "events": [
                            {
                                "event": b.event_name,
                                "best_time": b.best_time,
                                "mean_time": b.mean_time,
                                "sample_size": b.sample_size,
                            }
                            for b in bests
                        ],
                    }
                )
            return roster

    def check_import_exists(self, checksum: str) -> bool:
        """Check if a file has already been imported."""
        with self._session() as session:
            log = session.exec(
                select(ImportLog).where(ImportLog.checksum == checksum)
            ).first()
            return log is not None and log.status == "success"

    def create_import_log(
        self, source_path: str, source_type: str, checksum: str
    ) -> ImportLog:
        """Create a new import log entry."""
        with self._session() as session:
            log = ImportLog(
                source_path=source_path,
                source_type=source_type,
                checksum=checksum,
                status="running",
            )
            session.add(log)
            session.commit()
            session.refresh(log)
            return log

    def update_import_log(
        self,
        log_id: int,
        status: str,
        records_imported: int = 0,
        records_skipped: int = 0,
        errors: list[str] | None = None,
    ) -> None:
        """Update an import log after completion."""
        with self._session() as session:
            log = session.get(ImportLog, log_id)
            if log:
                log.status = status
                log.records_imported = records_imported
                log.records_skipped = records_skipped
                if errors:
                    log.errors = errors
                session.add(log)
                session.commit()
