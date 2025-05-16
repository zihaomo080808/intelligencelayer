"""
Conversation analysis and management for nuanced feedback extraction.
"""
import json
import logging
from datetime import datetime
from typing import Dict, Any, List, Tuple, Optional

import numpy as np
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from openai import AsyncOpenAI

from config import settings
from database.models import UserConversation, UserFeedback

# Configure logging
logger = logging.getLogger(__name__)

# Initialize OpenAI client
client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

async def get_or_create_conversation(
    db: AsyncSession, 
    user_id: str, 
    item_id: str
) -> UserConversation:
    """
    Get an existing conversation or create a new one.
    
    Args:
        db: Database session
        user_id: User ID
        item_id: Item ID
        
    Returns:
        UserConversation: The conversation record
    """
    # Check for an existing active conversation
    stmt = select(UserConversation).where(
        UserConversation.user_id == user_id,
        UserConversation.item_id == item_id,
        UserConversation.ended_at.is_(None)
    )
    result = await db.execute(stmt)
    conversation = result.scalars().first()
    
    if conversation:
        return conversation
    
    # Create a new conversation
    conversation = UserConversation(
        user_id=user_id,
        item_id=item_id,
        transcript="",
        message_count=0,
        started_at=datetime.utcnow()
    )
    db.add(conversation)
    await db.flush()  # Get the ID without committing
    
    return conversation

def extract_item_id_from_conversation(conversation_history: str) -> Optional[str]:
    """
    Extract item ID from conversation history using simple heuristics.
    
    Args:
        conversation_history: The full conversation transcript
        
    Returns:
        str: Item ID if found, None otherwise
    """
    # Look for item ID in the conversation (simple implementation)
    # In a real system, you'd track this explicitly during the conversation
    import re
    
    # Look for patterns like "opportunity ID: ABC123" or similar
    match = re.search(r'(?:opportunity|item|id)[:\s]+([a-zA-Z0-9_-]+)', 
                      conversation_history, re.IGNORECASE)
    if match:
        return match.group(1)
    
    return None

def is_conversation_complete(conversation: UserConversation) -> bool:
    """
    Determine if a conversation is complete and ready for analysis.
    
    Args:
        conversation: The conversation record
        
    Returns:
        bool: True if the conversation appears complete
    """
    # Simple heuristics - in reality, you might have more sophisticated detection
    
    # If more than 3 messages exchanged
    if conversation.message_count >= 3:
        return True
        
    # Check for concluding phrases in the transcript
    conclusion_phrases = [
        "thank you", "thanks", "goodbye", "bye", 
        "not interested", "sign me up", "sounds good"
    ]
    
    for phrase in conclusion_phrases:
        if phrase in conversation.transcript.lower():
            return True
    
    return False

async def analyze_conversation(
    conversation_text: str, 
    item_id: str
) -> Dict[str, Any]:
    """
    Analyze conversation using OpenAI to extract interest level and other insights.
    
    Args:
        conversation_text: Full conversation transcript
        item_id: Item ID being discussed
        
    Returns:
        dict: Analysis results including interest level, likes, objections, questions
    """
    try:
        # Skip if OpenAI API key is not set (for testing)
        if not settings.OPENAI_API_KEY:
            logger.warning("OPENAI_API_KEY not set, skipping conversation analysis")
            return {
                "interest_level": 5,  # Neutral default
                "aspects_liked": [],
                "objections": [],
                "questions": []
            }
        
        prompt = f"""
        Analyze this conversation about opportunity {item_id}. 
        Extract the following information:
        
        1. Interest level (0-10 scale, where 0 is completely uninterested, 10 is extremely interested)
        2. Specific aspects the person liked (list)
        3. Objections or concerns raised (list)
        4. Questions asked (list)
        
        Return your analysis as a structured JSON object.
        
        Conversation:
        {conversation_text}
        """
        
        response = await client.chat.completions.create(
            model="gpt-4o",  # or "gpt-3.5-turbo" for lower cost
            messages=[
                {"role": "system", "content": "You are an AI assistant that analyzes conversations to extract interest levels and insights."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"}
        )
        
        # Parse the analysis
        analysis_text = response.choices[0].message.content
        analysis = json.loads(analysis_text)
        
        # Ensure expected fields exist
        required_fields = ["interest_level", "aspects_liked", "objections", "questions"]
        for field in required_fields:
            if field not in analysis:
                analysis[field] = [] if field != "interest_level" else 5
        
        return analysis
        
    except Exception as e:
        logger.error(f"Error analyzing conversation: {str(e)}")
        # Return a neutral analysis on error
        return {
            "interest_level": 5,
            "aspects_liked": [],
            "objections": [],
            "questions": []
        }

def calculate_feedback_confidence(
    analysis: Dict[str, Any], 
    engagement_metrics: Dict[str, Any]
) -> float:
    """
    Calculate confidence score for feedback based on conversation analysis.
    
    Args:
        analysis: Conversation analysis results
        engagement_metrics: Metrics about user engagement with the conversation
        
    Returns:
        float: Confidence score between 0.1 and 1.0
    """
    # Base score from interest level (0-1 scale)
    interest_score = analysis["interest_level"] / 10.0
    
    # Engagement factors
    msg_count = engagement_metrics.get("message_count", 0)
    msg_count_factor = min(msg_count / 5.0, 1.0)
    
    duration = engagement_metrics.get("duration_seconds", 0)
    time_factor = min(duration / 120.0, 1.0)  # Cap at 2 minutes
    
    # Questions reduce certainty
    question_count = len(analysis.get("questions", []))
    question_penalty = min(question_count * 0.1, 0.3)  # Cap penalty at 0.3
    
    # Calculate confidence (capped between 0.1-1.0)
    confidence = max(0.1, min(1.0, 
        interest_score * 0.6 + 
        msg_count_factor * 0.2 + 
        time_factor * 0.2 - 
        question_penalty
    ))
    
    return confidence

async def record_nuanced_feedback(
    db: AsyncSession,
    user_id: str,
    item_id: str,
    feedback_type: str,
    confidence: float,
    item_embedding: List[float] = None,
    conversation_id: int = None
) -> None:
    """
    Record user feedback with confidence score.
    
    Args:
        db: Database session
        user_id: User ID
        item_id: Item ID
        feedback_type: Type of feedback ('like', 'neutral', or 'skip')
        confidence: Confidence score (0.0-1.0)
        item_embedding: Optional item embedding
        conversation_id: Optional conversation ID
    """
    try:
        # Ensure the embedding is properly formatted for storage as ARRAY(Float)
        if item_embedding:
            # Make sure it's a list (not a numpy array or other format)
            if isinstance(item_embedding, np.ndarray):
                item_embedding = item_embedding.tolist()
            elif not isinstance(item_embedding, list):
                item_embedding = list(item_embedding)
        
        # Record the feedback
        feedback = UserFeedback(
            user_id=user_id,
            item_id=item_id,
            feedback_type=feedback_type,
            confidence=confidence,
            timestamp=datetime.utcnow(),
            item_embedding=item_embedding,
            conversation_id=conversation_id
        )
        db.add(feedback)
        
        # Also add a user interaction record
        from database.models import UserItemInteraction
        interaction = UserItemInteraction(
            user_id=user_id,
            item_id=item_id,
            interaction_type=feedback_type,
            timestamp=datetime.utcnow()
        )
        db.add(interaction)
        
        await db.commit()
        
    except Exception as e:
        logger.error(f"Error recording nuanced feedback: {str(e)}")
        await db.rollback()
        raise