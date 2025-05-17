"""
API routes for handling session information
"""
from fastapi import APIRouter, HTTPException
from typing import Dict, Any
import logging

from session_service import session_service

# Configure logging
logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/session-info", response_model=Dict[str, Any], tags=["session"])
async def get_session_info():
    """
    Get current server session information
    
    This endpoint provides information about the current server session,
    including the session ID and start time. Clients can use this to
    detect server restarts.
    
    Returns:
        Dictionary containing session information
    """
    try:
        logger.info("Session info requested")
        return session_service.get_session_info()
    except Exception as e:
        logger.error(f"Error retrieving session info: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error retrieving session info: {str(e)}")