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

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup/shutdown events."""
    # Startup
    logger.info("🚀 AquaForge FastAPI Backend starting up...")
    logger.info(f"📁 Upload directory: {os.getenv('UPLOAD_DIR', 'uploads')}")
    yield
    # Shutdown
    logger.info("🛑 AquaForge FastAPI Backend shutting down...")


def create_app() -> FastAPI:
    """
    Factory function to create the FastAPI application.

    Returns:
        Configured FastAPI application instance
    """
    app = FastAPI(
        title="AquaForge API",
        description="Swim Meet Optimization API - Backend services for AquaForge.ai",
        version="1.0.0",
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
        lifespan=lifespan,
    )

    # Configure CORS for frontend access
    origins = [
        "http://localhost:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "http://localhost:8001",
        "http://127.0.0.1:8001",
    ]

    # Add local network IPs if known or dynamic
    # In a real dev environment, we often allow all on local network

    # Add production origins from environment
    railway_domain = os.getenv("RAILWAY_PUBLIC_DOMAIN")
    render_url = os.getenv("RENDER_EXTERNAL_URL")

    if railway_domain:
        origins.append(f"https://{railway_domain}")
    if render_url:
        origins.append(render_url)

    # Allow all origins in development or if explicitly allowed
    is_dev = os.getenv("ENVIRONMENT", "development") == "development"
    allow_all = is_dev or os.getenv("CORS_ALLOW_ALL", "true").lower() == "true"

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] if allow_all else origins,
        allow_credentials=not allow_all,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Global exception handler
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        logger.error(f"Unhandled exception: {exc}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal server error",
                "detail": str(exc)
                if os.getenv("DEBUG", "false").lower() == "true"
                else None,
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

    # Live tracking (v2)
    app.include_router(live_tracker.router, tags=["Live Tracking"])

    return app


# Create the default application instance
api_app = create_app()
