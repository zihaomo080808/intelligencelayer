"""
Shared database models used across the application.
This file should import and re-export all models from various parts of the application
to provide a central reference point.
"""

# Import Base for model definitions
from .base import Base

# Import required SQLAlchemy types
from sqlalchemy import Column, Integer, String, DateTime, ARRAY, Float, ForeignKey
from sqlalchemy.dialects.postgresql import JSON
from pgvector.sqlalchemy import Vector
from datetime import datetime

class Opportunity(Base):
    """Model for storing opportunity data."""
    __tablename__ = "opportunities"

    id = Column(String, primary_key=True)
    title = Column(String, nullable=False)
    description = Column(String, nullable=True)
    type = Column(String, nullable=True)
    cost = Column(Float, nullable=True)
    deadline = Column(DateTime, nullable=True)
    state = Column(String, nullable=True)
    city = Column(String, nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    embedding = Column(Vector(1536), nullable=True)  # Dimension based on OpenAI's embedding size
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class UserProfile(Base):
    """User profile model with vector embeddings for stance matching."""
    __tablename__ = "profiles"

    user_id = Column(String, primary_key=True, index=True)
    bio = Column(String, nullable=True)
    location = Column(String, nullable=True)
    stances = Column(JSON, default={})
    embedding = Column(Vector(1536), nullable=True)  # Dimension based on OpenAI's embedding size
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class UserConversation(Base):
    __tablename__ = "user_conversations"

    id = Column(Integer, primary_key=True)
    user_id = Column(String, nullable=False)
    item_id = Column(String, nullable=False)
    transcript = Column(String, nullable=False)
    analysis = Column(JSON, nullable=True)
    message_count = Column(Integer, default=0)
    duration_seconds = Column(Integer, default=0)
    started_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    ended_at = Column(DateTime, nullable=True)

class UserFeedback(Base):
    __tablename__ = "user_feedback"

    id = Column(Integer, primary_key=True)
    user_id = Column(String, nullable=False)
    item_id = Column(String, nullable=False)
    feedback_type = Column(String, nullable=False)  # 'like', 'neutral', or 'skip'
    confidence = Column(Float, default=1.0)  # How confident we are in this feedback (0.0-1.0)
    timestamp = Column(DateTime, nullable=False)
    item_embedding = Column(ARRAY(Float), nullable=True)  # Store as regular array
    conversation_id = Column(Integer, ForeignKey("user_conversations.id"), nullable=True)

class UserItemInteraction(Base):
    __tablename__ = "user_item_interactions"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(String, nullable=False)
    item_id = Column(String, nullable=False)
    interaction_type = Column(String, nullable=False)  # 'view', 'click', 'apply'
    timestamp = Column(DateTime, nullable=False)

# Track which recommendations have been shown to users
class UserRecommendation(Base):
    __tablename__ = "user_recommendations"

    id = Column(Integer, primary_key=True)
    user_id = Column(String, nullable=False)
    item_id = Column(String, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    recommended_score = Column(Float, nullable=True)  # Match score when recommended
    status = Column(String, default="shown")  # "shown", "liked", "skipped", "clicked"

# Re-export all models
__all__ = [
    "UserProfile",
    "UserFeedback",
    "UserItemInteraction",
    "UserConversation",
    "UserRecommendation",
    "Opportunity"
]
