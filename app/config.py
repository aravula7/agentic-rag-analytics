"""Application configuration using Pydantic settings."""

from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Database
    DB_HOST: str
    DB_PORT: int = 5432
    DB_NAME: str
    DB_USER: str
    DB_PASSWORD: str

    # S3/MinIO
    S3_ENDPOINT_URL: Optional[str] = None
    S3_BUCKET_NAME: str = "rag-reports"
    AWS_ACCESS_KEY_ID: str
    AWS_SECRET_ACCESS_KEY: str
    AWS_REGION: str = "us-east-1"

    # LLM APIs
    OPENAI_API_KEY: str
    OPENAI_GENERAL_MODEL: str = "gpt-4o"
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-small"
    OPENAI_MAX_TOKENS: int = 500

    ANTHROPIC_API_KEY: str
    ANTHROPIC_SQL_MODEL: str = "claude-haiku-4-20250514"
    ANTHROPIC_MAX_TOKENS: int = 1000

    # Redis
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6380
    REDIS_PASSWORD: Optional[str] = None
    REDIS_CACHE_TTL: int = 86400

    # Chroma
    CHROMA_HOST: str = "localhost"
    CHROMA_PORT: int = 8082
    CHROMA_COLLECTION: str = "schema_embeddings"
    CHROMA_PERSIST_DIR: str = "./embeddings"

    # Langfuse
    LANGFUSE_PUBLIC_KEY: str
    LANGFUSE_SECRET_KEY: str
    LANGFUSE_HOST: str = "https://cloud.langfuse.com"

    # Email
    EMAIL_PROVIDER: str = "gmail"
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str
    SMTP_PASSWORD: str

    # Application
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8001
    LOG_LEVEL: str = "INFO"

    # Agent Configuration
    SQL_RETRY_MAX: int = 3
    QUERY_TIMEOUT: int = 30
    ENABLE_CACHE: bool = True

    class Config:
        env_file = ".env"
        case_sensitive = True


# Global settings instance
settings = Settings()