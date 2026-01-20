"""
Swim Data Service - High-level API for Championship Module integration.

This service provides a clean interface for accessing swim data,
suitable for use by the Championship Module and other AquaForge components.

Usage:
    from swim_ai_reflex.core.data import SwimDataService

    service = SwimDataService.from_csv('data/real_exports/csv')
    roster = await service.get_current_roster()
    best_times = await service.get_best_times_report(['100 Free', '200 IM'])
"""

from __future__ import annotations

import asyncio
from datetime import date
from pathlib import Path
from typing import TYPE_CHECKING

from swim_ai_reflex.core.data.entities import (
    AthleteEntity,
    MeetEntity,
    SwimResultEntity,
)
from swim_ai_reflex.core.data.loaders.csv_loader import CSVLoader
from swim_ai_reflex.core.data.repository.base import (
    InMemoryRepository,
    SwimDataRepository,
)

if TYPE_CHECKING:
    pass  # Future: SwimmerTime, SwimmerProfile for domain model integration


# Map event names to (distance, stroke) tuples
# Stroke codes: 1=Free, 2=Back, 3=Breast, 4=Fly, 5=IM
EVENT_MAP = {
    # Individual Freestyle
    "50 Free": (50, 1),
    "100 Free": (100, 1),
    "200 Free": (200, 1),
    "500 Free": (500, 1),
    "1000 Free": (1000, 1),
    "1650 Free": (1650, 1),
    # Backstroke
    "100 Back": (100, 2),
    "200 Back": (200, 2),
    # Breaststroke
    "100 Breast": (100, 3),
    "200 Breast": (200, 3),
    # Butterfly
    "100 Fly": (100, 4),
    "200 Fly": (200, 4),
    # Individual Medley
    "200 IM": (200, 5),
    "400 IM": (400, 5),
    # Relays (distance is total, stroke 1=Free, 5=Medley)
    "200 Free Relay": (200, 1),
    "400 Free Relay": (400, 1),
    "200 Medley Relay": (200, 5),
    "400 Medley Relay": (400, 5),
}


