"""
Database models for the ingest service.
"""
from sqlalchemy import Column, String, Text, DateTime, Integer, ForeignKey, JSON, Boolean, ARRAY
from sqlalchemy.sql import func
from datetime import datetime
from typing import List, Optional, Dict, Any

from database.base import Base

class Source(Base):
    """
    Data source model - represents an external data source like RSS feed or API.
    """
    __tablename__ = "sources"
    
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    description = Column(Text)
    url = Column(String, nullable=False)
    source_type = Column(String, nullable=False)  # 'rss', 'api', etc.
    config = Column(JSON)  # JSON configuration specific to the source
    is_active = Column(Boolean, default=True)
    refresh_frequency = Column(Integer, default=1440)  # in minutes, default to daily
    last_fetched = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)

class Item(Base):
    """
    Item model - represents a piece of content extracted from a source.
    """
    __tablename__ = "items"
    
    id = Column(String, primary_key=True)
    source_id = Column(String, ForeignKey("sources.id"), nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text)
    url = Column(String)
    published_at = Column(DateTime)
    author = Column(String)
    categories = Column(ARRAY(String), default=[])
    content = Column(Text)
    item_metadata = Column(JSON, default={})
    processed = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)

class ProcessingJob(Base):
    """
    Processing job model - represents a background task to process a source.
    """
    __tablename__ = "processing_jobs"
    
    id = Column(Integer, primary_key=True)
    source_id = Column(String, ForeignKey("sources.id"), nullable=False)
    status = Column(String, nullable=False)  # 'pending', 'running', 'completed', 'failed'
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    items_processed = Column(Integer, default=0)
    errors = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)
