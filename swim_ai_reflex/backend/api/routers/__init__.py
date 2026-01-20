"""
API Routers Package

Contains all FastAPI routers for the AquaForge API.
"""

from swim_ai_reflex.backend.api.routers import (
    analytics,
    championship,
    data,
    dual_meet,
    export,
    health,
    optimization,
)

__all__ = [
    "health",
    "optimization",
    "data",
    "export",
    "analytics",
    "dual_meet",
    "championship",
]
