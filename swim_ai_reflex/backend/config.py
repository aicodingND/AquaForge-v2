"""
Configuration settings for SwimAI Reflex application.
PERFORMANCE OPTIMIZED: Added performance and caching configurations
"""
from dataclasses import dataclass, field
from typing import List, Optional
from pathlib import Path


@dataclass
class SecurityConfig:
    """Security-related configuration"""
    upload_directory: str = "uploads"
    allowed_extensions: List[str] = field(default_factory=lambda: [".pdf", ".csv", ".xlsx", ".xls"])
    max_file_size_mb: int = 50
    max_files_per_upload: int = 10
    

@dataclass
class OptimizationConfig:
    """Optimization engine configuration"""
    default_max_iterations: int = 1000
    default_optimizer: str = "heuristic"  # or "gurobi"
    enable_caching: bool = True
    cache_ttl_seconds: int = 3600  # 1 hour
    max_cache_entries: int = 100  # PERFORMANCE: Limit cache size


@dataclass  
class UIConfig:
    """UI-related configuration"""
    theme: str = "dark"
    enable_animations: bool = True
    max_log_entries: int = 100  # PERFORMANCE: Limit log history


@dataclass
class PerformanceConfig:
    """Performance optimization settings"""
    lazy_load_analytics: bool = True  # PERFORMANCE: Defer analytics loading
    lazy_load_exports: bool = True    # PERFORMANCE: Defer export service loading
    batch_state_updates: bool = True  # PERFORMANCE: Reduce re-render frequency
    max_yield_frequency: int = 4      # PERFORMANCE: Max yields per operation
    async_pdf_parsing: bool = True    # PERFORMANCE: Parse PDFs in background
    enable_test_data: bool = True     # ENABLED FOR DEMO: Show load test data button
    

@dataclass
class AppConfig:
    """Main application configuration"""
    security: SecurityConfig = field(default_factory=SecurityConfig)
    optimization: OptimizationConfig = field(default_factory=OptimizationConfig)
    ui: UIConfig = field(default_factory=UIConfig)
    performance: PerformanceConfig = field(default_factory=PerformanceConfig)
    
    def ensure_directories(self):
        """Create necessary directories if they don't exist"""
        Path(self.security.upload_directory).mkdir(parents=True, exist_ok=True)


# Singleton configuration instance
_config: Optional[AppConfig] = None


def get_config() -> AppConfig:
    """Get the application configuration singleton"""
    global _config
    if _config is None:
        _config = AppConfig()
        _config.ensure_directories()
    return _config


def reset_config():
    """Reset configuration (mainly for testing)"""
    global _config
    _config = None
