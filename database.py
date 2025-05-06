# database.py
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from config import settings

def is_valid_postgresql_url(url):
    """Check if the URL is a valid PostgreSQL URL."""
    return (
        url.startswith("postgres://") or 
        url.startswith("postgresql://") or
        url.startswith("postgresql+asyncpg://")
    )

DATABASE_URL = settings.DATABASE_URL

# Print the URL for debugging
print(f"Database URL: {DATABASE_URL}")

# 2. Normalize to the asyncpg dialect
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+asyncpg://", 1)
elif DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)
elif not is_valid_postgresql_url(DATABASE_URL):
    raise ValueError(f"Only PostgreSQL URLs are supported. Got: {DATABASE_URL}")

# Print the normalized URL for debugging
print(f"Normalized Database URL: {DATABASE_URL}")

# 1) Async engine using asyncpg
engine = create_async_engine(
    DATABASE_URL, 
    echo=False,              # or True for SQL logging
    future=True
)

# 2) AsyncSession factory
AsyncSessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    future=True,
)

# 3) Base class for your models
Base = declarative_base()

async def get_db():
    """
    Yield a fresh database session, and ensure it's closed
    (returned to the pool) when the request is done.
    """
    async with AsyncSessionLocal() as session:
        yield session