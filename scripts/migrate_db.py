#!/usr/bin/env python3
"""
migrate_db.py - Migrate AquaForge Mac 5-table SQLite DB to the Windows 16-table schema.

Reads the legacy Mac database (team, meet, swimmer, evententry, backtestresult)
and writes into a new database with the normalized Windows schema (16 tables).

Usage:
    python scripts/migrate_db.py                         # Full migration
    python scripts/migrate_db.py --dry-run                # Preview only
    python scripts/migrate_db.py --source data/other.db   # Custom source
    python scripts/migrate_db.py --output data/output.db  # Custom output

Safety:
    - Creates a timestamped backup of the source DB before anything else
    - Never modifies the source database
    - The output is a brand-new file (will not overwrite without --force)
"""

from __future__ import annotations

import argparse
import hashlib
import logging
import re
import shutil
import sqlite3
import sys
from dataclasses import dataclass, field
from datetime import UTC, datetime
from datetime import date as date_type
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("migrate_db")

# ---------------------------------------------------------------------------
# Paths (defaults)
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SOURCE = PROJECT_ROOT / "data" / "aquaforge.db"
DEFAULT_OUTPUT = PROJECT_ROOT / "data" / "aquaforge_v2.db"
BACKUP_DIR = PROJECT_ROOT / "data" / "backups"

