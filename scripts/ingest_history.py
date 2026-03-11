#!/usr/bin/env python3
"""
HyTek MDB → Supabase ETL Pipeline

Reads HyTek Meet Manager .mdb exports and ingests historical meet data
into the production Supabase PostgreSQL database (via the persistence layer).

Maps MDB tables to the new schema:
  TEAM    → teams
  ATHLETE → swimmers + swimmer_team_seasons
  MEET    → meets + meet_teams + seasons
  RESULT  → events + entries

Usage:
    python scripts/ingest_history.py                     # Ingest 2024-2026 seasons
    python scripts/ingest_history.py --all                # Ingest all meets
    python scripts/ingest_history.py --meet-id 512       # Ingest single meet
    python scripts/ingest_history.py --dry-run            # Show what would be ingested
"""

import argparse
import logging
import os
import sys
from datetime import date, datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd  # noqa: E402
from sqlmodel import select  # noqa: E402

from swim_ai_reflex.backend.persistence.database import (  # noqa: E402
    get_session,
    init_db,
)
from swim_ai_reflex.backend.persistence.db_models import (  # noqa: E402
    Entry,
    Event,
    Meet,
    MeetTeam,
    Season,
    Swimmer,
    SwimmerTeamSeason,
    Team,
)
from swim_ai_reflex.backend.utils.mdb_connector import MDBConnector  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

DB_PATH = "data/real_exports/SSTdata.mdb"

# Stroke mapping for event name construction
STROKE_MAP = {1: "Free", 2: "Back", 3: "Breast", 4: "Fly", 5: "IM"}

# Standard HS event ordering (for event_number)
STANDARD_EVENT_ORDER = [
    "200 Medley Relay",
    "200 Free",
    "200 IM",
    "50 Free",
    "Diving",
    "100 Fly",
    "100 Free",
    "500 Free",
    "200 Free Relay",
    "100 Back",
    "100 Breast",
    "400 Free Relay",
]

# Date range for default ingestion
START_DATE = datetime(2023, 9, 1)
END_DATE = datetime(2026, 12, 31)


def determine_season(meet_date: date) -> str:
    """Determine season name from meet date (swim season is Sept-Feb)."""
    if meet_date.month >= 9:
        return f"{meet_date.year}-{meet_date.year + 1}"
    else:
        return f"{meet_date.year - 1}-{meet_date.year}"


def determine_meet_type(name: str) -> str:
    """Classify meet type from name."""
    lower = name.lower()
    if "visaa" in lower or "state" in lower:
        return "championship"
    if "vcac" in lower or "catholic" in lower:
        return "conference"
    if "invitational" in lower or "invite" in lower:
        return "invitational"
    if "time trial" in lower or "tt " in lower:
        return "time_trial"
    return "dual"


def construct_event_name(dist: int, stroke: int, is_relay: bool) -> str:
    """Construct standardized event name (without gender prefix)."""
    stroke_name = STROKE_MAP.get(stroke, "Free")

    if is_relay:
        if dist == 200 and stroke == 1:
            return "200 Free Relay"
        if dist == 400 and stroke == 1:
            return "400 Free Relay"
        if dist == 200 and stroke in (2, 5):
            return "200 Medley Relay"
        return f"{dist} Relay"

    return f"{dist} {stroke_name}"


def get_event_number(event_name: str) -> int | None:
    """Map event name to standard HS event number."""
    for i, name in enumerate(STANDARD_EVENT_ORDER, 1):
        if name in event_name:
            return i
    return None


