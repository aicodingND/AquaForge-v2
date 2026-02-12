"""
Psych Sheet Parser Service

Handles parsing of psych sheets from various formats into structured data.
Supports:
- HyTek CSV Exports
- Generic Text/PDF content (via Regex)
- Meet Mobile HTML (Stub)
"""

import csv
import logging
import re
from datetime import date
from io import StringIO

from swim_ai_reflex.backend.models.championship import MeetPsychSheet, PsychSheetEntry
from swim_ai_reflex.backend.services.shared.normalization import (
    normalize_event_name_with_gender,
    normalize_grade,
    normalize_swimmer_name,
    normalize_team_name,
    normalize_time,
)

logger = logging.getLogger(__name__)


class PsychSheetParser:
    """Parses psych sheet files into MeetPsychSheet objects."""

    def __init__(self):
        self.entries = []

    def parse(self, content: str, filename: str = "") -> MeetPsychSheet:
        """
        Parse psych sheet content.

        Args:
            content: Raw string content of the file
            filename: Optional filename to aid format detection

        Returns:
            MeetPsychSheet object with parsed entries
        """
        format_type = self._detect_format(content, filename)
        logger.info(f"Detected psych sheet format: {format_type}")

        if format_type == "hytek_csv":
            sheet = self._parse_hytek_csv(content)
        elif format_type == "meet_mobile_html":
            sheet = self._parse_meet_mobile_html(content)
        else:
            # Default to text regex parser
            sheet = self._parse_text_regex(content)

        # Populate derived fields if missing
        if not sheet.teams:
            sheet.teams = sorted(list(set(e.team for e in sheet.entries if e.team)))

        return sheet

    def _detect_format(self, content: str, filename: str) -> str:
        """Detect format based on content and filename."""
        if filename.lower().endswith(".csv"):
            return "hytek_csv"

        # Check for HyTek CSV headers (common patterns)
        if "Event #," in content or "Meet Event Only," in content:
            return "hytek_csv"

        if "<html" in content.lower() and "meet mobile" in content.lower():
            return "meet_mobile_html"

        return "text_regex"

    def _parse_hytek_csv(self, content: str) -> MeetPsychSheet:
        """Parse HyTek CSV export."""
        entries = []
        # Handle potential BOM or different newlines
        f = StringIO(content.strip())
        reader = csv.reader(f)

        headers = []
        try:
            headers = next(reader)
        except StopIteration:
            return MeetPsychSheet(
                meet_name="Parsed Meet", meet_date=date.today(), teams=[], entries=[]
            )

        # Map headers to indices
        col_map = {}
        for i, h in enumerate(headers):
            h_norm = h.lower().strip()
            if "event" in h_norm and "name" in h_norm:
                col_map["event"] = i
            elif "time" in h_norm or "seed" in h_norm:
                col_map["time"] = i
            elif "athlete" in h_norm or "swimmer" in h_norm:
                col_map["swimmer"] = i
            elif "team" in h_norm:
                col_map["team"] = i
            elif "grade" in h_norm or "school year" in h_norm:
                col_map["grade"] = i

        for row in reader:
            if not row or len(row) < 3:
                continue

            try:
                # Extract fields
                event_raw = row[col_map["event"]] if "event" in col_map else ""
                swimmer_raw = (
                    row[col_map["swimmer"]] if "swimmer" in col_map else "Relay"
                )
                team_raw = row[col_map["team"]] if "team" in col_map else ""
                time_raw = row[col_map["time"]] if "time" in col_map else ""
                grade_raw = row[col_map["grade"]] if "grade" in col_map else "12"

                # Normalize
                event_norm = normalize_event_name_with_gender(event_raw)
                swimmer_norm = normalize_swimmer_name(swimmer_raw)

                # Skip if event not recognized or swimmer is empty (Relay line without names)
                if not event_norm or not swimmer_norm:
                    continue

                entries.append(
                    PsychSheetEntry(
                        swimmer_name=swimmer_norm,
                        team=normalize_team_name(team_raw),
                        event=event_norm,
                        seed_time=normalize_time(time_raw) or float("inf"),
                        # visual_seed_time=time_raw,
                        seed_rank=0,  # Calculated later if needed
                        grade=normalize_grade(grade_raw) or 12,
                    )
                )

            except (IndexError, ValueError) as e:
                logger.warning(f"Error parsing CSV line: {row} - {e}")

        return MeetPsychSheet(
            meet_name="Parsed Meet",
            meet_date=date.today(),
            teams=[],  # Will be populated in parse()
            entries=entries,
        )

    def _parse_text_regex(self, content: str) -> MeetPsychSheet:
        """
        Parse generic text/PDF content using Regex.

        Looks for lines like:
        1   Smith, John     12   SST     22.50
        """
        entries = []
        current_event = None

        # Regex patterns
        # Event Header: "Event 3  Boys 50 Yard Freestyle"
        # Extract the part after "Event X"
        event_re = re.compile(
            r"Event\s+\d+\s+((?:Boys|Girls|Men|Women).+?)(?=\n|$)", re.IGNORECASE
        )

        # Entry Line: "  1  Smith, John   12  SST   22.50"
        # Rank(opt) Name(Last, First) Grade Team Time
        entry_re = re.compile(
            r"^\s*(\d+)?\s+([A-Za-z\.' -]+,\s*[A-Za-z\.' -]+)\s+(\d{1,2}|JR|SR|SO|FR)\s+([A-Z]{2,4})\s+([\d:.]+|NT|X[\d:.]+)",
            re.MULTILINE,
        )

        lines = content.split("\n")
        for line in lines:
            line_clean = line.strip()
            # Check for event header using regex to be robust
            event_match = event_re.search(line_clean)
            if event_match:
                # Extract event name (Group 1)
                raw_event = event_match.group(1)
                normalized = normalize_event_name_with_gender(raw_event)
                if normalized:
                    current_event = normalized
                continue

            # Legacy check if regex failed but line starts with Event (fallback)
            if line_clean.lower().startswith("event") and not event_match:
                # Try to clean "Event X" manually
                parts = line_clean.split(maxsplit=2)
                if (
                    len(parts) >= 3
                    and parts[0].lower() == "event"
                    and parts[1].isdigit()
                ):
                    raw_event = parts[2]
                    normalized = normalize_event_name_with_gender(raw_event)
                    if normalized:
                        current_event = normalized
                continue

            if not current_event:
                continue

            # Check for swimmer entry
            match = entry_re.search(line)
            if match:
                # Groups: 1=Rank, 2=Name, 3=Grade, 4=Team, 5=Time
                # rank = match.group(1)
                name = match.group(2)
                grade = match.group(3)
                team = match.group(4)
                seed_time = match.group(5)

                entries.append(
                    PsychSheetEntry(
                        swimmer_name=normalize_swimmer_name(name),
                        team=normalize_team_name(team),
                        event=current_event,
                        seed_time=normalize_time(seed_time) or float("inf"),
                        # visual_seed_time=seed_time,
                        seed_rank=int(match.group(1)) if match.group(1) else 0,
                        grade=normalize_grade(grade) or 12,
                    )
                )

        return MeetPsychSheet(
            meet_name="Parsed Meet",
            meet_date=date.today(),
            teams=[],  # Will be populated in parse()
            entries=entries,
        )

    def _parse_meet_mobile_html(self, content: str) -> MeetPsychSheet:
        """Parse Meet Mobile HTML content (stub)."""
        # This would use BeautifulSoup in a real implementation
        # For now, return empty as stub
        logger.warning("Meet Mobile parsing not fully implemented yet")
        return MeetPsychSheet(
            meet_name="Meet Mobile Parse", meet_date=date.today(), teams=[], entries=[]
        )
