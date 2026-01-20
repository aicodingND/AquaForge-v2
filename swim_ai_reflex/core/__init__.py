"""
AquaForge Core Module

This module provides the data layer for AquaForge, supporting direct HyTek
database ingestion and analytics-optimized storage.

Components:
    - data.entities: Pydantic models for swim data
    - data.loaders: Data ingestion from various sources
    - data.mappers: Transform raw data to domain models
    - data.repository: Database access layer
    - data.service: High-level data operations
"""

__version__ = "1.0.0"