class SupabaseIngestor:
    """Ingests HyTek MDB data into the Supabase persistence layer."""

    def __init__(self, mdb_path: str):
        if not os.path.exists(mdb_path):
            raise FileNotFoundError(f"MDB file not found: {mdb_path}")
        self.connector = MDBConnector(mdb_path)
        self._team_cache: dict[str, int] = {}  # name -> team_id
        self._swimmer_cache: dict[str, int] = {}  # "first last" -> swimmer_id
        self._season_cache: dict[str, int] = {}  # season_name -> season_id

        # Pre-load MDB tables (read once)
        logger.info("Loading MDB tables...")
        self.meet_df = self.connector.read_table("MEET")
        self.result_df = self.connector.read_table("RESULT")
        self.team_df = self.connector.read_table("TEAM")
        self.athlete_df = self.connector.read_table("ATHLETE")
        logger.info(
            "  %d meets, %d results, %d teams, %d athletes",
            len(self.meet_df),
            len(self.result_df),
            len(self.team_df),
            len(self.athlete_df),
        )

        # Build lookup maps (HyTek uses uppercase column names)
        self.team_name_map = dict(zip(self.team_df["TEAM"], self.team_df["TNAME"]))
        self.team_code_map = {}
        if "TCODE" in self.team_df.columns:
            self.team_code_map = dict(zip(self.team_df["TEAM"], self.team_df["TCODE"]))

        self.athlete_first = dict(
            zip(self.athlete_df["ATHLETE"], self.athlete_df["FIRST"])
        )
        self.athlete_last = dict(
            zip(self.athlete_df["ATHLETE"], self.athlete_df["LAST"])
        )
        self.athlete_sex = dict(zip(self.athlete_df["ATHLETE"], self.athlete_df["SEX"]))
        self.athlete_team = dict(
            zip(self.athlete_df["ATHLETE"], self.athlete_df["TEAM1"])
        )

    def _get_or_create_season(self, session, season_name: str) -> int:
        if season_name in self._season_cache:
            return self._season_cache[season_name]

        season = session.exec(select(Season).where(Season.name == season_name)).first()
        if not season:
            season = Season(name=season_name)
            session.add(season)
            session.flush()

        self._season_cache[season_name] = season.id
        return season.id

    def _get_or_create_team(self, session, name: str, code: str | None = None) -> int:
        cache_key = name.lower()
        if cache_key in self._team_cache:
            return self._team_cache[cache_key]

        team = session.exec(select(Team).where(Team.name == name)).first()
        if not team:
            # Check by short_name
            if code:
                team = session.exec(select(Team).where(Team.short_name == code)).first()

        if not team:
            is_seton = "seton" in name.lower()
            team = Team(
                name=name,
                short_name=code,
                state="VA",
                is_user_team=is_seton,
            )
            session.add(team)
            session.flush()

        self._team_cache[cache_key] = team.id
        return team.id

    def _get_or_create_swimmer(
        self, session, first: str, last: str, gender: str | None = None
    ) -> int:
        cache_key = f"{first.lower()} {last.lower()}"
        if cache_key in self._swimmer_cache:
            return self._swimmer_cache[cache_key]

        stmt = select(Swimmer).where(
            Swimmer.first_name == first, Swimmer.last_name == last
        )
        if gender:
            stmt = stmt.where(Swimmer.gender == gender)
        swimmer = session.exec(stmt).first()

        if not swimmer:
            swimmer = Swimmer(first_name=first, last_name=last, gender=gender)
            session.add(swimmer)
            session.flush()

        self._swimmer_cache[cache_key] = swimmer.id
        return swimmer.id

    def _ensure_swimmer_team_season(
        self, session, swimmer_id: int, team_id: int, season_id: int
    ):
        existing = session.exec(
            select(SwimmerTeamSeason).where(
                SwimmerTeamSeason.swimmer_id == swimmer_id,
                SwimmerTeamSeason.team_id == team_id,
                SwimmerTeamSeason.season_id == season_id,
            )
        ).first()
        if not existing:
            sts = SwimmerTeamSeason(
                swimmer_id=swimmer_id, team_id=team_id, season_id=season_id
            )
            session.add(sts)

    def get_filtered_meets(
        self,
        start: datetime | None = None,
        end: datetime | None = None,
        meet_id: int | None = None,
    ) -> list[tuple[int, str, date]]:
        """Get list of (mdb_meet_id, meet_name, meet_date) to ingest."""
        meets_with_results = set(self.result_df["MEET"].unique())
        filtered = []

        for _, row in self.meet_df.iterrows():
            mid = row["MEET"]
            if meet_id is not None and mid != meet_id:
                continue
            if mid not in meets_with_results:
                continue

            # Parse date
            meet_date = None
            if "START" in self.meet_df.columns:
                try:
                    dt = pd.to_datetime(row["START"])
                    if not pd.isna(dt):
                        meet_date = dt.date()
                except (ValueError, TypeError):
                    pass

            if meet_date is None:
                meet_date = date.today()

            # Date filter
            if start and datetime.combine(meet_date, datetime.min.time()) < start:
                continue
            if end and datetime.combine(meet_date, datetime.min.time()) > end:
                continue

            name = row.get("MNAME", f"Meet_{mid}")
            if not name or str(name).lower() == "nan":
                name = f"Meet_{mid}"
            name = str(name).strip()

            filtered.append((mid, name, meet_date))

        return sorted(filtered, key=lambda x: x[2])

    def ingest_meet(self, mdb_meet_id: int, meet_name: str, meet_date: date) -> bool:
        """Ingest a single meet into the Supabase persistence layer."""
        with get_session() as session:
            # Check if already ingested
            existing = session.exec(
                select(Meet).where(Meet.name == meet_name, Meet.meet_date == meet_date)
            ).first()
            if existing:
                logger.debug("  Skipping (already exists): %s", meet_name)
                return False

            # Determine season and meet type
            season_name = determine_season(meet_date)
            season_id = self._get_or_create_season(session, season_name)
            meet_type = determine_meet_type(meet_name)

            # Extract location from MDB
            meet_row = self.meet_df[self.meet_df["MEET"] == mdb_meet_id]
            location = None
            if "Location" in meet_row.columns and not meet_row["Location"].isna().all():
                loc = str(meet_row["Location"].iloc[0])
                if loc.lower() != "nan":
                    location = loc

            # Create Meet
            meet = Meet(
                name=meet_name,
                meet_date=meet_date,
                season_id=season_id,
                location=location,
                meet_type=meet_type,
                hytek_db_path=DB_PATH,
                pool_course="25Y",
            )
            session.add(meet)
            session.flush()

            # Get results for this meet
            meet_results = self.result_df[self.result_df["MEET"] == mdb_meet_id]
            if meet_results.empty:
                session.commit()
                return True

            # Track teams in this meet and event creation
            teams_in_meet: set[int] = set()
            event_cache: dict[str, int] = {}  # "M_200 Free" -> event_id
            entry_count = 0

            for _, row in meet_results.iterrows():
                athlete_id = row.get("ATHLETE")

                # Resolve team
                t_id = row.get("TEAM")
                if pd.isna(t_id) or t_id is None:
                    t_id = self.athlete_team.get(athlete_id)
                t_name = self.team_name_map.get(t_id, f"Team_{t_id}")
                t_code = self.team_code_map.get(t_id, "")
                if pd.isna(t_name):
                    t_name = f"Team_{t_id}"
                if pd.isna(t_code):
                    t_code = None
                team_id = self._get_or_create_team(session, str(t_name), t_code)
                teams_in_meet.add(team_id)

                # Resolve swimmer
                first = self.athlete_first.get(athlete_id, "")
                last = self.athlete_last.get(athlete_id, "")
                if pd.isna(first):
                    first = ""
                if pd.isna(last):
                    last = ""
                first, last = str(first).strip(), str(last).strip()
                if not first and not last:
                    continue

                gender = self.athlete_sex.get(athlete_id, "M")
                if pd.isna(gender):
                    gender = "M"
                gender = str(gender).strip()

                swimmer_id = self._get_or_create_swimmer(session, first, last, gender)
                self._ensure_swimmer_team_season(
                    session, swimmer_id, team_id, season_id
                )

                # Resolve event
                dist = int(row.get("DISTANCE", 0) or 0)
                stroke_num = row.get("STROKE", 1)
                if pd.isna(stroke_num):
                    stroke_num = 1
                stroke_num = int(stroke_num)
                is_relay = str(row.get("I_R", "I")).strip() == "R"
                event_name = construct_event_name(dist, stroke_num, is_relay)
                stroke_name = STROKE_MAP.get(stroke_num, "Free")

                event_key = f"{gender}_{event_name}"
                if event_key not in event_cache:
                    event = Event(
                        meet_id=meet.id,
                        event_name=event_name,
                        event_distance=dist,
                        event_stroke=stroke_name
                        if not is_relay
                        else "Medley"
                        if stroke_num in (2, 5)
                        else "Free",
                        gender=gender,
                        is_relay=is_relay,
                        event_number=get_event_number(event_name),
                        event_category="standard",
                    )
                    session.add(event)
                    session.flush()
                    event_cache[event_key] = event.id

                event_id = event_cache[event_key]

                # Parse time
                time_val = pd.to_numeric(row.get("SCORE"), errors="coerce")
                if pd.isna(time_val):
                    time_val = None
                elif time_val > 1000:
                    time_val = time_val / 100.0

                # Parse place and points
                place = row.get("PLACE")
                if pd.notna(place):
                    place = int(place)
                else:
                    place = None

                points = float(row.get("POINTS", 0) or 0)
                points = points / 10.0 if points > 50 else points

                # Skip relay entries for individual Entry table
                if is_relay:
                    continue

                # Create Entry
                entry = Entry(
                    event_id=event_id,
                    swimmer_id=swimmer_id,
                    team_id=team_id,
                    finals_time=time_val,
                    seed_time=time_val,
                    place=place,
                    points=points,
                )
                session.add(entry)
                entry_count += 1

            # Create MeetTeam records
            for tid in teams_in_meet:
                existing_mt = session.exec(
                    select(MeetTeam).where(
                        MeetTeam.meet_id == meet.id, MeetTeam.team_id == tid
                    )
                ).first()
                if not existing_mt:
                    session.add(MeetTeam(meet_id=meet.id, team_id=tid))

            session.commit()
            logger.info(
                "  Ingested: %s (%s) — %d entries, %d teams",
                meet_name,
                meet_date,
                entry_count,
                len(teams_in_meet),
            )
            return True


