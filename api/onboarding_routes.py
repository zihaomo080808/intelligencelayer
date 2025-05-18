"""
API routes for handling onboarding messages and profile extraction
"""
from fastapi import APIRouter, HTTPException, Body, Depends
from pydantic import BaseModel
from typing import Dict, Any, Optional, List
import logging
import json
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from config import settings

from onboarding_messages import process_onboarding_message, extract_name_from_greeting
from perplexity_client import query_user_background
from embeddings.embedder import get_embedding
from database.session import get_db
from database.models import UserProfile

# Configure logging
logger = logging.getLogger(__name__)

router = APIRouter()

class OnboardingMessageRequest(BaseModel):
    """Request model for processing onboarding messages"""
    message: str
    step: int
    profile: Optional[Dict[str, Any]] = None
    user_id: str

class OnboardingResponse(BaseModel):
    """Response model for onboarding messages"""
    profile: Dict[str, Any]
    next_question: Optional[str] = ""
    is_complete: bool

@router.post("/onboarding/process", response_model=OnboardingResponse, tags=["onboarding"])
async def process_message(request: OnboardingMessageRequest, db: AsyncSession = Depends(get_db)):
    """
    Process an onboarding message and update the user profile
    """
    try:
        logger.info(f"Processing onboarding message for step {request.step}")
        logger.info(f"Message: {request.message[:50]}...")
        logger.info(f"Profile exists: {request.profile is not None}")
        logger.info(f"User ID: {request.user_id}")
        
        # Process the message and get updated profile
        profile, next_question, is_complete = await process_onboarding_message(
            request.message,
            request.step,
            request.profile or {},
            request.user_id,
            db
        )
        
        # Ensure next_question is never None
        safe_next_question = next_question if next_question is not None else ""
        
        return OnboardingResponse(
            profile=profile,
            next_question=safe_next_question,
            is_complete=is_complete
        )
        
    except Exception as e:
        # Get detailed stack trace
        import traceback
        stack_trace = traceback.format_exc()
        
        # Log detailed error information
        logger.error(f"Error processing onboarding message: {str(e)}")
        logger.error(f"Stack trace: {stack_trace}")
        
        # Return a more detailed error message to the client
        error_detail = {
            "message": str(e),
            "type": type(e).__name__,
            "stack_trace": stack_trace if settings.DEBUG else "Enable DEBUG mode for stack trace"
        }
        raise HTTPException(status_code=500, detail=str(error_detail))

@router.post("/onboarding/extract-name", response_model=Dict[str, Any], tags=["onboarding"])
async def extract_name(message: Dict[str, str] = Body(...)):
    """
    Extract just the name from a greeting message

    Request:
    - message: The user's first message

    Returns:
    - Extracted name
    """
    try:
        logger.info("Extracting name from greeting message")
        name = await extract_name_from_greeting(message.get("text", ""))
        return {"name": name}
    except Exception as e:
        logger.error(f"Error extracting name: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error extracting name: {str(e)}")

@router.get("/onboarding/profile-info/{user_id}", response_model=Dict[str, Any], tags=["onboarding"])
async def get_profile_info(user_id: str, db: AsyncSession = Depends(get_db)):
    """
    Get a user's profile information including bio and embedding

    This endpoint is used after onboarding to retrieve the generated
    bio and embedding for a user.

    Parameters:
    - user_id: The unique identifier for the user

    Returns:
    - User profile information including bio and embedding
    """
    try:
        # Query the database for the user's profile
        result = await db.execute(
            select(UserProfile).where(UserProfile.user_id == user_id)
        )
        profile = result.scalar_one_or_none()
        
        if profile:
            return {
                "user_id": user_id,
                "username": profile.username,
                "bio_available": bool(profile.bio),
                "embedding_available": bool(profile.embedding),
                "bio": profile.bio,
                "location": profile.location,
                "stances": profile.stances,
                "message": "Profile information retrieved successfully"
            }
        else:
            return {
                "user_id": user_id,
                "username": None,
                "bio_available": False,
                "embedding_available": False,
                "message": "No profile found for this user"
            }
    except Exception as e:
        logger.error(f"Error retrieving profile info: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))