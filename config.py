# config.py
import os
from pathlib import Path
from pydantic_settings import BaseSettings
import logging

# Configure logging
logger = logging.getLogger(__name__)

# project root
BASE_DIR = Path(__file__).resolve().parent

# Log environment info
logger.warning("Config module loading...")

class Settings(BaseSettings):
    # base path for locating files in your repo
    BASE_DIR: Path = BASE_DIR

    OPENAI_API_KEY: str
    EMBEDDING_MODEL: str
    CLASSIFIER_MODEL: str
    GENERATOR_MODEL: str
    VECTOR_DIM: int
    VECTOR_INDEX_PATH: str
    DATABASE_URL: str

    # Perplexity API settings
    PERPLEXITY_API_KEY: str = os.getenv("PERPLEXITY_API_KEY", "")

    # Twilio settings
    TWILIO_ACCOUNT_SID: str = os.getenv("TWILIO_ACCOUNT_SID", "")
    TWILIO_AUTH_TOKEN: str = os.getenv("TWILIO_AUTH_TOKEN", "")
    TWILIO_PHONE_NUMBER: str = os.getenv("TWILIO_PHONE_NUMBER", "")
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"

    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
    SUPABASE_SERVICE_ROLE_KEY: str = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")

    class Config:
        env_file = ".env"

settings = Settings()

# Log critical settings for debugging
logger.warning(f"Loaded settings:")
logger.warning(f"OPENAI_API_KEY set: {bool(settings.OPENAI_API_KEY)}")
logger.warning(f"OPENAI_API_KEY length: {len(settings.OPENAI_API_KEY) if settings.OPENAI_API_KEY else 0}")
logger.warning(f"OPENAI_API_KEY first 5 chars: {settings.OPENAI_API_KEY[:5] + '...' if settings.OPENAI_API_KEY else 'None'}")
logger.warning(f"GENERATOR_MODEL: {settings.GENERATOR_MODEL}")