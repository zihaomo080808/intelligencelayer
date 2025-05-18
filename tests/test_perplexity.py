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

from perplexity_client import query_user_background
from config import settings

async def test_perplexity_api():
    print("Testing Perplexity API...")
    print(f"PERPLEXITY_API_KEY set: {bool(settings.PERPLEXITY_API_KEY)}")
    print(f"PERPLEXITY_API_KEY length: {len(settings.PERPLEXITY_API_KEY) if settings.PERPLEXITY_API_KEY else 0}")
    
    if not settings.PERPLEXITY_API_KEY:
        print("❌ PERPLEXITY_API_KEY not set!")
        return
    
    try:
        test_profile = {
            "name": "Test User",
            "location": "San Francisco",
            "education": "Stanford University",
            "occupation": "Software Engineer",
            "interests": ["artificial intelligence", "machine learning", "coding"]
        }
        
        print("Calling Perplexity API with test profile...")
        result = await query_user_background(test_profile)
        
        if result:
            print("✅ Perplexity API call successful!")
            print(f"Result: {result}")
        else:
            print("❌ Perplexity API call returned empty result!")
            
    except Exception as e:
        print(f"❌ Perplexity API call failed: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_perplexity_api())