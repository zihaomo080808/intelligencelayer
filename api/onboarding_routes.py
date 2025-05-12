"""
API routes for handling onboarding messages and profile extraction
"""
from fastapi import APIRouter, HTTPException, Body
from pydantic import BaseModel
from typing import Dict, Any, Optional, List
import logging
import json

from onboarding_messages import process_onboarding_message, extract_name_from_greeting

# Configure logging
logger = logging.getLogger(__name__)

router = APIRouter()

class OnboardingMessageRequest(BaseModel):
    """Request model for processing onboarding messages"""
    message: str
    step: int = 0
    profile: Optional[Dict[str, Any]] = None
    user_id: Optional[str] = None

class OnboardingResponse(BaseModel):
    """Response model for onboarding messages"""
    profile: Dict[str, Any]
    next_question: Optional[str] = None
    complete: bool = False

@router.post("/onboarding/process", response_model=OnboardingResponse, tags=["onboarding"])
async def process_message(request: OnboardingMessageRequest):
    """
    Process an onboarding message and extract profile information
    
    Request:
    - message: The user's message
    - step: The current onboarding step (0 = name, 1 = background, 2 = interests)
    - profile: The existing user profile (if any)
    - user_id: Optional user ID for tracking
    
    Returns:
    - Updated profile information
    - Next question to ask (if any)
    - Whether onboarding is complete
    """
    try:
        logger.info(f"Processing onboarding message for step {request.step}")
        
        # Process the message
        updated_profile = await process_onboarding_message(
            request.message, 
            request.step, 
            request.profile or {}
        )
        
        # Determine next question and completion status
        next_question = None
        complete = False
        
        # Step 0: Asked for name, next ask for background
        if request.step == 0:
            name = updated_profile.get('name', 'there')
            next_question = f"Nice to meet you, {name}! Where are you located, where have you studied, and what are you currently working on?"
        
        # Step 1: Asked for background, next ask for interests
        elif request.step == 1:
            next_question = "What are your top interests and skills? (Feel free to list several)"
        
        # Step 2: Asked for interests, onboarding is complete
        elif request.step == 2:
            name = updated_profile.get('name', 'there')
            next_question = f"Thanks {name}! I've got your profile set up. How can I help you today?"
            complete = True
        
        logger.info(f"Returning updated profile with {len(updated_profile)} fields")
        return OnboardingResponse(
            profile=updated_profile,
            next_question=next_question,
            complete=complete
        )
        
    except Exception as e:
        logger.error(f"Error processing onboarding message: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing message: {str(e)}")

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