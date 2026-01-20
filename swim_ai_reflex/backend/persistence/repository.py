"""
Repository Pattern - Abstract Storage Interface

Defines the interface for data persistence.
Implementations can use SQLite (current) or PostgreSQL (future).
"""

from abc import ABC, abstractmethod
from typing import List, Optional
from datetime import datetime

from swim_ai_reflex.backend.models.opponent import (
    CoachTendency,
    MeetResult,
    OpponentProfile,
)


class MeetRepository(ABC):
    """
    Abstract repository for meet data persistence.
    
    This follows the repository pattern for clean architecture:
    - Business logic doesn't know about storage details
    - Easy to swap SQLite → PostgreSQL
    - Testable with mock implementations
    """
    
    # =========================================================================
    # Meet Results
    # =========================================================================
    
    @abstractmethod
    async def save_meet(self, meet: MeetResult) -> str:
        """
        Save a meet result.
        
        Returns:
            meet_id of saved meet
        """
        pass
    
    @abstractmethod
    async def get_meet(self, meet_id: str) -> Optional[MeetResult]:
        """Get a specific meet by ID."""
        pass
    
    @abstractmethod
    async def get_meets_by_opponent(self, opponent: str) -> List[MeetResult]:
        """Get all meets against a specific opponent."""
        pass
    
    @abstractmethod
    async def get_recent_meets(self, limit: int = 10) -> List[MeetResult]:
        """Get most recent meets."""
        pass
    
    @abstractmethod
    async def get_meets_in_range(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> List[MeetResult]:
        """Get meets within a date range."""
        pass
    
    # =========================================================================
    # Coach Tendencies
    # =========================================================================
    
    @abstractmethod
    async def save_tendency(self, tendency: CoachTendency) -> None:
        """Save or update a coach tendency profile."""
        pass
    
    @abstractmethod
    async def get_tendency(self, team_name: str) -> Optional[CoachTendency]:
        """Get tendency for a specific team."""
        pass
    
    @abstractmethod
    async def get_all_tendencies(self) -> List[CoachTendency]:
        """Get all saved tendencies."""
        pass
    
    # =========================================================================
    # Opponent Profiles
    # =========================================================================
    
    @abstractmethod
    async def save_opponent(self, profile: OpponentProfile) -> None:
        """Save or update an opponent profile."""
        pass
    
    @abstractmethod
    async def get_opponent(self, team_name: str) -> Optional[OpponentProfile]:
        """Get opponent profile by team name."""
        pass
    
    @abstractmethod
    async def list_opponents(self) -> List[str]:
        """List all known opponent team names."""
        pass


class InMemoryRepository(MeetRepository):
    """
    In-memory implementation for testing and development.
    Data is lost when the application restarts.
    """
    
    def __init__(self):
        self._meets: dict[str, MeetResult] = {}
        self._tendencies: dict[str, CoachTendency] = {}
        self._opponents: dict[str, OpponentProfile] = {}
    
    async def save_meet(self, meet: MeetResult) -> str:
        self._meets[meet.meet_id] = meet
        return meet.meet_id
    
    async def get_meet(self, meet_id: str) -> Optional[MeetResult]:
        return self._meets.get(meet_id)
    
    async def get_meets_by_opponent(self, opponent: str) -> List[MeetResult]:
        return [m for m in self._meets.values() if m.opponent_team.lower() == opponent.lower()]
    
    async def get_recent_meets(self, limit: int = 10) -> List[MeetResult]:
        sorted_meets = sorted(self._meets.values(), key=lambda m: m.date, reverse=True)
        return sorted_meets[:limit]
    
    async def get_meets_in_range(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> List[MeetResult]:
        return [
            m for m in self._meets.values()
            if start_date <= m.date <= end_date
        ]
    
    async def save_tendency(self, tendency: CoachTendency) -> None:
        self._tendencies[tendency.team_name.lower()] = tendency
    
    async def get_tendency(self, team_name: str) -> Optional[CoachTendency]:
        return self._tendencies.get(team_name.lower())
    
    async def get_all_tendencies(self) -> List[CoachTendency]:
        return list(self._tendencies.values())
    
    async def save_opponent(self, profile: OpponentProfile) -> None:
        self._opponents[profile.team_name.lower()] = profile
    
    async def get_opponent(self, team_name: str) -> Optional[OpponentProfile]:
        return self._opponents.get(team_name.lower())
    
    async def list_opponents(self) -> List[str]:
        return [p.team_name for p in self._opponents.values()]


# Default repository instance (in-memory for now)
_repository: Optional[MeetRepository] = None


def get_repository() -> MeetRepository:
    """Get the current repository instance."""
    global _repository
    if _repository is None:
        _repository = InMemoryRepository()
    return _repository


def set_repository(repo: MeetRepository) -> None:
    """Set a custom repository (for switching to SQLite/PostgreSQL)."""
    global _repository
    _repository = repo
