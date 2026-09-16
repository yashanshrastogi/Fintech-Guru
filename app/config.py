from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import AnyHttpUrl, SecretStr
from typing import List, Optional, Union

class Settings(BaseSettings):
    # Base configuration
    PROJECT_NAME: str = "FinTech Guru V2 API"
    VERSION: str = "2.0.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = False
    
    # API / CORS
    API_V1_STR: str = "/api/v1"
    CORS_ORIGINS: List[AnyHttpUrl] = []

    # Database
    DATABASE_URL: str = "sqlite:///./fintech_guru.db"
    
    # Security / Auth
    # To generate a new secret key: openssl rand -hex 32
    SECRET_KEY: SecretStr = SecretStr("insecure-dev-secret-key-change-in-prod")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7 # 7 days
    
    # LLM Settings
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "qwen3:8b"
    LLM_TIMEOUT: int = 30
    LLM_RETRY_LIMIT: int = 3
    
    # Storage
    STORAGE_BACKEND: str = "local" # 'local' or 's3'
    S3_BUCKET_NAME: Optional[str] = None
    AWS_ACCESS_KEY_ID: Optional[str] = None
    AWS_SECRET_ACCESS_KEY: Optional[str] = None
    AWS_REGION: Optional[str] = None
    
    # Observability
    DEBUG_PIPELINE_TRACE: bool = True

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )

settings = Settings()
