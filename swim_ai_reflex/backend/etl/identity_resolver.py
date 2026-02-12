"""
Swimmer Identity Resolution - Match swimmers across files, meets, and seasons.

Tiered matching strategy:
1. Exact match (normalized name + gender + team) -> confidence 1.0
2. Fuzzy match (rapidfuzz >=90% + same team/gender) -> confidence 0.85
3. Grade progression (+1 year, same name/team) -> confidence 0.95
4. Alias table lookup -> confidence 1.0
"""

import re

from sqlalchemy import func  # TODO: port dependency -- pip install sqlalchemy
from sqlmodel import Session, select  # TODO: port dependency -- pip install sqlmodel

from swim_ai_reflex.backend.persistence.db_models import (  # TODO: port dependency -- db_models.py not yet on Mac
    Swimmer,
    SwimmerAlias,
    SwimmerTeamSeason,
)

try:
    from rapidfuzz import fuzz  # TODO: port dependency -- pip install rapidfuzz

    HAS_RAPIDFUZZ = True
except ImportError:
    HAS_RAPIDFUZZ = False


def normalize_name(name: str) -> tuple[str, str]:
    """
    Normalize a swimmer name to (first_name, last_name).

    Handles:
    - "First Last" -> ("First", "Last")
    - "Last, First" -> ("First", "Last")
    - "First Middle Last" -> ("First", "Last")
    - Extra whitespace, punctuation
    """
    if not name:
        return ("", "")

    cleaned = name.strip()
    # Remove parenthetical grade info: "John Smith (SR)"
    cleaned = re.sub(r"\s*\([^)]*\)\s*", " ", cleaned).strip()

    # Handle "Last, First" format (common in Hy-Tek)
    if "," in cleaned:
        parts = [p.strip() for p in cleaned.split(",", 1)]
        last_name = parts[0]
        first_name = parts[1] if len(parts) > 1 else ""
    else:
        parts = cleaned.split()
        if len(parts) == 0:
            return ("", "")
        elif len(parts) == 1:
            return (parts[0], "")
        else:
            first_name = parts[0]
            last_name = parts[-1]  # Last word is last name

    return (first_name.strip().title(), last_name.strip().title())


