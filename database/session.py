"""
Database session management including AsyncSessionLocal factory and get_db utility.
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker
from .base import engine

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
    async with AsyncSessionLocal() as session:
        yield session
