"""
Base Repository - Abstract interface for data persistence.

This follows the repository pattern for clean architecture:
- Business logic doesn't know about storage details
- Easy to swap DuckDB → PostgreSQL
- Testable with mock implementations

Future Extensions:
    - PostgreSQL for production multi-user access
    - Read replicas for heavy analytics
    - Caching layer with Redis
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from swim_ai_reflex.core.data.entities import (
        AthleteEntity,
        MeetEntity,
        RelayResultEntity,
        SplitEntity,
        SwimResultEntity,
        TeamEntity,
    )


class SwimDataRepository(ABC):
    """
    Abstract repository for swim data persistence.

    Implementations:
        - DuckDBRepository (analytics, development)
        - PostgresRepository (production, future)
    """

    # =========================================================================
    # Teams
    # =========================================================================

    @abstractmethod
    async def save_teams(self, teams: list[TeamEntity]) -> int:
        """Bulk save teams. Returns count saved."""
        pass

    @abstractmethod
    async def get_team(self, team_id: int) -> TeamEntity | None:
        """Get team by ID."""
        pass

    @abstractmethod
    async def get_team_by_code(self, code: str) -> TeamEntity | None:
        """Get team by code (e.g., 'SST')."""
        pass

    @abstractmethod
    async def list_teams(self) -> list[TeamEntity]:
        """List all teams."""
        pass

    # =========================================================================
    # Athletes
    # =========================================================================

    @abstractmethod
    async def save_athletes(self, athletes: list[AthleteEntity]) -> int:
        """Bulk save athletes. Returns count saved."""
        pass

    @abstractmethod
    async def get_athlete(self, athlete_id: int) -> AthleteEntity | None:
        """Get athlete by ID."""
        pass

    @abstractmethod
    async def search_athletes(
        self,
        name: str | None = None,
        team_id: int | None = None,
        grade: str | None = None,
        active_only: bool = True,
    ) -> list[AthleteEntity]:
        """Search athletes with filters."""
        pass

    @abstractmethod
    async def get_roster(
        self, team_id: int, active_only: bool = True
    ) -> list[AthleteEntity]:
        """Get team roster."""
        pass

    # =========================================================================
    # Meets
    # =========================================================================

    @abstractmethod
    async def save_meets(self, meets: list[MeetEntity]) -> int:
        """Bulk save meets. Returns count saved."""
        pass

    @abstractmethod
    async def get_meet(self, meet_id: int) -> MeetEntity | None:
        """Get meet by ID."""
        pass

    @abstractmethod
    async def get_meets_by_season(self, season: str) -> list[MeetEntity]:
        """Get all meets in a season (e.g., '2025-2026')."""
        pass

    @abstractmethod
    async def get_recent_meets(self, limit: int = 10) -> list[MeetEntity]:
        """Get most recent meets."""
        pass

    # =========================================================================
    # Results
    # =========================================================================

    @abstractmethod
    async def save_results(self, results: list[SwimResultEntity]) -> int:
        """Bulk save results. Returns count saved."""
        pass

    @abstractmethod
    async def get_athlete_results(
        self,
        athlete_id: int,
        event: str | None = None,
        season: str | None = None,
    ) -> list[SwimResultEntity]:
        """Get results for an athlete, optionally filtered."""
        pass

    @abstractmethod
    async def get_best_time(
        self, athlete_id: int, distance: int, stroke: int
    ) -> SwimResultEntity | None:
        """Get athlete's best time for an event."""
        pass

    @abstractmethod
    async def get_best_times_by_event(
        self,
        distance: int,
        stroke: int,
        team_id: int | None = None,
        limit: int = 20,
    ) -> list[SwimResultEntity]:
        """Get ranked best times for an event."""
        pass

    @abstractmethod
    async def get_meet_results(self, meet_id: int) -> list[SwimResultEntity]:
        """Get all results from a meet."""
        pass

    # =========================================================================
    # Relays
    # =========================================================================

    @abstractmethod
    async def save_relays(self, relays: list[RelayResultEntity]) -> int:
        """Bulk save relays. Returns count saved."""
        pass

    @abstractmethod
    async def get_relay_history(
        self, athlete_id: int, season: str | None = None
    ) -> list[RelayResultEntity]:
        """Get relay participation for an athlete."""
        pass

    # =========================================================================
    # Splits
    # =========================================================================

    @abstractmethod
    async def save_splits(self, splits: list[SplitEntity]) -> int:
        """Bulk save splits. Returns count saved."""
        pass

    # =========================================================================
    # Analytics Queries
    # =========================================================================

    @abstractmethod
    async def get_season_progression(
        self, athlete_id: int, distance: int, stroke: int
    ) -> list[tuple[date, float]]:
        """Get time progression throughout a season."""
        pass

    @abstractmethod
    async def get_team_strength_by_event(
        self, team_id: int, distance: int, stroke: int, top_n: int = 3
    ) -> list[tuple[AthleteEntity, float]]:
        """Get top N swimmers for an event with their best times."""
        pass


