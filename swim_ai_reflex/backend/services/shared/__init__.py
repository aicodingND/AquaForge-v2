"""
Shared Services Package

Common services used by both dual meet and championship pipelines:
- Validation: Unified data validation
- Normalization: Event name and time normalization
- Caching: Result caching
"""


# Use lazy imports to avoid circular import issues
def __getattr__(name):
    if name == "MeetDataValidator":
        from swim_ai_reflex.backend.services.shared.validation import MeetDataValidator

        return MeetDataValidator
    if name == "normalize_event_name":
        from swim_ai_reflex.backend.services.shared.normalization import (
            normalize_event_name,
        )

        return normalize_event_name
    if name == "normalize_swimmer_name":
        from swim_ai_reflex.backend.services.shared.normalization import (
            normalize_swimmer_name,
        )

        return normalize_swimmer_name
    if name == "normalize_time":
        from swim_ai_reflex.backend.services.shared.normalization import normalize_time

        return normalize_time
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "MeetDataValidator",
    "normalize_event_name",
    "normalize_time",
    "normalize_swimmer_name",
]
