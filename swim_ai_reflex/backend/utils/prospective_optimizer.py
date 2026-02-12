"""
Prospective Championship Optimizer -- Roster Assembly

Builds championship rosters from the swimmer_bests table for prospective
(future meet) optimization. Shared by the API endpoint and CLI script.

NOTE: References swim_ai_reflex.backend.etl.normalizer.is_scoreable_event
which may not exist on Mac yet. If missing, a fallback is provided.
"""

import logging

import pandas as pd
from sqlalchemy import text
from sqlmodel import Session, select

from swim_ai_reflex.backend.persistence.db_models import Season, Team

logger = logging.getLogger(__name__)

# Try to import the ETL normalizer; provide fallback if not available on Mac
try:
    from swim_ai_reflex.backend.etl.normalizer import is_scoreable_event
except ImportError:

    def is_scoreable_event(event_name: str, meet_type: str = "championship") -> bool:
        """Fallback: assume all standard events are scoreable."""
        non_scoreable = {"diving", "1 mtr diving", "1m diving"}
        return event_name.lower().strip() not in non_scoreable


# Valid time metric columns in swimmer_bests
VALID_TIME_METRICS = ("best_time", "recent_time", "mean_time")


def validate_teams(session: Session, team_ids: list[int]) -> dict[int, str]:
    """Validate team IDs exist and return {id: name} mapping."""
    teams = session.exec(select(Team).where(Team.id.in_(team_ids))).all()
    found = {t.id: t.name for t in teams}
    missing = set(team_ids) - set(found.keys())
    if missing:
        raise ValueError(f"Team IDs not found: {sorted(missing)}")
    return found


def validate_season(session: Session, season_id: int) -> str:
    """Validate season exists and return its name."""
    season = session.get(Season, season_id)
    if not season:
        raise ValueError(f"Season ID {season_id} not found")
    return season.name


def build_championship_roster(
    session: Session,
    team_ids: list[int],
    season_id: int,
    time_metric: str = "best_time",
) -> pd.DataFrame:
    """
    Build an all_entries DataFrame from swimmer_bests for championship optimization.
    """
    if time_metric not in VALID_TIME_METRICS:
        raise ValueError(
            f"Invalid time_metric '{time_metric}'. Must be one of: {VALID_TIME_METRICS}"
        )

    placeholders = ",".join(str(tid) for tid in team_ids)
    time_col = f"sb.{time_metric}"

    rows = session.exec(
        text(f"""
        SELECT s.first_name || ' ' || s.last_name AS swimmer_name,
               sb.event_name,
               {time_col} AS time_val,
               t.name AS team_name,
               t.id AS team_id,
               sts.grade
        FROM swimmer_bests sb
        JOIN swimmers s ON sb.swimmer_id = s.id
        JOIN swimmer_team_seasons sts
            ON sts.swimmer_id = s.id
            AND sts.season_id = :season_id
            AND sts.team_id IN ({placeholders})
        JOIN teams t ON sts.team_id = t.id
        WHERE sb.season_id = :season_id
          AND {time_col} IS NOT NULL
          AND {time_col} > 0
        ORDER BY t.name, s.last_name, s.first_name, sb.event_name
    """),
        params={"season_id": season_id},
    ).all()

    if not rows:
        return pd.DataFrame()

    records = []
    filtered_events = 0
    for swimmer_name, event_name, time_val, team_name, team_id, grade in rows:
        if not is_scoreable_event(event_name, "championship"):
            filtered_events += 1
            continue
        records.append(
            {
                "swimmer": swimmer_name,
                "event": event_name,
                "time": round(time_val, 2),
                "team": team_name,
                "team_id": team_id,
                "grade": grade if grade else 10,
            }
        )

    if filtered_events:
        logger.info(f"Filtered {filtered_events} non-championship events")

    return pd.DataFrame(records)


def get_season_teams(
    session: Session,
    season_id: int,
    min_swimmers: int = 1,
) -> list[dict]:
    """List teams that have swimmers with bests in a given season."""
    rows = session.exec(
        text("""
        SELECT t.id, t.name, COUNT(DISTINCT sb.swimmer_id) AS swimmer_count
        FROM swimmer_bests sb
        JOIN swimmer_team_seasons sts
            ON sts.swimmer_id = sb.swimmer_id
            AND sts.season_id = :season_id
        JOIN teams t ON sts.team_id = t.id
        WHERE sb.season_id = :season_id
          AND sb.best_time IS NOT NULL
        GROUP BY t.id, t.name
        HAVING swimmer_count >= :min_swimmers
        ORDER BY swimmer_count DESC
    """),
        params={"season_id": season_id, "min_swimmers": min_swimmers},
    ).all()

    return [
        {"id": tid, "name": name, "swimmer_count": count} for tid, name, count in rows
    ]
