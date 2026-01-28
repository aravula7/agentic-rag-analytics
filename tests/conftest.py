"""Shared pytest fixtures for Agentic RAG Analytics tests."""

import os
import sys
import json
import pytest
from unittest.mock import Mock, MagicMock, patch, AsyncMock
from typing import Dict, Any, List
import pandas as pd
import httpx

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set test environment variables before importing app modules
os.environ["LANGFUSE_PUBLIC_KEY"] = "test-public-key"
os.environ["LANGFUSE_SECRET_KEY"] = "test-secret-key"
os.environ["OPENAI_API_KEY"] = "test-openai-key"
os.environ["ANTHROPIC_API_KEY"] = "test-anthropic-key"
os.environ["ENABLE_CACHE"] = "false"


# ---------------------------------------------------------------------------
# OpenAI Mock Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_openai_routing_response():
    """Mock OpenAI API response for routing decisions."""
    return {
        "requires_sql": True,
        "requires_email": False,
        "tables_involved": ["customers", "orders"],
        "query_complexity": "simple",
        "reasoning": "Query requires fetching customer order data"
    }


@pytest.fixture
def mock_openai_routing_response_with_email():
    """Mock OpenAI API response for routing with email."""
    return {
        "requires_sql": True,
        "requires_email": True,
        "tables_involved": ["products", "subscriptions"],
        "query_complexity": "complex",
        "reasoning": "Complex query requiring email delivery"
    }


@pytest.fixture
def mock_openai_routing_no_sql():
    """Mock OpenAI API response when no SQL is needed."""
    return {
        "requires_sql": False,
        "requires_email": False,
        "tables_involved": [],
        "query_complexity": "none",
        "reasoning": "Query is a general question, not a data request"
    }


@pytest.fixture
def mock_openai_client(mock_openai_routing_response):
    """Mock OpenAI client for router agent."""
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_choice = MagicMock()
    mock_message = MagicMock()

    mock_message.content = json.dumps(mock_openai_routing_response)
    mock_choice.message = mock_message
    mock_response.choices = [mock_choice]
    mock_client.chat.completions.create.return_value = mock_response

    return mock_client


@pytest.fixture
def mock_openai_embedding_response():
    """Mock OpenAI embedding response."""
    return [0.1] * 1536  # text-embedding-3-small returns 1536 dimensions


# ---------------------------------------------------------------------------
# Anthropic Mock Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_anthropic_sql_response():
    """Mock Anthropic API response for SQL generation."""
    return "SELECT c.customer_id, c.name, COUNT(o.order_id) as order_count FROM customers c JOIN orders o ON c.customer_id = o.customer_id GROUP BY c.customer_id, c.name ORDER BY order_count DESC LIMIT 10;"


@pytest.fixture
def mock_anthropic_client(mock_anthropic_sql_response):
    """Mock Anthropic client for SQL agent."""
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_text_block = MagicMock()

    # Set up the text attribute
    mock_text_block.text = mock_anthropic_sql_response

    # Make it pass isinstance check for TextBlock
    mock_response.content = [mock_text_block]
    mock_client.messages.create.return_value = mock_response

    return mock_client


# ---------------------------------------------------------------------------
# Database Mock Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_db_cursor():
    """Mock database cursor with sample results."""
    cursor = MagicMock()
    cursor.description = [
        ("customer_id",), ("name",), ("order_count",)
    ]
    cursor.fetchall.return_value = [
        {"customer_id": 1, "name": "Alice", "order_count": 50},
        {"customer_id": 2, "name": "Bob", "order_count": 45},
        {"customer_id": 3, "name": "Charlie", "order_count": 40},
    ]
    return cursor


@pytest.fixture
def mock_db_connection(mock_db_cursor):
    """Mock database connection."""
    conn = MagicMock()
    conn.cursor.return_value = mock_db_cursor
    return conn


@pytest.fixture
def sample_query_results():
    """Sample query results data."""
    return [
        {"customer_id": 1, "name": "Alice", "total_revenue": 15000.00},
        {"customer_id": 2, "name": "Bob", "total_revenue": 12500.00},
        {"customer_id": 3, "name": "Charlie", "total_revenue": 11000.00},
        {"customer_id": 4, "name": "Diana", "total_revenue": 9800.00},
        {"customer_id": 5, "name": "Eve", "total_revenue": 8500.00},
    ]


@pytest.fixture
def sample_columns():
    """Sample column names."""
    return ["customer_id", "name", "total_revenue"]


# ---------------------------------------------------------------------------
# Redis Mock Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_redis_cache():
    """Mock Redis cache instance."""
    cache = MagicMock()
    cache.get_result.return_value = None
    cache.set_result.return_value = None
    cache.delete.return_value = None
    return cache


