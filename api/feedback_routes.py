"""
API routes for handling feedback and profile updates.
"""
import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any, Optional
from pydantic import BaseModel
from datetime import datetime

from database.session import get_db
from profiles.enhanced_profiles import update_user_embedding_enhanced, batch_update_profiles
from feedback.conversation import get_or_create_conversation
from agents.conversation_agent import update_conversation_with_agent_response

# Configure logging
logger = logging.getLogger(__name__)

# Initialize FastAPI router
router = APIRouter()

# Define model for conversation requests
class ConversationRequest(BaseModel):
    user_id: str
    item_id: str
    message: str
    context: Optional[Dict[str, Any]] = None

@router.post("/feedback/update-profiles")
async def update_all_profiles(
    days_back: int = 30,
    max_users: int = 100,
    db: AsyncSession = Depends(get_db)
):
    """
    Update all user profiles with recent feedback.
    
    This endpoint is designed to be called on a schedule (e.g., daily) to
    update user embeddings based on their recent feedback.
    
    Args:
        days_back: Number of days to look back for feedback
        max_users: Maximum number of users to update in one batch
    """
    try:
        result = await batch_update_profiles(db, days_back, max_users)
        return result
    except Exception as e:
        logger.error(f"Error updating profiles: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/feedback/update-profile/{user_id}")
async def update_single_profile(
    user_id: str,
    days_back: int = 30,
    db: AsyncSession = Depends(get_db)
):
    """
    Update a single user's profile with recent feedback.
    
    Args:
        user_id: User ID to update
        days_back: Number of days to look back for feedback
    """
    try:
        await update_user_embedding_enhanced(db, user_id, days_back)
        return {"status": "success", "message": f"Profile updated for user {user_id}"}
    except Exception as e:
        logger.error(f"Error updating profile for user {user_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/conversation")
async def handle_conversation(
    request: ConversationRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Process a user message and return an agent response.

    This endpoint is used by the chat interface to communicate with the AI assistant.

    Args:
        request: The conversation request containing user message and context
    """
    try:
        logger.info(f"Received conversation request from {request.user_id} about item {request.item_id}")

        # Get or create the conversation
        conversation = await get_or_create_conversation(db, request.user_id, request.item_id)

        # Update the conversation with the user message
        conversation.transcript += f"\n[{datetime.utcnow()}] User: {request.message}"
        conversation.message_count += 1

        # Generate agent response
        agent_response = await update_conversation_with_agent_response(
            conversation, request.context or {}
        )

        # Save the conversation
        await db.commit()

        return {
            "status": "success",
            "conversation_id": conversation.id,
            "response": agent_response
        }

    except Exception as e:
        logger.error(f"Error processing conversation: {str(e)}")
        return {
            "status": "error",
            "message": str(e),
            "response": f"I'm having trouble connecting to my backend. Let's talk about {request.context.get('title', 'this opportunity') if request.context else 'this opportunity'} later!"
        }