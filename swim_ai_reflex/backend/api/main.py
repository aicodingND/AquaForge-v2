"""
FastAPI Application Factory

Creates and configures the standalone FastAPI application with all routers,
middleware, and exception handlers.
"""

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from swim_ai_reflex.backend.core.settings import get_settings
from swim_ai_reflex.backend.utils.observability import (
    RequestIdMiddleware,
    setup_logging,
    setup_telemetry,
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup/shutdown events."""
    settings = get_settings()

    # Initialize structured logging
    setup_logging(log_level=settings.log_level, environment=settings.environment)

    # Startup
    logger.info("AquaForge FastAPI Backend starting up...")
    logger.info("Upload directory: %s", settings.upload_dir)
    logger.info("Environment: %s", settings.environment)
    logger.info("Default optimizer: %s", settings.default_optimizer)
    yield
    # Shutdown
    logger.info("AquaForge FastAPI Backend shutting down...")


def create_app() -> FastAPI:
    """
    Factory function to create the FastAPI application.

    Returns:
        Configured FastAPI application instance
    """
    settings = get_settings()

    app = FastAPI(
        title="AquaForge API",
        description="Swim Meet Optimization API - Backend services for AquaForge.ai",
        version="1.0.0",
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
        lifespan=lifespan,
    )

    # Request ID middleware (adds X-Request-ID header)
    app.add_middleware(RequestIdMiddleware)

    # Configure CORS from settings
    origins = list(settings.cors_origins_list)

    # Add production origins from environment
    railway_domain = os.getenv("RAILWAY_PUBLIC_DOMAIN")
    render_url = os.getenv("RENDER_EXTERNAL_URL")
    frontend_url = os.getenv("FRONTEND_URL")

    if railway_domain:
        origins.append(f"https://{railway_domain}")
    if render_url:
        origins.append(render_url)
    if frontend_url:
        origins.append(frontend_url)

    # Only allow all origins in development
    allow_all = settings.is_development

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] if allow_all else origins,
        allow_credentials=not allow_all,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # OpenTelemetry tracing (if configured)
    setup_telemetry(app)

    # Global exception handler
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        logger.error("Unhandled exception: %s", exc, exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal server error",
                "detail": str(exc) if settings.debug else None,
            },
        )

    # Import and include routers
    from swim_ai_reflex.backend.api.routers import (
        analytics,
        championship,
        data,
        dual_meet,
        export,
        health,
        historical,
        intelligence,
        live_tracker,
        optimization,
    )

    app.include_router(health.router, prefix="/api/v1", tags=["Health"])
    app.include_router(
        optimization.router, prefix="/api/v1", tags=["Optimization (Legacy)"]
    )
    app.include_router(data.router, prefix="/api/v1", tags=["Data"])
    app.include_router(export.router, prefix="/api/v1", tags=["Export"])
    app.include_router(analytics.router, prefix="/api/v1", tags=["Analytics"])

    # New pipeline-based routers (v2)
    app.include_router(dual_meet.router, prefix="/api/v2", tags=["Dual Meet"])
    app.include_router(championship.router, prefix="/api/v2", tags=["Championship"])

    # Live tracking
    app.include_router(live_tracker.router, prefix="/api/v1", tags=["Live Tracking"])

    # Historical data
    app.include_router(historical.router, prefix="/api/v1", tags=["Historical"])

    # Intelligence analysis
    app.include_router(intelligence.router, prefix="/api/v1", tags=["Intelligence"])

    return app


# Create the default application instance
api_app = create_app()
