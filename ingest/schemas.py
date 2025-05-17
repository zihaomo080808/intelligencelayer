# ingest/schemas.py
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, HttpUrl, validator


class SourceBase(BaseModel):
    """Base schema for source data."""
    name: str = Field(..., description="Display name of the source")
    description: Optional[str] = Field(None, description="Description of what this source provides")
    source_type: str = Field(..., description="Type of source (rss, api, etc.)")
    url: str = Field(..., description="URL of the source")
    is_active: bool = Field(True, description="Whether this source is active and should be processed")
    refresh_frequency: Optional[int] = Field(1440, description="How often to refresh in minutes (default: daily)")
    config: Optional[Dict[str, Any]] = Field(None, description="Additional configuration for the source")


class SourceCreate(SourceBase):
    """Schema for creating a new source."""
    pass


class SourceUpdate(BaseModel):
    """Schema for updating an existing source."""
    name: Optional[str] = None
    description: Optional[str] = None
    url: Optional[str] = None
    is_active: Optional[bool] = None
    refresh_frequency: Optional[int] = None
    config: Optional[Dict[str, Any]] = None


class Source(SourceBase):
    """Schema for returning a source."""
    id: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    last_fetched: Optional[datetime] = None

    class Config:
        orm_mode = True


class ItemBase(BaseModel):
    """Base schema for item data."""
    source_id: str = Field(..., description="ID of the source this item came from")
    title: str = Field(..., description="Title of the item")
    description: Optional[str] = Field(None, description="Description or summary")
    content: Optional[str] = Field(None, description="Full content if available")
    url: Optional[str] = Field(None, description="URL to the original item")
    published_at: Optional[datetime] = Field(None, description="When the item was published")
    author: Optional[str] = Field(None, description="Author of the item")
    categories: Optional[List[str]] = Field(None, description="Categories or tags")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class ItemCreate(ItemBase):
    """Schema for creating a new item."""
    pass


class Item(ItemBase):
    """Schema for returning an item."""
    id: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    processed: bool = Field(False, description="Whether this item has been processed")

    class Config:
        orm_mode = True


class ProcessingJobBase(BaseModel):
    """Base schema for processing job data."""
    source_id: str = Field(..., description="ID of the source being processed")
    status: str = Field(..., description="Status of the job (pending, running, completed, failed)")
    items_processed: Optional[int] = Field(0, description="Number of items processed")
    errors: Optional[str] = Field(None, description="Error messages if the job failed")


class ProcessingJob(ProcessingJobBase):
    """Schema for returning a processing job."""
    id: int
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    class Config:
        orm_mode = True


class ItemQueryParams(BaseModel):
    """Query parameters for filtering items."""
    source_id: Optional[str] = None
    processed: Optional[bool] = None
    from_date: Optional[datetime] = None
    to_date: Optional[datetime] = None
    limit: Optional[int] = 100
    offset: Optional[int] = 0 