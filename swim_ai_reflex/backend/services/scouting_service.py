"""
Scouting Service

Bridges scraped/historical opponent data to the optimizer.
Pulls team rosters with best times from the DB and formats them
as SwimmerEntry objects ready for optimization endpoints.
"""

import logging

from sqlmodel import col, select

from swim_ai_reflex.backend.persistence.database import get_session
from swim_ai_reflex.backend.persistence.db_models import (
    Season,
    Swimmer,
    SwimmerBest,
    SwimmerTeamSeason,
    Team,
)

logger = logging.getLogger(__name__)


def get_team_roster_for_optimizer(
    team_id: int | None = None,
    team_name: str | None = None,
    season_name: str | None = None,
) -> list[dict]:
    """Pull a team's roster with best times from the DB.

    Returns list of dicts matching the SwimmerEntry format expected
    by optimization endpoints:
        {"swimmer": str, "event": str, "time": float, "team": str, "grade": int, "gender": str}

    Args:
        team_id: Team ID (preferred, exact match)
        team_name: Team name (fuzzy match, used if team_id not provided)
        season_name: Season (default: latest available)
    """
    with get_session() as session:
        # Resolve team
        if team_id:
            team = session.get(Team, team_id)
        elif team_name:
            team = session.exec(
                select(Team).where(
                    Team.name.ilike(f"%{team_name}%")
                    | Team.short_name.ilike(f"%{team_name}%")
                )
            ).first()
        else:
            logger.warning("No team_id or team_name provided")
            return []

        if not team:
            logger.warning("Team not found: id=%s name=%s", team_id, team_name)
            return []

        # Resolve season
        if season_name:
            season = session.exec(
                select(Season).where(Season.name == season_name)
            ).first()
            season_id = season.id if season else None
        else:
            # Find latest season for this team
            latest = session.exec(
                select(Season)
                .join(SwimmerTeamSeason, SwimmerTeamSeason.season_id == Season.id)
                .where(SwimmerTeamSeason.team_id == team.id)
                .order_by(col(Season.name).desc())
                .limit(1)
            ).first()
            season_id = latest.id if latest else None

        if not season_id:
            logger.warning("No season data found for team %s", team.name)
            return []

        # Get all swimmers + their bests for this team/season
        sts_rows = session.exec(
            select(SwimmerTeamSeason, Swimmer)
            .join(Swimmer, SwimmerTeamSeason.swimmer_id == Swimmer.id)
            .where(SwimmerTeamSeason.team_id == team.id)
            .where(SwimmerTeamSeason.season_id == season_id)
        ).all()

        entries = []
        for sts, swimmer in sts_rows:
            # Get this swimmer's best times
            bests = session.exec(
                select(SwimmerBest).where(
                    SwimmerBest.swimmer_id == swimmer.id,
                    SwimmerBest.season_id == season_id,
                )
            ).all()

            for best in bests:
                entries.append(
                    {
                        "swimmer": f"{swimmer.first_name} {swimmer.last_name}",
                        "event": best.event_name,
                        "time": best.best_time,
                        "team": team.short_name or team.name,
                        "grade": sts.grade or 12,
                        "gender": swimmer.gender or "M",
                    }
                )

        logger.info(
            "Scouting: %s — %d swimmers, %d entries",
            team.name,
            len(sts_rows),
            len(entries),
        )
        return entries


def list_scouted_teams(season_name: str | None = None) -> list[dict]:
    """List all teams with scouting data in the DB.

    Returns list of dicts: {id, name, short_name, swimmer_count, entry_count}
    """
    with get_session() as session:
        # Get season filter
        season_id = None
        if season_name:
            season = session.exec(
                select(Season).where(Season.name == season_name)
            ).first()
            if season:
                season_id = season.id

        # Build query for teams with swimmers
        stmt = select(Team).join(
            SwimmerTeamSeason, SwimmerTeamSeason.team_id == Team.id
        )
        if season_id:
            stmt = stmt.where(SwimmerTeamSeason.season_id == season_id)

        stmt = stmt.distinct()
        teams = session.exec(stmt).all()

        result = []
        for team in teams:
            # Count swimmers and entries for this team
            sts_query = select(SwimmerTeamSeason).where(
                SwimmerTeamSeason.team_id == team.id
            )
            if season_id:
                sts_query = sts_query.where(SwimmerTeamSeason.season_id == season_id)

            swimmer_count = len(session.exec(sts_query).all())

            result.append(
                {
                    "id": team.id,
                    "name": team.name,
                    "short_name": team.short_name,
                    "swimmer_count": swimmer_count,
                    "is_user_team": team.is_user_team,
                }
            )

        return sorted(result, key=lambda t: t["name"])
