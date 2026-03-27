"""
Unified Data Service - Enterprise Data Management Layer

Centralizes all data sources:
- Local scraped data (data/scraped/)
- SwimCloud data (data/swimcloud/)
- Championship data (data/championship_data/)
- External HDD data (/Volumes/Miguel/swimdatadump/)
- Meet entry files (ZIP exports)

Architecture follows repository pattern with caching and validation.
"""

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

logger = logging.getLogger(__name__)


# ============================================================================
# DATA CONTRACTS
# ============================================================================


@dataclass
class SwimmerTime:
    """Standardized swimmer time entry."""

    swimmer: str
    event: str
    time: float  # Always in seconds
    time_str: str  # Original format (MM:SS.ss or SS.ss)
    team: str
    grade: int | None = None
    gender: str | None = None
    source: str = "unknown"
    scraped_at: str | None = None


@dataclass
class TeamData:
    """Standardized team data container."""

    team_code: str
    team_name: str
    swimmers: list[dict[str, Any]] = field(default_factory=list)
    times: list[SwimmerTime] = field(default_factory=list)
    source: str = "unknown"
    last_updated: str | None = None


@dataclass
class DataSourceStatus:
    """Status of a data source."""

    name: str
    path: str
    available: bool
    last_checked: str
    record_count: int = 0
    error: str | None = None


# ============================================================================
# TIME CONVERSION UTILITIES
# ============================================================================


def time_to_seconds(time_input: str | float | int) -> float:
    """
    Convert any time format to seconds.

    Handles:
    - Float/int (already seconds or needs conversion)
    - "MM:SS.ss" format
    - "SS.ss" format
    - "M:SS.ss" format
    """
    if isinstance(time_input, (int, float)):
        # If > 100, likely already in seconds for long events
        # If < 100, could be 50 free (22.5s) or already seconds
        return float(time_input)

    time_str = str(time_input).strip()
    if not time_str or time_str.lower() in ("nt", "ns", "dq", "scr", ""):
        return 9999.99  # No time

    try:
        if ":" in time_str:
            parts = time_str.split(":")
            if len(parts) == 2:
                minutes = float(parts[0])
                seconds = float(parts[1])
                return minutes * 60 + seconds
            elif len(parts) == 3:  # HH:MM:SS unlikely but handle
                hours = float(parts[0])
                minutes = float(parts[1])
                seconds = float(parts[2])
                return hours * 3600 + minutes * 60 + seconds
        else:
            return float(time_str)
    except (ValueError, TypeError):
        logger.warning(f"Could not parse time: {time_input}")
        return 9999.99


