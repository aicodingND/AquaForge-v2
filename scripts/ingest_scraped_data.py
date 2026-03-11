#!/usr/bin/env python3
"""
Ingest Scraped SwimCloud Data into AquaForge Database

Reads JSON files from data/scraped/{CODE}_swimcloud.json and imports:
- Teams (creates or updates)
- Swimmers (creates or matches existing)
- SwimmerTeamSeason associations
- SwimmerBest records (from scraped seed_time data)

Usage:
    python scripts/ingest_scraped_data.py [--dir data/scraped] [--season 2025-2026] [--dry-run]
"""

import argparse
import json
import logging
import sys
from datetime import datetime
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlmodel import select  # noqa: E402

from swim_ai_reflex.backend.persistence.database import (  # noqa: E402
    get_session,
    init_db,
)
from swim_ai_reflex.backend.persistence.db_models import (  # noqa: E402
    Season,
    Swimmer,
    SwimmerBest,
    SwimmerTeamSeason,
    Team,
)

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


# Map class year strings to approximate grade numbers
CLASS_YEAR_TO_GRADE = {
    "SR": 12,
    "JR": 11,
    "SO": 10,
    "FR": 9,
    "8": 8,
    "7": 7,
}


# Normalize event names: strip gender prefix if present
# "Boys 50 Free" -> "50 Free", "Girls 100 Back" -> "100 Back"
def normalize_event_name(event: str) -> str:
    """Strip gender prefix from event name."""
    for prefix in ("Boys ", "Girls "):
        if event.startswith(prefix):
            return event[len(prefix) :]
    return event


def parse_name(full_name: str) -> tuple[str, str]:
    """Split full name into (first_name, last_name)."""
    parts = full_name.strip().split()
    if len(parts) == 1:
        return parts[0], ""
    return parts[0], " ".join(parts[1:])


def get_or_create_season(session, season_name: str) -> int:
    """Get or create a season, return its ID."""
    season = session.exec(select(Season).where(Season.name == season_name)).first()
    if season:
        return season.id

    season = Season(name=season_name)
    session.add(season)
    session.flush()
    logger.info("Created season: %s (id=%d)", season_name, season.id)
    return season.id


def get_or_create_team(session, code: str, name: str) -> int:
    """Get or create a team, return its ID."""
    # Try exact short_name match first
    team = session.exec(select(Team).where(Team.short_name == code)).first()
    if team:
        return team.id

    # Try name match
    team = session.exec(select(Team).where(Team.name == name)).first()
    if team:
        if not team.short_name:
            team.short_name = code
            session.add(team)
        return team.id

    # Create new
    team = Team(name=name, short_name=code, state="VA")
    session.add(team)
    session.flush()
    logger.info("Created team: %s (%s) id=%d", name, code, team.id)
    return team.id


def find_or_create_swimmer(
    session, first_name: str, last_name: str, gender: str | None = None
) -> int:
    """Find existing swimmer by name or create new, return ID."""
    stmt = select(Swimmer).where(
        Swimmer.first_name == first_name,
        Swimmer.last_name == last_name,
    )
    if gender:
        stmt = stmt.where(Swimmer.gender == gender)

    swimmer = session.exec(stmt).first()
    if swimmer:
        return swimmer.id

    swimmer = Swimmer(
        first_name=first_name,
        last_name=last_name,
        gender=gender,
    )
    session.add(swimmer)
    session.flush()
    return swimmer.id


