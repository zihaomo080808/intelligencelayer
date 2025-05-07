# ingest/tasks.py
import asyncio
import logging
from datetime import datetime
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import AsyncSessionLocal
from ingest.models import Source, ProcessingJob
from ingest.processors import process_source

logger = logging.getLogger(__name__)

async def schedule_new_job(source_id: str, db: AsyncSession):
    """
    Schedule a new processing job for a source.
    
    Args:
        source_id: ID of the source to process
        db: Database session
    
    Returns:
        The created job ID
    """
    # Check if source exists
    result = await db.execute(select(Source).filter(Source.id == source_id))
    source = result.scalars().first()
    
    if not source:
        raise ValueError(f"Source not found: {source_id}")
    
    # Create new job
    job = ProcessingJob(
        source_id=source_id,
        status="pending",
        created_at=datetime.utcnow()
    )
    
    db.add(job)
    await db.commit()
    await db.refresh(job)
    
    # Schedule job to run asynchronously
    asyncio.create_task(process_source(source_id, job.id))
    
    return job.id

async def check_all_sources_status():
    """
    Check all sources and schedule jobs for those that need processing.
    This can be run as a scheduled task.
    """
    async with AsyncSessionLocal() as db:
        # Get all active sources
        result = await db.execute(select(Source).filter(Source.is_active == True))
        sources = result.scalars().all()
        
        jobs_scheduled = 0
        for source in sources:
            try:
                # Check if source needs processing based on schedule
                if should_process_source(source):
                    job_id = await schedule_new_job(source.id, db)
                    logger.info(f"Scheduled job {job_id} for source {source.id}")
                    jobs_scheduled += 1
            except Exception as e:
                logger.exception(f"Error scheduling job for source {source.id}: {e}")
        
        return jobs_scheduled

def should_process_source(source: Source) -> bool:
    """
    Determine if a source should be processed based on its schedule.
    
    Args:
        source: The source to check
    
    Returns:
        True if the source should be processed, False otherwise
    """
    # If never fetched before, process it
    if not source.last_fetched:
        return True
    
    # Get current time
    now = datetime.utcnow()
    time_since_last = now - source.last_fetched
    
    # Check frequency (in minutes)
    frequency = source.refresh_frequency or 1440  # Default to daily
    
    # Return true if enough time has passed
    return time_since_last.total_seconds() >= (frequency * 60) 