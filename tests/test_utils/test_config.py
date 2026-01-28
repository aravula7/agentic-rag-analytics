"""Tests for application configuration."""

import os
import pytest
from unittest.mock import patch


class TestSettings:
    """Test cases for Settings class."""

    def test_settings_defaults(self):
        """Test Settings has correct default values."""
        with patch.dict(os.environ, {}, clear=True):
            # Need to reload module to pick up fresh env
            from app.config import Settings

            settings = Settings()

            assert settings.DB_PORT == 5432
            assert settings.S3_BUCKET_NAME == "rag-reports"
            assert settings.AWS_REGION == "us-east-1"
            assert settings.REDIS_CACHE_TTL == 86400
            assert settings.ENABLE_CACHE is True
            assert settings.OPENAI_GENERAL_MODEL == "gpt-4o"
            assert settings.OPENAI_EMBEDDING_MODEL == "text-embedding-3-small"
            assert settings.CHROMA_HOST == "localhost"
            assert settings.CHROMA_PORT == 8082
            assert settings.SMTP_HOST == "smtp.gmail.com"
            assert settings.SMTP_PORT == 587
            assert settings.SQL_RETRY_MAX == 3
            assert settings.QUERY_TIMEOUT == 30

    def test_settings_from_environment(self):
        """Test Settings loads from environment variables."""
        env_vars = {
            "DB_HOST": "production-db.example.com",
            "DB_PORT": "5433",
            "DB_NAME": "production_db",
            "DB_USER": "prod_user",
            "DB_PASSWORD": "secret123",
            "OPENAI_API_KEY": "sk-test-key",
            "ANTHROPIC_API_KEY": "sk-ant-test",
            "REDIS_CACHE_TTL": "7200",
            "ENABLE_CACHE": "false",
        }

        with patch.dict(os.environ, env_vars):
            from app.config import Settings

            settings = Settings()

            assert settings.DB_HOST == "production-db.example.com"
            assert settings.DB_PORT == 5433
            assert settings.DB_NAME == "production_db"
            assert settings.DB_USER == "prod_user"
            assert settings.DB_PASSWORD == "secret123"
            assert settings.OPENAI_API_KEY == "sk-test-key"
            assert settings.ANTHROPIC_API_KEY == "sk-ant-test"
            assert settings.REDIS_CACHE_TTL == 7200
            assert settings.ENABLE_CACHE is False

    def test_settings_case_sensitive(self):
        """Test Settings is case sensitive for env vars."""
        env_vars = {
            "db_host": "lowercase-host",
            "DB_HOST": "uppercase-host",
        }

        with patch.dict(os.environ, env_vars):
            from app.config import Settings

            settings = Settings()

            # Should use uppercase version
            assert settings.DB_HOST == "uppercase-host"

    def test_settings_optional_fields(self):
        """Test Settings declares optional fields correctly.

        This test must clear env vars AND disable .env file loading so
        that only the field defaults are used.
        """
        from app.config import Settings

        # Temporarily remove AWS keys from the environment so defaults apply
        with patch.dict(os.environ, {}, clear=True):
            settings = Settings(_env_file=None)

        assert settings.AWS_ACCESS_KEY_ID is None
        assert settings.AWS_SECRET_ACCESS_KEY is None
        assert settings.DB_HOST == ""
        assert settings.OPENAI_API_KEY == ""

    def test_settings_s3_configuration(self):
        """Test S3/Supabase configuration."""
        env_vars = {
            "S3_ENDPOINT_URL": "https://abc123.supabase.co/storage/v1/s3",
            "S3_BUCKET_NAME": "my-bucket",
            "AWS_ACCESS_KEY_ID": "my-access-key",
            "AWS_SECRET_ACCESS_KEY": "my-secret-key",
            "AWS_REGION": "eu-west-1",
        }

        with patch.dict(os.environ, env_vars):
            from app.config import Settings

            settings = Settings()

            assert settings.S3_ENDPOINT_URL == "https://abc123.supabase.co/storage/v1/s3"
            assert settings.S3_BUCKET_NAME == "my-bucket"
            assert settings.AWS_ACCESS_KEY_ID == "my-access-key"
            assert settings.AWS_SECRET_ACCESS_KEY == "my-secret-key"
            assert settings.AWS_REGION == "eu-west-1"

    def test_settings_upstash_configuration(self):
        """Test Upstash Redis configuration."""
        env_vars = {
            "UPSTASH_REDIS_REST_URL": "https://my-redis.upstash.io",
            "UPSTASH_REDIS_REST_TOKEN": "my-token",
            "REDIS_CACHE_TTL": "86400",
            "ENABLE_CACHE": "true",
        }

        with patch.dict(os.environ, env_vars):
            from app.config import Settings

            settings = Settings()

            assert settings.UPSTASH_REDIS_REST_URL == "https://my-redis.upstash.io"
            assert settings.UPSTASH_REDIS_REST_TOKEN == "my-token"
            assert settings.REDIS_CACHE_TTL == 86400
            assert settings.ENABLE_CACHE is True

    def test_settings_llm_configuration(self):
        """Test LLM API configuration."""
        env_vars = {
            "OPENAI_API_KEY": "sk-openai-key",
            "OPENAI_GENERAL_MODEL": "gpt-4-turbo",
            "OPENAI_EMBEDDING_MODEL": "text-embedding-3-large",
            "OPENAI_MAX_TOKENS": "1000",
            "ANTHROPIC_API_KEY": "sk-anthropic-key",
            "ANTHROPIC_SQL_MODEL": "claude-3-5-haiku-20241022",
            "ANTHROPIC_MAX_TOKENS": "2000",
        }

        with patch.dict(os.environ, env_vars):
            from app.config import Settings

            settings = Settings()

            assert settings.OPENAI_API_KEY == "sk-openai-key"
            assert settings.OPENAI_GENERAL_MODEL == "gpt-4-turbo"
            assert settings.OPENAI_EMBEDDING_MODEL == "text-embedding-3-large"
            assert settings.OPENAI_MAX_TOKENS == 1000
            assert settings.ANTHROPIC_API_KEY == "sk-anthropic-key"
            assert settings.ANTHROPIC_SQL_MODEL == "claude-3-5-haiku-20241022"
            assert settings.ANTHROPIC_MAX_TOKENS == 2000

    def test_settings_chroma_configuration(self):
        """Test ChromaDB configuration."""
        env_vars = {
            "CHROMA_HOST": "chroma.example.com",
            "CHROMA_PORT": "8000",
            "CHROMA_COLLECTION": "my_collection",
            "CHROMA_PERSIST_DIR": "/data/embeddings",
        }

        with patch.dict(os.environ, env_vars):
            from app.config import Settings

            settings = Settings()

            assert settings.CHROMA_HOST == "chroma.example.com"
            assert settings.CHROMA_PORT == 8000
            assert settings.CHROMA_COLLECTION == "my_collection"
            assert settings.CHROMA_PERSIST_DIR == "/data/embeddings"

    def test_settings_langfuse_configuration(self):
        """Test Langfuse configuration."""
        env_vars = {
            "LANGFUSE_PUBLIC_KEY": "pk-lf-test",
            "LANGFUSE_SECRET_KEY": "sk-lf-test",
            "LANGFUSE_BASE_URL": "https://cloud.langfuse.com",
        }

        with patch.dict(os.environ, env_vars):
            from app.config import Settings

            settings = Settings()

            assert settings.LANGFUSE_PUBLIC_KEY == "pk-lf-test"
            assert settings.LANGFUSE_SECRET_KEY == "sk-lf-test"
            assert settings.LANGFUSE_BASE_URL == "https://cloud.langfuse.com"

    def test_settings_email_configuration(self):
        """Test email/SMTP configuration."""
        env_vars = {
            "EMAIL_PROVIDER": "gmail",
            "SMTP_HOST": "smtp.gmail.com",
            "SMTP_PORT": "587",
            "SMTP_USER": "user@gmail.com",
            "SMTP_PASSWORD": "app-password",
        }

        with patch.dict(os.environ, env_vars):
            from app.config import Settings

            settings = Settings()

            assert settings.EMAIL_PROVIDER == "gmail"
            assert settings.SMTP_HOST == "smtp.gmail.com"
            assert settings.SMTP_PORT == 587
            assert settings.SMTP_USER == "user@gmail.com"
            assert settings.SMTP_PASSWORD == "app-password"

    def test_settings_application_configuration(self):
        """Test application configuration."""
        env_vars = {
            "API_HOST": "0.0.0.0",
            "API_PORT": "8080",
            "STREAMLIT_PORT": "8502",
            "LOG_LEVEL": "DEBUG",
        }

        with patch.dict(os.environ, env_vars):
            from app.config import Settings

            settings = Settings()

            assert settings.API_HOST == "0.0.0.0"
            assert settings.API_PORT == 8080
            assert settings.STREAMLIT_PORT == 8502
            assert settings.LOG_LEVEL == "DEBUG"

    def test_settings_agent_configuration(self):
        """Test agent-specific configuration."""
        env_vars = {
            "SQL_RETRY_MAX": "5",
            "QUERY_TIMEOUT": "60",
        }

        with patch.dict(os.environ, env_vars):
            from app.config import Settings

            settings = Settings()

            assert settings.SQL_RETRY_MAX == 5
            assert settings.QUERY_TIMEOUT == 60


class TestGlobalSettings:
    """Test cases for global settings instance."""

    def test_global_settings_exists(self):
        """Test global settings instance exists."""
        from app.config import settings

        assert settings is not None

    def test_global_settings_is_singleton(self):
        """Test that settings is a singleton."""
        from app.config import settings as settings1
        from app.config import settings as settings2

        assert settings1 is settings2
