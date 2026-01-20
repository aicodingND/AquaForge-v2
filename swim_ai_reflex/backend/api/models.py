"""
Pydantic Models for API Request/Response Validation

These models ensure type safety and automatic validation for all API endpoints.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


def _utc_now() -> datetime:
    """Return timezone-aware UTC datetime."""
    return datetime.now(timezone.utc)


# ==================== Enums ====================


class OptimizerBackend(str, Enum):
    """Available optimization backends."""

    HEURISTIC = "heuristic"
    GUROBI = "gurobi"


class ExportFormat(str, Enum):
    """Supported export formats."""

    CSV = "csv"
    PDF = "pdf"
    HTML = "html"
    JSON = "json"


class TeamType(str, Enum):
    """Team type classification."""

    SETON = "seton"
    OPPONENT = "opponent"


# ==================== Request Models ====================


class SwimmerEntry(BaseModel):
    """Single swimmer entry data."""

    model_config = ConfigDict(extra="allow")

    swimmer: str = Field(..., description="Swimmer name")
    event: str = Field(..., description="Event name")
    time: str = Field(..., description="Best time for this event")
    seed_time: Optional[str] = Field(None, description="Seed time if different")
    age: Optional[int] = Field(None, description="Swimmer age")
    grade: Optional[str] = Field(None, description="Swimmer grade")


class TeamDataRequest(BaseModel):
    """Request model for team data upload."""

    team_name: str = Field(..., description="Team name")
    team_type: TeamType = Field(..., description="Team classification (seton/opponent)")
    entries: List[SwimmerEntry] = Field(..., description="List of swimmer entries")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)


class OptimizationRequest(BaseModel):
    """Request model for optimization."""

    seton_data: List[Dict[str, Any]] = Field(..., description="Seton team data")
    opponent_data: List[Dict[str, Any]] = Field(..., description="Opponent team data")

    # Optimization parameters
    optimizer_backend: OptimizerBackend = Field(
        default=OptimizerBackend.GUROBI,
        description="Optimization engine to use (GUROBI = accurate MILP, HEURISTIC = fast fallback)",
    )
    max_individual_events: int = Field(default=4, ge=1, le=6)
    enforce_fatigue: bool = Field(default=True)
    use_relay_optimization: bool = Field(default=True)
    robust_mode: bool = Field(
        default=False, description="Run multi-scenario evaluation"
    )
    scoring_type: str = Field(
        default="visaa_top7", description="Scoring rules (visaa_top7 or standard_top5)"
    )

    # Optional team names
    seton_team_name: Optional[str] = Field(default="Seton")
    opponent_team_name: Optional[str] = Field(default="Opponent")


class ExportRequest(BaseModel):
    """Request model for exporting results."""

    format: ExportFormat = Field(..., description="Export format")
    optimization_results: Dict[str, Any] = Field(
        ..., description="Optimization results to export"
    )
    seton_score: float = Field(default=0.0)
    opponent_score: float = Field(default=0.0)
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)


class FileUploadMetadata(BaseModel):
    """Metadata for file upload."""

    filename: str
    team_type: TeamType
    file_size: int
    content_type: str


# ==================== Response Models ====================


class HealthResponse(BaseModel):
    """Health check response."""

    status: str = Field(..., description="Service status")
    timestamp: datetime = Field(default_factory=_utc_now)
    version: str = Field(default="1.0.0")
    services: Dict[str, str] = Field(default_factory=dict)


class TeamDataResponse(BaseModel):
    """Response after processing team data."""

    success: bool
    team_name: str
    team_type: TeamType
    swimmer_count: int
    entry_count: int
    events: List[str] = Field(default_factory=list, description="Unique events")
    data: List[Dict[str, Any]] = Field(
        default_factory=list, description="Parsed entry data"
    )
    warnings: List[str] = Field(default_factory=list)
    file_hash: Optional[str] = None
    message: Optional[str] = None
    teams: Optional[List[str]] = Field(
        default=None, description="Team codes for championship meets"
    )


class OptimizationResult(BaseModel):
    """Single event optimization result."""

    event: str
    event_number: int
    seton_swimmers: List[str]
    opponent_swimmers: List[str]
    seton_times: List[str]
    opponent_times: List[str]
    seton_points: List[float] = Field(default_factory=list)
    opponent_points: List[float] = Field(default_factory=list)
    projected_score: Dict[str, float]


class OptimizationResponse(BaseModel):
    """Response from optimization request."""

    success: bool
    seton_score: float
    opponent_score: float
    score_margin: float
    results: List[OptimizationResult]
    statistics: Dict[str, Any] = Field(default_factory=dict)
    warnings: List[str] = Field(default_factory=list)
    optimization_time_ms: float

    # Championship-specific fields
    championship_standings: Optional[List[Dict[str, Any]]] = Field(
        default=None,
        description="Full team standings for championship mode: [{rank, team, points}, ...]",
    )
    event_breakdowns: Optional[Dict[str, Any]] = Field(
        default=None, description="Per-event point breakdown for all teams"
    )
    swing_events: Optional[List[Dict[str, Any]]] = Field(
        default=None,
        description="Events where small improvements yield significant gains",
    )

    # Advanced Analytics (Monte Carlo, Fatigue, Nash)
    analytics: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Advanced analytics: monte_carlo, fatigue_warnings, nash_insights, relay_tradeoffs",
    )


class ChampionshipAnalytics(BaseModel):
    """Advanced analytics for championship optimization."""

    # Monte Carlo Results
    monte_carlo: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Monte Carlo simulation results: win_probability, confidence_interval, risk_level",
    )

    # Fatigue Warnings
    fatigue_warnings: Optional[List[Dict[str, Any]]] = Field(
        default=None,
        description="Swimmers with high fatigue: [{swimmer, events, fatigue_cost, risk}]",
    )

    # Nash Equilibrium Insights
    nash_insights: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Nash equilibrium analysis: rankings, equilibrium_found, insights",
    )

    # Relay Trade-offs
    relay_tradeoffs: Optional[List[Dict[str, Any]]] = Field(
        default=None,
        description="400FR trade-off analysis: [{swimmer, individual_event, relay_gain, individual_loss, recommendation}]",
    )


class ExportResponse(BaseModel):
    """Response from export request."""

    success: bool
    format: ExportFormat
    filename: str
    content: Optional[str] = Field(
        None, description="Base64 encoded content for binary formats"
    )
    download_url: Optional[str] = Field(
        None, description="URL for file download if stored"
    )


class AnalyticsResponse(BaseModel):
    """Response with analytics data."""

    team_comparison: Dict[str, Any]
    event_analysis: List[Dict[str, Any]]
    swimmer_utilization: Dict[str, Any]
    recommendations: List[str]


class ErrorResponse(BaseModel):
    """Standard error response."""

    error: str
    detail: Optional[str] = None
    code: Optional[str] = None


# ==================== Shared Models ====================


class PaginatedResponse(BaseModel):
    """Generic paginated response wrapper."""

    items: List[Any]
    total: int
    page: int
    page_size: int
    has_more: bool
