"""
CSV Loader - Fallback data ingestion from Team Manager CSV exports.

This loader handles CSV files exported from HyTek Team Manager.
It's the fallback method when .mdb or .hy3 files aren't available.

Usage:
    from swim_ai_reflex.core.data.loaders.csv_loader import CSVLoader

    loader = CSVLoader(data_path)
    athletes = loader.load_athletes()
    results = loader.load_results()
"""

from __future__ import annotations

import csv
from datetime import date, datetime
from pathlib import Path
from typing import Generator

from swim_ai_reflex.core.data.entities import (
    AthleteEntity,
    MeetEntity,
    RelayResultEntity,
    SplitEntity,
    SwimResultEntity,
    TeamEntity,
    ValidationError,
)


class CSVLoader:
    """
    Load swim data from HyTek Team Manager CSV exports.

    Expected files:
        - athletes.csv
        - results.csv
        - relays.csv
        - splits.csv
        - meets.csv
        - teams.csv
    """

    def __init__(self, data_path: str | Path):
        """
        Initialize loader with path to CSV data directory.

        Args:
            data_path: Path to directory containing CSV files
        """
        self.data_path = Path(data_path)
        self.validation_errors: list[ValidationError] = []

    def _log_error(
        self, source_file: str, row_num: int, field: str, value: str, error: str
    ) -> None:
        """Log validation error without silently fixing."""
        self.validation_errors.append(
            ValidationError(
                source_file=source_file,
                row_number=row_num,
                field_name=field,
                raw_value=str(value)[:100],
                error_message=error,
            )
        )

    def _parse_date(self, date_str: str) -> date | None:
        """Parse HyTek date format (MM/DD/YY HH:MM:SS or similar)."""
        if not date_str or date_str.strip() == "":
            return None

        # Try common formats
        formats = [
            "%m/%d/%y %H:%M:%S",
            "%m/%d/%Y %H:%M:%S",
            "%m/%d/%y",
            "%m/%d/%Y",
            "%Y-%m-%d",
        ]

        for fmt in formats:
            try:
                return datetime.strptime(date_str.strip(), fmt).date()
            except ValueError:
                continue

        return None

    def load_teams(self) -> list[TeamEntity]:
        """Load teams from teams.csv."""
        teams: list[TeamEntity] = []
        csv_path = self.data_path / "teams.csv"

        if not csv_path.exists():
            return teams

        with open(csv_path, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row_num, row in enumerate(reader, start=2):
                try:
                    team = TeamEntity(
                        team_id=int(row.get("TEAM", 0)),
                        code=row.get("TCODE", ""),
                        name=row.get("TNAME", ""),
                        short_name=row.get("SHORT", ""),
                        state=row.get("TSTATE", "VA"),
                        team_type=row.get("TTYPE", "HS"),
                    )
                    teams.append(team)
                except Exception as e:
                    self._log_error("teams.csv", row_num, "row", str(row), str(e))

        return teams

    def load_athletes(self) -> list[AthleteEntity]:
        """Load athletes from athletes.csv."""
        athletes: list[AthleteEntity] = []
        csv_path = self.data_path / "athletes.csv"

        if not csv_path.exists():
            return athletes

        with open(csv_path, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row_num, row in enumerate(reader, start=2):
                try:
                    # Skip inactive athletes with no names
                    last_name = row.get("LAST", "").strip()
                    first_name = row.get("FIRST", "").strip()
                    if not last_name or not first_name:
                        continue

                    athlete = AthleteEntity(
                        athlete_id=int(row.get("ATHLETE", 0)),
                        team_id=int(row.get("TEAM1", 0) or 0),
                        last_name=last_name,
                        first_name=first_name,
                        sex=row.get("SEX", "M"),
                        birth_date=self._parse_date(row.get("BIRTH", "")),
                        grade=row.get("CLASS"),
                        inactive=row.get("INACTIVE", "0") == "1",
                        preferred_name=row.get("PREF") or None,
                    )
                    athletes.append(athlete)
                except Exception as e:
                    self._log_error(
                        "athletes.csv",
                        row_num,
                        "row",
                        f"{first_name} {last_name}",
                        str(e),
                    )

        return athletes

    def load_meets(self) -> list[MeetEntity]:
        """Load meets from meets.csv."""
        meets: list[MeetEntity] = []
        csv_path = self.data_path / "meets.csv"

        if not csv_path.exists():
            return meets

        with open(csv_path, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row_num, row in enumerate(reader, start=2):
                try:
                    start_date = self._parse_date(row.get("START", ""))
                    if not start_date:
                        continue

                    # Normalize course code (handle legacy 'YO' format)
                    course_raw = (row.get("COURSE", "") or "").strip().upper()
                    if course_raw.startswith("Y"):
                        course = "Y"
                    elif course_raw.startswith("S"):
                        course = "S"
                    elif course_raw.startswith("L"):
                        course = "L"
                    else:
                        course = "Y"  # Default to yards

                    meet = MeetEntity(
                        meet_id=int(row.get("MEET", 0)),
                        name=row.get("MNAME", ""),
                        start_date=start_date,
                        end_date=self._parse_date(row.get("END", "")),
                        course=course,
                        location=row.get("Location", ""),
                        altitude=int(row.get("Altitude", 0) or 0),
                    )
                    meets.append(meet)
                except Exception as e:
                    self._log_error(
                        "meets.csv", row_num, "row", row.get("MNAME", ""), str(e)
                    )

        return meets

    def load_results(self) -> Generator[SwimResultEntity, None, None]:
        """
        Load results from results.csv as a generator (large file).

        Edge cases handled:
            - Missing/invalid result_type (defaults to "I")
            - Missing/invalid course (defaults to "Y")
            - Zero or negative athlete_id (skipped)
            - Zero or negative times (skipped)
            - Invalid distances (skipped silently - likely diving)

        Yields:
            SwimResultEntity for each valid result row
        """
        csv_path = self.data_path / "results.csv"

        if not csv_path.exists():
            return

        with open(csv_path, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row_num, row in enumerate(reader, start=2):
                try:
                    # CRITICAL: Time is in SCORE column, not RESULT
                    # RESULT is an auto-increment ID
                    # SCORE is time in hundredths of a second
                    score_raw = row.get("SCORE", "")
                    if not score_raw or score_raw == "0":
                        continue

                    time_hundredths = int(score_raw)
                    if time_hundredths <= 0:
                        continue

                    distance = int(row.get("DISTANCE", 0))
                    stroke = int(row.get("STROKE", 0))

                    # Skip invalid swim events (diving handled separately)
                    if distance <= 0 or stroke < 1 or stroke > 5:
                        continue

                    # Handle athlete_id edge cases
                    try:
                        athlete_id = int(row.get("ATHLETE", 0) or 0)
                        if athlete_id <= 0:
                            continue
                    except (ValueError, TypeError):
                        continue

                    # Handle result_type edge cases (empty, lowercase, etc.)
                    result_type_raw = (row.get("I_R", "") or "").strip().upper()
                    result_type = (
                        result_type_raw if result_type_raw in ("I", "R") else "I"
                    )

                    # Handle course edge cases (empty, invalid values)
                    course_raw = (row.get("COURSE", "") or "").strip().upper()
                    course = course_raw if course_raw in ("Y", "S", "L") else "Y"

                    # Exhibition flag: only 'X' means exhibition, space is NOT exhibition
                    ex_value = (row.get("EX", "") or "").strip().upper()
                    is_exhibition = ex_value == "X"

                    result = SwimResultEntity.from_hundredths(
                        meet_id=int(row.get("MEET", 0) or 0),
                        athlete_id=athlete_id,
                        result_type=result_type,
                        time_hundredths=time_hundredths,
                        distance=distance,
                        stroke=stroke,
                        course=course,
                        place=int(row.get("PLACE", 0) or 0),
                        points=float(row.get("POINTS", 0) or 0),
                        is_exhibition=is_exhibition,
                        dq_code=row.get("DQCODE") or None,
                        dq_description=row.get("DQDESCRIPT") or None,
                    )
                    yield result
                except Exception as e:
                    self._log_error(
                        "results.csv", row_num, "row", str(row)[:50], str(e)
                    )

    def load_relays(self) -> Generator[RelayResultEntity, None, None]:
        """
        Load relays from relays.csv as a generator.

        Yields:
            RelayResultEntity for each valid relay row
        """
        csv_path = self.data_path / "relays.csv"

        if not csv_path.exists():
            return

        with open(csv_path, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row_num, row in enumerate(reader, start=2):
                try:
                    # Extract swimmer IDs from ATH(1) through ATH(8)
                    swimmers = []
                    for i in range(1, 9):
                        ath_id = row.get(f"ATH({i})", "0")
                        if ath_id and int(ath_id) > 0:
                            swimmers.append(int(ath_id))

                    if len(swimmers) < 4:
                        continue

                    relay = RelayResultEntity(
                        relay_id=int(row.get("RELAY", 0)),
                        meet_id=int(row.get("MEET", 0)),
                        team_id=int(row.get("TEAM", 0)),
                        letter=row.get("LETTER", "A"),
                        sex=row.get("SEX", "M"),
                        swimmers=swimmers,
                        distance=int(row.get("DISTANCE", 0)),
                        stroke=int(row.get("STROKE", 0)),
                    )
                    yield relay
                except Exception as e:
                    self._log_error("relays.csv", row_num, "row", str(row)[:50], str(e))

    def load_splits(self) -> Generator[SplitEntity, None, None]:
        """
        Load splits from splits.csv as a generator.

        Yields:
            SplitEntity for each valid split row
        """
        csv_path = self.data_path / "splits.csv"

        if not csv_path.exists():
            return

        with open(csv_path, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row_num, row in enumerate(reader, start=2):
                try:
                    split_time = row.get("Split", "")
                    if not split_time or int(split_time) <= 0:
                        continue

                    stroke_rate = row.get("StrokeRate", "")
                    stroke_rate_val = float(stroke_rate) if stroke_rate else None

                    split = SplitEntity.from_hundredths(
                        split_id=int(row.get("SplitID", 0)),
                        split_index=int(row.get("SplitIndex", 1)),
                        time_hundredths=int(split_time),
                        stroke_rate=stroke_rate_val,
                    )
                    yield split
                except Exception as e:
                    self._log_error("splits.csv", row_num, "row", str(row)[:50], str(e))

    def get_summary(self) -> dict:
        """
        Get summary of loaded data with counts.

        Returns:
            Dictionary with record counts and error count
        """
        return {
            "teams": len(self.load_teams()),
            "athletes": len(self.load_athletes()),
            "meets": len(self.load_meets()),
            "results": sum(1 for _ in self.load_results()),
            "relays": sum(1 for _ in self.load_relays()),
            "splits": sum(1 for _ in self.load_splits()),
            "validation_errors": len(self.validation_errors),
        }