# ---------------------------------------------------------------------------
# Windows 16-table DDL (matches db_models.py exactly)
# ---------------------------------------------------------------------------
WINDOWS_SCHEMA_DDL = """
-- ==========================================================================
-- Organizations
-- ==========================================================================
CREATE TABLE teams (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT    NOT NULL,
    short_name  TEXT,
    aliases_json TEXT,
    conference  TEXT,
    division    TEXT,
    state       TEXT    NOT NULL DEFAULT 'VA',
    is_user_team INTEGER NOT NULL DEFAULT 0,
    created_at  TEXT    NOT NULL,
    updated_at  TEXT    NOT NULL
);
CREATE UNIQUE INDEX ix_teams_name ON teams (name);

CREATE TABLE seasons (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    name       TEXT    NOT NULL UNIQUE,
    start_date TEXT,
    end_date   TEXT
);
CREATE INDEX ix_seasons_name ON seasons (name);

-- ==========================================================================
-- People
-- ==========================================================================
CREATE TABLE swimmers (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    first_name     TEXT NOT NULL,
    last_name      TEXT NOT NULL,
    middle_initial TEXT,
    gender         TEXT,
    birth_year     INTEGER,
    usa_swimming_id TEXT,
    created_at     TEXT NOT NULL,
    updated_at     TEXT NOT NULL
);
CREATE INDEX ix_swimmers_first_name ON swimmers (first_name);
CREATE INDEX ix_swimmers_last_name  ON swimmers (last_name);

CREATE TABLE swimmer_aliases (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    swimmer_id INTEGER NOT NULL REFERENCES swimmers(id),
    alias_name TEXT    NOT NULL UNIQUE,
    source     TEXT
);
CREATE INDEX ix_swimmer_aliases_swimmer_id ON swimmer_aliases (swimmer_id);
CREATE UNIQUE INDEX ix_swimmer_aliases_alias_name ON swimmer_aliases (alias_name);

CREATE TABLE swimmer_team_seasons (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    swimmer_id INTEGER NOT NULL REFERENCES swimmers(id),
    team_id    INTEGER NOT NULL REFERENCES teams(id),
    season_id  INTEGER NOT NULL REFERENCES seasons(id),
    grade      INTEGER,
    is_active  INTEGER NOT NULL DEFAULT 1
);
CREATE INDEX ix_sts_swimmer_id ON swimmer_team_seasons (swimmer_id);
CREATE INDEX ix_sts_team_id    ON swimmer_team_seasons (team_id);

-- ==========================================================================
-- Competitions
-- ==========================================================================
CREATE TABLE meets (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    name             TEXT    NOT NULL,
    meet_date        TEXT    NOT NULL,
    meet_end_date    TEXT,
    season_id        INTEGER REFERENCES seasons(id),
    location         TEXT,
    city             TEXT,
    state            TEXT,
    pool_course      TEXT    NOT NULL DEFAULT '25Y',
    num_lanes        INTEGER,
    meet_type        TEXT    NOT NULL DEFAULT 'dual',
    ind_max_scorers  INTEGER,
    relay_max_scorers INTEGER,
    hytek_db_path    TEXT,
    source_file      TEXT,
    notes            TEXT,
    created_at       TEXT    NOT NULL
);
CREATE INDEX ix_meets_name      ON meets (name);
CREATE INDEX ix_meets_meet_date ON meets (meet_date);

CREATE TABLE meet_teams (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    meet_id     INTEGER NOT NULL REFERENCES meets(id),
    team_id     INTEGER NOT NULL REFERENCES teams(id),
    final_score REAL,
    is_home     INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX ix_meet_teams_meet_id ON meet_teams (meet_id);

CREATE TABLE events (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    meet_id         INTEGER NOT NULL REFERENCES meets(id),
    event_number    INTEGER,
    event_name      TEXT    NOT NULL,
    event_distance  INTEGER,
    event_stroke    TEXT,
    gender          TEXT,
    is_relay        INTEGER NOT NULL DEFAULT 0,
    is_diving       INTEGER NOT NULL DEFAULT 0,
    event_category  TEXT
);
CREATE INDEX ix_events_meet_id    ON events (meet_id);
CREATE INDEX ix_events_event_name ON events (event_name);

-- ==========================================================================
-- Performance
-- ==========================================================================
CREATE TABLE entries (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id      INTEGER NOT NULL REFERENCES events(id),
    swimmer_id    INTEGER NOT NULL REFERENCES swimmers(id),
    team_id       INTEGER REFERENCES teams(id),
    seed_time     REAL,
    finals_time   REAL,
    heat          INTEGER,
    lane          INTEGER,
    place         INTEGER,
    points        REAL    NOT NULL DEFAULT 0.0,
    is_exhibition INTEGER NOT NULL DEFAULT 0,
    is_dq         INTEGER NOT NULL DEFAULT 0,
    is_dns        INTEGER NOT NULL DEFAULT 0,
    dq_code       TEXT,
    course        TEXT,
    created_at    TEXT    NOT NULL
);
CREATE INDEX ix_entries_event_id   ON entries (event_id);
CREATE INDEX ix_entries_swimmer_id ON entries (swimmer_id);

CREATE TABLE relay_entries (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id      INTEGER NOT NULL REFERENCES events(id),
    team_id       INTEGER NOT NULL REFERENCES teams(id),
    relay_letter  TEXT    NOT NULL DEFAULT 'A',
    seed_time     REAL,
    finals_time   REAL,
    heat          INTEGER,
    lane          INTEGER,
    place         INTEGER,
    points        REAL    NOT NULL DEFAULT 0.0,
    is_exhibition INTEGER NOT NULL DEFAULT 0,
    is_dq         INTEGER NOT NULL DEFAULT 0,
    created_at    TEXT    NOT NULL
);
CREATE INDEX ix_relay_entries_event_id ON relay_entries (event_id);

CREATE TABLE relay_legs (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    relay_entry_id INTEGER NOT NULL REFERENCES relay_entries(id),
    swimmer_id     INTEGER NOT NULL REFERENCES swimmers(id),
    leg_order      INTEGER NOT NULL,
    split_time     REAL
);
CREATE INDEX ix_relay_legs_relay_entry_id ON relay_legs (relay_entry_id);

CREATE TABLE splits (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id       INTEGER NOT NULL REFERENCES events(id),
    swimmer_id     INTEGER REFERENCES swimmers(id),
    relay_entry_id INTEGER REFERENCES relay_entries(id),
    split_number   INTEGER NOT NULL,
    split_time     REAL    NOT NULL,
    round_code     TEXT    NOT NULL DEFAULT 'F'
);
CREATE INDEX ix_splits_event_id ON splits (event_id);

CREATE TABLE dual_meet_pairings (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    meet_id   INTEGER NOT NULL REFERENCES meets(id),
    team_a_id INTEGER NOT NULL REFERENCES teams(id),
    team_b_id INTEGER NOT NULL REFERENCES teams(id),
    gender    TEXT
);
CREATE INDEX ix_dmp_meet_id ON dual_meet_pairings (meet_id);

-- ==========================================================================
-- Analytics
-- ==========================================================================
CREATE TABLE swimmer_bests (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    swimmer_id      INTEGER NOT NULL REFERENCES swimmers(id),
    event_name      TEXT    NOT NULL,
    season_id       INTEGER REFERENCES seasons(id),
    best_time       REAL    NOT NULL,
    mean_time       REAL,
    std_dev         REAL,
    recent_time     REAL,
    sample_size     INTEGER NOT NULL DEFAULT 1,
    improvement_pct REAL,
    updated_at      TEXT    NOT NULL
);
CREATE INDEX ix_swimmer_bests_swimmer_id  ON swimmer_bests (swimmer_id);
CREATE INDEX ix_swimmer_bests_event_name  ON swimmer_bests (event_name);

CREATE TABLE qualifying_times (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    event_name    TEXT NOT NULL,
    gender        TEXT NOT NULL,
    time_standard REAL NOT NULL,
    level         TEXT NOT NULL,
    season        TEXT NOT NULL
);

-- ==========================================================================
-- ETL
-- ==========================================================================
CREATE TABLE import_logs (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    source_path      TEXT NOT NULL,
    source_type      TEXT,
    import_date      TEXT NOT NULL,
    records_imported INTEGER NOT NULL DEFAULT 0,
    records_skipped  INTEGER NOT NULL DEFAULT 0,
    errors_json      TEXT,
    status           TEXT NOT NULL DEFAULT 'pending',
    checksum         TEXT
);
CREATE INDEX ix_import_logs_source_path ON import_logs (source_path);
CREATE INDEX ix_import_logs_checksum    ON import_logs (checksum);

-- ==========================================================================
-- Optimization History
-- ==========================================================================
CREATE TABLE optimization_runs (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    meet_id        INTEGER REFERENCES meets(id),
    run_date       TEXT    NOT NULL,
    optimizer_type TEXT    NOT NULL DEFAULT 'gurobi',
    home_score     REAL    NOT NULL DEFAULT 0.0,
    away_score     REAL    NOT NULL DEFAULT 0.0,
    lineup_json    TEXT,
    config_json    TEXT,
    notes          TEXT
);
"""


