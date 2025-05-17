"""
session_service.py - Manages server session information

This module provides functionality to generate and track server session IDs,
which helps identify when the server has been restarted.
"""

import logging
import time
import uuid
from typing import Dict, Any

# Configure logging
logger = logging.getLogger(__name__)

class SessionService:
    """
    Service for managing server session information.
    
    This class generates a unique session ID when the server starts and
    provides methods to access this ID, allowing clients to detect server restarts.
    """
    
    def __init__(self):
        """Initialize the session service with a new session ID and timestamp."""
        self._session_id = str(uuid.uuid4())
        self._start_time = time.time()
        logger.info(f"New server session started with ID: {self._session_id}")
        
    @property
    def session_id(self) -> str:
        """Get the current server session ID."""
        return self._session_id
    
    @property
    def start_time(self) -> float:
        """Get the session start timestamp."""
        return self._start_time
    
    def get_session_info(self) -> Dict[str, Any]:
        """
        Get complete session information.
        
        Returns:
            Dictionary containing session ID and start time information.
        """
        return {
            "session_id": self._session_id,
            "start_time": self._start_time,
            "start_time_formatted": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(self._start_time))
        }


# Create a singleton instance for use throughout the application
session_service = SessionService()