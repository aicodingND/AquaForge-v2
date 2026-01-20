"""
AquaForge Data Layer

High-performance data layer for swim analytics with:
- Direct HyTek Team Manager integration
- DuckDB analytics engine
- Strict validation (no fuzzy matching)

Edge Cases Handled:
    - Missing/NULL values in source data
    - Date format variations across HyTek versions
    - Legacy data with incomplete fields
    - Unicode characters in swimmer names
    - Timezone-naive date handling
    - Large file streaming (77K+ results)
"""

from swim_ai_reflex.core.data.entities import (
    AthleteEntity,
    DivingResultEntity,
    MeetEntity,
    RelayResultEntity,
    SplitEntity,
    SwimResultEntity,
    TeamEntity,
    ValidationError,
)

__all__ = [
    "AthleteEntity",
    "DivingResultEntity",
    "MeetEntity",
    "RelayResultEntity",
    "SplitEntity",
    "SwimResultEntity",
    "TeamEntity",
    "ValidationError",
]
