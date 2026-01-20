"""
Health Check Router

Provides endpoints for service health monitoring and status checks.
"""

import os
import sys
from datetime import datetime, timezone

from fastapi import APIRouter

from swim_ai_reflex.backend.api.models import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Check the health status of the API and its dependencies.

    Returns:
        Health status with service availability information
    """
    services = {
        "api": "healthy",
        "python": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
    }

    # Check if Gurobi is available
    import importlib.util

    if importlib.util.find_spec("gurobipy") is not None:
        services["gurobi"] = "available"
    else:
        services["gurobi"] = "not installed"

    # Check pandas
    try:
        import pandas

        services["pandas"] = pandas.__version__
    except ImportError:
        services["pandas"] = "not installed"

    return HealthResponse(
        status="healthy",
        timestamp=datetime.now(timezone.utc),
        version=os.getenv("APP_VERSION", "1.0.0"),
        services=services,
    )


@router.get("/ready")
async def readiness_check():
    """
    Kubernetes-style readiness probe.

    Returns:
        Simple ready status
    """
    return {"ready": True}


@router.get("/live")
async def liveness_check():
    """
    Kubernetes-style liveness probe.

    Returns:
        Simple alive status
    """
    return {"alive": True}