def main():
    parser = argparse.ArgumentParser(description="Ingest HyTek MDB data into Supabase")
    parser.add_argument("--mdb", default=DB_PATH, help="Path to .mdb file")
    parser.add_argument(
        "--all", action="store_true", help="Ingest all meets (no date filter)"
    )
    parser.add_argument("--meet-id", type=int, help="Ingest single meet by MDB ID")
    parser.add_argument(
        "--dry-run", action="store_true", help="Show meets without ingesting"
    )
    parser.add_argument("--start", help="Start date YYYY-MM-DD")
    parser.add_argument("--end", help="End date YYYY-MM-DD")
    args = parser.parse_args()

    init_db()

    ingestor = SupabaseIngestor(args.mdb)

    # Date range
    start = None if args.all else START_DATE
    end = None if args.all else END_DATE
    if args.start:
        start = datetime.strptime(args.start, "%Y-%m-%d")
    if args.end:
        end = datetime.strptime(args.end, "%Y-%m-%d")

    meets = ingestor.get_filtered_meets(start=start, end=end, meet_id=args.meet_id)
    logger.info("Found %d meets to process", len(meets))

    if args.dry_run:
        for mid, name, mdate in meets:
            logger.info(
                "  [%d] %s (%s) — %s", mid, name, mdate, determine_meet_type(name)
            )
        logger.info("Dry run complete. %d meets would be ingested.", len(meets))
        return

    success = 0
    for i, (mid, name, mdate) in enumerate(meets):
        try:
            if ingestor.ingest_meet(mid, name, mdate):
                success += 1
        except Exception as e:
            logger.error("Error ingesting meet %d (%s): %s", mid, name, e)

        if (i + 1) % 20 == 0:
            logger.info("  Progress: %d/%d...", i + 1, len(meets))

    logger.info(
        "\nIngestion complete: %d/%d meets processed successfully",
        success,
        len(meets),
    )


if __name__ == "__main__":
    main()
