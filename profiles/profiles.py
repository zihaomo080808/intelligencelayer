# profiles/profiles.py
from typing import Optional, List, Dict, Any
from datetime import datetime
import logging
import traceback
import numpy as np
from openai import AsyncOpenAI
from pydantic import BaseModel, Field

from sqlalchemy import Column, String, DateTime, text
from sqlalchemy.dialects.postgresql import ARRAY, JSON
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import update

from pgvector.sqlalchemy import Vector

from database import Base, AsyncSessionLocal
from database.base import engine
from config import settings  # in case you need it elsewhere
from database.session import get_db
from fastapi import APIRouter, Depends, HTTPException

import json
from pathlib import Path

# Configure logging
logger = logging.getLogger(__name__)

# Initialize OpenAI client
client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

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

class UserProfile(Base):
    """User profile model with vector embeddings for stance matching."""
    __tablename__ = "profiles"

    user_id = Column(String, primary_key=True, index=True)
    bio = Column(String, nullable=True)
    location = Column(String, nullable=True)
    stances = Column(JSON, default={})
    embedding = Column(Vector(1536), nullable=True)  # Dimension based on OpenAI's embedding size
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

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
