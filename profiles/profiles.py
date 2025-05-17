# profiles/profiles.py
# Standard library imports
import json
import logging
import traceback
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any

# Third-party imports
import numpy as np
from fastapi import APIRouter, Depends, HTTPException
from openai import AsyncOpenAI
from pydantic import BaseModel, Field
from sqlalchemy import text, select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

# Local application imports
from database import Base, AsyncSessionLocal
from database.base import engine
from database.models import UserProfile, UserFeedback, UserItemInteraction
from database.session import get_db
from config import settings
from feedback.rocchio import RocchioUpdater

# Configure logging
logger = logging.getLogger(__name__)

# Initialize OpenAI client
client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

# Initialize Rocchio updater
rocchio_updater = RocchioUpdater()

# Pydantic models for request/response
class ProfileBase(BaseModel):
    bio: Optional[str] = None
    location: Optional[str] = None
    stances: Optional[Dict[str, Any]] = Field(default_factory=dict)

class ProfileCreate(ProfileBase):
    pass

class ProfileResponse(ProfileBase):
    user_id: str
    embedding: Optional[List[float]] = None
    updated_at: datetime

    class Config:
        from_attributes = True

# Initialize FastAPI router
router = APIRouter()

# Check if OpenAI API key is set
if not settings.OPENAI_API_KEY:
    logger.warning("OPENAI_API_KEY is not set. Embeddings will not be generated.")

async def init_db():
    """Create database tables if they don't exist."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def get_profile(user_id: str, db: AsyncSession):
    """Get a user profile by ID."""
    result = await db.execute(select(UserProfile).filter(UserProfile.user_id == user_id))
    return result.scalars().first()

async def generate_embedding(text: str) -> list:
    """Generate an embedding vector for the given text using OpenAI's API."""
    try:
        # Validate OpenAI API key
        if not settings.OPENAI_API_KEY:
            logger.error("OPENAI_API_KEY is not set in environment variables")
            raise ValueError("OpenAI API key is not configured")
        
        # Log the API call
        logger.info(f"Calling OpenAI API for embedding with model: {settings.EMBEDDING_MODEL}")
        logger.info(f"Text length: {len(text)}")
        
        try:
            # Create embedding using the new API syntax
            response = await client.embeddings.create(
                input=text,
                model=settings.EMBEDDING_MODEL
            )
            
            # Log the response structure
            logger.info(f"Response received: {type(response)}")
            
            # Extract and return the embedding vector
            embedding = response.data[0].embedding
            logger.info(f"Successfully generated embedding with {len(embedding)} dimensions")
            return embedding
            
        except Exception as api_error:
            error_msg = f"OpenAI API error: {str(api_error)}"
            logger.error(error_msg)
            logger.error(traceback.format_exc())
            raise HTTPException(
                status_code=500,
                detail=error_msg
            )
            
    except HTTPException as he:
        # Re-raise HTTP exceptions
        raise he
    except Exception as e:
        error_msg = f"Error generating embedding: {str(e)}"
        logger.error(error_msg)
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=500,
            detail=error_msg
        )

async def update_profile(
    user_id: str, 
    bio: Optional[str] = None,
    location: Optional[str] = None, 
    stances: Optional[Dict[str, Any]] = None,
    embedding: Optional[list] = None,
    db: AsyncSession = None
):
    """Update a user profile, creating it if it doesn't exist."""
    if db is None:
        async with AsyncSessionLocal() as db:
            return await _update_profile(user_id, bio, location, stances, embedding, db)
    else:
        return await _update_profile(user_id, bio, location, stances, embedding, db)

async def _update_profile(
    user_id: str, 
    bio: Optional[str],
    location: Optional[str], 
    stances: Optional[Dict[str, Any]],
    embedding: Optional[list],
    db: AsyncSession
):
    """Internal function to update a profile with a provided database session."""
    # Check if profile exists
    profile = await get_profile(user_id, db)
    
    if profile:
        # Update existing profile
        update_data = {}
        if bio is not None:
            update_data["bio"] = bio
        if location is not None:
            update_data["location"] = location
        if stances is not None:
            update_data["stances"] = stances
        if embedding is not None:
            update_data["embedding"] = embedding
        
        if update_data:
            stmt = update(UserProfile).where(UserProfile.user_id == user_id).values(**update_data)
            await db.execute(stmt)
            await db.commit()
            await db.refresh(profile)
        return profile
    else:
        # Create new profile
        # Generate embedding for new users if bio is provided and embedding isn't
        if embedding is None and bio is not None:
            # Create text for embedding from bio and stances
            embedding_text = bio
            if stances:
                stance_text = " ".join([f"{k}: {v}" for k, v in stances.items()])
                embedding_text += " " + stance_text
            
            # Generate embedding
            embedding = await generate_embedding(embedding_text)
            logger.info(f"Generated embedding for new user {user_id}")
        
        new_profile = UserProfile(
                user_id=user_id, 
                bio=bio, 
                location=location,
            stances=stances if stances is not None else {},
                embedding=embedding
        )
        db.add(new_profile)
        await db.commit()
        await db.refresh(new_profile)
        return new_profile

