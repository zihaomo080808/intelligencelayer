# database/base.py
"""
Base database components including engine setup and connection handling.
"""
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import declarative_base
from config import settings

def is_valid_postgresql_url(url):
    """Check if the URL is a valid PostgreSQL URL."""
    return (
        url.startswith("postgres://") or 
        url.startswith("postgresql://") or
        url.startswith("postgresql+asyncpg://")
    )

# Get database URL from settings
DATABASE_URL = settings.DATABASE_URL

# Normalize to the asyncpg dialect
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+asyncpg://", 1)
elif DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)
elif not is_valid_postgresql_url(DATABASE_URL):
    raise ValueError(f"Only PostgreSQL URLs are supported. Got: {DATABASE_URL}")

# Create async engine using asyncpg
engine = create_async_engine(
    DATABASE_URL, 
    echo=False,    # Set to True for SQL logging
    future=True
)

# Base class for SQLAlchemy models
Base = declarative_base()

async def init_db():
    """Initialize database tables."""
    import logging
    logger = logging.getLogger(__name__)

    # Attempt database initialization even in DEBUG mode
    from sqlalchemy.ext.asyncio import AsyncSession
    from sqlalchemy import text

    try:
        # First, create pgvector extension if it doesn't exist
        async with engine.begin() as conn:
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))

        # Then create all tables
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        logger.info("Database tables initialized successfully")
    except Exception as e:
        logger.error(f"Error initializing database tables: {str(e)}")
        if settings.DEBUG:
            logger.warning("DEBUG mode enabled, continuing despite database initialization error")
        else:
            # In production, re-raise the exception
            raise