@pytest.fixture
def mock_redis_cached_result():
    """Mock cached result from Redis."""
    return {
        "query": "show top customers",
        "routing_decision": {
            "requires_sql": True,
            "requires_email": False,
            "tables_involved": ["customers"],
            "query_complexity": "simple",
            "reasoning": "Simple customer query"
        },
        "sql": "SELECT * FROM customers LIMIT 10;",
        "s3_url": "https://example.com/results.csv",
        "metadata": {
            "row_count": 10,
            "column_count": 3,
            "execution_time_seconds": 0.5,
            "columns": ["customer_id", "name", "email"],
            "csv_s3_key": "reports/2024/01/15/query_test.csv",
            "csv_s3_url": "https://example.com/results.csv",
            "sql_s3_key": "queries/2024/01/15/query_test.sql",
            "sql_s3_url": "https://example.com/query.sql",
            "timestamp": "2024-01-15T10:00:00"
        }
    }


@pytest.fixture
def mock_upstash_response():
    """Mock Upstash REST API response."""
    def _make_response(result):
        response = MagicMock()
        response.status_code = 200
        response.json.return_value = {"result": result}
        return response
    return _make_response


# ---------------------------------------------------------------------------
# S3 Mock Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_s3_client():
    """Mock boto3 S3 client."""
    client = MagicMock()
    client.upload_file.return_value = None
    client.download_file.return_value = None
    client.head_bucket.return_value = {}
    client.generate_presigned_url.return_value = "https://example.com/presigned-url"
    return client


@pytest.fixture
def mock_s3_uploader():
    """Mock S3Uploader instance as a MagicMock."""
    uploader = MagicMock()
    uploader.upload_file.return_value = "https://test.supabase.co/storage/v1/object/public/test-bucket/reports/test.csv"
    uploader.download_file.return_value = None
    uploader.get_presigned_url.return_value = "https://example.com/presigned-url"
    uploader.bucket_name = "test-bucket"
    uploader.endpoint_url = "https://test.supabase.co/storage/v1/s3"
    return uploader


# ---------------------------------------------------------------------------
# SMTP Mock Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_smtp_server():
    """Mock SMTP server."""
    server = MagicMock()
    server.starttls.return_value = None
    server.login.return_value = None
    server.send_message.return_value = None
    server.__enter__ = MagicMock(return_value=server)
    server.__exit__ = MagicMock(return_value=False)
    return server


# ---------------------------------------------------------------------------
# ChromaDB Mock Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_chroma_collection():
    """Mock ChromaDB collection."""
    collection = MagicMock()
    collection.query.return_value = {
        "documents": [[
            "Table: customers - Contains customer information including id, name, email",
            "Table: orders - Contains order details with customer_id foreign key"
        ]],
        "metadatas": [[{"table": "customers"}, {"table": "orders"}]],
        "distances": [[0.1, 0.2]]
    }
    collection.get.return_value = {
        "documents": [
            "Table: customers - Contains customer information",
            "Table: orders - Contains order details"
        ],
        "metadatas": [{"table": "customers"}, {"table": "orders"}]
    }
    return collection


@pytest.fixture
def mock_chroma_client(mock_chroma_collection):
    """Mock ChromaDB client."""
    client = MagicMock()
    client.get_collection.return_value = mock_chroma_collection
    return client


# ---------------------------------------------------------------------------
# Sample Request Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_query_request():
    """Sample query request data."""
    return {
        "query": "Show me the top 10 customers by total revenue",
        "user_email": "test@example.com",
        "enable_cache": True
    }


@pytest.fixture
def sample_query_request_no_email():
    """Sample query request without email."""
    return {
        "query": "List all products with price over 100",
        "user_email": None,
        "enable_cache": True
    }


@pytest.fixture
def sample_query_request_no_cache():
    """Sample query request with caching disabled."""
    return {
        "query": "Get subscription statistics",
        "user_email": "test@example.com",
        "enable_cache": False
    }


# ---------------------------------------------------------------------------
# Schema Context Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_schema_context():
    """Sample schema context for SQL generation."""
    return """
Table: customers
- customer_id (INTEGER, PRIMARY KEY)
- name (VARCHAR(255))
- email (VARCHAR(255))
- created_at (TIMESTAMP)

Table: orders
- order_id (INTEGER, PRIMARY KEY)
- customer_id (INTEGER, FOREIGN KEY -> customers.customer_id)
- total_amount (DECIMAL(10,2))
- order_date (DATE)
- status (VARCHAR(50))

Table: products
- product_id (INTEGER, PRIMARY KEY)
- name (VARCHAR(255))
- price (DECIMAL(10,2))
- category (VARCHAR(100))
"""


# ---------------------------------------------------------------------------
# DataFrame Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_dataframe():
    """Sample pandas DataFrame for testing."""
    return pd.DataFrame({
        "customer_id": [1, 2, 3],
        "name": ["Alice", "Bob", "Charlie"],
        "total_revenue": [15000.00, 12500.00, 11000.00]
    })


@pytest.fixture
def empty_dataframe():
    """Empty pandas DataFrame."""
    return pd.DataFrame()


