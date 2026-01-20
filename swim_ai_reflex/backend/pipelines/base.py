"""
Base Pipeline Classes

Defines the abstract interface for all meet pipelines.
Based on 2025 FastAPI best practices:
- Layered architecture (Router → Pipeline → Service)
- Pydantic for API models, dataclasses for internal domain
- Dependency injection ready
- Clear separation of concerns
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Generic, List, Optional, TypeVar

logger = logging.getLogger(__name__)


class MeetType(str, Enum):
    """Enumeration of supported meet types."""

    DUAL_MEET = "dual"
    TRI_MEET = "tri"  # 3-team variation of dual
    CONFERENCE_CHAMPIONSHIP = "conference"  # VCAC-style
    STATE_CHAMPIONSHIP = "state"  # VISAA State
    INVITATIONAL = "invitational"  # Multi-team, less formal


@dataclass
class ValidationResult:
    """Result of data validation."""

    valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def add_error(self, error: str) -> None:
        """Add an error to the result."""
        self.errors.append(error)
        self.valid = False

    def add_warning(self, warning: str) -> None:
        """Add a warning (doesn't affect validity)."""
        self.warnings.append(warning)

    def merge(self, other: "ValidationResult") -> "ValidationResult":
        """Merge another validation result into this one."""
        return ValidationResult(
            valid=self.valid and other.valid,
            errors=self.errors + other.errors,
            warnings=self.warnings + other.warnings,
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API response."""
        return {
            "valid": self.valid,
            "errors": self.errors,
            "warnings": self.warnings,
        }


@dataclass
class PipelineMetrics:
    """Metrics collected during pipeline execution."""

    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    validation_time_ms: float = 0.0
    optimization_time_ms: float = 0.0
    total_time_ms: float = 0.0
    cache_hit: bool = False

    def complete(self) -> None:
        """Mark pipeline as complete and calculate total time."""
        self.end_time = datetime.now()
        self.total_time_ms = (self.end_time - self.start_time).total_seconds() * 1000


# Type variables for generic pipeline
TInput = TypeVar("TInput")
TResult = TypeVar("TResult")


class MeetPipeline(ABC, Generic[TInput, TResult]):
    """
    Abstract base class for all meet pipelines.

    Each pipeline implements:
    - Input validation
    - Core processing (optimization or projection)
    - Result formatting for API response

    Follows the Strategy pattern for meet-type-specific logic.
    """

    def __init__(self, meet_type: MeetType):
        self.meet_type = meet_type
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    @abstractmethod
    def validate_input(self, data: TInput) -> ValidationResult:
        """
        Validate input data against meet rules.

        Args:
            data: Input data for the pipeline

        Returns:
            ValidationResult with errors/warnings
        """
        pass

    @abstractmethod
    def run(self, data: TInput, **options) -> TResult:
        """
        Execute the main pipeline logic.

        Args:
            data: Validated input data
            **options: Pipeline-specific options

        Returns:
            Pipeline result (type depends on implementation)
        """
        pass

    @abstractmethod
    def format_response(self, result: TResult) -> Dict[str, Any]:
        """
        Format result for API response.

        Args:
            result: Pipeline result

        Returns:
            Dictionary ready for JSON serialization
        """
        pass

    def execute(self, data: TInput, **options) -> Dict[str, Any]:
        """
        Full pipeline execution with validation, processing, and formatting.

        This is the main entry point for running a pipeline.

        Args:
            data: Input data
            **options: Pipeline options

        Returns:
            Formatted API response

        Raises:
            ValueError: If validation fails
        """
        metrics = PipelineMetrics()

        # Step 1: Validate
        import time

        start = time.perf_counter()
        validation = self.validate_input(data)
        metrics.validation_time_ms = (time.perf_counter() - start) * 1000

        if not validation.valid:
            self.logger.warning(f"Validation failed: {validation.errors}")
            return {
                "success": False,
                "error": "Validation failed",
                "validation": validation.to_dict(),
                "metrics": {
                    "validation_time_ms": metrics.validation_time_ms,
                },
            }

        # Step 2: Run pipeline
        start = time.perf_counter()
        try:
            result = self.run(data, **options)
        except Exception as e:
            self.logger.exception(f"Pipeline execution failed: {e}")
            metrics.complete()
            return {
                "success": False,
                "error": str(e),
                "metrics": {
                    "total_time_ms": metrics.total_time_ms,
                },
            }
        metrics.optimization_time_ms = (time.perf_counter() - start) * 1000

        # Step 3: Format response
        response = self.format_response(result)

        metrics.complete()

        # Add metadata
        response["success"] = True
        response["meet_type"] = self.meet_type.value
        response["metrics"] = {
            "validation_time_ms": round(metrics.validation_time_ms, 2),
            "optimization_time_ms": round(metrics.optimization_time_ms, 2),
            "total_time_ms": round(metrics.total_time_ms, 2),
            "cache_hit": metrics.cache_hit,
        }

        if validation.warnings:
            response["warnings"] = validation.warnings

        return response

    def get_rules(self):
        """Get the meet rules for this pipeline's meet type."""
        from swim_ai_reflex.backend.core.rules import get_meet_profile

        profile_map = {
            MeetType.DUAL_MEET: "seton_dual",
            MeetType.TRI_MEET: "seton_dual",  # Use dual rules for tri-meets
            MeetType.CONFERENCE_CHAMPIONSHIP: "vcac_championship",
            MeetType.STATE_CHAMPIONSHIP: "visaa_state",
            MeetType.INVITATIONAL: "vcac_championship",  # Default to VCAC
        }

        return get_meet_profile(profile_map.get(self.meet_type, "seton_dual"))


@dataclass
class BaseResult:
    """Base class for pipeline results."""

    total_points: float
    recommendations: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
