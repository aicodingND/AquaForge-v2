"""
MDB Data Ingestion Module

Dedicated module for ingesting historical meet data from MDB files
into the centralized AquaForge SQLite database.
"""

import os
from datetime import datetime

import pandas as pd
from sqlmodel import Session, select

from swim_ai_reflex.backend.database.engine import create_db_and_tables, engine
from swim_ai_reflex.backend.database.models import EventEntry, Meet, Swimmer, Team
from swim_ai_reflex.backend.utils.mdb_connector import MDBConnector

# Stroke mapping for event name construction
STROKE_MAP = {1: "Free", 2: "Back", 3: "Breast", 4: "Fly", 5: "IM"}


class MDBIngestor:
    """Handles ingestion of MDB data into the centralized database."""

    def __init__(self, mdb_path: str):
        """Initialize with path to MDB file."""
        if not os.path.exists(mdb_path):
            raise FileNotFoundError(f"MDB file not found: {mdb_path}")
        self.connector = MDBConnector(mdb_path)
        self._team_cache: dict[str, Team] = {}
        self._swimmer_cache: dict[str, Swimmer] = {}

    def _get_or_create_team(
        self, session: Session, name: str, code: str | None = None
    ) -> Team:
        """Get existing team or create new one."""
        cache_key = name.lower()
        if cache_key in self._team_cache:
            return self._team_cache[cache_key]

        statement = select(Team).where(Team.name == name)
        team = session.exec(statement).first()
        if not team:
            team = Team(name=name, code=code)
            session.add(team)
            session.commit()
            session.refresh(team)
        self._team_cache[cache_key] = team
        return team

    def _get_or_create_swimmer(
        self,
        session: Session,
        name: str,
        team_id: int,
        gender: str | None = None,
    ) -> Swimmer:
        """Get existing swimmer or create new one."""
        cache_key = f"{name.lower()}_{team_id}"
        if cache_key in self._swimmer_cache:
            return self._swimmer_cache[cache_key]

        statement = (
            select(Swimmer)
            .where(Swimmer.name == name)
            .where(Swimmer.team_id == team_id)
        )
        swimmer = session.exec(statement).first()
        if not swimmer:
            swimmer = Swimmer(name=name, team_id=team_id, gender=gender)
            session.add(swimmer)
            session.commit()
            session.refresh(swimmer)
        self._swimmer_cache[cache_key] = swimmer
        return swimmer

    def _construct_event_name(
        self, dist: int, stroke: int, gender: str, is_relay: bool
    ) -> str:
        """Construct standardized event name."""
        stroke_name = STROKE_MAP.get(stroke, "Free")
        prefix = f"{gender}s"

        if is_relay:
            if dist == 200 and stroke == 1:
                return f"{prefix} 200 Free Relay"
            elif dist == 400 and stroke == 1:
                return f"{prefix} 400 Free Relay"
            elif dist == 200 and stroke in (2, 5):
                return f"{prefix} 200 Medley Relay"
            else:
                return f"{prefix} {dist} Relay"
        else:
            return f"{prefix} {dist} {stroke_name}"

    def ingest_meet(
        self, session: Session, meet_id: int, meet_name: str, profile: str
    ) -> bool:
        """
        Ingest a single meet's data into the database.

        Returns True if successful, False if skipped/failed.
        """
        print(f"Ingesting meet {meet_id}: {meet_name}")

        # Check if meet exists
        statement = select(Meet).where(Meet.name == meet_name)
        existing = session.exec(statement).first()
        if existing:
            print("  - Meet already exists, skipping")
            return False

        # Load MDB tables
        result_df = self.connector.read_table("RESULT")
        meet_df = self.connector.read_table("MEET")
        team_df = self.connector.read_table("TEAM")
        athlete_df = self.connector.read_table("ATHLETE")

        # Find meet row
        meet_row = meet_df[meet_df["MEET"] == meet_id]
        if meet_row.empty:
            print("  - Meet not found in MDB")
            return False

        # Extract date and location safely
        start_date = datetime.now()
        if "Start" in meet_row.columns and not meet_row["Start"].isna().all():
            start_date = pd.to_datetime(meet_row["Start"].iloc[0]).to_pydatetime()

        location = None
        if "Location" in meet_row.columns and not meet_row["Location"].isna().all():
            location = str(meet_row["Location"].iloc[0])

        # Create Meet
        meet = Meet(
            name=meet_name,
            date=start_date,
            location=location,
            profile_type=profile,
        )
        session.add(meet)
        session.commit()
        session.refresh(meet)

        # Build team maps
        team_map = dict(zip(team_df["TEAM"], team_df["TNAME"]))
        team_code_map = {}
        if "TCode" in team_df.columns:
            team_code_map = dict(zip(team_df["TEAM"], team_df["TCode"]))

        # Build athlete lookup maps (ATHLETE ID -> first, last, sex)
        athlete_first = dict(zip(athlete_df["ATHLETE"], athlete_df["FIRST"]))
        athlete_last = dict(zip(athlete_df["ATHLETE"], athlete_df["LAST"]))
        athlete_sex = dict(zip(athlete_df["ATHLETE"], athlete_df["SEX"]))
        athlete_team = dict(zip(athlete_df["ATHLETE"], athlete_df["TEAM1"]))

        # Process results
        meet_results = result_df[result_df["MEET"] == meet_id]
        count = 0

        for _, row in meet_results.iterrows():
            # Get athlete ID and lookup info
            athlete_id = row.get("ATHLETE")

            # Get team - try from result row first, then athlete table
            t_id = row.get("TEAM")
            if pd.isna(t_id) or t_id is None:
                t_id = athlete_team.get(athlete_id)
            t_name = team_map.get(t_id, f"Team_{t_id}")
            t_code = team_code_map.get(t_id, "")
            team = self._get_or_create_team(session, t_name, t_code)

            # Get swimmer name from athlete table
            first = athlete_first.get(athlete_id, "")
            last = athlete_last.get(athlete_id, "")
            if pd.isna(first):
                first = ""
            if pd.isna(last):
                last = ""

            s_name = f"{first} {last}".strip()
            if not s_name or s_name.lower() == "nan nan":
                continue

            gender = athlete_sex.get(athlete_id, "M")
            if pd.isna(gender):
                gender = "M"
            swimmer = self._get_or_create_swimmer(session, s_name, team.id, gender)

            # Construct event name
            dist = int(row.get("DISTANCE", 0))
            stroke = row.get("STROKE", 1)
            is_relay = row.get("I_R") == "R"
            event_name = self._construct_event_name(dist, stroke, gender, is_relay)

            # Parse time
            time_val = pd.to_numeric(row.get("SCORE"), errors="coerce")
            if pd.isna(time_val):
                time_val = 0
            if time_val > 1000:
                time_val = time_val / 100.0

            points = float(row.get("POINTS", 0)) / 10.0

            # Create entry
            entry = EventEntry(
                event_name=event_name,
                seed_time=time_val,
                actual_time=time_val,
                points=points,
                meet_id=meet.id,
                swimmer_id=swimmer.id,
            )
            session.add(entry)
            count += 1

        session.commit()
        print(f"  - Ingested {count} entries")
        return True


def run_full_ingestion(mdb_path: str, meets: list[tuple[int, str, str]]):
    """Run full ingestion for a list of meets."""
    print("Initializing Database...")
    create_db_and_tables()

    print(f"Connecting to MDB: {mdb_path}")
    ingestor = MDBIngestor(mdb_path)

    with Session(engine) as session:
        success = 0
        for meet_id, meet_name, profile in meets:
            try:
                if ingestor.ingest_meet(session, meet_id, meet_name, profile):
                    success += 1
            except Exception as e:
                print(f"Error ingesting meet {meet_id}: {e}")

    print(f"\nIngestion complete: {success}/{len(meets)} meets processed")