class SwimDataService:
    """
    High-level service for accessing swim data.

    This service abstracts the data layer complexity and provides
    championship-specific queries for the AquaForge modules.
    """

    def __init__(self, repository: SwimDataRepository):
        """Initialize with a repository instance."""
        self._repo = repository
        self._current_season: str | None = None

    @classmethod
    def from_csv(cls, csv_path: str | Path) -> "SwimDataService":
        """
        Create service from CSV data directory.

        This is a synchronous factory method that loads all data
        into an in-memory repository.

        Raises:
            FileNotFoundError: If csv_path does not exist
            RuntimeError: If data loading fails
        """
        path = Path(csv_path)
        if not path.exists():
            raise FileNotFoundError(f"CSV data directory not found: {path}")

        loader = CSVLoader(path)
        repo = InMemoryRepository()

        async def load():
            await repo.save_teams(loader.load_teams())
            await repo.save_athletes(loader.load_athletes())
            await repo.save_meets(loader.load_meets())

            # Batch load results for performance
            results = list(loader.load_results())
            await repo.save_results(results)

            relays = list(loader.load_relays())
            await repo.save_relays(relays)

            splits = list(loader.load_splits())
            await repo.save_splits(splits)

        # Use asyncio.run() for Python 3.10+ compatibility
        # This creates a new event loop, runs the coroutine, and closes it
        try:
            asyncio.run(load())
        except RuntimeError:
            # Already running in an async context - use nested approach
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(load())
            finally:
                loop.close()

        service = cls(repo)
        service._loader = loader  # Keep for diagnostics
        return service

    @property
    def current_season(self) -> str:
        """Get current season string (e.g., '2025-2026')."""
        if self._current_season:
            return self._current_season

        today = date.today()
        year = today.year
        month = today.month
        if month >= 8:
            return f"{year}-{year + 1}"
        return f"{year - 1}-{year}"

    # =========================================================================
    # Roster Queries
    # =========================================================================

    async def get_current_roster(
        self, team_id: int = 1, active_only: bool = True
    ) -> list[AthleteEntity]:
        """
        Get active swimmers for a team.

        Args:
            team_id: Team ID (default 1 = Seton)
            active_only: Exclude inactive swimmers

        Returns:
            List of athletes
        """
        return await self._repo.get_roster(team_id=team_id, active_only=active_only)

    async def get_athlete(self, athlete_id: int) -> AthleteEntity | None:
        """Get athlete by ID."""
        return await self._repo.get_athlete(athlete_id)

    async def search_athletes(
        self, name: str | None = None, grade: str | None = None
    ) -> list[AthleteEntity]:
        """Search athletes by name or grade."""
        return await self._repo.search_athletes(name=name, grade=grade)

    # =========================================================================
    # Best Times
    # =========================================================================

    async def get_best_time(
        self, athlete_id: int, event: str
    ) -> SwimResultEntity | None:
        """
        Get athlete's best time for a specific event.

        Args:
            athlete_id: Athlete ID
            event: Event name (e.g., '100 Free')

        Returns:
            Best result or None
        """
        if event not in EVENT_MAP:
            return None

        distance, stroke = EVENT_MAP[event]
        return await self._repo.get_best_time(athlete_id, distance, stroke)

    async def get_best_times_report(
        self,
        events: list[str] | None = None,
        team_id: int = 1,
        limit_per_event: int = 10,
    ) -> dict[str, list[tuple[AthleteEntity, SwimResultEntity]]]:
        """
        Get ranked best times for multiple events.

        Args:
            events: List of event names (defaults to all standard events)
            team_id: Filter to team
            limit_per_event: Max swimmers per event

        Returns:
            Dictionary mapping event name to list of (athlete, result) tuples
        """
        if events is None:
            events = list(EVENT_MAP.keys())

        report: dict[str, list[tuple[AthleteEntity, SwimResultEntity]]] = {}

        for event in events:
            if event not in EVENT_MAP:
                continue

            distance, stroke = EVENT_MAP[event]
            results = await self._repo.get_best_times_by_event(
                distance, stroke, team_id=team_id, limit=limit_per_event
            )

            # Attach athlete info
            event_data = []
            for result in results:
                athlete = await self._repo.get_athlete(result.athlete_id)
                if athlete:
                    event_data.append((athlete, result))

            report[event] = event_data

        return report

    async def get_athlete_best_times(
        self, athlete_id: int, events: list[str] | None = None
    ) -> dict[str, SwimResultEntity]:
        """
        Get all best times for a single athlete.

        Args:
            athlete_id: Athlete ID
            events: Specific events (defaults to all)

        Returns:
            Dictionary mapping event name to best result
        """
        if events is None:
            events = list(EVENT_MAP.keys())

        best_times: dict[str, SwimResultEntity] = {}

        for event in events:
            result = await self.get_best_time(athlete_id, event)
            if result:
                best_times[event] = result

        return best_times

    # =========================================================================
    # Meet Data
    # =========================================================================

    async def get_meet(self, meet_id: int) -> MeetEntity | None:
        """Get meet by ID."""
        return await self._repo.get_meet(meet_id)

    async def get_season_meets(self, season: str | None = None) -> list[MeetEntity]:
        """
        Get all meets for a season.

        Args:
            season: Season string (e.g., '2025-2026'), defaults to current

        Returns:
            List of meets sorted by date
        """
        if season is None:
            season = self.current_season

        meets = await self._repo.get_meets_by_season(season)
        return sorted(meets, key=lambda m: m.start_date)

    async def get_recent_meets(self, limit: int = 10) -> list[MeetEntity]:
        """Get most recent meets."""
        return await self._repo.get_recent_meets(limit)

    # =========================================================================
    # Statistics
    # =========================================================================

    async def get_summary(self) -> dict:
        """
        Get data summary statistics.

        Returns:
            Dictionary with counts and metadata
        """
        teams = await self._repo.list_teams()
        athletes = await self._repo.get_roster(team_id=1, active_only=False)
        active = [a for a in athletes if not a.inactive]
        recent_meets = await self._repo.get_recent_meets(limit=1)

        return {
            "teams": len(teams),
            "athletes_total": len(athletes),
            "athletes_active": len(active),
            "current_season": self.current_season,
            "last_meet": recent_meets[0].name if recent_meets else None,
        }


# Convenience function for quick access
def load_swim_data(csv_path: str | Path = "data/real_exports/csv") -> SwimDataService:
    """
    Quick loader for swim data service.

    Usage:
        service = load_swim_data()
        roster = asyncio.run(service.get_current_roster())
    """
    return SwimDataService.from_csv(csv_path)