# ---------------------------------------------------------------------------
# Event-name parsing helpers
# ---------------------------------------------------------------------------

# Mac DB event names look like "Ms 200 IM", "Fs 50 Free", "Ms 200 Free Relay"
_EVENT_RE = re.compile(
    r"^(?P<gender>[MF])s\s+"
    r"(?P<distance>\d+)\s+"
    r"(?P<stroke>.+)$",
    re.IGNORECASE,
)

_RELAY_KEYWORDS = {"relay"}
_DIVING_KEYWORDS = {"diving", "1 mtr diving", "1 m diving"}

STROKE_NORMALIZE: dict[str, str] = {
    "free": "Free",
    "back": "Back",
    "breast": "Breast",
    "fly": "Fly",
    "im": "IM",
    "medley relay": "Medley",
    "free relay": "Free",
}


def parse_event_name(raw: str) -> dict[str, Any]:
    """Parse a Mac-format event name into structured fields.

    Returns dict with keys:
        gender, distance, stroke, normalized_name, is_relay, is_diving
    """
    result: dict[str, Any] = {
        "gender": None,
        "distance": None,
        "stroke": None,
        "normalized_name": raw,
        "is_relay": False,
        "is_diving": False,
    }

    if raw.lower().strip() in _DIVING_KEYWORDS:
        result["is_diving"] = True
        return result

    m = _EVENT_RE.match(raw.strip())
    if not m:
        return result

    gender_code = m.group("gender").upper()
    distance = int(m.group("distance"))
    stroke_raw = m.group("stroke").strip()

    result["gender"] = gender_code  # "M" or "F"
    result["distance"] = distance

    is_relay = any(kw in stroke_raw.lower() for kw in _RELAY_KEYWORDS)
    result["is_relay"] = is_relay

    # Normalize the stroke name
    stroke_lower = stroke_raw.lower()
    result["stroke"] = STROKE_NORMALIZE.get(stroke_lower, stroke_raw.title())

    # Build a gender-free canonical name: "200 IM", "100 Free", "200 Medley Relay"
    result["normalized_name"] = f"{distance} {stroke_raw.title()}"

    return result


