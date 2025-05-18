# api/twilio_routes.py
import logging
import traceback
from datetime import datetime
from fastapi import APIRouter, Form, Request, Response, Depends
from typing import Optional, Dict, Any, List
from pydantic import BaseModel
from twilio.twiml.messaging_response import MessagingResponse
from twilio.request_validator import RequestValidator
from sqlalchemy.ext.asyncio import AsyncSession
import os

from profiles.profiles import get_profile, update_profile
from classifier.model import predict_stance
from embeddings.embedder import get_embedding
from matcher.matcher import match_items, OPPS
from generator.generator import generate_recommendation
from database.session import get_db
from database.models import UserConversation
from feedback.conversation import (
    get_or_create_conversation,
    is_conversation_complete,
    analyze_conversation,
    calculate_feedback_confidence,
    record_nuanced_feedback
)
from config import settings
from agents.conversation_agent import _extract_conversation_messages

# Configure logging
logger = logging.getLogger(__name__)

router = APIRouter()

# Default stances to apply to all new users
DEFAULT_STANCES = ["startup-interested", "tech-positive", "Mission-Driven"]

# Helper function to validate Twilio requests
async def validate_twilio_request(request: Request) -> bool:
    """Validates that incoming requests are from Twilio"""
    validator = RequestValidator(settings.TWILIO_AUTH_TOKEN)
    
    # Get the request URL and POST data
    request_url = str(request.url)
    form_data = await request.form()
    signature = request.headers.get("X-Twilio-Signature", "")
    
    # Convert form data to dict
    form_dict = {}
    for key, value in form_data.items():
        form_dict[key] = value
        
    return validator.validate(request_url, form_dict, signature)

@router.post("/sms")
async def handle_sms(
    request: Request,
    From: str = Form(...),  # Phone number of sender
    Body: str = Form(...),  # Message content
    City: Optional[str] = Form(None)  # Optional location data from Twilio
):
    # Validate the request is from Twilio
    if not settings.DEBUG:
        is_valid = await validate_twilio_request(request)
        if not is_valid:
            return Response("Invalid request", status_code=403)
    
    # Create a response object
    resp = MessagingResponse()
    
    # Use phone number as user_id
    user_id = From
    
    # Check if this is an existing user
    profile = await get_profile(user_id)
    
    if not profile:
        # New user - create profile
        predicted_stances = predict_stance(Body)
        
        # Combine predicted stances with default stances
        # Using set to avoid duplicates
        stances = list(set(predicted_stances + DEFAULT_STANCES))
        
        # Build embedding from message content and city if available
        text_to_embed = Body
        if City:
            text_to_embed = f"{Body}\n\nLocation: {City}"
        embedding = get_embedding(text_to_embed)
        
        # Store new profile
        await update_profile(
            user_id=user_id,
            bio=Body,
            stances=stances,
            embedding=embedding,
            location=City
        )
        
        # Welcome message
        resp.message("Welcome! I've created your profile based on your message.")
    else:
        # Existing user - generate recommendations
        if Body.lower().startswith("update:"):
            # Update profile if message starts with "update:"
            new_bio = Body[7:].strip()  # Remove "update:" prefix
            
            # Get stances from the new bio
            predicted_stances = predict_stance(new_bio)
            
            # Ensure default stances are preserved
            stances = list(set(predicted_stances + DEFAULT_STANCES))
            
            # Build embedding
            text_to_embed = new_bio
            location = profile.location
            if location:
                text_to_embed = f"{new_bio}\n\nLocation: {location}"
            embedding = get_embedding(text_to_embed)

            # Fetch conversation history if available
            conversation_history = []
            # Try to get the latest conversation for this user (and item if available)
            try:
                from sqlalchemy import select, desc
                result = await db.execute(
                    select(UserConversation)
                    .where(UserConversation.user_id == user_id)
                    .order_by(desc(UserConversation.started_at))
                )
                conversation = result.scalars().first()
                if conversation and conversation.transcript:
                    messages = _extract_conversation_messages(conversation.transcript)
                    conversation_history = messages[-3:] if len(messages) >= 3 else messages
            except Exception as e:
                logger.warning(f"Could not fetch conversation history: {e}")

            # Update profile
            await update_profile(
                user_id=user_id,
                bio=new_bio,
                stances=stances,
                embedding=embedding,
                location=location,
                conversation_history=conversation_history
            )
            
            resp.message("Your profile has been updated! Text me again for new recommendations.")
        else:
            # Generate recommendations based on existing profile
            if profile.location:
                # Filter by location if available
                items = match_items(
                    user_embedding=profile.embedding,
                    stances=profile.stances,
                    only_type=None,
                    location_scope="cities",
                    cities=[profile.location]
                )
            else:
                items = match_items(
                    user_embedding=profile.embedding,
                    stances=profile.stances,
                    only_type=None
                )
                
            # Generate recommendation text
            rec = generate_recommendation(
                {"user_id": profile.user_id, "stances": profile.stances, "location": profile.location},
                items
            )
            
            # Send recommendation via SMS
            resp.message(rec)
    
    return Response(content=str(resp), media_type="application/xml")

