# ingest/routes.py
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List, Optional
from uuid import uuid4
from datetime import datetime

from database import get_db
from ingest.models import Source, Item, ProcessingJob
from ingest.schemas import (
    Source as SourceSchema,
    SourceCreate, 
    SourceUpdate,
    Item as ItemSchema,
    ItemCreate,
    ProcessingJob as ProcessingJobSchema,
    ItemQueryParams
)
from ingest.processors import process_source
from ingest.tasks import schedule_new_job, check_all_sources_status
from ingest.utils import generate_source_id, get_source_stats

router = APIRouter()

# Source endpoints
@router.post("/sources", response_model=SourceSchema, status_code=status.HTTP_201_CREATED)
async def create_source(source: SourceCreate, db: AsyncSession = Depends(get_db)):
    """Create a new source."""
    # Generate a unique ID based on URL and type
    source_id = generate_source_id(source.url, source.source_type)
    
    # Check if source already exists
    result = await db.execute(select(Source).filter(Source.id == source_id))
    existing = result.scalars().first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Source with URL {source.url} and type {source.source_type} already exists"
        )
    
    # Create new source
    new_source = Source(
        id=source_id,
        **source.dict(),
        created_at=datetime.utcnow()
    )
    
    db.add(new_source)
    await db.commit()
    await db.refresh(new_source)
    
    return new_source

@router.get("/sources", response_model=List[SourceSchema])
async def list_sources(
    is_active: Optional[bool] = None,
    source_type: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """List all sources with optional filtering."""
    query = select(Source)
    
    # Apply filters
    if is_active is not None:
        query = query.filter(Source.is_active == is_active)
    
    if source_type:
        query = query.filter(Source.source_type == source_type)
    
    result = await db.execute(query)
    sources = result.scalars().all()
    
    return sources

@router.get("/sources/{source_id}", response_model=SourceSchema)
async def get_source(source_id: str, db: AsyncSession = Depends(get_db)):
    """Get a source by ID."""
    result = await db.execute(select(Source).filter(Source.id == source_id))
    source = result.scalars().first()
    
    if not source:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Source with ID {source_id} not found"
        )
    
    return source

@router.put("/sources/{source_id}", response_model=SourceSchema)
async def update_source(
    source_id: str, 
    source_update: SourceUpdate, 
    db: AsyncSession = Depends(get_db)
):
    """Update a source."""
    result = await db.execute(select(Source).filter(Source.id == source_id))
    source = result.scalars().first()
    
    if not source:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Source with ID {source_id} not found"
        )
    
    # Update fields
    update_data = source_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(source, field, value)
    
    source.updated_at = datetime.utcnow()
    
    await db.commit()
    await db.refresh(source)
    
    return source

@router.delete("/sources/{source_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_source(source_id: str, db: AsyncSession = Depends(get_db)):
    """Delete a source."""
    result = await db.execute(select(Source).filter(Source.id == source_id))
    source = result.scalars().first()
    
    if not source:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Source with ID {source_id} not found"
        )
    
    await db.delete(source)
    await db.commit()
    
    return None

@router.get("/sources/{source_id}/stats")
async def get_source_statistics(source_id: str, db: AsyncSession = Depends(get_db)):
    """Get statistics for a source."""
    try:
        stats = await get_source_stats(db, source_id)
        return stats
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )

# Item endpoints
@router.get("/items", response_model=List[ItemSchema])
async def list_items(
    query_params: ItemQueryParams = Depends(),
    db: AsyncSession = Depends(get_db)
):
    """List items with optional filtering."""
    query = select(Item)
    
    # Apply filters
    if query_params.source_id:
        query = query.filter(Item.source_id == query_params.source_id)
    
    if query_params.processed is not None:
        query = query.filter(Item.processed == query_params.processed)
    
    if query_params.from_date:
        query = query.filter(Item.created_at >= query_params.from_date)
    
    if query_params.to_date:
        query = query.filter(Item.created_at <= query_params.to_date)
    
    # Apply pagination
    query = query.offset(query_params.offset).limit(query_params.limit)
    
    result = await db.execute(query)
    items = result.scalars().all()
    
    return items

@router.get("/items/{item_id}", response_model=ItemSchema)
async def get_item(item_id: str, db: AsyncSession = Depends(get_db)):
    """Get an item by ID."""
    result = await db.execute(select(Item).filter(Item.id == item_id))
    item = result.scalars().first()
    
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Item with ID {item_id} not found"
        )
    
    return item

@router.post("/items", response_model=ItemSchema, status_code=status.HTTP_201_CREATED)
async def create_item(item: ItemCreate, db: AsyncSession = Depends(get_db)):
    """Create a new item manually."""
    # Check if source exists
    result = await db.execute(select(Source).filter(Source.id == item.source_id))
    source = result.scalars().first()
    
    if not source:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Source with ID {item.source_id} not found"
        )
    
    # Create new item
    new_item = Item(
        id=str(uuid4()),
        **item.dict(),
        created_at=datetime.utcnow()
    )
    
    db.add(new_item)
    await db.commit()
    await db.refresh(new_item)
    
    return new_item

@router.put("/items/{item_id}/mark-processed")
async def mark_item_processed(item_id: str, db: AsyncSession = Depends(get_db)):
    """Mark an item as processed."""
    result = await db.execute(select(Item).filter(Item.id == item_id))
    item = result.scalars().first()
    
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Item with ID {item_id} not found"
        )
    
    item.processed = True
    item.updated_at = datetime.utcnow()
    
    await db.commit()
    await db.refresh(item)
    
    return {"status": "success", "message": f"Item {item_id} marked as processed"}

# Processing job endpoints
@router.post("/jobs", response_model=ProcessingJobSchema)
async def create_processing_job(source_id: str, db: AsyncSession = Depends(get_db)):
    """Schedule a new processing job for a source."""
    try:
        job_id = await schedule_new_job(source_id, db)
        
        # Get the job to return
        result = await db.execute(select(ProcessingJob).filter(ProcessingJob.id == job_id))
        job = result.scalars().first()
        
        return job
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )

@router.get("/jobs", response_model=List[ProcessingJobSchema])
async def list_jobs(
    source_id: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db)
):
    """List processing jobs with optional filtering."""
    query = select(ProcessingJob)
    
    # Apply filters
    if source_id:
        query = query.filter(ProcessingJob.source_id == source_id)
    
    if status:
        query = query.filter(ProcessingJob.status == status)
    
    # Apply pagination
    query = query.offset(offset).limit(limit)
    
    result = await db.execute(query)
    jobs = result.scalars().all()
    
    return jobs

@router.get("/jobs/{job_id}", response_model=ProcessingJobSchema)
async def get_job(job_id: int, db: AsyncSession = Depends(get_db)):
    """Get a processing job by ID."""
    result = await db.execute(select(ProcessingJob).filter(ProcessingJob.id == job_id))
    job = result.scalars().first()
    
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job with ID {job_id} not found"
        )
    
    return job

@router.post("/check-sources")
async def check_sources():
    """Check all sources and schedule jobs for those that need processing."""
    try:
        jobs_scheduled = await check_all_sources_status()
        return {"status": "success", "jobs_scheduled": jobs_scheduled}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error checking sources: {str(e)}"
        )