# ---------------------------------------------------------------------------
# Season inference
# ---------------------------------------------------------------------------


def infer_season_name(dt: datetime | date_type) -> str:
    """Infer a season name like '2025-2026' from a date.

    Swimming seasons run Aug-Jul, so a date in Jan 2026 -> '2025-2026'.
    """
    year = dt.year
    month = dt.month
    if month >= 8:
        return f"{year}-{year + 1}"
    else:
        return f"{year - 1}-{year}"


# ---------------------------------------------------------------------------
# Swimmer name splitting
# ---------------------------------------------------------------------------


def split_swimmer_name(full_name: str) -> tuple[str, str, str | None]:
    """Split 'First Last' or 'First M Last' into (first, last, middle_initial)."""
    parts = full_name.strip().split()
    if len(parts) == 0:
        return ("Unknown", "Unknown", None)
    elif len(parts) == 1:
        return (parts[0], "Unknown", None)
    elif len(parts) == 2:
        return (parts[0], parts[1], None)
    else:
        # Check if middle token is a single character (initial)
        if len(parts[1]) == 1 or (len(parts[1]) == 2 and parts[1].endswith(".")):
            middle = parts[1].rstrip(".")
            return (parts[0], " ".join(parts[2:]), middle)
        else:
            # Multi-word last name: treat first token as first name, rest as last
            return (parts[0], " ".join(parts[1:]), None)


# ---------------------------------------------------------------------------
# Migration stats tracker
# ---------------------------------------------------------------------------


@dataclass
class MigrationStats:
    teams: int = 0
    seasons: int = 0
    swimmers: int = 0
    swimmer_aliases: int = 0
    swimmer_team_seasons: int = 0
    meets: int = 0
    events: int = 0
    entries: int = 0
    optimization_runs: int = 0
    import_log: int = 0
    skipped_relay_entries: int = 0
    warnings: list[str] = field(default_factory=list)

    def summary(self) -> str:
        lines = [
            "",
            "=" * 60,
            "  Migration Summary",
            "=" * 60,
            f"  teams                -> {self.teams:>6}",
            f"  seasons              -> {self.seasons:>6}",
            f"  swimmers             -> {self.swimmers:>6}",
            f"  swimmer_aliases      -> {self.swimmer_aliases:>6}",
            f"  swimmer_team_seasons -> {self.swimmer_team_seasons:>6}",
            f"  meets                -> {self.meets:>6}",
            f"  events (distinct)    -> {self.events:>6}",
            f"  entries (individual)  -> {self.entries:>6}",
            f"  optimization_runs    -> {self.optimization_runs:>6}",
            f"  import_logs          -> {self.import_log:>6}",
            "  ---",
            f"  relay entries skipped (no swimmer data) -> {self.skipped_relay_entries}",
            f"  warnings -> {len(self.warnings)}",
        ]
        if self.warnings:
            lines.append("")
            for w in self.warnings[:20]:
                lines.append(f"    WARN: {w}")
            if len(self.warnings) > 20:
                lines.append(f"    ... and {len(self.warnings) - 20} more")
        lines.append("=" * 60)
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Core migration logic
# ---------------------------------------------------------------------------


