import asyncio
import sys
import logging
from pathlib import Path
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.append(str(PROJECT_ROOT))

from agents.conversation_agent import get_agent_response
from database.models import UserConversation

async def test_agent_response():
    """Test the conversation agent by sending a test message to OpenAI."""
    print("Testing conversation agent with OpenAI...")
    
    # Create a mock conversation
    conversation = UserConversation(
        id=999,
        user_id="test_user",
        item_id="test_item",
        transcript=f"[{datetime.utcnow()}] User: Tell me about this opportunity.",
        message_count=1,
        started_at=datetime.utcnow()
    )
    
    # Create a mock opportunity
    opportunity = {
        "title": "AI Hackathon",
        "description": "Join our weekend hackathon focused on artificial intelligence and machine learning projects.",
        "date": "June 15-16, 2025",
        "location": "San Francisco, CA",
        "requirements": "Open to all skill levels. Basic programming knowledge helpful.",
        "url": "https://example.com/ai-hackathon"
    }
    
    # Get a response from the agent
    try:
        print("Sending request to OpenAI API...")
        response = await get_agent_response(conversation, opportunity)
        print("\n--- Agent Response ---")
        print(response)
        print("----------------------\n")
        
        if response:
            print("✅ Conversation agent successfully connected to OpenAI!")
            return True
        else:
            print("❌ Received empty response from the agent")
            return False
            
    except Exception as e:
        print(f"❌ Error testing conversation agent: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    asyncio.run(test_agent_response())