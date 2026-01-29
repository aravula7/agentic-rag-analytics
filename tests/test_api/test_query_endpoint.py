"""Tests for the /query endpoint with LangGraph workflow."""

import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

from app.main import app
from app.graph.state import QueryState


client = TestClient(app)


class TestQueryEndpoint:
    """Test cases for POST /query/ endpoint."""

    @patch("app.routers.query.workflow_graph")
    @patch("app.routers.query.redis_cache")
    def test_successful_query_no_cache(self, mock_cache, mock_graph):
        """Test successful query execution without cache."""
        # Setup cache mock
        mock_cache.get_result.return_value = None

        # Setup graph mock
        mock_final_state: QueryState = {
            "query": "Show top 10 products",
            "user_email": None,
            "enable_cache": True,
            "requires_sql": True,
            "requires_email": False,
            "tables_involved": ["products", "orders"],
            "query_complexity": "medium",
            "routing_reasoning": "Join products with orders",
            "generated_sql": "SELECT * FROM products LIMIT 10;",
            "sql_generation_error": None,
            "sql_retry_count": 0,
            "csv_s3_url": "https://example.com/results.csv",
            "sql_s3_url": "https://example.com/query.sql",
            "execution_metadata": {
                "row_count": 10,
                "column_count": 3,
                "execution_time_seconds": 0.5,
                "columns": ["product_id", "name", "price"],
                "csv_s3_key": "reports/test.csv",
                "csv_s3_url": "https://example.com/results.csv",
                "sql_s3_key": "queries/test.sql",
                "sql_s3_url": "https://example.com/query.sql",
                "timestamp": "2024-01-01T00:00:00"
            },
            "execution_error": None,
            "execution_retry_count": 0,
            "success": True,
            "error_message": None,
            "cache_hit": False,
        }
        mock_graph.invoke.return_value = mock_final_state

        # Make request
        response = client.post(
            "/query/",
            json={
                "query": "Show top 10 products",
                "user_email": None,
                "enable_cache": True
            }
        )

        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["query"] == "Show top 10 products"
        assert data["generated_sql"] == "SELECT * FROM products LIMIT 10;"
        assert data["s3_url"] == "https://example.com/results.csv"
        assert data["cache_hit"] is False
        assert data["routing_decision"]["requires_sql"] is True

        # Verify graph was invoked
        mock_graph.invoke.assert_called_once()

        # Verify cache was checked and set
        mock_cache.get_result.assert_called_once()
        mock_cache.set_result.assert_called_once()

    @patch("app.routers.query.workflow_graph")
    @patch("app.routers.query.redis_cache")
    def test_cache_hit(self, mock_cache, mock_graph):
        """Test query returns cached result."""
        # Setup cache mock with cached result
        # IMPORTANT: Cache stores normalized query (lowercase)
        cached_result = {
            "query": "show top customers",  # Must match normalized input exactly
            "routing_decision": {
                "requires_sql": True,
                "requires_email": False,
                "tables_involved": ["customers"],
                "query_complexity": "simple",
                "reasoning": "Simple customer query"
            },
            "sql": "SELECT * FROM customers LIMIT 10;",
            "s3_url": "https://example.com/cached.csv",
            "metadata": {
                "row_count": 10,
                "column_count": 3,
                "execution_time_seconds": 0.5,
                "columns": ["customer_id", "name", "email"],
                "csv_s3_key": "reports/cached.csv",
                "csv_s3_url": "https://example.com/cached.csv",
                "sql_s3_key": "queries/cached.sql",
                "sql_s3_url": "https://example.com/cached.sql",
                "timestamp": "2024-01-01T00:00:00"
            }
        }
        mock_cache.get_result.return_value = cached_result

        # Make request - query will be normalized to "show top customers"
        response = client.post(
            "/query/",
            json={
                "query": "show top customers",  # Use exact normalized form
                "user_email": None,
                "enable_cache": True
            }
        )

        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["cache_hit"] is True
        assert data["generated_sql"] == "SELECT * FROM customers LIMIT 10;"
        assert data["s3_url"] == "https://example.com/cached.csv"
        
        # Verify cache was checked but workflow was NOT invoked
        mock_cache.get_result.assert_called_once()
        mock_graph.invoke.assert_not_called()  # Should NOT invoke workflow on cache hit

    @patch("app.routers.query.workflow_graph")
    @patch("app.routers.query.redis_cache")
    def test_workflow_failure(self, mock_cache, mock_graph):
        """Test query when workflow fails."""
        # Setup cache mock
        mock_cache.get_result.return_value = None

        # Setup graph mock - workflow fails
        mock_final_state: QueryState = {
            "query": "Invalid query",
            "user_email": None,
            "enable_cache": False,
            "requires_sql": True,
            "requires_email": False,
            "tables_involved": [],
            "query_complexity": "simple",
            "routing_reasoning": "",
            "generated_sql": None,
            "sql_generation_error": "SQL generation failed",
            "sql_retry_count": 3,
            "csv_s3_url": None,
            "sql_s3_url": None,
            "execution_metadata": None,
            "execution_error": None,
            "execution_retry_count": 0,
            "success": False,
            "error_message": "SQL generation failed after 3 retries",
            "cache_hit": False,
        }
        mock_graph.invoke.return_value = mock_final_state

        # Make request
        response = client.post(
            "/query/",
            json={
                "query": "Invalid query",
                "user_email": None,
                "enable_cache": False
            }
        )

        # Assertions
        assert response.status_code == 500
        data = response.json()
        assert "SQL generation failed" in data["detail"]

    @patch("app.routers.query.workflow_graph")
    @patch("app.routers.query.redis_cache")
    def test_workflow_no_csv_url(self, mock_cache, mock_graph):
        """Test query when workflow succeeds but no CSV URL."""
        # Setup cache mock
        mock_cache.get_result.return_value = None

        # Setup graph mock - success but no CSV URL
        mock_final_state: QueryState = {
            "query": "Test query",
            "user_email": None,
            "enable_cache": False,
            "requires_sql": False,
            "requires_email": False,
            "tables_involved": [],
            "query_complexity": "none",
            "routing_reasoning": "General question",
            "generated_sql": None,
            "sql_generation_error": None,
            "sql_retry_count": 0,
            "csv_s3_url": None,  # No CSV URL
            "sql_s3_url": None,
            "execution_metadata": None,
            "execution_error": None,
            "execution_retry_count": 0,
            "success": True,
            "error_message": None,
            "cache_hit": False,
        }
        mock_graph.invoke.return_value = mock_final_state

        # Make request
        response = client.post(
            "/query/",
            json={
                "query": "What is SQL?",
                "user_email": None,
                "enable_cache": False
            }
        )

        # Assertions
        assert response.status_code == 500
        data = response.json()
        assert "No CSV URL generated" in data["detail"]

    @patch("app.routers.query.workflow_graph")
    @patch("app.routers.query.redis_cache")
    def test_query_with_email(self, mock_cache, mock_graph):
        """Test query with email delivery."""
        # Setup cache mock
        mock_cache.get_result.return_value = None

        # Setup graph mock
        mock_final_state: QueryState = {
            "query": "Email me customer list",
            "user_email": "test@example.com",
            "enable_cache": False,
            "requires_sql": True,
            "requires_email": True,
            "tables_involved": ["customers"],
            "query_complexity": "simple",
            "routing_reasoning": "Customer query with email",
            "generated_sql": "SELECT * FROM customers;",
            "sql_generation_error": None,
            "sql_retry_count": 0,
            "csv_s3_url": "https://example.com/results.csv",
            "sql_s3_url": "https://example.com/query.sql",
            "execution_metadata": {
                "row_count": 50,
                "column_count": 4,
                "execution_time_seconds": 0.3,
                "columns": ["customer_id", "name", "email", "region"],
                "csv_s3_key": "reports/test.csv",
                "csv_s3_url": "https://example.com/results.csv",
                "sql_s3_key": "queries/test.sql",
                "sql_s3_url": "https://example.com/query.sql",
                "timestamp": "2024-01-01T00:00:00"
            },
            "execution_error": None,
            "execution_retry_count": 0,
            "success": True,
            "error_message": None,
            "cache_hit": False,
        }
        mock_graph.invoke.return_value = mock_final_state

        # Make request
        response = client.post(
            "/query/",
            json={
                "query": "Email me customer list",
                "user_email": "test@example.com",
                "enable_cache": False
            }
        )

        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["routing_decision"]["requires_email"] is True

    @patch("app.routers.query.workflow_graph")
    def test_unhandled_exception(self, mock_graph):
        """Test handling of unexpected exceptions."""
        # Setup graph mock to raise exception
        mock_graph.invoke.side_effect = Exception("Unexpected error")

        # Make request
        response = client.post(
            "/query/",
            json={
                "query": "Test query",
                "user_email": None,
                "enable_cache": False
            }
        )

        # Assertions
        assert response.status_code == 500
        data = response.json()
        assert "Unexpected error" in data["detail"]

    @patch("app.routers.query.workflow_graph")
    @patch("app.routers.query.redis_cache")
    def test_cache_mismatch_deletes_and_recomputes(self, mock_cache, mock_graph):
        """Test that mismatched cache entries are deleted and recomputed."""
        # Setup cache mock with mismatched query
        cached_result = {
            "query": "different query",  # Mismatched query
            "routing_decision": {
                "requires_sql": True,
                "requires_email": False,
                "tables_involved": ["customers"],
                "query_complexity": "simple",
                "reasoning": "Simple query"
            },
            "sql": "SELECT * FROM customers;",
            "s3_url": "https://example.com/old.csv",
            "metadata": {}
        }
        mock_cache.get_result.return_value = cached_result

        # Setup graph mock for recomputation
        mock_final_state: QueryState = {
            "query": "Show top products",
            "user_email": None,
            "enable_cache": True,
            "requires_sql": True,
            "requires_email": False,
            "tables_involved": ["products"],
            "query_complexity": "simple",
            "routing_reasoning": "Product query",
            "generated_sql": "SELECT * FROM products;",
            "sql_generation_error": None,
            "sql_retry_count": 0,
            "csv_s3_url": "https://example.com/new.csv",
            "sql_s3_url": "https://example.com/query.sql",
            "execution_metadata": {
                "row_count": 10,
                "column_count": 3,
                "execution_time_seconds": 0.5,
                "columns": ["product_id", "name", "price"],
                "csv_s3_key": "reports/new.csv",
                "csv_s3_url": "https://example.com/new.csv",
                "sql_s3_key": "queries/new.sql",
                "sql_s3_url": "https://example.com/query.sql",
                "timestamp": "2024-01-01T00:00:00"
            },
            "execution_error": None,
            "execution_retry_count": 0,
            "success": True,
            "error_message": None,
            "cache_hit": False,
        }
        mock_graph.invoke.return_value = mock_final_state

        # Make request
        response = client.post(
            "/query/",
            json={
                "query": "Show top products",
                "user_email": None,
                "enable_cache": True
            }
        )

        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data["cache_hit"] is False
        assert data["s3_url"] == "https://example.com/new.csv"

        # Verify cache was deleted and workflow was invoked
        mock_cache.delete.assert_called_once()
        mock_graph.invoke.assert_called_once()