class Migrator:
    """Reads from the legacy Mac DB and writes to a new Windows-schema DB."""

    def __init__(self, source_path: Path, output_path: Path, *, dry_run: bool = False):
        self.source_path = source_path
        self.output_path = output_path
        self.dry_run = dry_run
        self.stats = MigrationStats()
        self.now_iso = datetime.now(UTC).isoformat()

        # ID mapping tables: old_id -> new_id
        self._team_map: dict[int, int] = {}
        self._swimmer_map: dict[int, int] = {}
        self._meet_map: dict[int, int] = {}
        self._season_map: dict[str, int] = {}  # season_name -> new_id
        # (meet_id, event_name) -> new event_id
        self._event_map: dict[tuple[int, str], int] = {}

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------
    def run(self) -> MigrationStats:
        """Execute the full migration pipeline."""
        log.info("Source DB : %s", self.source_path)
        log.info("Output DB: %s", self.output_path)
        log.info("Dry run  : %s", self.dry_run)

        if not self.source_path.exists():
            log.error("Source database not found: %s", self.source_path)
            sys.exit(1)

        # Step 0: backup
        self._backup_source()

        # Open source (read-only)
        src = sqlite3.connect(f"file:{self.source_path}?mode=ro", uri=True)
        src.row_factory = sqlite3.Row

        # Create or connect to output
        if self.dry_run:
            # Use in-memory DB for dry run so nothing touches disk
            dst = sqlite3.connect(":memory:")
        else:
            if self.output_path.exists():
                log.error(
                    "Output file already exists: %s  (use --force to overwrite)",
                    self.output_path,
                )
                sys.exit(1)
            self.output_path.parent.mkdir(parents=True, exist_ok=True)
            dst = sqlite3.connect(str(self.output_path))

        dst.execute("PRAGMA journal_mode=WAL")
        dst.execute("PRAGMA foreign_keys=ON")

        try:
            # Create schema
            dst.executescript(WINDOWS_SCHEMA_DDL)
            log.info("Created 16-table schema in output DB")

            # Migrate in dependency order
            self._migrate_teams(src, dst)
            self._migrate_seasons(src, dst)
            self._migrate_swimmers(src, dst)
            self._migrate_swimmer_team_seasons(src, dst)
            self._migrate_meets(src, dst)
            self._migrate_events_and_entries(src, dst)
            self._migrate_backtest_results(src, dst)
            self._write_import_log(dst)

            if not self.dry_run:
                dst.commit()
                log.info("All changes committed to %s", self.output_path)
            else:
                log.info("Dry run complete -- no files written")

        except Exception:
            if not self.dry_run and self.output_path.exists():
                self.output_path.unlink()
                log.warning("Cleaned up partial output file")
            raise
        finally:
            src.close()
            dst.close()

        return self.stats

    # ------------------------------------------------------------------
    # Backup
    # ------------------------------------------------------------------
    def _backup_source(self) -> None:
        BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"aquaforge_backup_{ts}.db"
        backup_path = BACKUP_DIR / backup_name

        if self.dry_run:
            log.info("[DRY RUN] Would back up %s -> %s", self.source_path, backup_path)
            return

        shutil.copy2(self.source_path, backup_path)
        log.info("Backed up source DB -> %s", backup_path)

    # ------------------------------------------------------------------
    # Teams
    # ------------------------------------------------------------------
    def _migrate_teams(self, src: sqlite3.Connection, dst: sqlite3.Connection) -> None:
        rows = src.execute("SELECT id, name, code FROM team ORDER BY id").fetchall()
        log.info("Migrating %d teams ...", len(rows))

        for row in rows:
            old_id: int = row["id"]
            name: str = row["name"]
            code: str | None = row["code"]

            # Detect if this is the user's team (SST / Seton)
            is_user = name.lower().startswith("seton") or (code or "").upper() == "SST"

            cur = dst.execute(
                """INSERT INTO teams
                       (name, short_name, state, is_user_team, created_at, updated_at)
                   VALUES (?, ?, 'VA', ?, ?, ?)""",
                (name, code, int(is_user), self.now_iso, self.now_iso),
            )
            new_id = cur.lastrowid
            assert new_id is not None
            self._team_map[old_id] = new_id
            self.stats.teams += 1

    # ------------------------------------------------------------------
    # Seasons (inferred from meet dates)
    # ------------------------------------------------------------------
    def _migrate_seasons(
        self, src: sqlite3.Connection, dst: sqlite3.Connection
    ) -> None:
        rows = src.execute("SELECT date FROM meet ORDER BY date").fetchall()
        season_names: set[str] = set()

        for row in rows:
            dt = _parse_datetime(row["date"])
            season_names.add(infer_season_name(dt))

        # Always ensure at least the current season exists
        season_names.add(infer_season_name(datetime.now(UTC)))

        log.info("Creating %d season(s): %s", len(season_names), sorted(season_names))

        for sname in sorted(season_names):
            start_year = int(sname.split("-")[0])
            cur = dst.execute(
                "INSERT INTO seasons (name, start_date, end_date) VALUES (?, ?, ?)",
                (sname, f"{start_year}-08-01", f"{start_year + 1}-07-31"),
            )
            new_id = cur.lastrowid
            assert new_id is not None
            self._season_map[sname] = new_id
            self.stats.seasons += 1

    # ------------------------------------------------------------------
    # Swimmers
    # ------------------------------------------------------------------
    def _migrate_swimmers(
        self, src: sqlite3.Connection, dst: sqlite3.Connection
    ) -> None:
        rows = src.execute(
            "SELECT id, name, gender, graduation_year FROM swimmer ORDER BY id"
        ).fetchall()
        log.info("Migrating %d swimmers ...", len(rows))

        for row in rows:
            old_id: int = row["id"]
            full_name: str = row["name"]
            gender: str | None = row["gender"]

            first, last, middle = split_swimmer_name(full_name)

            # Estimate birth_year from graduation_year (graduate at ~18)
            grad_year: int | None = row["graduation_year"]
            birth_year: int | None = (grad_year - 18) if grad_year else None

            cur = dst.execute(
                """INSERT INTO swimmers
                       (first_name, last_name, middle_initial, gender,
                        birth_year, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (first, last, middle, gender, birth_year, self.now_iso, self.now_iso),
            )
            new_id = cur.lastrowid
            assert new_id is not None
            self._swimmer_map[old_id] = new_id
            self.stats.swimmers += 1

            # Store the original full name as an alias for identity resolution
            try:
                dst.execute(
                    """INSERT INTO swimmer_aliases (swimmer_id, alias_name, source)
                       VALUES (?, ?, 'mac_db_migration')""",
                    (new_id, full_name),
                )
                self.stats.swimmer_aliases += 1
            except sqlite3.IntegrityError:
                # Duplicate alias -- two swimmers with the same name
                self.stats.warnings.append(
                    f"Duplicate swimmer alias skipped: '{full_name}' (swimmer_id={new_id})"
                )

    # ------------------------------------------------------------------
    # Swimmer-Team-Season links
    # ------------------------------------------------------------------
    def _migrate_swimmer_team_seasons(
        self, src: sqlite3.Connection, dst: sqlite3.Connection
    ) -> None:
        """Create swimmer_team_seasons rows based on Mac swimmer.team_id.

        The Mac DB stores a single team_id per swimmer with no season info,
        so we link every swimmer to their team for each inferred season.
        """
        rows = src.execute(
            "SELECT id, team_id FROM swimmer WHERE team_id IS NOT NULL ORDER BY id"
        ).fetchall()

        log.info(
            "Creating swimmer_team_seasons for %d swimmers across %d season(s) ...",
            len(rows),
            len(self._season_map),
        )

        for row in rows:
            old_swimmer_id: int = row["id"]
            old_team_id: int = row["team_id"]

            new_swimmer_id = self._swimmer_map[old_swimmer_id]
            new_team_id = self._team_map.get(old_team_id)
            if new_team_id is None:
                self.stats.warnings.append(
                    f"Swimmer {old_swimmer_id} references unknown team {old_team_id}"
                )
                continue

            for _season_name, season_id in self._season_map.items():
                dst.execute(
                    """INSERT INTO swimmer_team_seasons
                           (swimmer_id, team_id, season_id, is_active)
                       VALUES (?, ?, ?, 1)""",
                    (new_swimmer_id, new_team_id, season_id),
                )
                self.stats.swimmer_team_seasons += 1

    # ------------------------------------------------------------------
    # Meets
    # ------------------------------------------------------------------
    def _migrate_meets(self, src: sqlite3.Connection, dst: sqlite3.Connection) -> None:
        rows = src.execute(
            "SELECT id, name, date, location, profile_type FROM meet ORDER BY id"
        ).fetchall()
        log.info("Migrating %d meets ...", len(rows))

        for row in rows:
            old_id: int = row["id"]
            name: str = row["name"]
            raw_date: str = row["date"]
            location: str | None = row["location"]
            profile_type: str | None = row["profile_type"]

            dt = _parse_datetime(raw_date)
            meet_date_str = dt.date().isoformat()
            season_name = infer_season_name(dt)
            season_id = self._season_map.get(season_name)

            # Map Mac profile_type to Windows meet_type
            meet_type = _map_meet_type(profile_type)

            cur = dst.execute(
                """INSERT INTO meets
                       (name, meet_date, season_id, location, pool_course,
                        meet_type, created_at)
                   VALUES (?, ?, ?, ?, '25Y', ?, ?)""",
                (name, meet_date_str, season_id, location, meet_type, self.now_iso),
            )
            new_id = cur.lastrowid
            assert new_id is not None
            self._meet_map[old_id] = new_id
            self.stats.meets += 1

    # ------------------------------------------------------------------
    # Events + Entries (the main transformation)
    # ------------------------------------------------------------------
    def _migrate_events_and_entries(
        self, src: sqlite3.Connection, dst: sqlite3.Connection
    ) -> None:
        """Migrate evententry rows, creating Event rows on-the-fly.

        The Mac DB has a flat evententry table with event_name embedded.
        The Windows schema separates Event (per-meet event definition) from
        Entry (individual swimmer performance).

        Relay events in the Mac DB are stored as individual swimmer entries
        with relay event names (e.g., "Ms 200 Free Relay"). Since the Mac DB
        does not store relay team/letter/leg data, we migrate these as
        individual entries rather than relay_entries.  A post-migration
        enrichment step can later restructure them if needed.
        """
        total = src.execute("SELECT COUNT(*) FROM evententry").fetchone()[0]
        log.info("Migrating %d event entries ...", total)

        rows = src.execute(
            """SELECT id, event_name, seed_time, actual_time, points, rank,
                      meet_id, swimmer_id
               FROM evententry ORDER BY meet_id, event_name, id"""
        ).fetchall()

        for row in rows:
            old_meet_id: int = row["meet_id"]
            old_swimmer_id: int = row["swimmer_id"]
            event_name_raw: str = row["event_name"]
            seed_time: float = row["seed_time"]
            actual_time: float | None = row["actual_time"]
            points: float | None = row["points"]
            rank: int | None = row["rank"]

            # Resolve foreign keys
            new_meet_id = self._meet_map.get(old_meet_id)
            new_swimmer_id = self._swimmer_map.get(old_swimmer_id)
            if new_meet_id is None:
                self.stats.warnings.append(
                    f"evententry {row['id']} references unknown meet {old_meet_id}"
                )
                continue
            if new_swimmer_id is None:
                self.stats.warnings.append(
                    f"evententry {row['id']} references unknown swimmer {old_swimmer_id}"
                )
                continue

            # Parse event name
            parsed = parse_event_name(event_name_raw)

            # Get or create the Event row
            event_key = (new_meet_id, event_name_raw)
            if event_key not in self._event_map:
                cur = dst.execute(
                    """INSERT INTO events
                           (meet_id, event_name, event_distance, event_stroke,
                            gender, is_relay, is_diving)
                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (
                        new_meet_id,
                        parsed["normalized_name"],
                        parsed["distance"],
                        parsed["stroke"],
                        parsed["gender"],
                        int(parsed["is_relay"]),
                        int(parsed["is_diving"]),
                    ),
                )
                event_id = cur.lastrowid
                assert event_id is not None
                self._event_map[event_key] = event_id
                self.stats.events += 1
            else:
                event_id = self._event_map[event_key]

            # Determine the swimmer's team_id in the new DB
            swimmer_team_id: int | None = None
            old_swimmer_row = src.execute(
                "SELECT team_id FROM swimmer WHERE id = ?", (old_swimmer_id,)
            ).fetchone()
            if old_swimmer_row and old_swimmer_row["team_id"]:
                swimmer_team_id = self._team_map.get(old_swimmer_row["team_id"])

            # Insert the entry
            dst.execute(
                """INSERT INTO entries
                       (event_id, swimmer_id, team_id, seed_time, finals_time,
                        place, points, is_exhibition, is_dq, is_dns, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, 0, 0, 0, ?)""",
                (
                    event_id,
                    new_swimmer_id,
                    swimmer_team_id,
                    seed_time,
                    actual_time,
                    rank,
                    points or 0.0,
                    self.now_iso,
                ),
            )
            self.stats.entries += 1

        log.info(
            "Created %d distinct events, %d entries",
            self.stats.events,
            self.stats.entries,
        )

    # ------------------------------------------------------------------
    # Backtest results -> optimization_runs
    # ------------------------------------------------------------------
    def _migrate_backtest_results(
        self, src: sqlite3.Connection, dst: sqlite3.Connection
    ) -> None:
        """Map backtestresult to optimization_runs.

        The Mac table has: id, timestamp, ai_score, coach_score, actual_score,
        rank_accuracy, meet_id, details.

        We map ai_score -> home_score, coach_score -> away_score, and store
        the full row data in notes/config_json for auditability.
        """
        rows = src.execute("SELECT * FROM backtestresult ORDER BY id").fetchall()

        if not rows:
            log.info("No backtest results to migrate (table is empty)")
            return

        log.info("Migrating %d backtest results -> optimization_runs ...", len(rows))

        for row in rows:
            old_meet_id: int = row["meet_id"]
            new_meet_id = self._meet_map.get(old_meet_id)
            if new_meet_id is None:
                self.stats.warnings.append(
                    f"backtestresult {row['id']} references unknown meet {old_meet_id}"
                )
                continue

            import json

            config_data = {
                "source": "mac_db_backtest",
                "original_id": row["id"],
                "actual_score": row["actual_score"],
                "rank_accuracy": row["rank_accuracy"],
            }

            dst.execute(
                """INSERT INTO optimization_runs
                       (meet_id, run_date, optimizer_type,
                        home_score, away_score, config_json, notes)
                   VALUES (?, ?, 'backtest', ?, ?, ?, ?)""",
                (
                    new_meet_id,
                    row["timestamp"],
                    row["ai_score"],
                    row["coach_score"],
                    json.dumps(config_data),
                    row["details"],
                ),
            )
            self.stats.optimization_runs += 1

    # ------------------------------------------------------------------
    # Import log (record the migration itself)
    # ------------------------------------------------------------------
    def _write_import_log(self, dst: sqlite3.Connection) -> None:
        """Write a record into import_logs documenting this migration."""
        import json

        # Compute a checksum of the source file
        checksum = _file_md5(self.source_path)
        total_records = (
            self.stats.teams
            + self.stats.swimmers
            + self.stats.meets
            + self.stats.entries
            + self.stats.optimization_runs
        )

        errors = self.stats.warnings[:50] if self.stats.warnings else []

        dst.execute(
            """INSERT INTO import_logs
                   (source_path, source_type, import_date,
                    records_imported, records_skipped, errors_json,
                    status, checksum)
               VALUES (?, 'sqlite_migration', ?, ?, ?, ?, 'success', ?)""",
            (
                str(self.source_path),
                self.now_iso,
                total_records,
                self.stats.skipped_relay_entries,
                json.dumps(errors) if errors else None,
                checksum,
            ),
        )
        self.stats.import_log = 1


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _parse_datetime(raw: str) -> datetime:
    """Parse various datetime string formats from the Mac DB."""
    for fmt in (
        "%Y-%m-%d %H:%M:%S.%f",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d",
    ):
        try:
            return datetime.strptime(raw, fmt)
        except ValueError:
            continue
    raise ValueError(f"Cannot parse datetime: {raw!r}")


