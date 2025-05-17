"""
Database session management including AsyncSessionLocal factory and get_db utility.
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker
from .base import engine
from config import settings
import logging

# Configure logging
logger = logging.getLogger(__name__)

# AsyncSession factory for creating database sessions
AsyncSessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    future=True,
)

async def get_db():
    """
    Yield a fresh database session, and ensure it's closed
    (returned to the pool) when the request is done.

    Usage:
        @app.get("/items/")
        async def read_items(db: AsyncSession = Depends(get_db)):
            items = await db.execute(select(Item))
            return items.scalars().all()
    """
    # In debug mode with DB connection issues, return a dummy session
    if settings.DEBUG:
        try:
            async with AsyncSessionLocal() as session:
                yield session
        except Exception as e:
            logger.warning(f"Database connection failed: {str(e)}. Using dummy session in DEBUG mode.")
            # Create a dummy session object that just logs operations
            class DummySession:
                async def __aenter__(self):
                    return self

                async def __aexit__(self, exc_type, exc_val, exc_tb):
                    pass

                async def commit(self):
                    logger.warning("Dummy commit called")
                    pass

                async def rollback(self):
                    logger.warning("Dummy rollback called")
                    pass

                async def execute(self, *args, **kwargs):
                    logger.warning(f"Dummy execute called with: {args}, {kwargs}")
                    return None

                async def get(self, *args, **kwargs):
                    logger.warning(f"Dummy get called with: {args}, {kwargs}")
                    return None

                def add(self, *args, **kwargs):
                    logger.warning(f"Dummy add called with: {args}, {kwargs}")
                    pass

                def add_all(self, *args, **kwargs):
                    logger.warning(f"Dummy add_all called with: {args}, {kwargs}")
                    pass

                def delete(self, *args, **kwargs):
                    logger.warning(f"Dummy delete called with: {args}, {kwargs}")
                    pass

                def close(self):
                    logger.warning("Dummy close called")
                    pass

                def refresh(self, *args, **kwargs):
                    logger.warning(f"Dummy refresh called with: {args}, {kwargs}")
                    pass

            yield DummySession()
    else:
        # Normal operation in production
        async with AsyncSessionLocal() as session:
            yield session
