"""
Base Service Class
Provides common functionality for all services including logging and standard response formatting.
"""
from typing import Dict, Any, Optional
import logging
from datetime import datetime

class BaseService:
    """
    Abstract base class for all services.
    Provides standardized logging and response structure.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def _success(self, data: Any = None, message: str = "Success", metadata: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Standard success response format.
        
        Args:
            data: The payload to return
            message: Human readable success message
            metadata: Optional additional metadata
            
        Returns:
            Dict with standard response structure
        """
        return {
            "success": True,
            "message": message,
            "data": data,
            "error": None,
            "timestamp": datetime.now().isoformat(),
            "metadata": metadata or {}
        }
    
    def _error(self, message: str, code: str = "UNKNOWN_ERROR", details: Any = None) -> Dict[str, Any]:
        """
        Standard error response format.
        
        Args:
            message: Human readable error message
            code: Error code string classification
            details: Optional technical details (stack trace, validation errors)
            
        Returns:
            Dict with standard response structure
        """
        self.logger.error(f"{code}: {message}")
        if details:
            self.logger.error(f"Details: {details}")
            
        return {
            "success": False,
            "message": message,
            "data": None,
            "error": {
                "code": code,
                "details": details
            },
            "timestamp": datetime.now().isoformat()
        }
    
    def log_info(self, message: str):
        """Log info message."""
        self.logger.info(message)
        
    def log_warning(self, message: str):
        """Log warning message."""
        self.logger.warning(message)

    def log_error(self, message: str):
        """Log error message."""
        self.logger.error(message)
