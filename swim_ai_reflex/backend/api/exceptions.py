"""
Standardized exception handling for AquaForge API.

All routers should use these exceptions for consistent error responses.
"""

import logging
from enum import Enum

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


class ErrorCode(str, Enum):
    """Standard error codes for API responses."""

    VALIDATION_ERROR = "VALIDATION_ERROR"
    OPTIMIZATION_FAILED = "OPTIMIZATION_FAILED"
    FILE_UPLOAD_ERROR = "FILE_UPLOAD_ERROR"
    DATA_PROCESSING_ERROR = "DATA_PROCESSING_ERROR"
    NOT_FOUND = "NOT_FOUND"
    INTERNAL_ERROR = "INTERNAL_ERROR"


class AppException(HTTPException):
    """Base application exception with error code support."""

    def __init__(
        self,
        status_code: int,
        code: ErrorCode,
        message: str,
        details: dict | None = None,
    ):
        self.code = code
        self.message = message
        self.details = details or {}
        super().__init__(
            status_code=status_code,
            detail={
                "code": code.value,
                "message": message,
                "details": self.details,
            },
        )


class ValidationError(AppException):
    """Raised when input data fails validation."""

    def __init__(self, message: str, details: dict | None = None):
        super().__init__(400, ErrorCode.VALIDATION_ERROR, message, details)


class OptimizationError(AppException):
    """Raised when optimization fails."""

    def __init__(self, message: str, details: dict | None = None):
        super().__init__(500, ErrorCode.OPTIMIZATION_FAILED, message, details)


class FileUploadError(AppException):
    """Raised when file upload/processing fails."""

    def __init__(self, message: str, details: dict | None = None):
        super().__init__(400, ErrorCode.FILE_UPLOAD_ERROR, message, details)


class DataProcessingError(AppException):
    """Raised when data processing fails."""

    def __init__(self, message: str, details: dict | None = None):
        super().__init__(500, ErrorCode.DATA_PROCESSING_ERROR, message, details)


async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    """Global exception handler for AppException."""
    logger.error(
        f"[{exc.code.value}] {exc.message}",
        extra={"details": exc.details, "path": request.url.path},
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "code": exc.code.value,
            "message": exc.message,
            "details": exc.details,
        },
    )