# API Routes
@router.post("/embedding/test")
async def test_embedding_generation(request: dict):
    """Test endpoint to check if embedding generation works."""
    try:
        # Debug logging
        logger.info("Starting embedding test")
        logger.info(f"Request body: {request}")
        
        if "text" not in request:
            logger.error("Missing 'text' field in request")
            raise HTTPException(status_code=400, detail="Missing 'text' field in request body")
            
        text = request["text"]
        logger.info(f"Generating embedding for text: {text[:50]}...")
        
        # Check OpenAI API key
        if not settings.OPENAI_API_KEY:
            error_msg = "OPENAI_API_KEY is not set in environment variables"
            logger.error(error_msg)
            raise HTTPException(status_code=500, detail=error_msg)
            
        # Generate embedding
        try:
            embedding = await generate_embedding(text)
            if embedding:
                logger.info("Successfully generated embedding")
                return {
                    "success": True,
                    "dimensions": len(embedding),
                    "embedding_sample": embedding[:5],
                    "model": settings.EMBEDDING_MODEL
                }
            else:
                error_msg = "Failed to generate embedding - no embedding returned"
                logger.error(error_msg)
                return {"success": False, "error": error_msg}
        except HTTPException as he:
            # Re-raise HTTP exceptions from generate_embedding
            raise he
        except Exception as embed_error:
            error_msg = f"Error in generate_embedding: {str(embed_error)}"
            logger.error(error_msg)
            logger.error(traceback.format_exc())
            raise HTTPException(status_code=500, detail=error_msg)
            
    except HTTPException as he:
        # Re-raise HTTP exceptions
        raise he
    except Exception as e:
        error_msg = f"Unexpected error in test_embedding_generation: {str(e)}"
        logger.error(error_msg)
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=error_msg)

@router.get("/{user_id}", response_model=ProfileResponse)
async def get_user_profile(user_id: str, db: AsyncSession = Depends(get_db)):
    """Get a user profile by ID."""
    profile = await get_profile(user_id, db)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return profile

