"""
Migration script for adding feedback models to the database.

Run this script to create the UserConversation and update the UserFeedback table.
"""
import asyncio
import logging
from typing import List, Dict
from sqlalchemy import text

from database.base import engine
from database.models import Base

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def create_tables():
    """Create new tables in the database."""
    try:
        async with engine.begin() as conn:
            # Create tables if they don't exist
            await conn.run_sync(Base.metadata.create_all)
            logger.info("Tables created successfully")
    except Exception as e:
        logger.error(f"Error creating tables: {str(e)}")
        raise

async def add_confidence_column():
    """Add confidence column to user_feedback table if it doesn't exist."""
    try:
        async with engine.connect() as conn:
            # Check if column exists
            exists_query = """
            SELECT column_name FROM information_schema.columns 
            WHERE table_name='user_feedback' AND column_name='confidence'
            """
            result = await conn.execute(text(exists_query))
            column_exists = result.scalar() is not None
            
            if not column_exists:
                # Add column
                logger.info("Adding confidence column to user_feedback table")
                await conn.execute(
                    text("ALTER TABLE user_feedback ADD COLUMN confidence FLOAT DEFAULT 1.0")
                )
                await conn.commit()
                logger.info("Added confidence column")
            else:
                logger.info("Confidence column already exists")
                
    except Exception as e:
        logger.error(f"Error adding confidence column: {str(e)}")
        raise

async def add_conversation_id_column():
    """Add conversation_id column to user_feedback table if it doesn't exist."""
    try:
        async with engine.connect() as conn:
            # Check if column exists
            exists_query = """
            SELECT column_name FROM information_schema.columns 
            WHERE table_name='user_feedback' AND column_name='conversation_id'
            """
            result = await conn.execute(text(exists_query))
            column_exists = result.scalar() is not None
            
            if not column_exists:
                # Add column
                logger.info("Adding conversation_id column to user_feedback table")
                await conn.execute(
                    text("ALTER TABLE user_feedback ADD COLUMN conversation_id INTEGER")
                )
                await conn.commit()
                logger.info("Added conversation_id column")
            else:
                logger.info("Conversation_id column already exists")
                
    except Exception as e:
        logger.error(f"Error adding conversation_id column: {str(e)}")
        raise

async def add_foreign_key():
    """Add foreign key constraint if it doesn't exist."""
    try:
        async with engine.connect() as conn:
            # Check if constraint exists
            exists_query = """
            SELECT constraint_name FROM information_schema.table_constraints
            WHERE table_name='user_feedback' AND constraint_type='FOREIGN KEY'
            AND constraint_name='user_feedback_conversation_id_fkey'
            """
            result = await conn.execute(text(exists_query))
            constraint_exists = result.scalar() is not None
            
            if not constraint_exists:
                # Add foreign key constraint
                logger.info("Adding foreign key constraint")
                await conn.execute(
                    text("""
                    ALTER TABLE user_feedback 
                    ADD CONSTRAINT user_feedback_conversation_id_fkey
                    FOREIGN KEY (conversation_id) REFERENCES user_conversations (id)
                    """)
                )
                await conn.commit()
                logger.info("Added foreign key constraint")
            else:
                logger.info("Foreign key constraint already exists")
                
    except Exception as e:
        logger.error(f"Error adding foreign key constraint: {str(e)}")
        raise

async def main():
    """Run all migration steps."""
    try:
        logger.info("Starting migration...")
        
        # Create tables
        await create_tables()
        
        # Add columns
        await add_confidence_column()
        await add_conversation_id_column()
        
        # Add foreign key
        await add_foreign_key()
        
        logger.info("Migration completed successfully")
        
    except Exception as e:
        logger.error(f"Migration failed: {str(e)}")
        raise

if __name__ == "__main__":
    asyncio.run(main())