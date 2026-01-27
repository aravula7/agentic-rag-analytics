"""Application configuration using Pydantic settings."""

import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Database
    DB_HOST: str = os.getenv("DB_HOST", "")
    DB_PORT: int = 5432
    DB_NAME: str = os.getenv("DB_NAME", "")
    DB_USER: str = os.getenv("DB_USER", "")
    DB_PASSWORD: str = os.getenv("DB_PASSWORD", "")

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
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_GENERAL_MODEL: str = "gpt-4o"
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-small"
    OPENAI_MAX_TOKENS: int = 500

    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
    ANTHROPIC_SQL_MODEL: str = os.environ.get("ANTHROPIC_SQL_MODEL", "")
    ANTHROPIC_MAX_TOKENS: int = 1000

    # Chroma
    CHROMA_HOST: str = "localhost"
    CHROMA_PORT: int = 8082
    CHROMA_COLLECTION: str = "agentic_rag_analytics_schema"
    CHROMA_PERSIST_DIR: str = "./embeddings"

    # Langfuse
    LANGFUSE_PUBLIC_KEY: str = os.getenv("LANGFUSE_PUBLIC_KEY", "")
    LANGFUSE_SECRET_KEY: str = os.getenv("LANGFUSE_SECRET_KEY", "")
    LANGFUSE_HOST: str = "https://us.cloud.langfuse.com"

    # Email
    EMAIL_PROVIDER: str = "gmail"
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = os.getenv("SMTP_USER", "")
    SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "")

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