def ingest_team_file(filepath: Path, season_name: str, dry_run: bool = False) -> dict:
    """Ingest a single scraped team JSON file.

    Returns stats dict with counts.
    """
    with open(filepath) as f:
        data = json.load(f)

    team_code = data.get("team_code", "???")
    team_name = data.get("team_name", "Unknown")
    roster = data.get("roster", [])
    times = data.get("times", [])
    scraped_at = data.get("scraped_at", "unknown")

    logger.info(
        "Processing %s (%s) — %d roster, %d times, scraped %s",
        team_code,
        team_name,
        len(roster),
        len(times),
        scraped_at,
    )

    if dry_run:
        return {
            "team": team_code,
            "roster": len(roster),
            "times": len(times),
            "status": "dry_run",
        }

    stats = {
        "team": team_code,
        "swimmers_created": 0,
        "swimmers_matched": 0,
        "bests_created": 0,
    }

    with get_session() as session:
        season_id = get_or_create_season(session, season_name)
        team_id = get_or_create_team(session, team_code, team_name)

        # Process roster
        swimmer_map: dict[str, int] = {}  # name -> swimmer_id
        for entry in roster:
            name = entry.get("name", "")
            if not name:
                continue

            first, last = parse_name(name)
            class_year = entry.get("classYear", "")
            grade = CLASS_YEAR_TO_GRADE.get(str(class_year))

            swimmer_id = find_or_create_swimmer(session, first, last)
            swimmer_map[name] = swimmer_id

            # Create SwimmerTeamSeason if not exists
            existing = session.exec(
                select(SwimmerTeamSeason).where(
                    SwimmerTeamSeason.swimmer_id == swimmer_id,
                    SwimmerTeamSeason.team_id == team_id,
                    SwimmerTeamSeason.season_id == season_id,
                )
            ).first()
            if not existing:
                sts = SwimmerTeamSeason(
                    swimmer_id=swimmer_id,
                    team_id=team_id,
                    season_id=season_id,
                    grade=grade,
                )
                session.add(sts)
                stats["swimmers_created"] += 1
            else:
                stats["swimmers_matched"] += 1

        # Process times -> SwimmerBest
        for time_entry in times:
            swimmer_name = time_entry.get("swimmer_name", "")
            event_raw = time_entry.get("event", "")
            seed_time = time_entry.get("seed_time")

            if not swimmer_name or not event_raw or not seed_time or seed_time <= 0:
                continue

            event_name = normalize_event_name(event_raw)

            # Find swimmer in our map
            swimmer_id = swimmer_map.get(swimmer_name)
            if not swimmer_id:
                # Try to find by parsing name
                first, last = parse_name(swimmer_name)
                swimmer_id = find_or_create_swimmer(
                    session, first, last, time_entry.get("gender")
                )

            # Upsert SwimmerBest
            existing_best = session.exec(
                select(SwimmerBest).where(
                    SwimmerBest.swimmer_id == swimmer_id,
                    SwimmerBest.event_name == event_name,
                    SwimmerBest.season_id == season_id,
                )
            ).first()

            if existing_best:
                # Update if scraped time is faster
                if seed_time < existing_best.best_time:
                    existing_best.best_time = seed_time
                    existing_best.updated_at = datetime.utcnow()
                    session.add(existing_best)
            else:
                best = SwimmerBest(
                    swimmer_id=swimmer_id,
                    event_name=event_name,
                    season_id=season_id,
                    best_time=seed_time,
                    mean_time=seed_time,
                    sample_size=1,
                )
                session.add(best)
                stats["bests_created"] += 1

        session.commit()

    logger.info(
        "  %s: %d swimmers created, %d matched, %d bests",
        team_code,
        stats["swimmers_created"],
        stats["swimmers_matched"],
        stats["bests_created"],
    )
    return stats


def main():
    parser = argparse.ArgumentParser(
        description="Ingest scraped SwimCloud data into DB"
    )
    parser.add_argument(
        "--dir",
        default="data/scraped",
        help="Directory containing *_swimcloud.json files",
    )
    parser.add_argument(
        "--season",
        default="2025-2026",
        help="Season name (default: 2025-2026)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be imported without writing",
    )
    parser.add_argument(
        "--team",
        default=None,
        help="Import only this team code (e.g. ICS)",
    )
    args = parser.parse_args()

    scraped_dir = project_root / args.dir
    if not scraped_dir.exists():
        logger.error("Scraped data directory not found: %s", scraped_dir)
        sys.exit(1)

    # Initialize DB
    if not args.dry_run:
        init_db()

    # Find JSON files
    files = sorted(scraped_dir.glob("*_swimcloud.json"))
    if args.team:
        files = [f for f in files if f.name.startswith(f"{args.team}_")]

    if not files:
        logger.warning("No scraped data files found in %s", scraped_dir)
        sys.exit(0)

    logger.info("Found %d scraped team files", len(files))

    all_stats = []
    for filepath in files:
        stats = ingest_team_file(filepath, args.season, dry_run=args.dry_run)
        all_stats.append(stats)

    # Summary
    total_swimmers = sum(s.get("swimmers_created", 0) for s in all_stats)
    total_bests = sum(s.get("bests_created", 0) for s in all_stats)
    logger.info(
        "\nIngestion complete: %d teams, %d new swimmers, %d best times",
        len(all_stats),
        total_swimmers,
        total_bests,
    )


if __name__ == "__main__":
    main()