def _map_meet_type(profile_type: str | None) -> str:
    """Map Mac profile_type to Windows meet_type enum."""
    mapping = {
        "dual_meet": "dual",
        "dual": "dual",
        "invitational": "invitational",
        "championship": "championship",
        "conference": "conference",
        "time_trial": "time_trial",
        "exhibition": "exhibition",
    }
    if profile_type:
        return mapping.get(profile_type.lower(), "dual")
    return "dual"


def _file_md5(path: Path) -> str:
    """Compute MD5 hex digest of a file."""
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Migrate AquaForge Mac 5-table DB to Windows 16-table schema",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    p.add_argument(
        "--source",
        type=Path,
        default=DEFAULT_SOURCE,
        help=f"Path to the source (Mac) database (default: {DEFAULT_SOURCE})",
    )
    p.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"Path for the new (Windows) database (default: {DEFAULT_OUTPUT})",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be migrated without writing any files",
    )
    p.add_argument(
        "--force",
        action="store_true",
        help="Overwrite the output file if it already exists",
    )
    p.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable debug-level logging",
    )
    return p


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Handle --force
    if args.force and args.output.exists() and not args.dry_run:
        log.warning("Removing existing output file: %s", args.output)
        args.output.unlink()

    migrator = Migrator(
        source_path=args.source.resolve(),
        output_path=args.output.resolve(),
        dry_run=args.dry_run,
    )

    stats = migrator.run()
    print(stats.summary())


if __name__ == "__main__":
    main()
