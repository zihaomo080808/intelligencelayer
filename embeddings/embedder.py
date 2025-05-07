# embeddings/embedder.py
from openai import OpenAI
import logging
from config import settings

# Configure logging
logger = logging.getLogger(__name__)

# Initialize OpenAI client
client = OpenAI(api_key=settings.OPENAI_API_KEY)

def get_embedding(text: str):
    try:
        logger.info(f"Generating embedding with model: {settings.EMBEDDING_MODEL}")
        resp = client.embeddings.create(
            model=settings.EMBEDDING_MODEL,
            input=[text]
        )
        return resp.data[0].embedding
    except Exception as e:
        logger.error(f"Error generating embedding: {str(e)}")
        raise Exception(f"Error generating embedding: {str(e)}")
