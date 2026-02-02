# backend/utils/validation.py
"""
Validation utilities for SwimAi application.
Provides input sanitization, path safety, and data validation.
"""

import os
import re
from pathlib import Path

import pandas as pd


def normalize_team_name(team: str) -> str:
    """
    Normalize team name for consistent comparison.

    Args:
        team: Raw team name string

    Returns:
        Normalized team name (lowercase, stripped)
    """
    if not team or not isinstance(team, str):
        return ""
    return team.lower().strip()


def sanitize_team_name(name: str, max_length: int = 50) -> str:
    """
    Sanitize team name to prevent XSS and injection attacks.

    Args:
        name: Raw team name input
        max_length: Maximum allowed length

    Returns:
        Sanitized team name
    """
    if not name or not isinstance(name, str):
        return ""

    # Remove special characters, keep alphanumeric, spaces, and hyphens
    sanitized = re.sub(r"[^a-zA-Z0-9\s-]", "", name)

    # Limit length
    sanitized = sanitized[:max_length]

    # Remove extra whitespace
    sanitized = " ".join(sanitized.split())

    return sanitized


def safe_join_path(base_dir: str, filename: str) -> str:
    """
    Safely join paths preventing directory traversal attacks.

    Args:
        base_dir: Base directory path
        filename: Filename to join

    Returns:
        Safe absolute path

    Raises:
        ValueError: If path traversal is detected
    """
    base = Path(base_dir).resolve()
    target = (base / filename).resolve()

    # Ensure target is within base directory
    if not str(target).startswith(str(base)):
        raise ValueError(f"Invalid filename: path traversal detected in '{filename}'")

    return str(target)


def validate_file_extension(filename: str, allowed_extensions: set) -> bool:
    """
    Validate file extension against allowed list.

    Args:
        filename: Name of file to check
        allowed_extensions: Set of allowed extensions (e.g., {'.pdf', '.csv'})

    Returns:
        True if extension is allowed, False otherwise
    """
    if not filename:
        return False

    ext = os.path.splitext(filename)[1].lower()
    return ext in allowed_extensions


def validate_roster_dataframe(
    df: pd.DataFrame, required_columns: list[str] | None = None
) -> tuple[bool, list[str]]:
    """
    Validate that a roster DataFrame has required columns and valid data.

    Args:
        df: DataFrame to validate
        required_columns: List of required column names

    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    if required_columns is None:
        required_columns = ["swimmer", "event", "time", "team"]

    errors = []

    # Check if DataFrame is empty
    if df is None or df.empty:
        errors.append("DataFrame is empty")
        return False, errors

    # Check for required columns
    missing_cols = [col for col in required_columns if col not in df.columns]
    if missing_cols:
        errors.append(f"Missing required columns: {', '.join(missing_cols)}")

    # Check for null values in critical columns
    for col in ["swimmer", "event"]:
        if col in df.columns and df[col].isnull().any():
            errors.append(f"Column '{col}' contains null values")

    # Validate time column (should be numeric and positive)
    if "time" in df.columns:
        if not pd.api.types.is_numeric_dtype(df["time"]):
            errors.append("'time' column must be numeric")
        elif (df["time"] < 0).any():
            errors.append("'time' column contains negative values")

    # Validate grade column if present
    if "grade" in df.columns:
        invalid_grades = df[~df["grade"].between(7, 12, inclusive="both")][
            "grade"
        ].dropna()
        if not invalid_grades.empty:
            errors.append(
                f"Invalid grade values found: {invalid_grades.unique().tolist()}"
            )

    return len(errors) == 0, errors


def validate_file_size(file_path: str, max_size_mb: int = 10) -> bool:
    """
    Validate that file size is within acceptable limits.

    Args:
        file_path: Path to file
        max_size_mb: Maximum allowed size in megabytes

    Returns:
        True if file size is acceptable, False otherwise
    """
    if not os.path.exists(file_path):
        return False

    file_size = os.path.getsize(file_path)
    max_size_bytes = max_size_mb * 1024 * 1024

    return file_size <= max_size_bytes


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename to remove potentially dangerous characters.

    Args:
        filename: Original filename

    Returns:
        Sanitized filename
    """
    # Remove path separators and dangerous characters
    sanitized = re.sub(r'[/\\:*?"<>|]', "", filename)

    # Remove leading/trailing dots and spaces
    sanitized = sanitized.strip(". ")

    # Limit length
    name, ext = os.path.splitext(sanitized)
    if len(name) > 200:
        name = name[:200]

    return name + ext if ext else name
