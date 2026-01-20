"""
HY3 File Parser - Parse Hy-Tek HY3 format for championship data.

HY3 is a fixed-width format used by Hy-Tek Meet Manager to exchange meet results.
This parser extracts teams, athletes, individual results, relay results, and splits.

Record Types:
- A1: File header
- B1/B2: Meet info
- C1/C2: Team info
- D1: Athlete info
- E1/E2: Individual event results
- F1/F2/F3: Relay results
- G1: Splits
- H1/H2: DQ codes

Usage:
    from swim_ai_reflex.core.data.loaders.hy3_loader import HY3Loader

    loader = HY3Loader("results.hy3")
    meet = loader.parse()

    for team in meet.teams:
        print(f"{team.code}: {team.name}")
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Generator


# =============================================================================
# Data Classes for HY3 Content
# =============================================================================


@dataclass
class HY3MeetInfo:
    """Meet header information from B1/B2 records."""

    name: str
    facility: str
    start_date: date
    end_date: date | None = None
    course: str = "Y"

    @property
    def season(self) -> str:
        """Calculate season string (e.g., '2025-2026')."""
        year = self.start_date.year
        month = self.start_date.month
        if month >= 8:
            return f"{year}-{year + 1}"
        return f"{year - 1}-{year}"


@dataclass
class HY3Team:
    """Team information from C1/C2 records."""

    code: str
    name: str
    short_name: str
    state: str = ""

    def __hash__(self):
        return hash(self.code)


@dataclass
class HY3Athlete:
    """Athlete information from D1 records."""

    athlete_id: str
    last_name: str
    first_name: str
    sex: str  # M or F
    team_code: str
    birth_date: date | None = None
    age: int = 0
    grade: str = ""

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"


@dataclass
class HY3IndividualResult:
    """Individual event result from E1/E2 records."""

    athlete_id: str
    event_code: str
    distance: int
    stroke: int
    seed_time: float  # in seconds
    final_time: float  # in seconds
    place: int = 0
    points: float = 0.0
    is_exhibition: bool = False
    is_dq: bool = False
    dq_code: str = ""
    heat: int = 0
    lane: int = 0

    # Stroke mapping
    STROKE_MAP = {
        "A": 1,  # Freestyle
        "B": 2,  # Backstroke
        "C": 3,  # Breaststroke
        "D": 4,  # Butterfly
        "E": 5,  # IM
    }

    STROKE_NAMES = {
        1: "Free",
        2: "Back",
        3: "Breast",
        4: "Fly",
        5: "IM",
    }

    @property
    def event_name(self) -> str:
        stroke_name = self.STROKE_NAMES.get(self.stroke, "Unknown")
        return f"{self.distance} {stroke_name}"

    @property
    def formatted_time(self) -> str:
        if self.final_time <= 0:
            return "NT"
        if self.final_time >= 60:
            mins = int(self.final_time // 60)
            secs = self.final_time % 60
            return f"{mins}:{secs:05.2f}"
        return f"{self.final_time:.2f}"


@dataclass
class HY3RelayResult:
    """Relay result from F1/F2/F3 records."""

    team_code: str
    letter: str  # A, B, C, etc.
    event_code: str
    distance: int
    stroke: int  # 1=Free relay, 5=Medley relay
    seed_time: float
    final_time: float
    place: int = 0
    points: float = 0.0
    swimmers: list[str] = field(default_factory=list)
    is_dq: bool = False

    @property
    def event_name(self) -> str:
        if self.stroke == 5:
            return f"{self.distance} Medley Relay"
        return f"{self.distance} Free Relay"


@dataclass
class HY3Split:
    """Split time from G1 records."""

    athlete_id: str
    split_number: int
    cumulative_time: float


@dataclass
class HY3ParsedMeet:
    """Complete parsed HY3 file."""

    meet_info: HY3MeetInfo
    teams: list[HY3Team]
    athletes: list[HY3Athlete]
    individual_results: list[HY3IndividualResult]
    relay_results: list[HY3RelayResult]
    splits: list[HY3Split]

    def get_team_results(self, team_code: str) -> list[HY3IndividualResult]:
        """Get all results for a team."""
        team_athletes = {
            a.athlete_id for a in self.athletes if a.team_code == team_code
        }
        return [r for r in self.individual_results if r.athlete_id in team_athletes]

    def get_athlete_results(self, athlete_id: str) -> list[HY3IndividualResult]:
        """Get all results for an athlete."""
        return [r for r in self.individual_results if r.athlete_id == athlete_id]

    def get_team_points(self) -> dict[str, float]:
        """Calculate total points per team."""
        points = {}
        for team in self.teams:
            team_athletes = {
                a.athlete_id for a in self.athletes if a.team_code == team.code
            }
            individual_pts = sum(
                r.points
                for r in self.individual_results
                if r.athlete_id in team_athletes and not r.is_exhibition
            )
            relay_pts = sum(
                r.points for r in self.relay_results if r.team_code == team.code
            )
            points[team.code] = individual_pts + relay_pts
        return points


# =============================================================================
# HY3 Parser
# =============================================================================


class HY3Loader:
    """
    Parse HY3 files exported from Hy-Tek Meet Manager.

    The HY3 format uses fixed-width columns with record type codes.
    """

    def __init__(self, file_path: str | Path):
        self.file_path = Path(file_path)
        self._lines: list[str] = []
        self._current_athlete_id: str = ""
        self._current_team_code: str = ""

    def parse(self) -> HY3ParsedMeet:
        """Parse the HY3 file and return structured data."""
        self._load_file()

        meet_info = self._parse_meet_info()
        teams = list(self._parse_teams())
        athletes = list(self._parse_athletes())
        individual_results = list(self._parse_individual_results())
        relay_results = list(self._parse_relay_results())
        splits = list(self._parse_splits())

        return HY3ParsedMeet(
            meet_info=meet_info,
            teams=teams,
            athletes=athletes,
            individual_results=individual_results,
            relay_results=relay_results,
            splits=splits,
        )

    def _load_file(self) -> None:
        """Load file content."""
        with open(self.file_path, "r", encoding="utf-8", errors="replace") as f:
            self._lines = f.readlines()

    def _parse_meet_info(self) -> HY3MeetInfo:
        """Parse B1/B2 records for meet info."""
        name = ""
        facility = ""
        start_date = date.today()
        course = "Y"

        for line in self._lines:
            if line.startswith("B1"):
                # B1: Meet name (2-50), Facility (50-90), Date at position 90-98
                # Example: B12026 NoVa Catholic Invitational Championship Freedom Aquatic...011020260110202611012025
                name = line[2:50].strip()
                facility = line[50:90].strip()
                # Date is MMDDYYYY format around position 90
                date_str = line[90:98].strip() if len(line) > 98 else ""
                if len(date_str) == 8:
                    try:
                        start_date = datetime.strptime(date_str, "%m%d%Y").date()
                    except ValueError:
                        pass
                break

        for line in self._lines:
            if line.startswith("B2"):
                # B2: Course is typically at position 66
                course_char = line[66:67].strip() if len(line) > 66 else "Y"
                if course_char in ("Y", "S", "L"):
                    course = course_char
                break

        return HY3MeetInfo(
            name=name,
            facility=facility,
            start_date=start_date,
            course=course,
        )

    def _parse_teams(self) -> Generator[HY3Team, None, None]:
        """Parse C1 records for team info."""
        for line in self._lines:
            if line.startswith("C1"):
                # C1: Code (2-6), Name (6-36), Short (36-52), State (52-54)
                code = line[2:6].strip()
                name = line[6:36].strip()
                short_name = line[36:52].strip()
                state = line[52:54].strip() if len(line) > 54 else ""

                if code:
                    yield HY3Team(
                        code=code,
                        name=name,
                        short_name=short_name,
                        state=state,
                    )

    def _parse_athletes(self) -> Generator[HY3Athlete, None, None]:
        """Parse D1 records for athlete info."""
        current_team = ""

        for line in self._lines:
            # Track current team from C1 records
            if line.startswith("C1"):
                current_team = line[2:6].strip()
                continue

            if line.startswith("D1"):
                # D1: Sex (2), ID (3-8), Last (8-28), First (28-48)
                # Age is at ~93-95, Grade at ~95-97
                sex = line[2:3]
                athlete_id = line[3:8].strip()
                last_name = line[8:28].strip()
                first_name = line[28:48].strip()

                # Parse birth date (position ~72-80, format MMDDYYYY)
                birth_date = None
                try:
                    birth_str = line[72:80].strip()
                    if birth_str and len(birth_str) == 8:
                        birth_date = datetime.strptime(birth_str, "%m%d%Y").date()
                except (ValueError, IndexError):
                    pass

                # Parse age (position 81-83)
                age = 0
                try:
                    age = int(line[81:83].strip())
                except (ValueError, IndexError):
                    pass

                # Parse grade (position 83-85)
                grade = ""
                try:
                    grade = line[83:85].strip()
                except IndexError:
                    pass

                if athlete_id and last_name:
                    yield HY3Athlete(
                        athlete_id=athlete_id,
                        last_name=last_name,
                        first_name=first_name,
                        sex=sex,
                        team_code=current_team,
                        birth_date=birth_date,
                        age=age,
                        grade=grade,
                    )

    def _parse_individual_results(self) -> Generator[HY3IndividualResult, None, None]:
        """Parse E1/E2 record pairs for individual results."""
        e1_data = {}

        for line in self._lines:
            if line.startswith("E1"):
                # E1 Format (from analysis):
                # [0-2]: E1M (record type + sex)
                # [3-8]: Athlete ID (e.g., " 5743")
                # [8-13]: Short name (e.g., "Amice")
                # [13-18]: Team code + event letter (e.g., "MB   ")
                # [18-21]: Distance (e.g., " 50")
                # [21-22]: Stroke code (A=Free, B=Back, C=Breast, D=Fly, E=IM)
                # [40-48]: Seed time (e.g., "  28.58Y")
                # [48-56]: Entry time
                line[2:3]
                athlete_id = line[3:8].strip()

                # Parse distance from position 18-21
                try:
                    distance = int(line[18:21].strip())
                except (ValueError, IndexError):
                    distance = 0

                # Stroke code at position 21
                stroke_code = line[21:22] if len(line) > 21 else "A"
                stroke = HY3IndividualResult.STROKE_MAP.get(stroke_code, 1)

                # Parse times - seed time at ~40-48
                seed_time = self._parse_time(line[40:48].strip())
                entry_time = self._parse_time(line[48:56].strip())

                # Exhibition flag - look for 'X' in the line after times
                is_exhibition = "X" in line[75:85]

                # Store for pairing with E2
                e1_data[athlete_id] = {
                    "distance": distance,
                    "stroke": stroke,
                    "seed_time": seed_time,
                    "entry_time": entry_time,
                    "is_exhibition": is_exhibition,
                    "event_code": f"{distance}{stroke_code}",
                }

            elif line.startswith("E2") and e1_data:
                # E2 Format (from analysis):
                # [3-11]: Final time (e.g., "  30.21Y")
                # [11-12]: Exhibition X marker
                # [17-19]: Heat
                # [19-21]: Lane
                # [21-23]: Place
                # [23-27]: Points
                # Get last athlete's data
                if e1_data:
                    last_id = list(e1_data.keys())[-1]
                    data = e1_data[last_id]

                    # Final time from E2
                    final_time_str = line[3:11].strip()
                    final_time = (
                        self._parse_time(final_time_str) if final_time_str else 0.0
                    )

                    # Exhibition from E2
                    is_exhibition = line[11:12].strip() == "X" or data["is_exhibition"]

                    # Parse place from E2 (around position 21-23)
                    try:
                        place = int(line[21:23].strip()) if line[21:23].strip() else 0
                    except (ValueError, IndexError):
                        place = 0

                    # Parse points from E2 (around position 23-27)
                    try:
                        points = (
                            float(line[23:27].strip()) if line[23:27].strip() else 0.0
                        )
                    except (ValueError, IndexError):
                        points = 0.0

                    yield HY3IndividualResult(
                        athlete_id=last_id,
                        event_code=data["event_code"],
                        distance=data["distance"],
                        stroke=data["stroke"],
                        seed_time=data["seed_time"],
                        final_time=final_time,
                        place=place,
                        points=points,
                        is_exhibition=is_exhibition,
                    )

                    # Clear processed data
                    del e1_data[last_id]

    def _parse_relay_results(self) -> Generator[HY3RelayResult, None, None]:
        """Parse F1/F2/F3 records for relay results."""
        current_relay = {}

        for line in self._lines:
            if line.startswith("F1"):
                # F1: Team (2-6), Letter (6-7), Event info, times
                team_code = line[2:6].strip()
                letter = line[6:7].strip()

                # Distance at ~19-22
                try:
                    distance = int(line[19:22].strip())
                except (ValueError, IndexError):
                    distance = 200

                # Stroke code at ~22-23
                stroke_code = line[22:23] if len(line) > 22 else "A"
                stroke = 5 if stroke_code == "E" else 1  # Medley or Free

                # Times
                seed_time = self._parse_time(line[40:48].strip())
                final_time = self._parse_time(line[48:56].strip())

                current_relay = {
                    "team_code": team_code,
                    "letter": letter,
                    "distance": distance,
                    "stroke": stroke,
                    "seed_time": seed_time,
                    "final_time": final_time,
                    "event_code": line[13:24].strip(),
                }

            elif line.startswith("F2") and current_relay:
                # F2: Final time (3-11), Place (22-24), Points (25-28)
                final_time_str = line[3:11].strip()

                try:
                    place = int(line[22:25].strip()) if line[22:25].strip() else 0
                except (ValueError, IndexError):
                    place = 0

                try:
                    points = float(line[25:29].strip()) if line[25:29].strip() else 0.0
                except (ValueError, IndexError):
                    points = 0.0

                if final_time_str:
                    current_relay["final_time"] = self._parse_time(final_time_str)
                current_relay["place"] = place
                current_relay["points"] = points

            elif line.startswith("F3") and current_relay:
                # F3: Swimmer IDs (4 swimmers at positions 2-7, 9-14, 16-21, 23-28)
                swimmers = []
                for pos in [(2, 7), (9, 14), (16, 21), (23, 28)]:
                    try:
                        swimmer_id = line[pos[0] : pos[1]].strip()
                        if swimmer_id:
                            # Extract just the ID (may have prefix)
                            swimmer_id = swimmer_id.replace("F", "").replace("M", "")[
                                :5
                            ]
                            if swimmer_id.isdigit():
                                swimmers.append(swimmer_id)
                    except IndexError:
                        pass

                yield HY3RelayResult(
                    team_code=current_relay["team_code"],
                    letter=current_relay["letter"],
                    event_code=current_relay.get("event_code", ""),
                    distance=current_relay["distance"],
                    stroke=current_relay["stroke"],
                    seed_time=current_relay["seed_time"],
                    final_time=current_relay["final_time"],
                    place=current_relay.get("place", 0),
                    points=current_relay.get("points", 0.0),
                    swimmers=swimmers,
                )
                current_relay = {}

    def _parse_splits(self) -> Generator[HY3Split, None, None]:
        """Parse G1 records for split times."""
        # G1 records are more complex - simplified for now
        for line in self._lines:
            if line.startswith("G1"):
                # G1: Split number (2-3), Time (4-10), etc.
                # Multiple splits per line
                # Format: G1F 2   32.10F 4   68.63
                try:
                    # Parse first split
                    split_num = int(line[3:5].strip())
                    split_time = self._parse_time(line[5:12].strip())

                    if split_num > 0 and split_time > 0:
                        yield HY3Split(
                            athlete_id="",  # Would need to track from previous E1
                            split_number=split_num,
                            cumulative_time=split_time,
                        )
                except (ValueError, IndexError):
                    pass

    def _parse_time(self, time_str: str) -> float:
        """Parse time string to seconds."""
        if not time_str or time_str == "NT" or time_str == "0.00":
            return 0.0

        time_str = time_str.strip().rstrip("Y").rstrip("S").rstrip("L")

        try:
            if ":" in time_str:
                parts = time_str.split(":")
                return float(parts[0]) * 60 + float(parts[1])
            return float(time_str)
        except (ValueError, IndexError):
            return 0.0


# =============================================================================
# Convenience Function
# =============================================================================


def load_hy3(file_path: str | Path) -> HY3ParsedMeet:
    """Quick loader for HY3 files."""
    loader = HY3Loader(file_path)
    return loader.parse()
