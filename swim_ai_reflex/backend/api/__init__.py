"""
FastAPI Backend API Module

This module provides a standalone FastAPI application that wraps
the existing backend services, enabling:
- Independent API access for external clients
- Microservices-style architecture
- Better separation of concerns
- Easier testing and scaling
"""

from swim_ai_reflex.backend.api.main import api_app, create_app

__all__ = ["create_app", "api_app"]
