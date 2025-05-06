# profiles/profiles.py
from typing import Optional, List
from datetime import datetime

from sqlalchemy import Column, String, DateTime, text
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.ext.asyncio import AsyncSession

from pgvector.sqlalchemy import Vector

from database import Base, engine, AsyncSessionLocal
from config import settings  # in case you need it elsewhere

class UserProfile(Base):
    __tablename__ = "user_profiles"

    user_id    = Column(String, primary_key=True, index=True)
    bio        = Column(String)
    location   = Column(String, nullable=True)  # new field to store user location
    stances    = Column(ARRAY(String))
    embedding  = Column(Vector(settings.VECTOR_DIM))
    updated_at = Column(
        DateTime, 
        server_default=text("NOW()"), 
        onupdate=datetime.utcnow
    )

async def init_db():
    """Call this on app startup to create tables if they don't exist."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def get_profile(user_id: str) -> Optional[UserProfile]:
    """Fetch a user profile by user_id."""
    async with AsyncSessionLocal() as session:
        return await session.get(UserProfile, user_id)

async def update_profile(
    user_id: str, 
    bio: str, 
    stances: List[str], 
    embedding: List[float],
    location: Optional[str] = None
):
    """
    Create or update a user profile, including optional location.
    """
    async with AsyncSessionLocal() as session:
        prof = await session.get(UserProfile, user_id)
        if not prof:
            prof = UserProfile(
                user_id=user_id, 
                bio=bio, 
                location=location,
                stances=stances, 
                embedding=embedding
            )
            session.add(prof)
        else:
            prof.bio       = bio
            prof.location  = location
            prof.stances   = stances
            prof.embedding = embedding
        await session.commit()
