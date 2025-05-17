import asyncio
import logging
from database.base import init_db
from config import settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_db_init():
    logger.info(f"DEBUG mode: {settings.DEBUG}")
    logger.info(f"DATABASE_URL: {settings.DATABASE_URL}")
    
    try:
        logger.info("Attempting to initialize database...")
        await init_db()
        logger.info("Database initialization completed successfully")
    except Exception as e:
        logger.error(f"Database initialization failed: {str(e)}")

if __name__ == "__main__":
    asyncio.run(test_db_init())