@router.post("/{user_id}", response_model=ProfileResponse)
async def create_or_update_profile(
    user_id: str,
    profile_data: ProfileCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create or update a user profile."""
    try:
        profile = await update_profile(
            user_id=user_id,
            bio=profile_data.bio,
            location=profile_data.location,
            stances=profile_data.stances,
            embedding=None,  # Will be generated if bio is provided
            db=db
        )
        return profile
    except Exception as e:
        logger.error(f"Error in create_or_update_profile: {e}")
        raise HTTPException(status_code=500, detail=f"Error updating profile: {str(e)}")

@router.get("/", response_model=List[ProfileResponse])
async def list_profiles(
    skip: int = 0, 
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
):
    """List all user profiles with pagination."""
    result = await db.execute(select(UserProfile).offset(skip).limit(limit))
    profiles = result.scalars().all()
    return profiles

@router.get("/embedding/debug")
async def debug_embedding_config():
    """Debug endpoint to check embedding configuration."""
    try:
        config = {
            "openai_api_key_set": bool(settings.OPENAI_API_KEY),
            "embedding_model": settings.EMBEDDING_MODEL,
            "vector_dim": settings.VECTOR_DIM,
            "debug_mode": settings.DEBUG
        }
        return config
    except Exception as e:
        logger.error(f"Error in debug_embedding_config: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Error checking configuration: {str(e)}")

@router.get("/opportunities/{user_id}")
async def find_matching_opportunities(
    user_id: str,
    limit: int = 5,
    db: AsyncSession = Depends(get_db)
):
    """Find opportunities that match the given user's profile based on embedding similarity."""
    try:
        # Get the user profile
        profile = await get_profile(user_id, db)
        if not profile:
            raise HTTPException(status_code=404, detail="Profile not found")
        
        # Check if embedding exists and is not None
        if profile.embedding is None or (isinstance(profile.embedding, (list, np.ndarray)) and len(profile.embedding) == 0):
            raise HTTPException(
                status_code=400,
                detail="Profile has no embedding. Please update the profile first."
            )

        # Load opportunities from JSONL file
        opportunities_path = Path("data/opportunities.jsonl")
        if not opportunities_path.exists():
            raise HTTPException(status_code=500, detail="Opportunities data not found")

        opportunities = []
        with open(opportunities_path) as f:
            for line in f:
                opportunities.append(json.loads(line))

        # Calculate similarity scores for each opportunity
        matches = []
        profile_vector = profile.embedding
        
        for opp in opportunities:
            if "embedding" not in opp:
                continue
                
            try:
                # Convert both vectors to lists for comparison
                profile_embedding = list(profile_vector)
                opp_embedding = list(opp["embedding"])
                
                # Calculate dot product and magnitudes
                dot_product = sum(a * b for a, b in zip(profile_embedding, opp_embedding))
                profile_magnitude = sum(a * a for a in profile_embedding) ** 0.5
                opp_magnitude = sum(b * b for b in opp_embedding) ** 0.5
                
                # Calculate cosine similarity
                if profile_magnitude == 0 or opp_magnitude == 0:
                    similarity = 0
                else:
                    similarity = dot_product / (profile_magnitude * opp_magnitude)
                
                matches.append({
                    "opportunity": opp,
                    "similarity_score": float(similarity)
                })
            except Exception as e:
                logger.error(f"Error calculating similarity for opportunity {opp.get('id')}: {str(e)}")
                continue

        # Sort by similarity score and return top matches
        matches.sort(key=lambda x: x["similarity_score"], reverse=True)
        return matches[:limit]

    except Exception as e:
        logger.error(f"Error in find_matching_opportunities: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Error finding matches: {str(e)}")

async def record_feedback(
    db: AsyncSession,
    user_id: str,
    item_id: str,
    feedback_type: str,
    item_embedding: List[float] = None
) -> None:
    """
    Record user feedback for an item.

    Args:
        db: Database session
        user_id: User ID
        item_id: Item ID
        feedback_type: Type of feedback ('like' or 'skip')
        item_embedding: Optional item embedding
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
            timestamp=datetime.utcnow(),
            item_embedding=item_embedding
        )
        db.add(feedback)

        # Record the interaction
        interaction = UserItemInteraction(
            user_id=user_id,
            item_id=item_id,
            interaction_type=feedback_type,
            timestamp=datetime.utcnow()
        )
        db.add(interaction)

        await db.commit()

        # Update user embedding using Rocchio
        await update_user_embedding(db, user_id)

    except Exception as e:
        logger.error(f"Error recording feedback: {str(e)}")
        await db.rollback()
        raise

async def update_user_embedding(db: AsyncSession, user_id: str) -> None:
    """
    Update user embedding based on their feedback history using Rocchio algorithm.
    
    Args:
        db: Database session
        user_id: User ID
    """
    try:
        # Get user profile
        profile = await get_profile(user_id, db)
        if not profile:
            return

        # Check for embedding
        if profile.embedding is None:
            return

        # Check if embedding is empty (for arrays, this check is different)
        if isinstance(profile.embedding, np.ndarray) and profile.embedding.size == 0:
            return
        elif isinstance(profile.embedding, list) and len(profile.embedding) == 0:
            return
            
        # Get recent feedback
        stmt = select(UserFeedback).where(
            UserFeedback.user_id == user_id
        ).order_by(UserFeedback.timestamp.desc()).limit(100)
        
        feedbacks = (await db.execute(stmt)).scalars().all()
        
        # Ensure profile embedding is in the right format for Rocchio
        if isinstance(profile.embedding, np.ndarray):
            profile_embedding = profile.embedding.tolist()
        else:
            profile_embedding = list(profile.embedding)

        # Separate liked and skipped items
        liked_embeddings = []
        skipped_embeddings = []

        for f in feedbacks:
            # For 'like' feedback
            if f.feedback_type == 'like' and f.item_embedding is not None:
                # Ensure we have a list, not a numpy array or string
                if isinstance(f.item_embedding, np.ndarray):
                    liked_embeddings.append(f.item_embedding.tolist())
                elif isinstance(f.item_embedding, list):
                    liked_embeddings.append(f.item_embedding)
                elif hasattr(f.item_embedding, 'tolist'):
                    liked_embeddings.append(f.item_embedding.tolist())
                else:
                    # Skip if not in a usable format
                    logger.warning(f"Skipping like item with embedding type {type(f.item_embedding)}")

            # For 'skip' feedback
            elif f.feedback_type == 'skip' and f.item_embedding is not None:
                # Ensure we have a list, not a numpy array or string
                if isinstance(f.item_embedding, np.ndarray):
                    skipped_embeddings.append(f.item_embedding.tolist())
                elif isinstance(f.item_embedding, list):
                    skipped_embeddings.append(f.item_embedding)
                elif hasattr(f.item_embedding, 'tolist'):
                    skipped_embeddings.append(f.item_embedding.tolist())
                else:
                    # Skip if not in a usable format
                    logger.warning(f"Skipping skip item with embedding type {type(f.item_embedding)}")
        
        # Update embedding using Rocchio
        new_embedding = rocchio_updater.update_embedding(
            profile_embedding,
            liked_embeddings,
            skipped_embeddings
        )
        
        # Update profile with the new embedding
        # Make sure it's compatible with the Vector column type in the database
        try:
            # Store the embedding in the format expected by the Vector column
            # For Vector type, we need to maintain numpy array format
            profile.embedding = np.array(new_embedding)

            logger.info(f"Updated embedding for user {user_id} using Rocchio algorithm")
            await db.commit()
        except Exception as e:
            logger.error(f"Error storing updated embedding: {str(e)}")
            await db.rollback()
            raise
        
    except Exception as e:
        logger.error(f"Error updating user embedding: {str(e)}")
        await db.rollback()
        raise
