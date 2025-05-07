# profiles/profiles.py
from typing import Optional, List, Dict, Any
from datetime import datetime

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

async def init_db():
    """Create database tables if they don't exist."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def get_profile(user_id: str, db: AsyncSession):
    """Get a user profile by ID."""
    result = await db.execute(select(UserProfile).filter(UserProfile.user_id == user_id))
    return result.scalars().first()

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
@router.get("/{user_id}")
async def get_user_profile(user_id: str, db: AsyncSession = Depends(get_db)):
    """Get a user profile by ID."""
    profile = await get_profile(user_id, db)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return profile

@router.post("/{user_id}")
async def create_or_update_profile(
    user_id: str,
    profile_data: dict,
    db: AsyncSession = Depends(get_db)
):
    """Create or update a user profile."""
    try:
        profile = await update_profile(
            user_id=user_id,
            bio=profile_data.get("bio"),
            location=profile_data.get("location"),
            stances=profile_data.get("stances"),
            embedding=profile_data.get("embedding"),
            db=db
        )
        return profile
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating profile: {str(e)}")

@router.get("/")
async def list_profiles(
    skip: int = 0, 
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
):
    """List all user profiles with pagination."""
    result = await db.execute(select(UserProfile).offset(skip).limit(limit))
    profiles = result.scalars().all()
    return profiles
