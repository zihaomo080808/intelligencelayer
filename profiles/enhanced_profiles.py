"""
Enhanced profile management with nuanced feedback.
"""
import logging
import traceback
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

import numpy as np
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import UserProfile, UserFeedback
from feedback.enhanced_rocchio import EnhancedRocchioUpdater
from config import settings

# Configure logging
logger = logging.getLogger(__name__)

# Initialize the enhanced Rocchio updater
enhanced_rocchio_updater = EnhancedRocchioUpdater(
    alpha=0.8,  # Weight for original profile
    beta=0.2,   # Weight for liked items
    gamma=0.1   # Weight for disliked items
)

async def update_user_embedding_enhanced(
    db: AsyncSession, 
    user_id: str,
    days_back: int = 30
) -> None:
    """
    Update user embedding based on their feedback history using enhanced Rocchio algorithm.
    
    This version uses confidence scores to weight the importance of different feedback items.
    
    Args:
        db: Database session
        user_id: User ID
        days_back: Number of days to look back for feedback
    """
    try:
        # Get user profile
        stmt = select(UserProfile).where(UserProfile.user_id == user_id)
        result = await db.execute(stmt)
        profile = result.scalars().first()
        
        if not profile:
            logger.warning(f"Profile not found for user {user_id}")
            return
            
        # Check for embedding
        if profile.embedding is None:
            logger.warning(f"No embedding found for user {user_id}")
            return
            
        # Check if embedding is empty
        if isinstance(profile.embedding, np.ndarray) and profile.embedding.size == 0:
            logger.warning(f"Empty embedding for user {user_id}")
            return
        elif isinstance(profile.embedding, list) and len(profile.embedding) == 0:
            logger.warning(f"Empty embedding for user {user_id}")
            return
            
        # Get recent feedback within the specified time window
        cutoff_date = datetime.utcnow() - timedelta(days=days_back)
        stmt = select(UserFeedback).where(
            UserFeedback.user_id == user_id,
            UserFeedback.timestamp >= cutoff_date
        ).order_by(UserFeedback.timestamp.desc())
        
        result = await db.execute(stmt)
        feedbacks = result.scalars().all()
        
        if not feedbacks:
            logger.info(f"No recent feedback found for user {user_id}")
            return
            
        # Ensure profile embedding is in the right format for Rocchio
        if isinstance(profile.embedding, np.ndarray):
            profile_embedding = profile.embedding.tolist()
        else:
            profile_embedding = list(profile.embedding)
        
        # Prepare feedback items for enhanced Rocchio
        feedback_items = []
        
        for feedback in feedbacks:
            # Skip items without embeddings
            if not feedback.item_embedding:
                continue
                
            # Prepare the embedding
            if isinstance(feedback.item_embedding, np.ndarray):
                item_embedding = feedback.item_embedding.tolist()
            else:
                item_embedding = list(feedback.item_embedding)
                
            # Add to feedback items with confidence score
            confidence = feedback.confidence if feedback.confidence is not None else 1.0
            feedback_items.append((item_embedding, confidence, feedback.feedback_type))
        
        # If no valid feedback items, return
        if not feedback_items:
            logger.info(f"No valid feedback items for user {user_id}")
            return
            
        # Update embedding using enhanced Rocchio
        new_embedding = enhanced_rocchio_updater.update_embedding(
            profile_embedding,
            feedback_items
        )
        
        # Store the updated embedding
        profile.embedding = np.array(new_embedding)
        
        # Update last_updated timestamp
        profile.updated_at = datetime.utcnow()
        
        # Commit changes
        await db.commit()
        
        logger.info(f"Updated embedding for user {user_id} using enhanced Rocchio algorithm")
        
    except Exception as e:
        logger.error(f"Error updating user embedding with enhanced Rocchio: {str(e)}")
        logger.error(traceback.format_exc())
        await db.rollback()
        raise

async def batch_update_profiles(
    db: AsyncSession,
    days_back: int = 30,
    max_users: int = 100
) -> Dict[str, Any]:
    """
    Update embeddings for all users with recent feedback.
    
    Args:
        db: Database session
        days_back: Number of days to look back for feedback
        max_users: Maximum number of users to update in one batch
        
    Returns:
        Dict with stats about the update process
    """
    try:
        # Get cutoff date
        cutoff_date = datetime.utcnow() - timedelta(days=days_back)
        
        # Find users with recent feedback
        stmt = select(UserFeedback.user_id).where(
            UserFeedback.timestamp >= cutoff_date
        ).group_by(UserFeedback.user_id).limit(max_users)
        
        result = await db.execute(stmt)
        user_ids = [row[0] for row in result]
        
        logger.info(f"Found {len(user_ids)} users with recent feedback")
        
        # Update each user's embedding
        updated_count = 0
        error_count = 0
        
        for user_id in user_ids:
            try:
                await update_user_embedding_enhanced(db, user_id, days_back)
                updated_count += 1
            except Exception as e:
                logger.error(f"Error updating user {user_id}: {str(e)}")
                error_count += 1
        
        return {
            "total_users": len(user_ids),
            "updated_count": updated_count,
            "error_count": error_count
        }
        
    except Exception as e:
        logger.error(f"Error in batch update profiles: {str(e)}")
        logger.error(traceback.format_exc())
        return {
            "total_users": 0,
            "updated_count": 0,
            "error_count": 1,
            "error": str(e)
        }