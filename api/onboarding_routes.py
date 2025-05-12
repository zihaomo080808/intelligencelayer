"""
API routes for handling onboarding messages and profile extraction
"""
from fastapi import APIRouter, HTTPException, Body
from pydantic import BaseModel
from typing import Dict, Any, Optional, List
import logging
import json

from onboarding_messages import process_onboarding_message, extract_name_from_greeting
from perplexity_client import query_user_background
from embeddings.embedder import get_embedding

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
        
        # Step 2: Asked for interests, onboarding is complete - generate bio and embedding
        elif request.step == 2:
            name = updated_profile.get('name', 'there')

            # Generate bio using Perplexity if not already present
            if not updated_profile.get('bio'):
                try:
                    logger.info(f"Generating bio for {name} using Perplexity")
                    bio = await query_user_background(updated_profile)

                    if bio:
                        updated_profile['bio'] = bio
                        logger.info(f"Successfully generated bio for {name}")
                    else:
                        logger.warning(f"Could not generate bio for {name}, using fallback")
                        # Fallback bio generation if Perplexity fails
                        interests_str = ", ".join(updated_profile.get('interests', []))
                        location = updated_profile.get('location', 'unknown location')
                        updated_profile['bio'] = f"{name} is from {location} with interests in {interests_str}."
                except Exception as e:
                    logger.error(f"Error generating bio: {str(e)}")
                    # Fallback if Perplexity API fails
                    interests_str = ", ".join(updated_profile.get('interests', []))
                    location = updated_profile.get('location', 'unknown location')
                    updated_profile['bio'] = f"{name} is from {location} with interests in {interests_str}."

            # Generate embedding from bio
            try:
                if updated_profile.get('bio'):
                    logger.info(f"Generating embedding for {name}")
                    embedding = get_embedding(updated_profile['bio'])
                    updated_profile['embedding'] = embedding
                    logger.info(f"Successfully generated embedding for {name}")
            except Exception as e:
                logger.error(f"Error generating embedding: {str(e)}")

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

@router.get("/onboarding/profile-info/{user_id}", response_model=Dict[str, Any], tags=["onboarding"])
async def get_profile_info(user_id: str):
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
        # NOTE: In a production app, you'd retrieve this from a database
        # For this example, we'll return placeholder data
        logger.info(f"Retrieving profile info for user {user_id}")
        return {
            "user_id": user_id,
            "bio_available": True,
            "embedding_available": True,
            "message": "Profile information successfully generated during onboarding"
        }
    except Exception as e:
        logger.error(f"Error retrieving profile info: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error retrieving profile info: {str(e)}")