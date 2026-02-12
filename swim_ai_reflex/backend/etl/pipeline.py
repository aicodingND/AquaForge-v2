"""
ETL Pipeline Orchestrator

Coordinates: scan -> parse -> normalize -> resolve identity -> write to DB.

Usage:
    from swim_ai_reflex.backend.etl.pipeline import Pipeline
    pipeline = Pipeline()
    result = pipeline.import_directory("/path/to/swimdatadump/...")
    result = pipeline.import_file("path/to/meet.mdb")
"""

import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date

from sqlmodel import Session, select  # TODO: port dependency -- pip install sqlmodel

from swim_ai_reflex.backend.etl.hytek_mdb_parser import MeetData, parse_mdb
from swim_ai_reflex.backend.etl.identity_resolver import IdentityResolver
from swim_ai_reflex.backend.etl.normalizer import (
    classify_event,
    infer_meet_type,
    infer_season_from_date,
    normalize_team_name,
    parse_meet_date,
    validate_event_for_meet,
)
from swim_ai_reflex.backend.etl.scanner import (
    file_checksum,
    scan_directory,
)
from swim_ai_reflex.backend.persistence.database import (  # TODO: port dependency -- database.py not yet on Mac
    get_session,
    init_db,
)
from swim_ai_reflex.backend.persistence.db_models import (  # TODO: port dependency -- db_models.py not yet on Mac
    DualMeetPairing,
    Entry,
    Event,
    ImportLog,
    Meet,
    MeetTeam,
    RelayEntry,
    RelayLeg,
    Season,
    Split,
    Swimmer,
    SwimmerBest,
    SwimmerTeamSeason,
    Team,
)

logger = logging.getLogger(__name__)


@dataclass
class ImportResult:
    """Result of an import operation."""

    files_processed: int = 0
    files_skipped: int = 0  # already imported
    files_failed: int = 0
    records_imported: int = 0
    swimmers_created: int = 0
    swimmers_matched: int = 0
    meets_created: int = 0
    errors: list[str] = field(default_factory=list)


ProgressCallback = Callable[[str, int, int], None] | None
"""Callback(message, current, total) for progress reporting."""


def _extract_date_from_path(
    file_path: str, season_hint: str | None = None
) -> date | None:
    """Try to extract a meet date from the file path.

    Common patterns:
      - "Oct19,25" or "Jan10,26" in folder names (month + day + 2-digit year)
      - "2025-01-10" style in some folder names
    """
    import re

    path_str = file_path.replace("\\", "/")

    # Pattern 1: MonDD,YY (e.g., "Oct19,25" or "Feb13-15,25")
    m = re.search(
        r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)(\d{1,2})(?:-\d{1,2})?,(\d{2})",
        path_str,
        re.IGNORECASE,
    )
    if m:
        return parse_meet_date(m.group(0), season_hint)

    # Pattern 2: YYYY-MM-DD
    m = re.search(r"(\d{4})-(\d{2})-(\d{2})", path_str)
    if m:
        try:
            return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError:
            pass

    return None


def _extract_meet_name_from_path(file_path: str) -> str:
    """Extract a meaningful meet name from the file path.

    Looks for the parent folder that contains a date-like pattern
    (e.g., "3. Seton vs Paul VI-Nov18,25") or just the filename stem.
    """
    import re
    from pathlib import PurePosixPath, PureWindowsPath

    # Use the correct path type
    p = PureWindowsPath(file_path) if "\\" in file_path else PurePosixPath(file_path)

    # Walk up from the file looking for a folder with a meet-like name
    # Skip folders named "Results", "Database", "Report" etc.
    SKIP_FOLDERS = {
        "results",
        "database",
        "report",
        "reports",
        "data",
        "organized",
        "hytek_databases",
        "hytek",
    }
    for part in reversed(p.parts[:-1]):  # Exclude filename itself
        if part.lower() in SKIP_FOLDERS:
            continue
        # Check if folder looks like a meet name (has letters, optionally date)
        if re.search(r"[A-Za-z]{2,}", part) and len(part) > 3:
            # Clean up: remove leading numbers like "3. " and trailing date
            cleaned = re.sub(r"^\d+\.\s*", "", part)
            # Remove date suffix like "-Nov18,25"
            cleaned = re.sub(r"-[A-Z][a-z]{2}\d{1,2}(?:-\d{1,2})?,\d{2}$", "", cleaned)
            if cleaned:
                return cleaned.strip()

    # Fallback: use filename stem
    return p.stem or f"Unknown Meet ({file_path})"


