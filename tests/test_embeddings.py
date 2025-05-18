import sys
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.append(str(PROJECT_ROOT))

from embeddings.embedder import get_embedding
from config import settings

def test_embeddings():
    print("Testing OpenAI embeddings...")
    print(f"OPENAI_API_KEY set: {bool(settings.OPENAI_API_KEY)}")
    print(f"OPENAI_API_KEY length: {len(settings.OPENAI_API_KEY) if settings.OPENAI_API_KEY else 0}")
    print(f"EMBEDDING_MODEL: {settings.EMBEDDING_MODEL}")
    
    if not settings.OPENAI_API_KEY:
        print("❌ OPENAI_API_KEY not set!")
        return
    
    try:
        test_text = "This is a test for generating embeddings."
        
        print("Calling OpenAI embeddings API...")
        result = get_embedding(test_text)
        
        if result:
            print("✅ OpenAI embeddings API call successful!")
            print(f"Embedding dimension: {len(result)}")
            print(f"First 5 values: {result[:5]}")
        else:
            print("❌ OpenAI embeddings API call returned empty result!")
            
    except Exception as e:
        print(f"❌ OpenAI embeddings API call failed: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_embeddings()