"""
API Dependencies

Shared dependencies for FastAPI endpoints including:
- API key authentication
- Rate limiting (in-memory sliding window)
- File validation
- Service factories
"""

import logging
import os
import time
from collections import defaultdict

from fastapi import Depends, Header, HTTPException, UploadFile, status

from swim_ai_reflex.backend.core.settings import get_settings

logger = logging.getLogger(__name__)


# ==================== Configuration ====================


def get_config():
    """Get application configuration."""
    from swim_ai_reflex.backend.config import get_config as _get_config

    return _get_config()


# ==================== Services ====================


def get_optimization_service():
    """Get optimization service instance."""
    from swim_ai_reflex.backend.services.optimization_service import OptimizationService

    return OptimizationService()


def get_data_service():
    """Get data service instance."""
    from swim_ai_reflex.backend.services.data_service import DataService

    config = get_config()
    return DataService(config.security.upload_directory)


def get_export_service():
    """Get export service instance."""
    from swim_ai_reflex.backend.services.export_service import export_service

    return export_service


def get_analytics_service():
    """Get analytics service instance."""
    from swim_ai_reflex.backend.services.strategy_analysis_service import (
        StrategyAnalysisService,
    )

    return StrategyAnalysisService()


# ==================== Authentication ====================

# Public routes that don't require API key
_PUBLIC_PREFIXES = (
    "/api/v1/health",
    "/api/v1/historical",
    "/api/docs",
    "/api/redoc",
    "/api/openapi.json",
)


async def get_api_key(x_api_key: str | None = Header(None)):
    """
    Validate API key from X-API-Key header.

    When API_KEY env var is set, all non-public routes require authentication.
    When API_KEY is not set (development), all requests are allowed.
    """
    expected_key = os.getenv("API_KEY")

    # No key configured = development mode, allow all
    if not expected_key:
        return x_api_key

    if not x_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API key. Set X-API-Key header.",
        )

    if x_api_key != expected_key:
        logger.warning("Invalid API key attempt")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid API key",
        )

    return x_api_key


async def require_api_key(api_key: str = Depends(get_api_key)):
    """Dependency that enforces API key for protected routes."""
    return api_key


# ==================== Rate Limiting ====================


class RateLimiter:
    """Simple in-memory sliding window rate limiter.

    Tracks request timestamps per client and enforces a maximum
    number of requests within a rolling time window.
    """

    def __init__(self, requests_per_minute: int = 60, window_seconds: int = 60):
        self.max_requests = requests_per_minute
        self.window_seconds = window_seconds
        self._requests: dict[str, list[float]] = defaultdict(list)

    async def check(self, client_id: str) -> bool:
        """Check if client is within rate limit. Returns False if exceeded."""
        now = time.time()
        cutoff = now - self.window_seconds

        # Clean old entries
        timestamps = self._requests[client_id]
        self._requests[client_id] = [t for t in timestamps if t > cutoff]

        if len(self._requests[client_id]) >= self.max_requests:
            return False

        self._requests[client_id].append(now)
        return True

    def reset(self, client_id: str | None = None):
        """Reset rate limit state. If client_id is None, resets all."""
        if client_id:
            self._requests.pop(client_id, None)
        else:
            self._requests.clear()


# Global rate limiters
api_limiter = RateLimiter(requests_per_minute=60)
optimization_limiter = RateLimiter(requests_per_minute=10, window_seconds=60)


async def check_rate_limit(api_key: str | None = Depends(get_api_key)):
    """Check if request is within the general rate limit."""
    client_id = api_key or "anonymous"
    if not await api_limiter.check(client_id):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Try again in a minute.",
        )
    return True


async def check_optimization_rate_limit(api_key: str | None = Depends(get_api_key)):
    """Stricter rate limit for optimization endpoints (10/min)."""
    client_id = api_key or "anonymous"
    if not await optimization_limiter.check(client_id):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Optimization rate limit exceeded. Max 10 requests per minute.",
        )
    return True


# ==================== Database (Future) ====================


def get_db():
    """Get database session. Placeholder for future integration."""
    yield None


# ==================== File Storage & Validation ====================


def get_file_manager():
    """Get file manager for uploads."""
    from swim_ai_reflex.backend.utils.file_manager import FileManager

    config = get_config()
    return FileManager(config.security.upload_directory)


def validate_team_data(data: list) -> bool:
    """Validate team data structure."""
    if not data:
        return False

    required_fields = {"swimmer", "event", "time"}
    for entry in data:
        if not isinstance(entry, dict):
            return False
        if not required_fields.issubset(entry.keys()):
            return False

    return True


def validate_file_extension(filename: str, allowed: list | None = None) -> bool:
    """Validate file extension."""
    if not allowed:
        settings = get_settings()
        allowed = settings.allowed_extensions

    ext = filename.lower().split(".")[-1] if "." in filename else ""
    return f".{ext}" in allowed


def sanitize_filename(filename: str) -> str:
    """Sanitize a filename to prevent path traversal and other attacks."""
    from swim_ai_reflex.backend.utils.file_manager import FileManager

    fm = FileManager()
    return fm.sanitize_filename(filename)


async def validate_upload(file: UploadFile) -> UploadFile:
    """Validate an uploaded file for size and extension.

    Use as a dependency: upload: UploadFile = Depends(validate_upload)
    """
    settings = get_settings()
    max_bytes = settings.max_upload_size_mb * 1024 * 1024

    # Validate extension
    if file.filename and not validate_file_extension(file.filename):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type not allowed. Accepted: {settings.allowed_extensions}",
        )

    # Check file size by reading content
    content = await file.read()
    if len(content) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large. Maximum size: {settings.max_upload_size_mb}MB",
        )

    # Reset file position for downstream consumers
    await file.seek(0)

    # Sanitize filename
    if file.filename:
        file.filename = sanitize_filename(file.filename)

    return file