class InMemoryRepository(SwimDataRepository):
    """
    In-memory implementation for testing.
    Data is lost when the application restarts.
    """

    def __init__(self):
        self._teams: dict[int, TeamEntity] = {}
        self._athletes: dict[int, AthleteEntity] = {}
        self._meets: dict[int, MeetEntity] = {}
        self._results: list[SwimResultEntity] = []
        self._relays: list[RelayResultEntity] = []
        self._splits: list[SplitEntity] = []

    async def save_teams(self, teams: list[TeamEntity]) -> int:
        for team in teams:
            self._teams[team.team_id] = team
        return len(teams)

    async def get_team(self, team_id: int) -> TeamEntity | None:
        return self._teams.get(team_id)

    async def get_team_by_code(self, code: str) -> TeamEntity | None:
        for team in self._teams.values():
            if team.code.upper() == code.upper():
                return team
        return None

    async def list_teams(self) -> list[TeamEntity]:
        return list(self._teams.values())

    async def save_athletes(self, athletes: list[AthleteEntity]) -> int:
        for athlete in athletes:
            self._athletes[athlete.athlete_id] = athlete
        return len(athletes)

    async def get_athlete(self, athlete_id: int) -> AthleteEntity | None:
        return self._athletes.get(athlete_id)

    async def search_athletes(
        self,
        name: str | None = None,
        team_id: int | None = None,
        grade: str | None = None,
        active_only: bool = True,
    ) -> list[AthleteEntity]:
        results = list(self._athletes.values())
        if active_only:
            results = [a for a in results if not a.inactive]
        if team_id:
            results = [a for a in results if a.team_id == team_id]
        if grade:
            results = [a for a in results if a.grade == grade]
        if name:
            name_lower = name.lower()
            results = [a for a in results if name_lower in a.full_name.lower()]
        return results

    async def get_roster(
        self, team_id: int, active_only: bool = True
    ) -> list[AthleteEntity]:
        return await self.search_athletes(team_id=team_id, active_only=active_only)

    async def save_meets(self, meets: list[MeetEntity]) -> int:
        for meet in meets:
            self._meets[meet.meet_id] = meet
        return len(meets)

    async def get_meet(self, meet_id: int) -> MeetEntity | None:
        return self._meets.get(meet_id)

    async def get_meets_by_season(self, season: str) -> list[MeetEntity]:
        return [m for m in self._meets.values() if m.season == season]

    async def get_recent_meets(self, limit: int = 10) -> list[MeetEntity]:
        sorted_meets = sorted(
            self._meets.values(), key=lambda m: m.start_date, reverse=True
        )
        return sorted_meets[:limit]

    async def save_results(self, results: list[SwimResultEntity]) -> int:
        self._results.extend(results)
        return len(results)

    async def get_athlete_results(
        self,
        athlete_id: int,
        event: str | None = None,
        season: str | None = None,
    ) -> list[SwimResultEntity]:
        results = [r for r in self._results if r.athlete_id == athlete_id]
        if event:
            results = [r for r in results if r.event_name == event]
        # Season filtering would need meet lookup - simplified here
        return results

    async def get_best_time(
        self, athlete_id: int, distance: int, stroke: int
    ) -> SwimResultEntity | None:
        matching = [
            r
            for r in self._results
            if r.athlete_id == athlete_id
            and r.distance == distance
            and r.stroke == stroke
            and not r.is_dq
        ]
        if not matching:
            return None
        return min(matching, key=lambda r: r.time_seconds)

    async def get_best_times_by_event(
        self,
        distance: int,
        stroke: int,
        team_id: int | None = None,
        limit: int = 20,
    ) -> list[SwimResultEntity]:
        # Get all results for event
        matching = [
            r
            for r in self._results
            if r.distance == distance and r.stroke == stroke and not r.is_dq
        ]

        # Get best per athlete
        best_by_athlete: dict[int, SwimResultEntity] = {}
        for r in matching:
            if r.athlete_id not in best_by_athlete:
                best_by_athlete[r.athlete_id] = r
            elif r.time_seconds < best_by_athlete[r.athlete_id].time_seconds:
                best_by_athlete[r.athlete_id] = r

        # Sort and limit
        sorted_results = sorted(best_by_athlete.values(), key=lambda r: r.time_seconds)
        return sorted_results[:limit]

    async def get_meet_results(self, meet_id: int) -> list[SwimResultEntity]:
        return [r for r in self._results if r.meet_id == meet_id]

    async def save_relays(self, relays: list[RelayResultEntity]) -> int:
        self._relays.extend(relays)
        return len(relays)

    async def get_relay_history(
        self, athlete_id: int, season: str | None = None
    ) -> list[RelayResultEntity]:
        return [r for r in self._relays if athlete_id in r.swimmers]

    async def save_splits(self, splits: list[SplitEntity]) -> int:
        self._splits.extend(splits)
        return len(splits)

    async def get_season_progression(
        self, athlete_id: int, distance: int, stroke: int
    ) -> list[tuple[date, float]]:
        # Would need meet dates - returning empty for in-memory
        return []

    async def get_team_strength_by_event(
        self, team_id: int, distance: int, stroke: int, top_n: int = 3
    ) -> list[tuple[AthleteEntity, float]]:
        # Simplified - would need proper join
        return []