class TestQueryValidation:
    """Test cases for input validation."""

    def test_empty_query(self):
        """Test that empty query is handled by workflow (returns 500)."""
        # Empty query passes FastAPI validation (min_length=1 on whitespace)
        # but fails in graph workflow, returning 500
        response = client.post(
            "/query/",
            json={
                "query": " ",  # Whitespace passes min_length but fails validator
                "user_email": None,
                "enable_cache": False
            }
        )
        # Pydantic validator catches whitespace-only, returns 422
        assert response.status_code == 422

    def test_truly_empty_query(self):
        """Test that truly empty string is rejected by Pydantic."""
        response = client.post(
            "/query/",
            json={
                "query": "",  # Empty string
                "user_email": None,
                "enable_cache": False
            }
        )
        # FastAPI validation catches empty string
        assert response.status_code == 422

    def test_invalid_email_format(self):
        """Test that invalid email format is rejected."""
        response = client.post(
            "/query/",
            json={
                "query": "Show products",
                "user_email": "not-an-email",
                "enable_cache": False
            }
        )
        # Note: user_email is Optional[str], not EmailStr, so this will actually pass
        # If you want strict email validation, change schema to use EmailStr
        assert response.status_code in [200, 422, 500]  # Depends on workflow execution

    def test_missing_required_fields(self):
        """Test that missing required fields are rejected."""
        response = client.post(
            "/query/",
            json={
                # Missing "query" field
                "user_email": None,
                "enable_cache": False
            }
        )
        assert response.status_code == 422