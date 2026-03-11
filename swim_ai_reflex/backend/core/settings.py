"""
AquaForge.ai - Application Settings
Centralized configuration using pydantic-settings for environment variable support.
"""

from functools import lru_cache

try:
    from pydantic import Field
    from pydantic_settings import BaseSettings
except ImportError:
    # Fallback for older pydantic
    from pydantic import BaseSettings, Field  # type: ignore[no-redef]


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    Use .env file or export environment variables.
    """

    # ==========================================================================
    # Application
    # ==========================================================================
    app_name: str = Field(default="AquaForge.ai", description="Application name")
    app_version: str = Field(default="1.0.0", description="Application version")
    environment: str = Field(
        default="development",
        description="Environment: development, staging, production",
    )
    debug: bool = Field(default=False, description="Enable debug mode")

    # ==========================================================================
    # API Server
    # ==========================================================================
    api_host: str = Field(default="0.0.0.0", description="API host")
    api_port: int = Field(default=8001, description="API port")
    api_workers: int = Field(default=1, description="Number of Uvicorn workers")

    # ==========================================================================
    # Security & CORS
    # ==========================================================================
    cors_origins: list[str] = Field(
        default=["http://localhost:3000", "http://127.0.0.1:3000"],
        description="Allowed CORS origins",
    )
    cors_allow_credentials: bool = Field(
        default=True, description="Allow credentials in CORS"
    )
    secret_key: str = Field(
        default="change-me-in-production", description="Secret key for JWT"
    )

    # ==========================================================================
    # Database (Future)
    # ==========================================================================
    database_url: str | None = Field(
        default=None, description="PostgreSQL connection URL"
    )
    redis_url: str | None = Field(default=None, description="Redis connection URL")

    # ==========================================================================
    # Optimization
    # ==========================================================================
    default_optimizer: str = Field(
        default="aquaopt",
        description="Default optimizer: aquaopt, gurobi, or heuristic",
    )
    optimization_timeout_seconds: int = Field(
        default=300, description="Max optimization time"
    )
    enable_caching: bool = Field(
        default=True, description="Enable optimization result caching"
    )

    # ==========================================================================
    # File Upload
    # ==========================================================================
    upload_dir: str = Field(default="uploads", description="Upload directory")
    max_upload_size_mb: int = Field(
        default=50, description="Maximum upload file size in MB"
    )
    allowed_extensions: list[str] = Field(
        default=[".csv", ".xlsx", ".xls", ".pdf"], description="Allowed file extensions"
    )

    # ==========================================================================
    # Gurobi (Optional)
    # ==========================================================================
    wls_access_id: str | None = Field(default=None, alias="WLSACCESSID")
    wls_secret: str | None = Field(default=None, alias="WLSSECRET")
    license_id: str | None = Field(default=None, alias="LICENSEID")

    # ==========================================================================
    # Error Tracking (Sentry)
    # ==========================================================================
    sentry_dsn: str | None = Field(
        default=None, description="Sentry DSN for error tracking"
    )
    sentry_traces_sample_rate: float = Field(
        default=0.1, description="Sentry traces sample rate"
    )

    # ==========================================================================
    # Logging
    # ==========================================================================
    log_level: str = Field(default="INFO", description="Logging level")
    log_format: str = Field(default="json", description="Log format: json or text")

    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.environment.lower() == "production"

    @property
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.environment.lower() in ("development", "dev")

    @property
    def cors_origins_list(self) -> list[str]:
        """Get CORS origins as a list, handling both string and list inputs."""
        if isinstance(self.cors_origins, str):
            return [origin.strip() for origin in self.cors_origins.split(",")]
        return self.cors_origins

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        # Allow environment variables without prefix
        env_prefix = ""
        extra = "ignore"


@lru_cache
def get_settings() -> Settings:
    """
    Get cached settings instance.
    Use dependency injection in FastAPI routes.
    """
    return Settings()


# Convenience function for quick access
settings = get_settings()
