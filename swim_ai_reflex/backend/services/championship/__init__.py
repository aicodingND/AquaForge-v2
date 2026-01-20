"""
Championship Services Package

Services specific to multi-team championship meets:
- Point projection
- Entry optimization
- Relay optimization
"""


# Use lazy imports to avoid circular import issues
def __getattr__(name):
    if name == "PointProjectionService":
        from swim_ai_reflex.backend.services.championship.projection import (
            PointProjectionService,
        )

        return PointProjectionService
    if name == "project_standings":
        from swim_ai_reflex.backend.services.championship.projection import (
            project_standings,
        )

        return project_standings
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "PointProjectionService",
    "project_standings",
]
