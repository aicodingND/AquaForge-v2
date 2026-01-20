"""
Championship Meet Data Models

Data structures for multi-team championship meets like VCAC and VISAA State.
Used with the Point Projection Engine to calculate expected team standings.
"""

from dataclasses import dataclass
from datetime import date
from typing import List, Dict, Optional
from collections import defaultdict


@dataclass
class PsychSheetEntry:
    """
    Single swimmer-event entry from a psych sheet.

    Represents one row of a psych sheet: a swimmer's seed time for one event.
    """

    swimmer_name: str
    team: str
    event: str
    seed_time: float  # Time in seconds (e.g., 25.43 for 25.43s)
    seed_rank: int = 0  # Rank within this event (1 = fastest seed)
    grade: int = 12  # Grade level (8-12 for high school)
    gender: str = "M"  # "M" or "F"
    is_diving: bool = False
    dive_score: Optional[float] = None

    def __post_init__(self):
        """Normalize team name and detect diving events."""
        self.team = self.team.strip()
        self.event = self.event.strip()
        self.swimmer_name = self.swimmer_name.strip()

        # Auto-detect diving
        if "diving" in self.event.lower() or "dive" in self.event.lower():
            self.is_diving = True

    @property
    def formatted_time(self) -> str:
        """Return time as MM:SS.ss or SS.ss string."""
        if self.is_diving:
            return f"{self.dive_score:.2f}" if self.dive_score else "NS"
        if self.seed_time == float("inf"):
            return "NT"
        if self.seed_time >= 60:
            mins = int(self.seed_time // 60)
            secs = self.seed_time % 60
            return f"{mins}:{secs:05.2f}"
        return f"{self.seed_time:.2f}"


@dataclass
class MeetPsychSheet:
    """
    Complete psych sheet for a championship meet.

    Contains all entries for all teams and events, with helper methods
    for filtering and querying the data.
    """

    meet_name: str
    meet_date: date
    teams: List[str]
    entries: List[PsychSheetEntry]
    meet_profile: str = "vcac_championship"  # Rules profile to use

    def __post_init__(self):
        """Calculate seed ranks and normalize data."""
        self._calculate_ranks()

    def _calculate_ranks(self):
        """Calculate seed ranks for each event based on seed times."""
        # Group entries by event
        events: Dict[str, List[PsychSheetEntry]] = defaultdict(list)
        for entry in self.entries:
            events[entry.event].append(entry)

        # Sort each event and assign ranks
        for event_name, event_entries in events.items():
            # Diving sorts by score (descending), swimming by time (ascending)
            if event_entries and event_entries[0].is_diving:
                sorted_entries = sorted(
                    event_entries, key=lambda e: -(e.dive_score or 0)
                )
            else:
                sorted_entries = sorted(
                    event_entries,
                    key=lambda e: e.seed_time if e.seed_time != float("inf") else 9999,
                )

            for rank, entry in enumerate(sorted_entries, 1):
                entry.seed_rank = rank

    def get_event_entries(self, event: str) -> List[PsychSheetEntry]:
        """
        Get all entries for a specific event, sorted by seed time.

        Args:
            event: Event name (e.g., "Boys 50 Free")

        Returns:
            List of entries sorted by seed rank (1st = fastest)
        """
        return sorted(
            [e for e in self.entries if self._event_matches(e.event, event)],
            key=lambda x: x.seed_rank,
        )

    def get_team_entries(self, team: str) -> List[PsychSheetEntry]:
        """
        Get all entries for a specific team.

        Args:
            team: Team name (case insensitive)

        Returns:
            List of all entries for this team
        """
        team_lower = team.lower().strip()
        return [e for e in self.entries if e.team.lower().strip() == team_lower]

    def get_swimmer_entries(
        self, swimmer_name: str, team: str = None
    ) -> List[PsychSheetEntry]:
        """
        Get all entries for a specific swimmer.

        Args:
            swimmer_name: Swimmer's name
            team: Optional team name to disambiguate same names

        Returns:
            List of all events this swimmer is entered in
        """
        name_lower = swimmer_name.lower().strip()
        entries = [
            e for e in self.entries if e.swimmer_name.lower().strip() == name_lower
        ]
        if team:
            team_lower = team.lower().strip()
            entries = [e for e in entries if e.team.lower().strip() == team_lower]
        return entries

    def get_all_events(self) -> List[str]:
        """Get list of all unique events in the meet."""
        return list(set(e.event for e in self.entries))

    def get_individual_events(self) -> List[str]:
        """Get list of individual (non-relay) events."""
        return [
            event for event in self.get_all_events() if "relay" not in event.lower()
        ]

    def get_relay_events(self) -> List[str]:
        """Get list of relay events."""
        return [event for event in self.get_all_events() if "relay" in event.lower()]

    def _event_matches(self, event1: str, event2: str) -> bool:
        """Check if two event names match (fuzzy matching)."""
        # Normalize: lowercase, remove extra spaces
        e1 = " ".join(event1.lower().split())
        e2 = " ".join(event2.lower().split())
        return e1 == e2

    @classmethod
    def from_dict(cls, data: Dict) -> "MeetPsychSheet":
        """
        Create MeetPsychSheet from dictionary (e.g., loaded from JSON).

        Args:
            data: Dictionary with meet_name, meet_date, teams, entries

        Returns:
            MeetPsychSheet instance
        """
        entries = [
            PsychSheetEntry(
                swimmer_name=e["swimmer_name"],
                team=e["team"],
                event=e["event"],
                seed_time=e.get("seed_time", float("inf")),
                grade=e.get("grade", 12),
                gender=e.get("gender", "M"),
                is_diving=e.get("is_diving", False),
                dive_score=e.get("dive_score"),
            )
            for e in data.get("entries", [])
        ]

        return cls(
            meet_name=data["meet_name"],
            meet_date=date.fromisoformat(data["meet_date"])
            if isinstance(data["meet_date"], str)
            else data["meet_date"],
            teams=data.get("teams", list(set(e.team for e in entries))),
            entries=entries,
            meet_profile=data.get("meet_profile", "vcac_championship"),
        )

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "meet_name": self.meet_name,
            "meet_date": self.meet_date.isoformat(),
            "teams": self.teams,
            "meet_profile": self.meet_profile,
            "entries": [
                {
                    "swimmer_name": e.swimmer_name,
                    "team": e.team,
                    "event": e.event,
                    "seed_time": e.seed_time,
                    "seed_rank": e.seed_rank,
                    "grade": e.grade,
                    "gender": e.gender,
                    "is_diving": e.is_diving,
                    "dive_score": e.dive_score,
                }
                for e in self.entries
            ],
        }
