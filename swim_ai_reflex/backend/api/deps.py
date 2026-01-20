"""
API Dependencies

Shared dependencies for FastAPI endpoints including:
- Authentication (future)
- Database sessions (future)
- Rate limiting (future)
- Common validation
"""

import logging
from typing import Optional

from fastapi import Depends, Header, HTTPException, status

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


# ==================== Authentication (Future) ====================


async def get_api_key(x_api_key: Optional[str] = Header(None)):
    """
    Validate API key from header.

    Currently disabled - all requests are allowed.
    Enable this when authentication is required.
    """
    # TODO: Implement API key validation
    # if not x_api_key:
    #     raise HTTPException(
    #         status_code=status.HTTP_401_UNAUTHORIZED,
    #         detail="Missing API key"
    #     )
    # if x_api_key != os.getenv("API_KEY"):
    #     raise HTTPException(
    #         status_code=status.HTTP_403_FORBIDDEN,
    #         detail="Invalid API key"
    #     )
    return x_api_key


async def get_current_user(api_key: str = Depends(get_api_key)):
    """
    Get current user from API key.

    Currently returns None - implement when user auth is needed.
    """
    # TODO: Look up user from API key
    return None


# ==================== Rate Limiting (Future) ====================


class RateLimiter:
    """Simple in-memory rate limiter."""

    def __init__(self, requests_per_minute: int = 60):
        self.requests_per_minute = requests_per_minute
        self._requests: dict = {}

    async def check(self, client_id: str) -> bool:
        """Check if client is within rate limit."""
        # TODO: Implement actual rate limiting with Redis
        return True


rate_limiter = RateLimiter()


async def check_rate_limit(api_key: Optional[str] = Depends(get_api_key)):
    """
    Check if request is within rate limit.

    Currently always passes - implement when needed.
    """
    client_id = api_key or "anonymous"
    if not await rate_limiter.check(client_id):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Rate limit exceeded"
        )
    return True


# ==================== Database (Future) ====================


def get_db():
    """
    Get database session.

    Placeholder for future database integration.
    """
    # TODO: Implement with SQLAlchemy
    # from app.core.database import SessionLocal
    # db = SessionLocal()
    # try:
    #     yield db
    # finally:
    #     db.close()
    yield None


# ==================== File Storage ====================


def get_file_manager():
    """Get file manager for uploads."""
    from swim_ai_reflex.backend.utils.file_manager import FileManager

    config = get_config()
    return FileManager(config.security.upload_directory)


# ==================== Validation Helpers ====================


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


def validate_file_extension(filename: str, allowed: Optional[list] = None) -> bool:
    """Validate file extension."""
    if not allowed:
        allowed = [".xlsx", ".xls", ".csv", ".pdf"]

    ext = filename.lower().split(".")[-1] if "." in filename else ""
    return f".{ext}" in allowed
