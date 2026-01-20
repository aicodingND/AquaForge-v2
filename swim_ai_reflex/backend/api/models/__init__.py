"""
API Models Package

Pydantic models for API request/response validation.
Follows 2025 best practice: Pydantic at API edges, dataclasses internal.
"""

# New pipeline-based models
# Legacy models - import from the original models.py location
# Note: These are imported from the parent directory's models.py
import importlib.util

from swim_ai_reflex.backend.api.models.championship import (
    ChampionshipOptimizeRequest,
    ChampionshipOptimizeResponse,
    ChampionshipProjectRequest,
    ChampionshipProjectResponse,
    PsychSheetEntryModel,
)
from swim_ai_reflex.backend.api.models.dual_meet import (
    DualMeetRequest,
    DualMeetResponse,
    SwimmerEntryModel,
    TeamRosterModel,
)

# Load the original models.py as a separate module
_models_path = __file__.replace("/models/__init__.py", "/models.py")
_spec = importlib.util.spec_from_file_location("_legacy_models", _models_path)
_legacy_models = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_legacy_models)

# Re-export legacy models
TeamDataRequest = _legacy_models.TeamDataRequest
TeamDataResponse = _legacy_models.TeamDataResponse
OptimizationRequest = _legacy_models.OptimizationRequest
OptimizationResponse = _legacy_models.OptimizationResponse
OptimizationResult = _legacy_models.OptimizationResult
ExportRequest = _legacy_models.ExportRequest
ExportResponse = _legacy_models.ExportResponse
HealthResponse = _legacy_models.HealthResponse
AnalyticsResponse = _legacy_models.AnalyticsResponse
ErrorResponse = _legacy_models.ErrorResponse
SwimmerEntry = _legacy_models.SwimmerEntry
OptimizerBackend = _legacy_models.OptimizerBackend
ExportFormat = _legacy_models.ExportFormat
TeamType = _legacy_models.TeamType
FileUploadMetadata = _legacy_models.FileUploadMetadata
PaginatedResponse = _legacy_models.PaginatedResponse

__all__ = [
    # Dual Meet (new)
    "DualMeetRequest",
    "DualMeetResponse",
    "SwimmerEntryModel",
    "TeamRosterModel",
    # Championship (new)
    "ChampionshipProjectRequest",
    "ChampionshipProjectResponse",
    "ChampionshipOptimizeRequest",
    "ChampionshipOptimizeResponse",
    "PsychSheetEntryModel",
    # Legacy
    "TeamDataRequest",
    "TeamDataResponse",
    "OptimizationRequest",
    "OptimizationResponse",
    "OptimizationResult",
    "ExportRequest",
    "ExportResponse",
    "HealthResponse",
    "AnalyticsResponse",
    "ErrorResponse",
    "SwimmerEntry",
    "OptimizerBackend",
    "ExportFormat",
    "TeamType",
    "FileUploadMetadata",
    "PaginatedResponse",
]
