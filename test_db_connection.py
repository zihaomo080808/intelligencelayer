import asyncio
import sys
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.append(str(PROJECT_ROOT))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
# Use hardcoded connection string for testing
DATABASE_URL = "postgresql+asyncpg://postgres:Mozihao08@localhost:5432/postgres"
print(f"Using hardcoded DATABASE_URL: {DATABASE_URL}")

async def test_database_connection():
    print("Testing database connection...")
    print(f"Database URL: {DATABASE_URL}")

    try:
        # Create a direct connection to the database
        logger.info("Creating engine with URL: %s", DATABASE_URL)
        engine = create_async_engine(
            DATABASE_URL,
            echo=True  # Show SQL queries
        )

        # Create a session factory
        logger.info("Creating session factory")
        async_session = sessionmaker(
            engine, class_=AsyncSession, expire_on_commit=False
        )

        # Test the connection
        logger.info("Testing connection")
        async with async_session() as session:
            # Test with a simple query
            result = await session.execute(text("SELECT 1"))
            value = result.scalar()

            if value == 1:
                print("✅ Database connection successful!")
            else:
                print("❌ Unexpected result:", value)
    except Exception as e:
        print(f"❌ Database connection failed: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_database_connection())