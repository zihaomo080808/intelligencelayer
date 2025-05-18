"""
Debug script for testing the onboarding process and username saving
"""
import asyncio
import logging
from typing import Dict, Any
import json

from database.session import get_db
from database.models import UserProfile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Test user information
TEST_USER_ID = "test_debug_user_123"
TEST_USERNAME = "Debug Test User"

async def test_direct_profile_creation():
    """Test creating a profile directly using database models"""
    logger.info("=== Testing direct profile creation ===")
    
    async for db in get_db():
        try:
            # Check if user already exists
            result = await db.execute(
                select(UserProfile).where(UserProfile.user_id == TEST_USER_ID)
            )
            existing_profile = result.scalar_one_or_none()
            
            if existing_profile:
                logger.info(f"Found existing profile: {existing_profile.user_id}")
                logger.info(f"Current username: {existing_profile.username}")
                
                # Update username
                existing_profile.username = TEST_USERNAME
                await db.commit()
                logger.info(f"Updated username to: {TEST_USERNAME}")
            else:
                # Create new profile
                logger.info(f"Creating new profile for user: {TEST_USER_ID}")
                new_profile = UserProfile(
                    user_id=TEST_USER_ID,
                    username=TEST_USERNAME,
                    bio="Test bio for debugging",
                    location="Test Location",
                    stances={"test_stance": "For testing"}
                )
                db.add(new_profile)
                await db.commit()
                logger.info(f"Created new profile with username: {TEST_USERNAME}")
            
            # Verify profile was saved correctly
            verification = await db.execute(
                select(UserProfile).where(UserProfile.user_id == TEST_USER_ID)
            )
            saved_profile = verification.scalar_one_or_none()
            
            if saved_profile:
                logger.info("Profile verification results:")
                logger.info(f"  user_id: {saved_profile.user_id}")
                logger.info(f"  username: {saved_profile.username}")
                logger.info(f"  bio: {saved_profile.bio}")
                logger.info(f"  stances: {saved_profile.stances}")
                
                # Check SQL representation
                if saved_profile.username != TEST_USERNAME:
                    logger.error(f"Username mismatch! Expected: {TEST_USERNAME}, Got: {saved_profile.username}")
                else:
                    logger.info("Username saved correctly")
            else:
                logger.error("Failed to retrieve profile after save")
            
            break  # Only process one database session
            
        except Exception as e:
            logger.error(f"Error in direct profile creation: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())

async def test_onboarding_flow():
    """Test the onboarding process flow"""
    from onboarding_messages import process_onboarding_message
    
    logger.info("=== Testing onboarding process flow ===")
    
    async for db in get_db():
        try:
            # Start with step 1 (introduction)
            user_id = f"{TEST_USER_ID}_onboarding"
            logger.info(f"Starting onboarding for user: {user_id}")
            
            # Step 1: Introduction
            step = 1
            message = "Hi, I'm TestUser for debugging"
            profile = {}
            
            logger.info(f"Step {step}: Processing message: '{message}'")
            updated_profile, next_question, is_complete = await process_onboarding_message(
                message, step, profile, user_id, db
            )
            
            logger.info(f"Step {step} result: Profile={updated_profile}, Next={next_question}, Complete={is_complete}")
            
            # Step 2: Follow-up
            step = 2
            message = "I'm interested in technology and debugging programs"
            profile = updated_profile
            
            logger.info(f"Step {step}: Processing message: '{message}'")
            updated_profile, next_question, is_complete = await process_onboarding_message(
                message, step, profile, user_id, db
            )
            
            logger.info(f"Step {step} result: Profile={updated_profile}, Next={next_question}, Complete={is_complete}")
            
            # Step 3: Location
            step = 3
            message = "San Francisco, CA"
            profile = updated_profile
            
            logger.info(f"Step {step}: Processing message: '{message}'")
            updated_profile, next_question, is_complete = await process_onboarding_message(
                message, step, profile, user_id, db
            )
            
            logger.info(f"Step {step} result: Profile={updated_profile}, Next={next_question}, Complete={is_complete}")
            
            # Check database for the final profile
            await asyncio.sleep(1)  # Allow time for any async operations to complete
            
            result = await db.execute(
                select(UserProfile).where(UserProfile.user_id == user_id)
            )
            saved_profile = result.scalar_one_or_none()
            
            if saved_profile:
                logger.info("Final saved profile in database:")
                logger.info(f"  user_id: {saved_profile.user_id}")
                logger.info(f"  username: {saved_profile.username}")
                logger.info(f"  bio: {saved_profile.bio}")
                logger.info(f"  location: {saved_profile.location}")
                logger.info(f"  stances: {saved_profile.stances}")
                
                # Check if username was saved
                if not saved_profile.username:
                    logger.error("Username was not saved in the database!")
                    
                    # Inspect internal profile data structure during onboarding
                    logger.info(f"Final profile from onboarding process: {json.dumps(updated_profile, default=str, indent=2)}")
                    
                    if "username" in updated_profile:
                        logger.info(f"Username in profile dict: {updated_profile.get('username')}")
                        logger.error("Username exists in process data but wasn't saved to DB")
                    else:
                        logger.error("Username missing from process data")
            else:
                logger.error(f"No profile found in database for user {user_id}")
                logger.info(f"Final profile from onboarding process: {json.dumps(updated_profile, default=str, indent=2)}")
            
            break  # Only process one database session
            
        except Exception as e:
            logger.error(f"Error in onboarding flow: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())

async def main():
    # Run tests
    logger.info("Starting onboarding debug tests")
    
    await test_direct_profile_creation()
    logger.info("\n")
    await test_onboarding_flow()
    
    logger.info("Debug tests completed")

if __name__ == "__main__":
    asyncio.run(main())