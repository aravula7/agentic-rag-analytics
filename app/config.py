"""Application configuration using Pydantic settings."""

import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Database
    DB_HOST: Optional[str] = None
    DB_PORT: int = 5432
    DB_NAME: Optional[str] = None
    DB_USER: Optional[str] = None
    DB_PASSWORD: Optional[str] = None

    # S3/Supabase Storage
    S3_ENDPOINT_URL: str = os.getenv("S3_ENDPOINT_URL", "")
    S3_BUCKET_NAME: str = "rag-reports"
    AWS_ACCESS_KEY_ID: Optional[str] = None
    AWS_SECRET_ACCESS_KEY: Optional[str] = None
    AWS_REGION: str = "us-east-1"

    # Upstash Redis (REST API)
    UPSTASH_REDIS_REST_URL: str = ""
    UPSTASH_REDIS_REST_TOKEN: str = ""
    REDIS_CACHE_TTL: int = 86400
    ENABLE_CACHE: bool = True

    # LLM APIs
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_GENERAL_MODEL: str = "gpt-4o"
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-small"
    OPENAI_MAX_TOKENS: int = 500

    ANTHROPIC_API_KEY: Optional[str] = None
    ANTHROPIC_SQL_MODEL: str = os.environ.get("ANTHROPIC_SQL_MODEL", "")
    ANTHROPIC_MAX_TOKENS: int = 1000

    # Chroma
    CHROMA_HOST: str = "localhost"
    CHROMA_PORT: int = 8082
    CHROMA_COLLECTION: str = "agentic_rag_analytics_schema"
    CHROMA_PERSIST_DIR: str = "./embeddings"

    # Langfuse
    LANGFUSE_PUBLIC_KEY: Optional[str] = None
    LANGFUSE_SECRET_KEY: Optional[str] = None
    LANGFUSE_HOST: str = "https://us.cloud.langfuse.com"

    # Email
    EMAIL_PROVIDER: str = "gmail"
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None

    # Application
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8001
    STREAMLIT_PORT: int = 8501
    LOG_LEVEL: str = "INFO"

    # Agent Configuration
    SQL_RETRY_MAX: int = 3
    QUERY_TIMEOUT: int = 30

    # Pydantic v2 configuration
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )


# Global settings instance
settings = Settings()