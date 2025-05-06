# config.py
import os
from pathlib import Path
from pydantic_settings import BaseSettings

# project root
BASE_DIR = Path(__file__).resolve().parent

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
    
    # Twilio settings
    TWILIO_ACCOUNT_SID: str = os.getenv("TWILIO_ACCOUNT_SID", "")
    TWILIO_AUTH_TOKEN: str = os.getenv("TWILIO_AUTH_TOKEN", "")
    TWILIO_PHONE_NUMBER: str = os.getenv("TWILIO_PHONE_NUMBER", "")
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"

    class Config:
        env_file = ".env"

settings = Settings()
