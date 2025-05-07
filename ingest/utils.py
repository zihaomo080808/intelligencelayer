# ingest/utils.py
import hashlib
import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func
from sqlalchemy.future import select

from ingest.models import Source, Item

logger = logging.getLogger(__name__)

def generate_source_id(url: str, source_type: str) -> str:
    """
    Generate a unique ID for a source based on its URL and type.
    
    Args:
        url: The source URL
        source_type: The type of source
    
    Returns:
        A unique ID string
    """
    # Create a hash of the URL and type
    combined = f"{url}:{source_type}"
    hash_obj = hashlib.sha256(combined.encode())
    return hash_obj.hexdigest()[:12]

def get_fingerprint(item_data: Dict[str, Any]) -> str:
    """
    Generate a fingerprint for an item to detect duplicates.
    
    Args:
        item_data: The item data
    
    Returns:
        A fingerprint string
    """
    # Use important fields to create a unique fingerprint
    fingerprint_data = {
        "title": item_data.get("title", ""),
        "url": item_data.get("url", ""),
        "published_at": str(item_data.get("published_at", "")),
    }
    
    # Convert to JSON and hash
    json_str = json.dumps(fingerprint_data, sort_keys=True)
    hash_obj = hashlib.sha256(json_str.encode())
    return hash_obj.hexdigest()

async def check_duplicate_item(db: AsyncSession, fingerprint: str) -> bool:
    """
    Check if an item with the given fingerprint already exists.
    
    Args:
        db: Database session
        fingerprint: Item fingerprint
    
    Returns:
        True if a duplicate exists, False otherwise
    """
    # Query for items with the same fingerprint
    query = select(func.count()).select_from(Item).filter(Item.metadata.contains({"fingerprint": fingerprint}))
    result = await db.execute(query)
    count = result.scalar()
    
    return count > 0

async def get_source_stats(db: AsyncSession, source_id: str) -> Dict[str, Any]:
    """
    Get statistics for a source.
    
    Args:
        db: Database session
        source_id: Source ID
    
    Returns:
        Dictionary of statistics
    """
    # Get source
    source_query = select(Source).filter(Source.id == source_id)
    source_result = await db.execute(source_query)
    source = source_result.scalars().first()
    
    if not source:
        raise ValueError(f"Source not found: {source_id}")
    
    # Count total items
    total_query = select(func.count()).select_from(Item).filter(Item.source_id == source_id)
    total_result = await db.execute(total_query)
    total_items = total_result.scalar()
    
    # Count processed items
    processed_query = select(func.count()).select_from(Item).filter(
        Item.source_id == source_id,
        Item.processed == True
    )
    processed_result = await db.execute(processed_query)
    processed_items = processed_result.scalar()
    
    # Get most recent item
    recent_query = select(Item).filter(Item.source_id == source_id).order_by(Item.created_at.desc()).limit(1)
    recent_result = await db.execute(recent_query)
    most_recent = recent_result.scalars().first()
    
    # Build stats
    stats = {
        "source_id": source_id,
        "source_name": source.name,
        "total_items": total_items,
        "processed_items": processed_items,
        "processing_ratio": processed_items / total_items if total_items > 0 else 0,
        "last_fetched": source.last_fetched,
        "last_item_timestamp": most_recent.created_at if most_recent else None,
        "is_active": source.is_active
    }
    
    return stats 