"""
Meet Pipelines Package

This package contains the pipeline implementations for different meet types:
- DualMeetPipeline: Head-to-head 2-team optimization
- ChampionshipPipeline: Multi-team championship scoring and optimization

Each pipeline follows a common interface but has distinct processing logic.
"""

from swim_ai_reflex.backend.pipelines.base import (
    MeetPipeline,
    MeetType,
    ValidationResult,
)
from swim_ai_reflex.backend.pipelines.championship import ChampionshipPipeline
from swim_ai_reflex.backend.pipelines.dual_meet import DualMeetPipeline

__all__ = [
    "MeetPipeline",
    "ValidationResult",
    "MeetType",
    "DualMeetPipeline",
    "ChampionshipPipeline",
]