def seconds_to_time_str(seconds: float) -> str:
    """Convert seconds to standard time string format."""
    if seconds >= 9999:
        return "NT"
    if seconds >= 60:
        minutes = int(seconds // 60)
        secs = seconds % 60
        return f"{minutes}:{secs:05.2f}"
    return f"{seconds:.2f}"


# ============================================================================
# DATA SOURCE REGISTRY
# ============================================================================


class DataSourceRegistry:
    """Registry of all available data sources."""

    # Base paths
    PROJECT_ROOT = Path(
        "/Users/mpage1/Desktop/AquaForge/AquaForge_v1.0.0-next_2026-01-10"
    )
    DATA_DIR = PROJECT_ROOT / "data"

    # Data source paths
    SOURCES = {
        "scraped": DATA_DIR / "scraped",
        "swimcloud": DATA_DIR / "swimcloud",
        "championship": DATA_DIR / "championship_data",
        "vcac": DATA_DIR / "vcac",
        "teams": DATA_DIR / "teams",
        "meets": DATA_DIR / "meets",
        "external_hdd": Path("/Volumes/Miguel/swimdatadump"),
    }

    # Team code mappings
    TEAM_CODES = {
        "SST": "Seton School",
        "ICS": "Immanuel Christian",
        "OAK": "Oakcrest",
        "TCS": "The Covenant School",
        "FCS": "Fredericksburg Christian",
        "DJO": "De Jonge",
        "PVI": "Paul VI",
        "BI": "Bishop Ireton",
    }

    @classmethod
    def check_sources(cls) -> list[DataSourceStatus]:
        """Check availability of all data sources."""
        statuses = []
        for name, path in cls.SOURCES.items():
            available = path.exists()
            record_count = 0
            error = None

            if available:
                try:
                    if path.is_dir():
                        record_count = len(list(path.glob("*.json")))
                except Exception as e:
                    error = str(e)

            statuses.append(
                DataSourceStatus(
                    name=name,
                    path=str(path),
                    available=available,
                    last_checked=datetime.now().isoformat(),
                    record_count=record_count,
                    error=error,
                )
            )
        return statuses


# ============================================================================
# UNIFIED DATA SERVICE
# ============================================================================


class UnifiedDataService:
    """
    Enterprise-grade unified data access layer.

    Features:
    - Multiple data source support
    - Automatic data normalization
    - Caching for performance
    - Validation and error handling
    - Grade/exhibition status inference
    """

    def __init__(self):
        self._cache: dict[str, Any] = {}
        self._cache_ttl = 300  # 5 minutes
        self._last_cache_time: dict[str, datetime] = {}

    def get_team_data(
        self, team_code: str, prefer_source: str | None = None
    ) -> TeamData | None:
        """
        Get unified team data from best available source.

        Priority:
        1. Championship data (most curated)
        2. SwimCloud (current season)
        3. Scraped data
        4. External HDD
        """
        cache_key = f"team_{team_code}"
        if self._is_cache_valid(cache_key):
            return self._cache[cache_key]

        team_data = None

        # Try championship data first
        champ_path = DataSourceRegistry.SOURCES["championship"]
        if champ_path.exists():
            for f in champ_path.glob("*.json"):
                try:
                    with open(f) as fp:
                        data = json.load(fp)
                        if self._matches_team(data, team_code):
                            team_data = self._parse_championship_data(data, team_code)
                            break
                except Exception as e:
                    logger.debug(f"Error reading {f}: {e}")

        # Try scraped data
        if not team_data:
            scraped_path = (
                DataSourceRegistry.SOURCES["scraped"] / f"{team_code}_swimcloud.json"
            )
            if scraped_path.exists():
                try:
                    with open(scraped_path) as fp:
                        data = json.load(fp)
                        team_data = self._parse_scraped_data(data, team_code)
                except Exception as e:
                    logger.warning(f"Error reading scraped data for {team_code}: {e}")

        if team_data:
            self._cache[cache_key] = team_data
            self._last_cache_time[cache_key] = datetime.now()

        return team_data

    def get_all_teams(self) -> list[str]:
        """Get list of all available team codes."""
        teams = set()

        # From scraped
        scraped = DataSourceRegistry.SOURCES["scraped"]
        if scraped.exists():
            for f in scraped.glob("*_swimcloud.json"):
                code = f.stem.replace("_swimcloud", "")
                teams.add(code)

        # From registry
        teams.update(DataSourceRegistry.TEAM_CODES.keys())

        return sorted(list(teams))

    def get_unified_psych_sheet(
        self, team_codes: list[str] | None = None
    ) -> pd.DataFrame:
        """
        Build unified psych sheet from all available sources.

        Returns DataFrame with columns:
        - swimmer, event, time, time_str, team, grade, gender, source
        """
        if team_codes is None:
            team_codes = self.get_all_teams()

        all_entries = []

        for code in team_codes:
            team_data = self.get_team_data(code)
            if team_data and team_data.times:
                for t in team_data.times:
                    all_entries.append(
                        {
                            "swimmer": t.swimmer,
                            "event": t.event,
                            "time": t.time,
                            "time_str": t.time_str,
                            "team": t.team,
                            "grade": t.grade,
                            "gender": t.gender,
                            "source": t.source,
                        }
                    )

        if not all_entries:
            return pd.DataFrame()

        df = pd.DataFrame(all_entries)

        # Normalize event names
        df["event"] = df["event"].apply(self._normalize_event_name)

        # Sort by event, then time
        df = df.sort_values(["event", "time"])

        return df

    def validate_data_integrity(self) -> dict[str, Any]:
        """Run data integrity checks across all sources."""
        issues = []
        stats = {"total_teams": 0, "total_entries": 0, "missing_grades": 0}

        for code in self.get_all_teams():
            team = self.get_team_data(code)
            if team:
                stats["total_teams"] += 1
                stats["total_entries"] += len(team.times)

                # Check for missing grades
                for t in team.times:
                    if t.grade is None:
                        stats["missing_grades"] += 1

                # Check for empty data
                if not team.times:
                    issues.append(f"Team {code} has no time entries")

        return {"stats": stats, "issues": issues, "valid": len(issues) == 0}

    # -------------------------------------------------------------------------
    # Private helpers
    # -------------------------------------------------------------------------

    def _is_cache_valid(self, key: str) -> bool:
        """Check if cache entry is still valid."""
        if key not in self._cache or key not in self._last_cache_time:
            return False
        age = (datetime.now() - self._last_cache_time[key]).total_seconds()
        return age < self._cache_ttl

    def _matches_team(self, data: dict, team_code: str) -> bool:
        """Check if data matches team code."""
        if isinstance(data, dict):
            return data.get("team_code") == team_code or data.get("team") == team_code
        return False

    def _parse_scraped_data(self, data: dict, team_code: str) -> TeamData:
        """Parse scraped SwimCloud format."""
        times = []
        for entry in data.get("times", []):
            time_val = entry.get("seed_time") or entry.get("time") or 9999
            times.append(
                SwimmerTime(
                    swimmer=entry.get("swimmer_name", "Unknown"),
                    event=entry.get("event", "Unknown"),
                    time=time_to_seconds(time_val),
                    time_str=seconds_to_time_str(time_to_seconds(time_val)),
                    team=team_code,
                    grade=self._infer_grade(entry.get("classYear")),
                    gender=entry.get("gender"),
                    source="swimcloud",
                )
            )

        return TeamData(
            team_code=team_code,
            team_name=data.get("team_name", team_code),
            swimmers=data.get("roster", []),
            times=times,
            source="swimcloud",
            last_updated=data.get("scraped_at"),
        )

    def _parse_championship_data(self, data: dict, team_code: str) -> TeamData:
        """Parse championship data format."""
        times = []
        entries = data.get("entries", []) or data.get("times", [])

        for entry in entries:
            if entry.get("team") == team_code:
                time_val = entry.get("time") or entry.get("seed_time") or 9999
                times.append(
                    SwimmerTime(
                        swimmer=entry.get("swimmer", "Unknown"),
                        event=entry.get("event", "Unknown"),
                        time=time_to_seconds(time_val),
                        time_str=seconds_to_time_str(time_to_seconds(time_val)),
                        team=team_code,
                        grade=entry.get("grade"),
                        gender=entry.get("gender"),
                        source="championship",
                    )
                )

        return TeamData(
            team_code=team_code,
            team_name=DataSourceRegistry.TEAM_CODES.get(team_code, team_code),
            times=times,
            source="championship",
        )

    def _infer_grade(self, class_year: str | None) -> int | None:
        """Infer numeric grade from class year string."""
        if class_year is None:
            return None

        class_year = str(class_year).upper().strip()

        # Direct numeric
        if class_year.isdigit():
            return int(class_year)

        # Class year abbreviations
        grade_map = {"FR": 9, "SO": 10, "JR": 11, "SR": 12, "8": 8, "7": 7, "6": 6}

        return grade_map.get(class_year)

    def _normalize_event_name(self, event: str) -> str:
        """Normalize event names to standard format."""
        if not event:
            return event

        event = str(event).strip()

        # Standard event mappings
        mappings = {
            "50 Free": "50 Freestyle",
            "100 Free": "100 Freestyle",
            "200 Free": "200 Freestyle",
            "500 Free": "500 Freestyle",
            "100 Back": "100 Backstroke",
            "100 Breast": "100 Breaststroke",
            "100 Fly": "100 Butterfly",
            "200 IM": "200 Individual Medley",
        }

        # Check for Boys/Girls prefix and normalize
        for short, full in mappings.items():
            if short in event:
                prefix = ""
                if "Boys" in event or "Men" in event:
                    prefix = "Boys "
                elif "Girls" in event or "Women" in event:
                    prefix = "Girls "
                return prefix + full

        return event


# ============================================================================
# SINGLETON INSTANCE
# ============================================================================

_data_service: UnifiedDataService | None = None


def get_data_service() -> UnifiedDataService:
    """Get singleton data service instance."""
    global _data_service
    if _data_service is None:
        _data_service = UnifiedDataService()
    return _data_service


# ============================================================================
# CLI INTERFACE
# ============================================================================

if __name__ == "__main__":
    service = get_data_service()

    print("=== Unified Data Service ===\n")

    # Check sources
    print("Data Sources:")
    for status in DataSourceRegistry.check_sources():
        icon = "✓ " if status.available else ""
        print(f"{icon} {status.name}: {status.record_count} files")

    print("\nAvailable Teams:", service.get_all_teams())

    # Validate
    print("\nValidation:")
    result = service.validate_data_integrity()
    print(f"Teams: {result['stats']['total_teams']}")
    print(f"Entries: {result['stats']['total_entries']}")
    print(f"Missing grades: {result['stats']['missing_grades']}")

    if result["issues"]:
        print("\nIssues:")
        for issue in result["issues"]:
            print(f"! {issue}")
