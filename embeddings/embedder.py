# embeddings/embedder.py
import openai
from config import settings

openai.api_key = settings.OPENAI_API_KEY

def get_embedding(text: str):
    resp = openai.Embedding.create(
        model=settings.EMBEDDING_MODEL,
        input=[text]
    )
    return resp["data"][0]["embedding"]