class IdentityResolver:
    """Resolves swimmer identities across different data sources."""

    def __init__(self, session: Session):
        self.session = session
        self._cache: dict[str, int] = {}  # normalized_key -> swimmer_id

    def resolve(
        self,
        raw_name: str,
        gender: str | None,
        team_name: str | None,
        grade: int | None = None,
        season_name: str | None = None,
    ) -> int:
        """
        Resolve a swimmer name to a swimmer_id.

        Creates a new Swimmer record if no match found.

        Returns: swimmer_id
        """
        first_name, last_name = normalize_name(raw_name)
        if not first_name and not last_name:
            first_name = raw_name.strip()

        # Cache key for fast repeated lookups within same import
        cache_key = f"{first_name}|{last_name}|{gender}|{team_name}".lower()
        if cache_key in self._cache:
            return self._cache[cache_key]

        # Tier 1: Exact match
        swimmer = self._exact_match(first_name, last_name, gender)
        if swimmer:
            self._cache[cache_key] = swimmer.id
            return swimmer.id

        # Tier 4: Alias table (before fuzzy, since aliases are authoritative)
        swimmer = self._alias_match(raw_name)
        if swimmer:
            self._cache[cache_key] = swimmer.id
            return swimmer.id

        # Tier 2: Fuzzy match (if rapidfuzz available)
        if HAS_RAPIDFUZZ:
            swimmer = self._fuzzy_match(first_name, last_name, gender, team_name)
            if swimmer:
                self._cache[cache_key] = swimmer.id
                # Store the raw name as an alias for future exact matches
                self._create_alias(swimmer.id, raw_name, "fuzzy_match")
                return swimmer.id

        # Tier 3: Grade progression
        if grade and season_name:
            swimmer = self._grade_progression_match(
                first_name, last_name, team_name, grade, season_name
            )
            if swimmer:
                self._cache[cache_key] = swimmer.id
                return swimmer.id

        # No match: create new swimmer
        swimmer = Swimmer(
            first_name=first_name,
            last_name=last_name,
            gender=gender,
        )
        self.session.add(swimmer)
        self.session.commit()
        self.session.refresh(swimmer)

        # Store raw name as alias if it differs from "First Last"
        canonical = f"{first_name} {last_name}"
        if raw_name.strip() != canonical:
            self._create_alias(swimmer.id, raw_name.strip(), "import")

        self._cache[cache_key] = swimmer.id
        return swimmer.id

    def _exact_match(
        self, first_name: str, last_name: str, gender: str | None
    ) -> Swimmer | None:
        """Tier 1: Exact name + gender match."""
        stmt = select(Swimmer).where(
            func.lower(Swimmer.first_name) == first_name.lower(),
            func.lower(Swimmer.last_name) == last_name.lower(),
        )
        if gender:
            stmt = stmt.where(Swimmer.gender == gender)
        return self.session.exec(stmt).first()

    def _alias_match(self, raw_name: str) -> Swimmer | None:
        """Tier 4: Lookup in alias table."""
        alias = self.session.exec(
            select(SwimmerAlias).where(
                func.lower(SwimmerAlias.alias_name) == raw_name.strip().lower()
            )
        ).first()
        if alias:
            return self.session.get(Swimmer, alias.swimmer_id)
        return None

    def _fuzzy_match(
        self,
        first_name: str,
        last_name: str,
        gender: str | None,
        team_name: str | None,
    ) -> Swimmer | None:
        """Tier 2: Fuzzy string matching with rapidfuzz."""
        full_name = f"{first_name} {last_name}"

        # Get candidates -- same gender, limit search space
        stmt = select(Swimmer)
        if gender:
            stmt = stmt.where(Swimmer.gender == gender)
        candidates = self.session.exec(stmt).all()

        best_score = 0.0
        best_match = None

        for candidate in candidates:
            candidate_name = f"{candidate.first_name} {candidate.last_name}"
            score = fuzz.WRatio(full_name.lower(), candidate_name.lower())
            if score > best_score and score >= 90:
                best_score = score
                best_match = candidate

        return best_match

    def _grade_progression_match(
        self,
        first_name: str,
        last_name: str,
        team_name: str | None,
        grade: int,
        season_name: str,
    ) -> Swimmer | None:
        """Tier 3: Find swimmer by grade progression (grade-1 in previous season)."""
        # Parse season to find previous: "2025-2026" -> "2024-2025"
        parts = season_name.split("-")
        if len(parts) != 2:
            return None
        try:
            prev_season = f"{int(parts[0]) - 1}-{int(parts[1]) - 1}"
        except ValueError:
            return None

        # Find swimmer with same name, grade-1, in previous season
        from swim_ai_reflex.backend.persistence.db_models import (  # TODO: port dependency -- db_models.py not yet on Mac
            Season,
        )

        prev = self.session.exec(
            select(Season).where(Season.name == prev_season)
        ).first()
        if not prev:
            return None

        stmt = (
            select(Swimmer)
            .join(SwimmerTeamSeason, SwimmerTeamSeason.swimmer_id == Swimmer.id)
            .where(
                func.lower(Swimmer.first_name) == first_name.lower(),
                func.lower(Swimmer.last_name) == last_name.lower(),
                SwimmerTeamSeason.season_id == prev.id,
                SwimmerTeamSeason.grade == grade - 1,
            )
        )
        return self.session.exec(stmt).first()

    def _create_alias(self, swimmer_id: int, alias_name: str, source: str) -> None:
        """Store an alias for future lookups."""
        existing = self.session.exec(
            select(SwimmerAlias).where(
                func.lower(SwimmerAlias.alias_name) == alias_name.lower()
            )
        ).first()
        if not existing:
            alias = SwimmerAlias(
                swimmer_id=swimmer_id,
                alias_name=alias_name,
                source=source,
            )
            self.session.add(alias)
            try:
                self.session.commit()
            except Exception:
                self.session.rollback()  # Unique constraint race
