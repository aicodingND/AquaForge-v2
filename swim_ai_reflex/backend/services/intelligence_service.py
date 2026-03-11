"""
Intelligence Service Adapter

Bridges the persistence layer (SQLite DB) to intelligence modules
by converting DB query results into the data formats expected by
TrajectoryPredictor, PsychologicalProfiler, and CoachTendencyAnalyzer.
"""

import logging
from datetime import datetime

from sqlmodel import select

from swim_ai_reflex.backend.models.opponent import MeetResult
from swim_ai_reflex.backend.models.swimmer import TimeRecord
from swim_ai_reflex.backend.persistence.database import get_session
from swim_ai_reflex.backend.persistence.db_models import (
    Entry,
    Event,
    Meet,
    MeetTeam,
    Swimmer,
    Team,
)

logger = logging.getLogger(__name__)


def get_swimmer_name(swimmer_id: int) -> str:
    """Look up a swimmer's full name by ID."""
    with get_session() as session:
        swimmer = session.get(Swimmer, swimmer_id)
        if swimmer:
            return f"{swimmer.first_name} {swimmer.last_name}"
        return ""


def get_swimmer_time_records(
    swimmer_id: int, event_name: str | None = None
) -> list[TimeRecord]:
    """Query DB for a swimmer's times, formatted for TrajectoryPredictor.

    Returns TimeRecord objects with correct field types.
    """
    with get_session() as session:
        # Get swimmer name
        swimmer = session.get(Swimmer, swimmer_id)
        swimmer_name = f"{swimmer.first_name} {swimmer.last_name}" if swimmer else ""

        stmt = (
            select(Entry, Event, Meet)
            .join(Event, Entry.event_id == Event.id)
            .join(Meet, Event.meet_id == Meet.id)
            .where(Entry.swimmer_id == swimmer_id)
            .where(Entry.finals_time.is_not(None))
            .where(Event.is_relay == False)  # noqa: E712
        )
        if event_name:
            stmt = stmt.where(Event.event_name == event_name)

        stmt = stmt.order_by(Meet.meet_date)
        rows = session.exec(stmt).all()

        records = []
        for entry, event, meet in rows:
            records.append(
                TimeRecord(
                    swimmer=swimmer_name,
                    event=event.event_name,
                    time=entry.finals_time,
                    meet_name=meet.name,
                    meet_date=meet.meet_date,
                    pool_length=meet.pool_course or "25Y",
                )
            )
        return records


def get_swimmer_profile_data(
    swimmer_id: int,
) -> tuple[list[MeetResult], list[dict]]:
    """Query DB for data needed by PsychologicalProfiler.

    Returns:
        meet_results: Meet-level MeetResult objects (for meet context lookup)
        swimmer_times: Per-entry dicts with {meet_id, event, time, place}
    """
    with get_session() as session:
        # Get all entries for this swimmer
        stmt = (
            select(Entry, Event, Meet)
            .join(Event, Entry.event_id == Event.id)
            .join(Meet, Event.meet_id == Meet.id)
            .where(Entry.swimmer_id == swimmer_id)
            .where(Entry.finals_time.is_not(None))
            .order_by(Meet.meet_date)
        )
        rows = session.exec(stmt).all()

        if not rows:
            return [], []

        # Build swimmer_times (per-entry data for PsychologicalProfiler)
        swimmer_times: list[dict] = []
        meet_ids: set[int] = set()

        for entry, event, meet in rows:
            meet_ids.add(meet.id)
            swimmer_times.append(
                {
                    "meet_id": str(meet.id),
                    "event": event.event_name,
                    "time": entry.finals_time,
                    "place": entry.place or 0,
                }
            )

        # Build meet-level MeetResult objects (aggregated by meet)
        meet_results = _build_meet_results(session, meet_ids)

        return meet_results, swimmer_times


def get_team_meet_results(team_name: str) -> list[MeetResult]:
    """Query DB for meet-level results involving a specific team.

    Used by CoachTendencyAnalyzer to analyze coaching patterns.
    Returns MeetResult objects aggregated at the meet level.
    """
    with get_session() as session:
        # Find the team
        team = session.exec(
            select(Team).where(
                Team.name.ilike(f"%{team_name}%")
                | Team.short_name.ilike(f"%{team_name}%")
            )
        ).first()

        if not team:
            logger.warning("Team not found: %s", team_name)
            return []

        # Find all meets this team participated in
        meet_team_rows = session.exec(
            select(MeetTeam).where(MeetTeam.team_id == team.id)
        ).all()

        if not meet_team_rows:
            return []

        meet_ids = {mt.meet_id for mt in meet_team_rows}
        return _build_meet_results(session, meet_ids, focus_team_id=team.id)


def _build_meet_results(
    session, meet_ids: set[int], focus_team_id: int | None = None
) -> list[MeetResult]:
    """Build meet-level MeetResult objects from DB data.

    Aggregates entries into lineups, pulls team scores from MeetTeam.
    """
    results = []

    for meet_id in sorted(meet_ids):
        meet = session.get(Meet, meet_id)
        if not meet:
            continue

        # Get team scores for this meet
        meet_teams = session.exec(
            select(MeetTeam, Team)
            .join(Team, MeetTeam.team_id == Team.id)
            .where(MeetTeam.meet_id == meet_id)
        ).all()

        # Determine Seton and opponent scores
        seton_score = 0.0
        opponent_score = 0.0
        opponent_team_name = ""

        for mt, t in meet_teams:
            if t.is_user_team:
                seton_score = mt.final_score or 0.0
            else:
                opponent_score = mt.final_score or 0.0
                opponent_team_name = t.name

        # If focus_team is the opponent, swap perspective
        if focus_team_id:
            for mt, t in meet_teams:
                if t.id == focus_team_id:
                    opponent_team_name = t.name
                    break

        # Get all entries for this meet grouped by team
        entry_stmt = (
            select(Entry, Event, Swimmer)
            .join(Event, Entry.event_id == Event.id)
            .join(Swimmer, Entry.swimmer_id == Swimmer.id)
            .where(Event.meet_id == meet_id)
            .where(Entry.finals_time.is_not(None))
            .order_by(Event.event_number)
        )
        entries = session.exec(entry_stmt).all()

        seton_lineup = []
        opponent_lineup = []

        for entry, event, swimmer in entries:
            lineup_entry = {
                "event": event.event_name,
                "swimmer": f"{swimmer.first_name} {swimmer.last_name}",
                "time": entry.finals_time,
                "place": entry.place or 0,
                "points": entry.points,
                "is_exhibition": entry.is_exhibition,
            }

            # Check which team this entry belongs to
            if entry.team_id:
                team = session.get(Team, entry.team_id)
                if team and team.is_user_team:
                    seton_lineup.append(lineup_entry)
                else:
                    opponent_lineup.append(lineup_entry)
            else:
                # Fall back: check via SwimmerTeamSeason
                opponent_lineup.append(lineup_entry)

        meet_date_dt = datetime.combine(meet.meet_date, datetime.min.time())

        results.append(
            MeetResult(
                meet_id=str(meet.id),
                date=meet_date_dt,
                opponent_team=opponent_team_name,
                seton_score=seton_score,
                opponent_score=opponent_score,
                seton_lineup=seton_lineup,
                opponent_lineup=opponent_lineup,
                location=meet.location or "Unknown",
                meet_type=meet.meet_type or "regular",
            )
        )

    return results