# ---------------------------------------------------------------------------
# Metadata Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_execution_metadata():
    """Sample query execution metadata."""
    return {
        "row_count": 10,
        "column_count": 3,
        "execution_time_seconds": 0.45,
        "columns": ["customer_id", "name", "total_revenue"],
        "csv_s3_key": "reports/2024/01/15/query_20240115_abc123.csv",
        "csv_s3_url": "https://test.supabase.co/storage/v1/object/public/test-bucket/reports/2024/01/15/query_20240115_abc123.csv",
        "sql_s3_key": "queries/2024/01/15/query_20240115_abc123.sql",
        "sql_s3_url": "https://test.supabase.co/storage/v1/object/public/test-bucket/queries/2024/01/15/query_20240115_abc123.sql",
        "timestamp": "2024-01-15T10:30:00"
    }


# ---------------------------------------------------------------------------
# File System Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def temp_csv_file(tmp_path, sample_dataframe):
    """Create a temporary CSV file for testing."""
    csv_path = tmp_path / "test_results.csv"
    sample_dataframe.to_csv(csv_path, index=False)
    return str(csv_path)


@pytest.fixture
def temp_sql_file(tmp_path):
    """Create a temporary SQL file for testing."""
    sql_path = tmp_path / "test_query.sql"
    sql_content = """-- Generated: 2024-01-15T10:00:00
-- User Query: Show top customers

SELECT customer_id, name, total_revenue
FROM customers
ORDER BY total_revenue DESC
LIMIT 10;
"""
    sql_path.write_text(sql_content)
    return str(sql_path)


# ---------------------------------------------------------------------------
# Langfuse Mock Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def mock_langfuse_observe():
    """Mock the Langfuse @observe decorator to avoid actual tracing."""
    def passthrough_decorator(*args, **kwargs):
        def decorator(func):
            return func
        if len(args) == 1 and callable(args[0]):
            return args[0]
        return decorator

    with patch('langfuse.observe', passthrough_decorator):
        yield


# ---------------------------------------------------------------------------
# Test Client Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def test_settings():
    """Test settings with mock values."""
    return {
        "DB_HOST": "localhost",
        "DB_PORT": 5432,
        "DB_NAME": "test_db",
        "DB_USER": "test_user",
        "DB_PASSWORD": "test_password",
        "S3_ENDPOINT_URL": "https://test.supabase.co/storage/v1/s3",
        "S3_BUCKET_NAME": "test-bucket",
        "AWS_ACCESS_KEY_ID": "test-access-key",
        "AWS_SECRET_ACCESS_KEY": "test-secret-key",
        "AWS_REGION": "us-east-1",
        "UPSTASH_REDIS_REST_URL": "https://test-redis.upstash.io",
        "UPSTASH_REDIS_REST_TOKEN": "test-token",
        "REDIS_CACHE_TTL": 3600,
        "ENABLE_CACHE": False,
        "OPENAI_API_KEY": "test-openai-key",
        "OPENAI_GENERAL_MODEL": "gpt-4o",
        "ANTHROPIC_API_KEY": "test-anthropic-key",
        "ANTHROPIC_SQL_MODEL": "claude-3-5-haiku-20241022",
        "ANTHROPIC_MAX_TOKENS": 1000,
        "SMTP_HOST": "smtp.test.com",
        "SMTP_PORT": 587,
        "SMTP_USER": "test@test.com",
        "SMTP_PASSWORD": "test-password",
        "SQL_RETRY_MAX": 3,
        "QUERY_TIMEOUT": 30,
    }


# ---------------------------------------------------------------------------
# Error Response Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_openai_error():
    """Mock OpenAI API error."""
    from openai import APIError
    request = httpx.Request("POST", "https://api.openai.com/v1/chat/completions")
    return APIError(message="API rate limit exceeded", request=request, body=None)


@pytest.fixture
def mock_anthropic_error():
    """Mock Anthropic API error."""
    from anthropic import APIError
    request = httpx.Request("POST", "https://api.anthropic.com/v1/messages")
    return APIError(message="Invalid API key", request=request, body=None)


@pytest.fixture
def mock_db_error():
    """Mock database error."""
    import psycopg2
    return psycopg2.OperationalError("Connection refused")


# ---------------------------------------------------------------------------
# Parametrized Test Data
# ---------------------------------------------------------------------------

@pytest.fixture(params=[
    "Show me top 10 customers",
    "List all orders from last month",
    "What are the best selling products?",
    "Calculate average order value by customer segment",
])
def sample_queries(request):
    """Parametrized sample queries for testing."""
    return request.param


@pytest.fixture(params=[
    ("SELECT * FROM customers", True),
    ("DELETE FROM customers", False),
    ("DROP TABLE orders", False),
    ("INSERT INTO products VALUES (1, 'test')", False),
    ("UPDATE customers SET name = 'test'", False),
    ("SELECT c.name, o.total FROM customers c JOIN orders o ON c.id = o.customer_id", True),
])
def sql_validation_cases(request):
    """Parametrized SQL validation test cases."""
    return request.param
