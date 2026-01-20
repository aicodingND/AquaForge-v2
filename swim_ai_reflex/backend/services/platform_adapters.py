"""
Platform Adapters for External Swimming Data Sources

Future-proofed adapters for major swimming platforms:
- SwimCloud (primary - most data available)
- USA Swimming SWIMS Database
- MeetMobile / Active.com
- Hy-Tek Meet Manager exports
- CollectiveSwim
- Swimtopia

Each adapter normalizes data to common SwimmerTime/TeamData contracts.
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Protocol

logger = logging.getLogger(__name__)


# ============================================================================
# PLATFORM ENUM
# ============================================================================


class SwimPlatform(str, Enum):
    """Supported swimming data platforms."""

    SWIMCLOUD = "swimcloud"
    USA_SWIMMING = "usa_swimming"
    MEET_MOBILE = "meet_mobile"
    HY_TEK = "hy_tek"
    COLLECTIVE_SWIM = "collective_swim"
    SWIMTOPIA = "swimtopia"
    MANUAL = "manual"


# ============================================================================
# UNIVERSAL DATA SCHEMA
# ============================================================================


@dataclass
class UniversalSwimEntry:
    """
    Universal swim entry - normalized format for all platforms.

    This schema is designed to be extensible and capture all relevant
    data from any swimming platform while maintaining a consistent API.
    """

    # Core identifiers
    swimmer_id: Optional[str] = None  # Platform-specific ID
    swimmer_name: str = ""
    team_code: str = ""
    team_name: str = ""

    # Event data
    event_name: str = ""  # Normalized: "100 Freestyle"
    event_code: Optional[str] = None  # Platform-specific: "100FR"
    distance: Optional[int] = None  # In yards/meters
    stroke: Optional[str] = None  # "Freestyle", "Backstroke", etc.
    course: str = "SCY"  # SCY, SCM, LCM

    # Time data
    time_seconds: float = 9999.99
    time_display: str = "NT"
    time_type: str = "seed"  # seed, prelim, final, split

    # Swimmer metadata
    age: Optional[int] = None
    birth_year: Optional[int] = None
    grade: Optional[int] = None
    gender: Optional[str] = None  # M, F
    class_year: Optional[str] = None  # FR, SO, JR, SR

    # Scoring eligibility
    is_exhibition: bool = False
    scoring_eligible: bool = True

    # Source tracking
    platform: str = "unknown"
    source_url: Optional[str] = None
    scraped_at: Optional[str] = None
    meet_name: Optional[str] = None
    meet_date: Optional[str] = None

    # Custom fields for platform-specific data
    extra: Optional[Dict[str, Any]] = None


@dataclass
class UniversalMeetEntry:
    """Universal meet/competition data."""

    meet_id: Optional[str] = None
    meet_name: str = ""
    meet_date: Optional[str] = None
    location: str = ""
    course: str = "SCY"
    sanctioning_body: Optional[str] = None  # "USA Swimming", "VISAA", etc.
    platform: str = "unknown"


# ============================================================================
# ADAPTER PROTOCOL
# ============================================================================


class PlatformAdapter(Protocol):
    """Protocol for platform adapters."""

    platform: SwimPlatform

    def parse_roster(self, raw_data: Dict) -> List[UniversalSwimEntry]:
        """Parse roster data from platform."""
        ...

    def parse_meet_results(self, raw_data: Dict) -> List[UniversalSwimEntry]:
        """Parse meet results from platform."""
        ...

    def normalize_event_name(self, event: str) -> str:
        """Normalize event name to universal format."""
        ...

    def normalize_time(self, time_input: Any) -> tuple[float, str]:
        """Normalize time to (seconds, display_str)."""
        ...


# ============================================================================
# BASE ADAPTER
# ============================================================================


class BaseAdapter(ABC):
    """Base adapter with common functionality."""

    # Standard event name mappings
    EVENT_MAPPINGS = {
        # Freestyle
        "50 FREE": "50 Freestyle",
        "50 FR": "50 Freestyle",
        "100 FREE": "100 Freestyle",
        "100 FR": "100 Freestyle",
        "200 FREE": "200 Freestyle",
        "200 FR": "200 Freestyle",
        "500 FREE": "500 Freestyle",
        "500 FR": "500 Freestyle",
        "1000 FREE": "1000 Freestyle",
        "1650 FREE": "1650 Freestyle",
        # Backstroke
        "100 BACK": "100 Backstroke",
        "100 BK": "100 Backstroke",
        "200 BACK": "200 Backstroke",
        # Breaststroke
        "100 BREAST": "100 Breaststroke",
        "100 BR": "100 Breaststroke",
        "200 BREAST": "200 Breaststroke",
        # Butterfly
        "100 FLY": "100 Butterfly",
        "100 FL": "100 Butterfly",
        "200 FLY": "200 Butterfly",
        # IM
        "200 IM": "200 Individual Medley",
        "400 IM": "400 Individual Medley",
        # Relays
        "200 FREE RELAY": "200 Freestyle Relay",
        "200 FR REL": "200 Freestyle Relay",
        "400 FREE RELAY": "400 Freestyle Relay",
        "400 FR REL": "400 Freestyle Relay",
        "200 MEDLEY RELAY": "200 Medley Relay",
        "200 MED REL": "200 Medley Relay",
    }

    GRADE_MAPPINGS = {
        "FR": 9,
        "SO": 10,
        "JR": 11,
        "SR": 12,
        "FRESHMAN": 9,
        "SOPHOMORE": 10,
        "JUNIOR": 11,
        "SENIOR": 12,
    }

    @abstractmethod
    def parse_roster(self, raw_data: Dict) -> List[UniversalSwimEntry]:
        """Parse roster data from platform."""
        pass

    @abstractmethod
    def parse_meet_results(self, raw_data: Dict) -> List[UniversalSwimEntry]:
        """Parse meet results from platform."""
        pass

    def normalize_event_name(self, event: str) -> str:
        """Normalize event name to universal format."""
        if not event:
            return ""

        event_upper = event.upper().strip()

        # Remove gender prefix for lookup
        for prefix in ["BOYS ", "GIRLS ", "MEN ", "WOMEN ", "MENS ", "WOMENS "]:
            if event_upper.startswith(prefix):
                event_upper = event_upper[len(prefix) :]
                break

        # Lookup in mappings
        normalized = self.EVENT_MAPPINGS.get(event_upper, event)

        # Add back gender prefix if present in original
        if "boys" in event.lower() or "men" in event.lower():
            normalized = f"Boys {normalized}"
        elif "girls" in event.lower() or "women" in event.lower():
            normalized = f"Girls {normalized}"

        return normalized

    def normalize_time(self, time_input: Any) -> tuple[float, str]:
        """Convert any time format to (seconds, display_str)."""
        if time_input is None:
            return 9999.99, "NT"

        if isinstance(time_input, (int, float)):
            seconds = float(time_input)
            return seconds, self._seconds_to_display(seconds)

        time_str = str(time_input).strip().upper()
        if time_str in ("NT", "NS", "DQ", "SCR", "", "X"):
            return 9999.99, time_str or "NT"

        try:
            if ":" in time_str:
                parts = time_str.split(":")
                if len(parts) == 2:
                    minutes = float(parts[0])
                    secs = float(parts[1])
                    seconds = minutes * 60 + secs
                    return seconds, time_str
            else:
                seconds = float(time_str)
                return seconds, self._seconds_to_display(seconds)
        except (ValueError, TypeError):
            logger.warning(f"Could not parse time: {time_input}")
            return 9999.99, "NT"

    def _seconds_to_display(self, seconds: float) -> str:
        """Convert seconds to display format."""
        if seconds >= 9999:
            return "NT"
        if seconds >= 60:
            mins = int(seconds // 60)
            secs = seconds % 60
            return f"{mins}:{secs:05.2f}"
        return f"{seconds:.2f}"

    def infer_grade(self, class_year: Optional[str]) -> Optional[int]:
        """Infer numeric grade from class year."""
        if class_year is None:
            return None

        cy = str(class_year).upper().strip()

        # Direct numeric
        if cy.isdigit():
            return int(cy)

        return self.GRADE_MAPPINGS.get(cy)


# ============================================================================
# SWIMCLOUD ADAPTER
# ============================================================================


class SwimCloudAdapter(BaseAdapter):
    """Adapter for SwimCloud data format."""

    platform = SwimPlatform.SWIMCLOUD

    def parse_roster(self, raw_data: Dict) -> List[UniversalSwimEntry]:
        """Parse SwimCloud roster/times JSON."""
        entries = []

        team_code = raw_data.get("team_code", "")
        team_name = raw_data.get("team_name", "")
        scraped_at = raw_data.get("scraped_at")

        for time_entry in raw_data.get("times", []):
            time_val = time_entry.get("seed_time") or time_entry.get("time")
            seconds, display = self.normalize_time(time_val)

            # Infer grade from roster if available
            swimmer_name = time_entry.get("swimmer_name", "")
            class_year = None
            for roster_entry in raw_data.get("roster", []):
                if roster_entry.get("name") == swimmer_name:
                    class_year = roster_entry.get("classYear")
                    break

            entries.append(
                UniversalSwimEntry(
                    swimmer_name=swimmer_name,
                    team_code=team_code,
                    team_name=team_name,
                    event_name=self.normalize_event_name(time_entry.get("event", "")),
                    time_seconds=seconds,
                    time_display=display,
                    gender=time_entry.get("gender"),
                    class_year=class_year,
                    grade=self.infer_grade(class_year),
                    platform=self.platform.value,
                    scraped_at=scraped_at,
                )
            )

        return entries

    def parse_meet_results(self, raw_data: Dict) -> List[UniversalSwimEntry]:
        """Parse SwimCloud meet results."""
        # Similar to roster but with result-specific fields
        entries = self.parse_roster(raw_data)
        for entry in entries:
            entry.time_type = "final"
            entry.meet_name = raw_data.get("meet_name")
            entry.meet_date = raw_data.get("meet_date")
        return entries


# ============================================================================
# USA SWIMMING SWIMS ADAPTER
# ============================================================================


class USASwimmingAdapter(BaseAdapter):
    """Adapter for USA Swimming SWIMS database format."""

    platform = SwimPlatform.USA_SWIMMING

    def parse_roster(self, raw_data: Dict) -> List[UniversalSwimEntry]:
        """Parse USA Swimming SWIMS data."""
        entries = []

        for swimmer in raw_data.get("swimmers", []):
            swimmer_id = swimmer.get("member_id")
            swimmer_name = swimmer.get("full_name", "")

            for time_entry in swimmer.get("times", []):
                seconds, display = self.normalize_time(time_entry.get("time"))

                entries.append(
                    UniversalSwimEntry(
                        swimmer_id=swimmer_id,
                        swimmer_name=swimmer_name,
                        team_code=time_entry.get("club_code", ""),
                        event_name=self.normalize_event_name(time_entry.get("event")),
                        event_code=time_entry.get("event_code"),
                        distance=time_entry.get("distance"),
                        stroke=time_entry.get("stroke"),
                        course=time_entry.get("course", "SCY"),
                        time_seconds=seconds,
                        time_display=display,
                        time_type=time_entry.get("time_type", "seed"),
                        age=swimmer.get("age"),
                        birth_year=swimmer.get("birth_year"),
                        gender=swimmer.get("gender"),
                        platform=self.platform.value,
                        meet_name=time_entry.get("meet_name"),
                        meet_date=time_entry.get("meet_date"),
                    )
                )

        return entries

    def parse_meet_results(self, raw_data: Dict) -> List[UniversalSwimEntry]:
        """Parse USA Swimming meet results."""
        return self.parse_roster(raw_data)


# ============================================================================
# HY-TEK MEET MANAGER ADAPTER
# ============================================================================


class HyTekAdapter(BaseAdapter):
    """Adapter for Hy-Tek Meet Manager export formats (.cl2, .hy3, .hyv)."""

    platform = SwimPlatform.HY_TEK

    # Hy-Tek event codes
    HY_TEK_EVENTS = {
        "1": "50 Freestyle",
        "2": "100 Freestyle",
        "3": "200 Freestyle",
        "4": "500 Freestyle",
        "5": "1000 Freestyle",
        "6": "1650 Freestyle",
        "7": "100 Backstroke",
        "8": "200 Backstroke",
        "9": "100 Breaststroke",
        "10": "200 Breaststroke",
        "11": "100 Butterfly",
        "12": "200 Butterfly",
        "13": "200 Individual Medley",
        "14": "400 Individual Medley",
    }

    def parse_roster(self, raw_data: Dict) -> List[UniversalSwimEntry]:
        """Parse Hy-Tek export data."""
        entries = []

        for athlete in raw_data.get("athletes", []):
            for entry in athlete.get("entries", []):
                event_code = str(entry.get("event_code", ""))
                event_name = self.HY_TEK_EVENTS.get(
                    event_code, self.normalize_event_name(entry.get("event_name", ""))
                )

                seconds, display = self.normalize_time(entry.get("seed_time"))

                entries.append(
                    UniversalSwimEntry(
                        swimmer_name=f"{athlete.get('first_name', '')} {athlete.get('last_name', '')}".strip(),
                        team_code=athlete.get("team_code", ""),
                        team_name=athlete.get("team_name", ""),
                        event_name=event_name,
                        event_code=event_code,
                        time_seconds=seconds,
                        time_display=display,
                        age=athlete.get("age"),
                        gender=athlete.get("gender"),
                        platform=self.platform.value,
                    )
                )

        return entries

    def parse_meet_results(self, raw_data: Dict) -> List[UniversalSwimEntry]:
        """Parse Hy-Tek meet results."""
        return self.parse_roster(raw_data)


# ============================================================================
# ADAPTER FACTORY
# ============================================================================


class AdapterFactory:
    """Factory for creating platform adapters."""

    _adapters = {
        SwimPlatform.SWIMCLOUD: SwimCloudAdapter,
        SwimPlatform.USA_SWIMMING: USASwimmingAdapter,
        SwimPlatform.HY_TEK: HyTekAdapter,
    }

    @classmethod
    def get_adapter(cls, platform: SwimPlatform) -> BaseAdapter:
        """Get adapter for specified platform."""
        adapter_class = cls._adapters.get(platform)
        if not adapter_class:
            raise ValueError(f"No adapter available for platform: {platform}")
        return adapter_class()

    @classmethod
    def detect_platform(cls, raw_data: Dict) -> Optional[SwimPlatform]:
        """Auto-detect platform from data structure."""
        if "source" in raw_data:
            source = raw_data["source"].lower()
            if "swimcloud" in source:
                return SwimPlatform.SWIMCLOUD
            if "usa" in source or "swims" in source:
                return SwimPlatform.USA_SWIMMING

        # Detect by structure
        if "team_code" in raw_data and "times" in raw_data:
            return SwimPlatform.SWIMCLOUD

        if "athletes" in raw_data and "entries" in raw_data.get("athletes", [{}])[0]:
            return SwimPlatform.HY_TEK

        return None

    @classmethod
    def parse_auto(cls, raw_data: Dict) -> List[UniversalSwimEntry]:
        """Auto-detect platform and parse data."""
        platform = cls.detect_platform(raw_data)
        if platform is None:
            logger.warning(
                "Could not detect platform, using SwimCloud adapter as default"
            )
            platform = SwimPlatform.SWIMCLOUD

        adapter = cls.get_adapter(platform)
        return adapter.parse_roster(raw_data)
