# app/core/config.py
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional
from pathlib import Path
import os
import secrets

class Settings(BaseSettings):
    # General App Settings
    PROJECT_NAME: str = "Fullstack RAG App"
    API_V1_STR: str = "/api/v1"
    DEBUG_MODE: bool = True

    # Database Settings
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "user"
    POSTGRES_PASSWORD: str = "password" 
    POSTGRES_DB: str = "db" 
    DATABASE_URL: Optional[str] = None 

    # Redis Settings (for Celery and caching)
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    CELERY_BROKER_URL: Optional[str] = None 
    CELERY_RESULT_BACKEND: Optional[str] = None 

    # S3/GCS Object Storage Settings
    AWS_ACCESS_KEY_ID: Optional[str] = None
    AWS_SECRET_ACCESS_KEY: Optional[str] = None
    AWS_REGION_NAME: Optional[str] = "us-east-1"
    S3_BUCKET_NAME: Optional[str] = "book-summarizer-pdfs"

    # LLM Settings
    LLM_INFERENCE_SERVICE_URL: str = "http://localhost:8001/llm_inference" 

    # Vector Database Settings (e.g., ChromaDB)
    CHROMA_HOST: str = "localhost"
    CHROMA_PORT: int = 8000
    CHROMA_COLLECTION_NAME: str = "book_summarizer_embeddings"

    # JWT Authentication settings
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    COLLEGE_LLM_ENDPOINT: str = "http://localhost:8002"
    
    # Model configuration for loading .env file
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.DATABASE_URL:
            self.DATABASE_URL = (
                f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@"
                f"{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
            )
        if not self.CELERY_BROKER_URL:
            self.CELERY_BROKER_URL = f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
        if not self.CELERY_RESULT_BACKEND:
            self.CELERY_RESULT_BACKEND = self.CELERY_BROKER_URL

        if not self.SECRET_KEY:
            dev_secret_path = Path(".dev_secret")
            if dev_secret_path.exists():
                self.SECRET_KEY = dev_secret_path.read_text().strip()
            else:
                import secrets
                new_secret = secrets.token_urlsafe(32)
                dev_secret_path.write_text(new_secret)
                self.SECRET_KEY = new_secret
                print(f"Generated new SECRET_KEY and saved to {dev_secret_path}. Add this to .env file.")


settings = Settings()
