#!/usr/bin/env python3
"""
Refresh Opponent Data Pipeline

One-command pipeline to:
1. Scrape all configured teams from SwimCloud (optional, if --scrape)
2. Ingest scraped JSON files into the database
3. Print summary of scouted teams

Usage:
    python scripts/refresh_opponent_data.py                    # Ingest only
    python scripts/refresh_opponent_data.py --scrape           # Scrape + ingest
    python scripts/refresh_opponent_data.py --season 2025-2026 # Specify season
    python scripts/refresh_opponent_data.py --list             # List scouted teams
"""

import argparse
import logging
import subprocess
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def run_scraper():
    """Run the auto_scraper to refresh scraped data files."""
    scraper_path = project_root / "swim_ai_reflex" / "scrapers" / "auto_scraper.py"
    if not scraper_path.exists():
        logger.error("Scraper not found: %s", scraper_path)
        return False

    logger.info("Running SwimCloud scraper...")
    result = subprocess.run(
        [sys.executable, str(scraper_path)],
        cwd=str(project_root),
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        logger.error("Scraper failed:\n%s", result.stderr)
        return False

    logger.info("Scraper output:\n%s", result.stdout)
    return True


def run_ingestion(season: str):
    """Run the ingestion script to load scraped data into DB."""
    ingest_path = project_root / "scripts" / "ingest_scraped_data.py"

    logger.info("Ingesting scraped data for season %s...", season)
    result = subprocess.run(
        [sys.executable, str(ingest_path), "--season", season],
        cwd=str(project_root),
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        logger.error("Ingestion failed:\n%s", result.stderr)
        return False

    logger.info(result.stdout)
    return True


def list_scouted_teams(season: str):
    """List all teams with scouting data in the DB."""
    from swim_ai_reflex.backend.persistence.database import init_db
    from swim_ai_reflex.backend.services.scouting_service import (
        list_scouted_teams as _list,
    )

    init_db()
    teams = _list(season_name=season)

    if not teams:
        logger.info("No scouted teams found for season %s", season)
        return

    logger.info("\nScouted Teams (%s):", season)
    logger.info("-" * 50)
    for t in teams:
        marker = " *" if t["is_user_team"] else ""
        logger.info(
            "  %-4s %-35s %d swimmers%s",
            t["short_name"] or "—",
            t["name"],
            t["swimmer_count"],
            marker,
        )
    logger.info("-" * 50)
    logger.info("Total: %d teams (* = user team)", len(teams))


def main():
    parser = argparse.ArgumentParser(description="Refresh opponent scouting data")
    parser.add_argument("--scrape", action="store_true", help="Run scraper first")
    parser.add_argument("--season", default="2025-2026", help="Season name")
    parser.add_argument("--list", action="store_true", help="List scouted teams only")
    parser.add_argument(
        "--ingest-only", action="store_true", help="Skip scraping, just ingest"
    )
    args = parser.parse_args()

    if args.list:
        list_scouted_teams(args.season)
        return

    if args.scrape:
        if not run_scraper():
            logger.error("Scraping failed. Aborting.")
            sys.exit(1)

    if not run_ingestion(args.season):
        logger.error("Ingestion failed.")
        sys.exit(1)

    # Show results
    list_scouted_teams(args.season)
    logger.info("\nRefresh complete.")


if __name__ == "__main__":
    main()
