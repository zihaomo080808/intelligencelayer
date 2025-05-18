import asyncio
import sys
import logging
import json
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.append(str(PROJECT_ROOT))

from onboarding_messages import process_onboarding_message
from database.session import get_db

async def test_onboarding_process():
    print("Testing onboarding process...")
    
    try:
        # Create a test message and profile
        test_message = "My name is John"
        test_step = 0
        test_profile = {}
        test_user_id = "test_user_123"
        
        # Get database session
        db_gen = get_db()
        db = await db_gen.__anext__()
        
        print("Calling process_onboarding_message...")
        profile, next_question, is_complete = await process_onboarding_message(
            test_message,
            test_step,
            test_profile,
            test_user_id,
            db
        )
        
        print("✅ Onboarding process successful!")
        print(f"Profile: {json.dumps(profile, indent=2)}")
        print(f"Next question: {next_question}")
        print(f"Is complete: {is_complete}")
            
    except Exception as e:
        print(f"❌ Onboarding process failed: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_onboarding_process())