#==============================================================================
# Enhanced Conversation and Feedback Handling
#==============================================================================

class ConversationUpdateRequest(BaseModel):
    """Model for conversation update requests."""
    user_id: str
    item_id: str
    message: str

    # Optional metadata
    feedback_hint: Optional[str] = None  # 'positive', 'negative', or None
    context: Optional[Dict[str, Any]] = None

@router.post("/feedback/conversation")
async def update_conversation(
    request: ConversationUpdateRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Update a conversation with a new message and extract implicit feedback.

    This endpoint is used for tracking conversations and extracting feedback
    based on the user's messages and engagement.
    """
    try:
        # Get or create the conversation
        conversation = await get_or_create_conversation(db, request.user_id, request.item_id)

        # Update the conversation
        conversation.transcript += f"\n[{datetime.utcnow()}] User: {request.message}"
        conversation.message_count += 1

        # Process feedback hint if provided
        if request.feedback_hint:
            if request.feedback_hint.lower() == "positive":
                await process_explicit_feedback(
                    db,
                    request.user_id,
                    request.item_id,
                    "like",
                    1.0,  # High confidence for explicit feedback
                    conversation.id
                )
            elif request.feedback_hint.lower() == "negative":
                await process_explicit_feedback(
                    db,
                    request.user_id,
                    request.item_id,
                    "skip",
                    1.0,  # High confidence for explicit feedback
                    conversation.id
                )

        # Check if we should finalize the conversation
        elif is_conversation_complete(conversation):
            await process_completed_conversation(db, conversation)

        # Save changes
        await db.commit()

        return {"status": "success", "conversation_id": conversation.id}

    except Exception as e:
        logger.error(f"Error updating conversation: {str(e)}")
        return {"status": "error", "message": str(e)}

@router.post("/feedback/explicit")
async def record_explicit_feedback(
    user_id: str,
    item_id: str,
    feedback_type: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Record explicit feedback from a user.

    Args:
        user_id: User ID
        item_id: Item ID
        feedback_type: Type of feedback ('like' or 'skip')
    """
    try:
        await process_explicit_feedback(
            db,
            user_id,
            item_id,
            feedback_type,
            1.0  # High confidence for explicit feedback
        )

        return {"status": "success"}

    except Exception as e:
        logger.error(f"Error recording explicit feedback: {str(e)}")
        return {"status": "error", "message": str(e)}

@router.get("/conversation/{conversation_id}")
async def get_conversation(
    conversation_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Get a conversation by ID.
    """
    try:
        conversation = await db.get(UserConversation, conversation_id)
        if not conversation:
            return {"status": "error", "message": "Conversation not found"}

        return {
            "status": "success",
            "conversation": {
                "id": conversation.id,
                "user_id": conversation.user_id,
                "item_id": conversation.item_id,
                "transcript": conversation.transcript,
                "message_count": conversation.message_count,
                "duration_seconds": conversation.duration_seconds,
                "started_at": conversation.started_at,
                "ended_at": conversation.ended_at,
                "analysis": conversation.analysis
            }
        }

    except Exception as e:
        logger.error(f"Error getting conversation: {str(e)}")
        return {"status": "error", "message": str(e)}

async def process_completed_conversation(
    db: AsyncSession,
    conversation: UserConversation
):
    """
    Process a completed conversation to extract feedback.

    Args:
        db: Database session
        conversation: The conversation to process
    """
    try:
        # Mark conversation as ended
        conversation.ended_at = datetime.utcnow()
        conversation.duration_seconds = int(
            (conversation.ended_at - conversation.started_at).total_seconds()
        )

        # Analyze conversation
        analysis = await analyze_conversation(conversation.transcript, conversation.item_id)
        conversation.analysis = analysis

        # Calculate feedback confidence
        confidence = calculate_feedback_confidence(
            analysis,
            {
                "message_count": conversation.message_count,
                "duration_seconds": conversation.duration_seconds
            }
        )

        # Determine feedback type based on interest level
        interest_level = analysis.get("interest_level", 5)
        if interest_level >= 7:
            feedback_type = "like"
        elif interest_level <= 3:
            feedback_type = "skip"
        else:
            feedback_type = "neutral"

        # Get item embedding
        item_embedding = await get_item_embedding(db, conversation.item_id)

        # Record feedback
        await record_nuanced_feedback(
            db=db,
            user_id=conversation.user_id,
            item_id=conversation.item_id,
            feedback_type=feedback_type,
            confidence=confidence,
            item_embedding=item_embedding,
            conversation_id=conversation.id
        )

        logger.info(
            f"Processed conversation {conversation.id} - "
            f"Feedback: {feedback_type}, Confidence: {confidence:.2f}"
        )

    except Exception as e:
        logger.error(f"Error processing conversation: {str(e)}")
        raise

async def process_explicit_feedback(
    db: AsyncSession,
    user_id: str,
    item_id: str,
    feedback_type: str,
    confidence: float,
    conversation_id: Optional[int] = None
):
    """
    Process explicit feedback from a user.

    Args:
        db: Database session
        user_id: User ID
        item_id: Item ID
        feedback_type: Type of feedback ('like' or 'skip')
        confidence: Confidence score
        conversation_id: Optional conversation ID
    """
    try:
        # Get item embedding
        item_embedding = await get_item_embedding(db, item_id)

        # Record feedback
        await record_nuanced_feedback(
            db=db,
            user_id=user_id,
            item_id=item_id,
            feedback_type=feedback_type,
            confidence=confidence,
            item_embedding=item_embedding,
            conversation_id=conversation_id
        )

        logger.info(
            f"Processed explicit feedback for user {user_id}, item {item_id} - "
            f"Feedback: {feedback_type}, Confidence: {confidence:.2f}"
        )

    except Exception as e:
        logger.error(f"Error processing explicit feedback: {str(e)}")
        raise

async def get_item_embedding(db: AsyncSession, item_id: str) -> Optional[List[float]]:
    """
    Get the embedding for an item.

    Args:
        db: Database session
        item_id: Item ID

    Returns:
        List[float]: Item embedding if found, None otherwise
    """
    # First, check in opportunities data
    for opp in OPPS:
        if opp.get("id") == item_id and "embedding" in opp:
            return opp["embedding"]

    # If not found, return None
    return None


class TwoWayConversationRequest(BaseModel):
    """Model for two-way conversation requests with agent responses."""
    user_id: str
    item_id: str
    message: str
    opportunity_details: Optional[Dict[str, Any]] = None

    # Optional metadata
    feedback_hint: Optional[str] = None  # 'positive', 'negative', or None

@router.post("/feedback/chat")
async def two_way_conversation(
    request: TwoWayConversationRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Process a user message, log it, and generate an agent response.

    This endpoint handles the full two-way conversation cycle:
    1. Logs the user message
    2. Analyzes it for implicit feedback
    3. Generates an agent response with Gen Z tone
    4. Returns the agent response for display

    Args:
        request: The conversation request with user message and context
    """
    try:
        # Import the conversation agent
        from agents.conversation_agent import update_conversation_with_agent_response

        # Log request details
        logger.warning(f"Received conversation request from {request.user_id} about item {request.item_id}")
        logger.warning(f"User message: {request.message}")
        logger.warning(f"Opportunity details: {request.opportunity_details}")

        # Get or create the conversation
        conversation = await get_or_create_conversation(db, request.user_id, request.item_id)
        logger.warning(f"Conversation ID: {conversation.id}")

        # Update with user message
        conversation.transcript += f"\n[{datetime.utcnow()}] User: {request.message}"
        conversation.message_count += 1
        logger.warning(f"Updated transcript, message count: {conversation.message_count}")

        # Process any explicit feedback hint
        if request.feedback_hint:
            if request.feedback_hint.lower() == "positive":
                await process_explicit_feedback(
                    db, request.user_id, request.item_id, "like", 1.0, conversation.id
                )
            elif request.feedback_hint.lower() == "negative":
                await process_explicit_feedback(
                    db, request.user_id, request.item_id, "skip", 1.0, conversation.id
                )

        # Get opportunity details if not provided
        opportunity = request.opportunity_details or {}
        if not opportunity and request.item_id:
            # Try to find opportunity in OPPS
            for opp in OPPS:
                if opp.get("id") == request.item_id:
                    opportunity = opp
                    break

        # Generate agent response
        logger.warning(f"Calling update_conversation_with_agent_response with opportunity: {opportunity}")
        import traceback
        try:
            # First try to call get_agent_response directly to isolate issues
            from agents.conversation_agent import get_agent_response
            logger.warning("About to call get_agent_response directly")
            try:
                direct_response = await get_agent_response(conversation, opportunity)
                logger.warning(f"Direct get_agent_response succeeded: {direct_response[:100]}...")
            except Exception as direct_err:
                logger.error(f"Direct call to get_agent_response failed: {str(direct_err)}")
                logger.error(f"Traceback: {traceback.format_exc()}")

            # Now call the normal update function
            agent_response = await update_conversation_with_agent_response(
                conversation, opportunity
            )
            logger.warning(f"Generated agent response: {agent_response[:100]}...")
        except Exception as e:
            logger.error(f"Error in update_conversation_with_agent_response: {str(e)}")
            logger.error(f"Detailed traceback: {traceback.format_exc()}")
            # Provide a fallback response
            agent_response = f"I'm having trouble connecting to my backend. Let's talk about {opportunity.get('title', 'this opportunity')} another way!"

        # Save the conversation
        await db.commit()
        logger.warning("Saved conversation to database")

        # If conversation seems complete, analyze for implicit feedback
        if is_conversation_complete(conversation):
            await process_completed_conversation(db, conversation)
            await db.commit()

        return {
            "status": "success",
            "conversation_id": conversation.id,
            "agent_response": agent_response
        }

    except Exception as e:
        logger.error(f"Error in two-way conversation: {str(e)}")
        logger.error(traceback.format_exc())
        return {"status": "error", "message": str(e)}