class Pipeline:
    """ETL pipeline for importing swim meet data into AquaForge."""

    def __init__(self):
        init_db()

    def import_directory(
        self,
        root_path: str,
        extensions: set[str] | None = None,
        progress_cb: ProgressCallback = None,
    ) -> ImportResult:
        """
        Scan a directory and import all supported files.

        Args:
            root_path: Directory to scan (e.g., "/Volumes/swimdata/...")
            extensions: File extensions to import (default: .mdb only)
            progress_cb: Optional callback for progress reporting

        Returns:
            ImportResult with statistics
        """
        target_ext = extensions or {".mdb"}
        result = ImportResult()

        # Step 1: Scan
        if progress_cb:
            progress_cb("Scanning directory...", 0, 0)

        scan = scan_directory(root_path, compute_checksums=True, extensions=target_ext)
        total = len(scan.files)

        if progress_cb:
            progress_cb(f"Found {total} files to process", 0, total)

        # Step 2: Import each file
        for i, discovered in enumerate(scan.files):
            if progress_cb:
                progress_cb(
                    f"Processing: {discovered.meet_name or discovered.path}",
                    i + 1,
                    total,
                )

            try:
                file_result = self.import_file(
                    discovered.path,
                    season_hint=discovered.season,
                    meet_name_hint=discovered.meet_name,
                    meet_date_hint=discovered.meet_date_str,
                    checksum=discovered.checksum,
                )
                result.files_processed += 1
                result.records_imported += file_result.records_imported
                result.swimmers_created += file_result.swimmers_created
                result.swimmers_matched += file_result.swimmers_matched
                result.meets_created += file_result.meets_created
                result.errors.extend(file_result.errors)
            except AlreadyImportedError:
                result.files_skipped += 1
            except Exception as e:
                result.files_failed += 1
                result.errors.append(f"{discovered.path}: {e}")
                logger.error(f"Failed to import {discovered.path}: {e}")

        if progress_cb:
            progress_cb("Import complete!", total, total)

        return result

    def import_file(
        self,
        file_path: str,
        season_hint: str | None = None,
        meet_name_hint: str | None = None,
        meet_date_hint: str | None = None,
        checksum: str | None = None,
    ) -> ImportResult:
        """
        Import a single file into the database.

        Args:
            file_path: Path to .mdb file
            season_hint: Season from path classification (e.g., "2025-2026")
            meet_name_hint: Meet name from folder structure
            meet_date_hint: Date string from folder (e.g., "Jan10,26")
            checksum: Pre-computed file checksum

        Returns:
            ImportResult with statistics

        Raises:
            AlreadyImportedError: If file was previously imported successfully
        """
        result = ImportResult()

        # Compute checksum if not provided
        if not checksum:
            checksum = file_checksum(file_path)

        # Check idempotency
        with get_session() as session:
            existing = session.exec(
                select(ImportLog).where(
                    ImportLog.checksum == checksum,
                    ImportLog.status == "success",
                )
            ).first()
            if existing:
                raise AlreadyImportedError(f"Already imported: {file_path}")

        # Parse the file
        ext = file_path.rsplit(".", 1)[-1].lower()
        if ext == "mdb":
            meet_data = parse_mdb(file_path)
        else:
            result.errors.append(f"Unsupported file type: .{ext}")
            return result

        if meet_data.is_empty:
            result.errors.extend(meet_data.errors)
            return result

        # Write to database
        with get_session() as session:
            # Create import log
            log = ImportLog(
                source_path=file_path,
                source_type=f"hytek_{ext}",
                checksum=checksum,
                status="running",
            )
            session.add(log)
            session.commit()
            session.refresh(log)

            try:
                self._write_meet_data(
                    session,
                    meet_data,
                    result,
                    season_hint=season_hint,
                    meet_name_hint=meet_name_hint,
                    meet_date_hint=meet_date_hint,
                )

                # Update log
                log.status = "success"
                log.records_imported = result.records_imported
                if result.errors:
                    log.errors_json = str(result.errors)
                session.add(log)
                session.commit()

            except Exception as e:
                session.rollback()
                log.status = "failed"
                log.errors_json = str([str(e)])
                session.add(log)
                session.commit()
                result.errors.append(str(e))
                logger.error(f"Failed to write data from {file_path}: {e}")

        return result

    def _write_meet_data(
        self,
        session: Session,
        data: MeetData,
        result: ImportResult,
        season_hint: str | None = None,
        meet_name_hint: str | None = None,
        meet_date_hint: str | None = None,
    ) -> None:
        """Write parsed meet data to the database."""

        resolver = IdentityResolver(session)

        # --- Meet date (compute early for season inference) ---
        mi = data.meet_info  # May be None if Meet table missing

        # Prefer Meet table date > folder hint > file path date > file mtime > today
        meet_date = None
        if mi and mi.start_date:
            try:
                # access_parser returns datetime strings like "2012-01-21 00:00:00"
                meet_date = date.fromisoformat(mi.start_date.split(" ")[0])
            except (ValueError, AttributeError):
                pass
        if not meet_date:
            meet_date = (
                parse_meet_date(meet_date_hint, season_hint) if meet_date_hint else None
            )
        if not meet_date:
            # Try to extract date from file path (e.g., "Oct19,25" in folder name)
            meet_date = _extract_date_from_path(data.source_path, season_hint)
        if not meet_date:
            # Last resort: use file modification time (better than today's date)
            try:
                import os

                mtime = os.path.getmtime(data.source_path)
                from datetime import datetime as dt

                meet_date = dt.fromtimestamp(mtime).date()
            except (OSError, ValueError):
                meet_date = date.today()
                logger.warning(f"Using today as fallback date for {data.source_path}")

        # --- Season (infer from date if no folder hint) ---
        season_name = season_hint or infer_season_from_date(meet_date) or "Unknown"
        season = session.exec(select(Season).where(Season.name == season_name)).first()
        if not season:
            season = Season(name=season_name)
            session.add(season)
            session.commit()
            session.refresh(season)

        # --- Teams ---
        team_map: dict[int, Team] = {}  # hytek_team_no -> Team
        for pt in data.teams:
            canonical = normalize_team_name(pt.name)
            if canonical == "Unknown":
                # Try abbreviation as fallback
                if pt.abbreviation:
                    canonical = normalize_team_name(pt.abbreviation)

            team = session.exec(select(Team).where(Team.name == canonical)).first()
            if not team:
                team = Team(
                    name=canonical,
                    short_name=pt.abbreviation or None,
                )
                session.add(team)
                session.commit()
                session.refresh(team)
            team_map[pt.team_no] = team

        # --- Meet ---
        meet_end = None
        if mi and mi.end_date:
            try:
                meet_end = date.fromisoformat(mi.end_date.split(" ")[0])
            except (ValueError, AttributeError):
                pass

        # Prefer Meet table name > folder hint > extracted from path > fallback
        meet_name = (mi.name if mi and mi.name else None) or meet_name_hint
        if not meet_name:
            meet_name = _extract_meet_name_from_path(data.source_path)

        # Meet type: infer from name (more reliable than Hy-Tek code)
        hytek_code = mi.meet_type if mi else None
        meet_type = infer_meet_type(meet_name, hytek_code)

        # Duplicate meet detection: same name + same date = skip
        existing_meet = session.exec(
            select(Meet).where(
                Meet.name == meet_name,
                Meet.meet_date == meet_date,
            )
        ).first()
        if existing_meet:
            result.errors.append(f"Duplicate meet skipped: {meet_name} on {meet_date}")
            return

        meet = Meet(
            name=meet_name,
            meet_date=meet_date,
            meet_end_date=meet_end if meet_end and meet_end != meet_date else None,
            season_id=season.id,
            location=mi.location if mi else None,
            city=mi.city if mi else None,
            state=mi.state if mi else None,
            pool_course=data.pool_course,
            num_lanes=mi.num_lanes if mi else None,
            meet_type=meet_type,
            ind_max_scorers=mi.ind_max_scorers if mi else None,
            relay_max_scorers=mi.relay_max_scorers if mi else None,
            hytek_db_path=data.source_path,
            source_file=data.source_path,
        )
        session.add(meet)
        session.commit()
        session.refresh(meet)
        result.meets_created += 1

        # --- MeetTeams ---
        for pt in data.teams:
            team = team_map.get(pt.team_no)
            if team:
                mt = MeetTeam(meet_id=meet.id, team_id=team.id)
                session.add(mt)
        session.commit()

        # --- Build lookup maps ---
        athlete_map: dict[int, int] = {}  # hytek_ath_no -> swimmer_id
        event_map: dict[int, int] = {}  # hytek_event_ptr -> event_id
        event_info: dict[int, dict] = {}  # hytek_event_ptr -> event metadata

        # --- Athletes -> Swimmers ---
        for pa in data.athletes:
            raw_name = f"{pa.first_name} {pa.last_name}".strip()
            if not raw_name:
                continue

            team = team_map.get(pa.team_no)
            team_name = team.name if team else None

            # Determine gender from athlete or from events they're in
            gender = pa.gender

            swimmer_id = resolver.resolve(
                raw_name=raw_name,
                gender=gender,
                team_name=team_name,
            )
            athlete_map[pa.ath_no] = swimmer_id

            # Update swimmer with birth/registration info if available
            if pa.birth_date or pa.usa_swimming_id:
                swimmer = session.get(Swimmer, swimmer_id)
                if swimmer:
                    if pa.birth_date and not swimmer.birth_year:
                        try:
                            swimmer.birth_year = int(pa.birth_date.split("-")[0])
                        except (ValueError, IndexError):
                            pass
                    if pa.usa_swimming_id and not swimmer.usa_swimming_id:
                        swimmer.usa_swimming_id = pa.usa_swimming_id
                    session.add(swimmer)

            # Ensure SwimmerTeamSeason link exists
            if team:
                existing_sts = session.exec(
                    select(SwimmerTeamSeason).where(
                        SwimmerTeamSeason.swimmer_id == swimmer_id,
                        SwimmerTeamSeason.team_id == team.id,
                        SwimmerTeamSeason.season_id == season.id,
                    )
                ).first()
                if not existing_sts:
                    sts = SwimmerTeamSeason(
                        swimmer_id=swimmer_id,
                        team_id=team.id,
                        season_id=season.id,
                        grade=pa.school_year,
                    )
                    session.add(sts)
                    result.swimmers_created += 1
                else:
                    result.swimmers_matched += 1

        session.commit()

        # --- Events ---
        for pe in data.events:
            # Classify event against meet type
            category = classify_event(pe.event_name, meet_type)

            # Log warnings for unusual events
            warnings = validate_event_for_meet(pe.event_name, meet_type)
            for w in warnings:
                logger.warning(f"[{meet_name}] {w}")

            event = Event(
                meet_id=meet.id,
                event_number=pe.event_no,
                event_name=pe.event_name,
                event_distance=pe.distance,
                event_stroke=STROKE_MAP.get(pe.stroke_code, pe.stroke_code),
                gender=pe.gender,
                is_relay=pe.is_relay,
                is_diving=pe.is_diving,
                event_category=category,
            )
            session.add(event)
            session.commit()
            session.refresh(event)
            event_map[pe.event_ptr] = event.id
            event_info[pe.event_ptr] = {
                "name": pe.event_name,
                "is_relay": pe.is_relay,
                "gender": pe.gender,
                "category": category,
            }

        # --- Individual Entries ---
        for pe in data.entries:
            swimmer_id = athlete_map.get(pe.ath_no)
            event_id = event_map.get(pe.event_ptr)
            if not swimmer_id or not event_id:
                continue

            # Get team_id from athlete
            athlete = next((a for a in data.athletes if a.ath_no == pe.ath_no), None)
            team_id = (
                team_map.get(athlete.team_no).id
                if athlete and athlete.team_no in team_map
                else None
            )

            entry = Entry(
                event_id=event_id,
                swimmer_id=swimmer_id,
                team_id=team_id,
                seed_time=pe.seed_time,
                finals_time=pe.finals_time,
                heat=pe.heat,
                lane=pe.lane,
                place=pe.place,
                points=pe.points,
                is_exhibition=pe.is_exhibition,
                is_dq=pe.is_dq,
                course=pe.course,
            )
            session.add(entry)
            result.records_imported += 1

        # --- Relays ---
        for pr in data.relays:
            event_id = event_map.get(pr.event_ptr)
            team = team_map.get(pr.team_no)
            if not event_id or not team:
                continue

            relay = RelayEntry(
                event_id=event_id,
                team_id=team.id,
                relay_letter=pr.relay_letter,
                seed_time=pr.seed_time,
                finals_time=pr.finals_time,
                place=pr.place,
                points=pr.points,
            )
            session.add(relay)
            session.commit()
            session.refresh(relay)

            # Relay legs
            for ath_no, leg_order in pr.legs:
                swimmer_id = athlete_map.get(ath_no)
                if swimmer_id:
                    leg = RelayLeg(
                        relay_entry_id=relay.id,
                        swimmer_id=swimmer_id,
                        leg_order=leg_order,
                    )
                    session.add(leg)
            result.records_imported += 1

        # --- Splits ---
        # Build relay_no -> relay_entry_id map
        relay_db_map: dict[int, int] = {}  # hytek relay_no -> DB relay_entry.id
        for pr in data.relays:
            event_id = event_map.get(pr.event_ptr)
            team = team_map.get(pr.team_no)
            if event_id and team:
                # Find the relay entry we just created
                existing_re = session.exec(
                    select(RelayEntry).where(
                        RelayEntry.event_id == event_id,
                        RelayEntry.team_id == team.id,
                        RelayEntry.relay_letter == pr.relay_letter,
                    )
                ).first()
                if existing_re:
                    relay_db_map[pr.relay_no] = existing_re.id

        for ps in data.splits:
            event_id = event_map.get(ps.event_ptr)
            if not event_id:
                continue

            swimmer_id = athlete_map.get(ps.ath_no) if ps.ath_no > 0 else None
            relay_entry_id = relay_db_map.get(ps.relay_no) if ps.relay_no > 0 else None

            # Need either a swimmer or relay link
            if not swimmer_id and not relay_entry_id:
                continue

            split = Split(
                event_id=event_id,
                swimmer_id=swimmer_id,
                relay_entry_id=relay_entry_id,
                split_number=ps.split_number,
                split_time=ps.split_time,
                round_code=ps.round_code,
            )
            session.add(split)

        # --- Dual Meet Pairings ---
        for dp in data.dual_pairings:
            team_a = team_map.get(dp.team_a_no)
            team_b = team_map.get(dp.team_b_no)
            if team_a and team_b:
                pairing = DualMeetPairing(
                    meet_id=meet.id,
                    team_a_id=team_a.id,
                    team_b_id=team_b.id,
                    gender=dp.gender,
                )
                session.add(pairing)

        session.commit()

    def refresh_swimmer_bests(self, season_name: str | None = None) -> int:
        """
        Recompute swimmer_bests table from entries.

        Args:
            season_name: If provided, only refresh for this season.

        Returns:
            Number of swimmer_bests records updated.
        """
        with get_session() as session:
            from sqlalchemy import func as sqlfunc

            # Build query: group entries by swimmer + event
            stmt = (
                select(
                    Entry.swimmer_id,
                    Event.event_name,
                    Season.id.label("season_id"),
                    sqlfunc.min(Entry.finals_time).label("best_time"),
                    sqlfunc.avg(Entry.finals_time).label("mean_time"),
                    sqlfunc.count(Entry.id).label("sample_size"),
                )
                .join(Event, Entry.event_id == Event.id)
                .join(Meet, Event.meet_id == Meet.id)
                .join(Season, Meet.season_id == Season.id)
                .where(Entry.finals_time.is_not(None))
                .where(Entry.is_dq == False)  # noqa: E712
                .group_by(Entry.swimmer_id, Event.event_name, Season.id)
            )

            if season_name:
                stmt = stmt.where(Season.name == season_name)

            rows = session.exec(stmt).all()
            count = 0

            for row in rows:
                # Upsert swimmer_best
                existing = session.exec(
                    select(SwimmerBest).where(
                        SwimmerBest.swimmer_id == row.swimmer_id,
                        SwimmerBest.event_name == row.event_name,
                        SwimmerBest.season_id == row.season_id,
                    )
                ).first()

                if existing:
                    existing.best_time = row.best_time
                    existing.mean_time = row.mean_time
                    existing.sample_size = row.sample_size
                    session.add(existing)
                else:
                    best = SwimmerBest(
                        swimmer_id=row.swimmer_id,
                        event_name=row.event_name,
                        season_id=row.season_id,
                        best_time=row.best_time,
                        mean_time=row.mean_time,
                        sample_size=row.sample_size,
                    )
                    session.add(best)
                count += 1

            session.commit()
            return count


# Hy-Tek stroke map (used in _write_meet_data)
STROKE_MAP = {"A": "Free", "B": "Back", "C": "Breast", "D": "Fly", "E": "IM"}


class AlreadyImportedError(Exception):
    """Raised when a file has already been imported."""

    pass
