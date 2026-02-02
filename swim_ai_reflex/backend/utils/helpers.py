"""
Utility helpers for common operations in the SwimAI application.
"""

import hashlib
from collections.abc import Callable
from datetime import datetime
from functools import lru_cache
from typing import Any

import pandas as pd


def generate_hash(data: Any) -> str:
    """
    Generate a consistent hash for any data structure.

    Args:
        data: Data to hash (dict, list, DataFrame, etc.)

    Returns:
        MD5 hash string
    """
    if isinstance(data, pd.DataFrame):
        return hashlib.md5(pd.util.hash_pandas_object(data).values).hexdigest()
    elif isinstance(data, (dict, list)):
        import json

        json_str = json.dumps(data, sort_keys=True)
        return hashlib.md5(json_str.encode()).hexdigest()
    else:
        return hashlib.md5(str(data).encode()).hexdigest()


def format_time(seconds: float) -> str:
    """
    Format seconds into human-readable time string.

    Args:
        seconds: Time in seconds

    Returns:
        Formatted string like "2m 30s" or "45s"
    """
    if seconds < 60:
        return f"{int(seconds)}s"
    elif seconds < 3600:
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes}m {secs}s"
    else:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        return f"{hours}h {minutes}m"


def format_number(num: float, decimals: int = 2) -> str:
    """
    Format number with thousands separators and decimals.

    Args:
        num: Number to format
        decimals: Number of decimal places

    Returns:
        Formatted string like "1,234.56"
    """
    return f"{num:,.{decimals}f}"


def safe_divide(numerator: float, denominator: float, default: float = 0.0) -> float:
    """
    Safely divide two numbers, returning default if denominator is zero.

    Args:
        numerator: Top number
        denominator: Bottom number
        default: Value to return if denominator is zero

    Returns:
        Result of division or default
    """
    try:
        return numerator / denominator if denominator != 0 else default
    except (TypeError, ZeroDivisionError):
        return default


def chunk_list(lst: list[Any], chunk_size: int) -> list[list[Any]]:
    """
    Split a list into chunks of specified size.

    Args:
        lst: List to chunk
        chunk_size: Size of each chunk

    Returns:
        List of chunks
    """
    return [lst[i : i + chunk_size] for i in range(0, len(lst), chunk_size)]


def merge_dicts(*dicts: dict[str, Any]) -> dict[str, Any]:
    """
    Merge multiple dictionaries, with later dicts taking precedence.

    Args:
        *dicts: Dictionaries to merge

    Returns:
        Merged dictionary
    """
    result = {}
    for d in dicts:
        result.update(d)
    return result


def filter_dict(
    d: dict[str, Any], predicate: Callable[[str, Any], bool]
) -> dict[str, Any]:
    """
    Filter dictionary by key-value predicate.

    Args:
        d: Dictionary to filter
        predicate: Function that takes (key, value) and returns bool

    Returns:
        Filtered dictionary
    """
    return {k: v for k, v in d.items() if predicate(k, v)}


def get_nested(d: dict[str, Any], path: str, default: Any = None) -> Any:
    """
    Get nested dictionary value using dot notation.

    Args:
        d: Dictionary to search
        path: Dot-separated path like "user.profile.name"
        default: Default value if path not found

    Returns:
        Value at path or default

    Example:
        >>> data = {"user": {"profile": {"name": "John"}}}
        >>> get_nested(data, "user.profile.name")
        "John"
    """
    keys = path.split(".")
    current = d

    for key in keys:
        if isinstance(current, dict) and key in current:
            current = current[key]
        else:
            return default

    return current


def set_nested(d: dict[str, Any], path: str, value: Any) -> dict[str, Any]:
    """
    Set nested dictionary value using dot notation.

    Args:
        d: Dictionary to modify
        path: Dot-separated path like "user.profile.name"
        value: Value to set

    Returns:
        Modified dictionary

    Example:
        >>> data = {}
        >>> set_nested(data, "user.profile.name", "John")
        {"user": {"profile": {"name": "John"}}}
    """
    keys = path.split(".")
    current = d

    for key in keys[:-1]:
        if key not in current or not isinstance(current[key], dict):
            current[key] = {}
        current = current[key]

    current[keys[-1]] = value
    return d


def timestamp() -> str:
    """
    Get current timestamp as ISO format string.

    Returns:
        ISO format timestamp
    """
    return datetime.now().isoformat()


def debounce(wait_ms: int):
    """
    Decorator to debounce a function call.

    Args:
        wait_ms: Milliseconds to wait before executing

    Returns:
        Decorated function
    """
    import asyncio
    from functools import wraps

    def decorator(func):
        timer = None

        @wraps(func)
        async def debounced(*args, **kwargs):
            nonlocal timer

            if timer:
                timer.cancel()

            timer = asyncio.create_task(asyncio.sleep(wait_ms / 1000))
            try:
                await timer
                return await func(*args, **kwargs)
            except asyncio.CancelledError:
                pass

        return debounced

    return decorator


class Singleton:
    """
    Singleton metaclass for creating singleton classes.

    Example:
        class MyService(metaclass=Singleton):
            pass
    """

    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]


def validate_email(email: str) -> bool:
    """
    Simple email validation.

    Args:
        email: Email address to validate

    Returns:
        True if valid format
    """
    import re

    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return bool(re.match(pattern, email))


def truncate_string(s: str, max_length: int, suffix: str = "...") -> str:
    """
    Truncate string to max length with suffix.

    Args:
        s: String to truncate
        max_length: Maximum length
        suffix: Suffix to add if truncated

    Returns:
        Truncated string
    """
    if len(s) <= max_length:
        return s
    return s[: max_length - len(suffix)] + suffix


@lru_cache(maxsize=256)
def normalize_team_name(team: str) -> str:
    """
    Normalize team name for consistent comparison across the application.

    This function should be used whenever comparing team names to ensure
    consistency (e.g., when calculating scores, filtering data).

    Args:
        team: Raw team name

    Returns:
        Normalized team name (lowercase, stripped of whitespace)
    """
    if not team or not isinstance(team, str):
        return ""

    t = team.lower().strip()

    # Critical: Normalize "Seton Swimming", "Seton School", etc. to simply "seton"
    # and any opponent variant to "opponent"
    if "seton" in t:
        return "seton"
    if "opponent" in t:
        return "opponent"

    return t


def sanitize_team_name(name: str) -> str:
    """
    Sanitize team name to prevent XSS and injection attacks.

    Removes special characters, keeping only alphanumeric, spaces, and hyphens.
    Limits length to prevent buffer overflow issues.

    Args:
        name: User-provided team name

    Returns:
        Sanitized team name safe for display and storage

    Example:
        >>> sanitize_team_name("Seton<script>alert('XSS')</script>")
        "Setonscriptalert'XSS'script"
        >>> sanitize_team_name("Trinity-Christian ABC 123")
        "Trinity-Christian ABC 123"
    """
    import re

    if not name or not isinstance(name, str):
        return ""

    # Remove special characters, keep alphanumeric, spaces, and hyphens
    sanitized = re.sub(r"[^a-zA-Z0-9\s\-]", "", name)

    # Limit length to 50 characters
    sanitized = sanitized[:50]

    # Remove multiple consecutive spaces
    sanitized = re.sub(r"\s+", " ", sanitized)

    return sanitized.strip()
