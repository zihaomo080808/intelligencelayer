# ingest/processors.py
import asyncio
import aiohttp
import feedparser
import json
import logging
from datetime import datetime
from uuid import uuid4
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from database import AsyncSessionLocal
from ingest.models import Source, Item, ProcessingJob

logger = logging.getLogger(__name__)

async def process_source(source_id: str, job_id: int):
    """
    Process a data source and store the results.
    This function runs as a background task.
    """
    async with AsyncSessionLocal() as db:
        # Get the source
        result = await db.execute(select(Source).filter(Source.id == source_id))
        source = result.scalars().first()
        
        if not source:
            logger.error(f"Source not found: {source_id}")
            return
        
        # Get the job
        result = await db.execute(select(ProcessingJob).filter(ProcessingJob.id == job_id))
        job = result.scalars().first()
        
        if not job:
            logger.error(f"Job not found: {job_id}")
            return
        
        # Update job status
        job.status = "running"
        job.started_at = datetime.utcnow()
        await db.commit()
        
        try:
            # Process based on source type
            if source.source_type == "rss":
                items = await process_rss_feed(source, db)
            elif source.source_type == "api":
                items = await process_api_source(source, db)
            else:
                job.status = "failed"
                job.errors = f"Unknown source type: {source.source_type}"
                await db.commit()
                return
            
            # Update job status
            job.status = "completed"
            job.completed_at = datetime.utcnow()
            job.items_processed = len(items)
            
            # Update source last fetched time
            source.last_fetched = datetime.utcnow()
            
            await db.commit()
            
        except Exception as e:
            logger.exception(f"Error processing source {source_id}")
            job.status = "failed"
            job.errors = str(e)
            await db.commit()

async def process_rss_feed(source: Source, db: AsyncSession):
    """Process an RSS feed source."""
    async with aiohttp.ClientSession() as session:
        async with session.get(source.url) as response:
            content = await response.text()
    
    feed = feedparser.parse(content)
    items = []
    
    for entry in feed.entries:
        # Extract data from feed entry
        item_data = {
            "id": str(uuid4()),
            "source_id": source.id,
            "title": entry.get("title", ""),
            "description": entry.get("summary", ""),
            "url": entry.get("link", ""),
            "published_at": parse_date(entry.get("published")),
            "author": entry.get("author", ""),
            "categories": [tag.term for tag in entry.get("tags", [])],
            "content": entry.get("content", [{}])[0].get("value", "") if "content" in entry else "",
            "metadata": {
                "feed_id": entry.get("id", ""),
                "feed_title": feed.feed.get("title", ""),
                "feed_link": feed.feed.get("link", "")
            }
        }
        
        # Create item
        item = Item(**item_data)
        db.add(item)
        items.append(item)
    
    await db.commit()
    return items

async def process_api_source(source: Source, db: AsyncSession):
    """Process an API source."""
    config = source.config or {}
    headers = config.get("headers", {})
    params = config.get("params", {})
    method = config.get("method", "GET")
    data_path = config.get("data_path", "")
    
    async with aiohttp.ClientSession() as session:
        if method.upper() == "GET":
            async with session.get(source.url, headers=headers, params=params) as response:
                content = await response.json()
        else:
            body = config.get("body", {})
            async with session.post(source.url, headers=headers, params=params, json=body) as response:
                content = await response.json()
    
    # Extract data using path if specified
    if data_path:
        for key in data_path.split('.'):
            if key in content:
                content = content[key]
            else:
                content = []
                break
    
    if not isinstance(content, list):
        content = [content]
    
    items = []
    for entry in content:
        mappings = config.get("mappings", {})
        
        # Map API fields to item fields
        item_data = {
            "id": str(uuid4()),
            "source_id": source.id,
            "title": extract_field(entry, mappings.get("title", "title")),
            "description": extract_field(entry, mappings.get("description", "description")),
            "url": extract_field(entry, mappings.get("url", "url")),
            "published_at": parse_date(extract_field(entry, mappings.get("published_at", "published_at"))),
            "author": extract_field(entry, mappings.get("author", "author")),
            "categories": extract_field(entry, mappings.get("categories", "categories")) or [],
            "content": extract_field(entry, mappings.get("content", "content")),
            "metadata": entry
        }
        
        # Create item
        item = Item(**item_data)
        db.add(item)
        items.append(item)
    
    await db.commit()
    return items

def extract_field(data, field_path):
    """Extract a field from nested data."""
    if not field_path:
        return None
    
    keys = field_path.split('.')
    result = data
    
    for key in keys:
        if isinstance(result, dict) and key in result:
            result = result[key]
        else:
            return None
    
    return result

def parse_date(date_string):
    """Parse a date string into a datetime object."""
    if not date_string:
        return None
    
    # Try common formats
    formats = [
        "%a, %d %b %Y %H:%M:%S %z",  # RSS format
        "%Y-%m-%dT%H:%M:%S%z",       # ISO 8601
        "%Y-%m-%d %H:%M:%S",         # Common SQL format
        "%Y-%m-%d"                   # Just date
    ]
    
    for fmt in formats:
        try:
            return datetime.strptime(date_string, fmt)
        except ValueError:
            continue
    
    # If all formats fail, return None
    return None 