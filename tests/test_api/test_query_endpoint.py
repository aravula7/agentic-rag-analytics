"""Tests for the query API endpoint."""

import json
import pytest
from unittest.mock import Mock, MagicMock, patch, PropertyMock


class TestQueryEndpoint:
    """Test cases for the POST /query/ endpoint."""

    @pytest.fixture
    def _mock_agents(self):
        """Patch all module-level agents used in query.py."""
        patches = {
            "router_agent": patch("app.routers.query.router_agent"),
            "sql_agent": patch("app.routers.query.sql_agent"),
            "executor_agent": patch("app.routers.query.executor_agent"),
            "email_agent": patch("app.routers.query.email_agent"),
            "redis_cache": patch("app.routers.query.redis_cache", None),
            "settings": patch("app.routers.query.settings"),
        }
        mocks = {}
        for key, p in patches.items():
            mocks[key] = p.start()

        # Configure settings mock
        mocks["settings"].ENABLE_CACHE = False
        mocks["settings"].SQL_RETRY_MAX = 3

        yield mocks

        for p in patches.values():
            p.stop()

    @pytest.fixture
    def test_client(self, _mock_agents):
        """Create test client with mocked agents."""
        from app.main import app
        from fastapi.testclient import TestClient
        return TestClient(app)

    def test_query_endpoint_success(
        self,
        test_client,
        _mock_agents,
        mock_openai_routing_response,
        sample_execution_metadata,
    ):
        """Test successful query execution."""
        _mock_agents["router_agent"].route.return_value = mock_openai_routing_response
        _mock_agents["sql_agent"].generate_sql.return_value = "SELECT * FROM customers LIMIT 10;"
        _mock_agents["executor_agent"].execute_sql.return_value = (
            "https://example.com/results.csv",
            sample_execution_metadata,
        )

        response = test_client.post(
            "/query/",
            json={"query": "Show top 10 customers", "enable_cache": False},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["generated_sql"] == "SELECT * FROM customers LIMIT 10;"
        assert data["s3_url"] == "https://example.com/results.csv"
        assert data["cache_hit"] is False

    def test_query_endpoint_non_sql_query(
        self,
        test_client,
        _mock_agents,
        mock_openai_routing_no_sql,
    ):
        """Test query that does not require SQL."""
        _mock_agents["router_agent"].route.return_value = mock_openai_routing_no_sql

        response = test_client.post(
            "/query/",
            json={"query": "What is a database?", "enable_cache": False},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert "does not require database access" in data["error"]

    def test_query_endpoint_sql_generation_failure(
        self,
        test_client,
        _mock_agents,
        mock_openai_routing_response,
    ):
        """Test query when SQL generation fails after retries."""
        _mock_agents["router_agent"].route.return_value = mock_openai_routing_response
        _mock_agents["sql_agent"].generate_sql.side_effect = Exception("Generation failed")

        response = test_client.post(
            "/query/",
            json={"query": "Show customers", "enable_cache": False},
        )

        assert response.status_code == 500
        assert "SQL generation failed" in response.json()["detail"]

    def test_query_endpoint_execution_failure(
        self,
        test_client,
        _mock_agents,
        mock_openai_routing_response,
    ):
        """Test query when SQL execution fails after retries."""
        _mock_agents["router_agent"].route.return_value = mock_openai_routing_response
        _mock_agents["sql_agent"].generate_sql.return_value = "SELECT * FROM customers;"
        _mock_agents["executor_agent"].execute_sql.side_effect = Exception("Execution failed")

        response = test_client.post(
            "/query/",
            json={"query": "Show customers", "enable_cache": False},
        )

        assert response.status_code == 500
        assert "SQL execution failed" in response.json()["detail"]

    def test_query_endpoint_with_email(
        self,
        test_client,
        _mock_agents,
        mock_openai_routing_response_with_email,
        sample_execution_metadata,
    ):
        """Test query with email delivery."""
        sample_execution_metadata["csv_s3_key"] = "reports/2024/01/test.csv"
        _mock_agents["router_agent"].route.return_value = mock_openai_routing_response_with_email
        _mock_agents["sql_agent"].generate_sql.return_value = "SELECT * FROM products;"
        _mock_agents["executor_agent"].execute_sql.return_value = (
            "https://example.com/results.csv",
            sample_execution_metadata,
        )
        _mock_agents["executor_agent"].get_row_preview.return_value = None
        _mock_agents["executor_agent"].get_full_csv_path.return_value = None

        response = test_client.post(
            "/query/",
            json={
                "query": "Send me product analysis",
                "user_email": "user@example.com",
                "enable_cache": False,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_query_endpoint_retries_sql_generation(
        self,
        test_client,
        _mock_agents,
        mock_openai_routing_response,
        sample_execution_metadata,
    ):
        """Test that SQL generation is retried on failure."""
        _mock_agents["router_agent"].route.return_value = mock_openai_routing_response
        # First call fails, second succeeds
        _mock_agents["sql_agent"].generate_sql.side_effect = [
            Exception("First attempt failed"),
            "SELECT * FROM customers;",
        ]
        _mock_agents["executor_agent"].execute_sql.return_value = (
            "https://example.com/results.csv",
            sample_execution_metadata,
        )

        response = test_client.post(
            "/query/",
            json={"query": "Show customers", "enable_cache": False},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert _mock_agents["sql_agent"].generate_sql.call_count == 2

    def test_query_endpoint_retries_execution_with_regeneration(
        self,
        test_client,
        _mock_agents,
        mock_openai_routing_response,
        sample_execution_metadata,
    ):
        """Test that execution failure triggers SQL regeneration."""
        _mock_agents["router_agent"].route.return_value = mock_openai_routing_response
        _mock_agents["sql_agent"].generate_sql.side_effect = [
            "SELECT * FROM bad_table;",
            "SELECT * FROM customers;",
        ]
        _mock_agents["executor_agent"].execute_sql.side_effect = [
            Exception("relation 'bad_table' does not exist"),
            ("https://example.com/results.csv", sample_execution_metadata),
        ]

        response = test_client.post(
            "/query/",
            json={"query": "Show customers", "enable_cache": False},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True


class TestQueryEndpointCaching:
    """Test cases for query endpoint caching behavior."""

    @pytest.fixture
    def _mock_agents_with_cache(self):
        """Patch agents with cache enabled."""
        patches = {
            "router_agent": patch("app.routers.query.router_agent"),
            "sql_agent": patch("app.routers.query.sql_agent"),
            "executor_agent": patch("app.routers.query.executor_agent"),
            "email_agent": patch("app.routers.query.email_agent"),
            "redis_cache": patch("app.routers.query.redis_cache"),
            "settings": patch("app.routers.query.settings"),
        }
        mocks = {}
        for key, p in patches.items():
            mocks[key] = p.start()

        mocks["settings"].ENABLE_CACHE = True
        mocks["settings"].SQL_RETRY_MAX = 3

        yield mocks

        for p in patches.values():
            p.stop()

    @pytest.fixture
    def test_client_cached(self, _mock_agents_with_cache):
        """Create test client with cache enabled."""
        from app.main import app
        from fastapi.testclient import TestClient
        return TestClient(app)

    def test_query_returns_cached_result(
        self,
        test_client_cached,
        _mock_agents_with_cache,
        mock_redis_cached_result,
    ):
        """Test that cached results are returned."""
        _mock_agents_with_cache["redis_cache"].get_result.return_value = mock_redis_cached_result

        response = test_client_cached.post(
            "/query/",
            json={"query": "show top customers", "enable_cache": True},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["cache_hit"] is True
        # Router should not be called when cache hit
        _mock_agents_with_cache["router_agent"].route.assert_not_called()

    def test_query_caches_new_result(
        self,
        test_client_cached,
        _mock_agents_with_cache,
        mock_openai_routing_response,
        sample_execution_metadata,
    ):
        """Test that new results are cached."""
        _mock_agents_with_cache["redis_cache"].get_result.return_value = None
        _mock_agents_with_cache["router_agent"].route.return_value = mock_openai_routing_response
        _mock_agents_with_cache["sql_agent"].generate_sql.return_value = "SELECT * FROM customers;"
        _mock_agents_with_cache["executor_agent"].execute_sql.return_value = (
            "https://example.com/results.csv",
            sample_execution_metadata,
        )

        response = test_client_cached.post(
            "/query/",
            json={"query": "Show top customers", "enable_cache": True},
        )

        assert response.status_code == 200
        _mock_agents_with_cache["redis_cache"].set_result.assert_called_once()

    def test_query_cache_disabled(
        self,
        test_client_cached,
        _mock_agents_with_cache,
        mock_openai_routing_response,
        sample_execution_metadata,
    ):
        """Test that cache is skipped when enable_cache is False."""
        _mock_agents_with_cache["router_agent"].route.return_value = mock_openai_routing_response
        _mock_agents_with_cache["sql_agent"].generate_sql.return_value = "SELECT * FROM customers;"
        _mock_agents_with_cache["executor_agent"].execute_sql.return_value = (
            "https://example.com/results.csv",
            sample_execution_metadata,
        )

        response = test_client_cached.post(
            "/query/",
            json={"query": "Show top customers", "enable_cache": False},
        )

        assert response.status_code == 200
        _mock_agents_with_cache["redis_cache"].get_result.assert_not_called()

    def test_query_cache_mismatch_deletes_entry(
        self,
        test_client_cached,
        _mock_agents_with_cache,
        mock_openai_routing_response,
        sample_execution_metadata,
    ):
        """Test that mismatched cache entries are deleted."""
        mismatched_result = {
            "query": "completely different query",
            "routing_decision": mock_openai_routing_response,
            "sql": "SELECT 1",
            "s3_url": "https://example.com/old.csv",
            "metadata": sample_execution_metadata,
        }
        _mock_agents_with_cache["redis_cache"].get_result.return_value = mismatched_result
        _mock_agents_with_cache["router_agent"].route.return_value = mock_openai_routing_response
        _mock_agents_with_cache["sql_agent"].generate_sql.return_value = "SELECT * FROM customers;"
        _mock_agents_with_cache["executor_agent"].execute_sql.return_value = (
            "https://example.com/results.csv",
            sample_execution_metadata,
        )

        response = test_client_cached.post(
            "/query/",
            json={"query": "Show top customers", "enable_cache": True},
        )

        assert response.status_code == 200
        _mock_agents_with_cache["redis_cache"].delete.assert_called_once()


class TestQueryEndpointValidation:
    """Test cases for request validation."""

    @pytest.fixture
    def _mock_agents(self):
        """Patch all module-level agents used in query.py."""
        patches = {
            "router_agent": patch("app.routers.query.router_agent"),
            "sql_agent": patch("app.routers.query.sql_agent"),
            "executor_agent": patch("app.routers.query.executor_agent"),
            "email_agent": patch("app.routers.query.email_agent"),
            "redis_cache": patch("app.routers.query.redis_cache", None),
            "settings": patch("app.routers.query.settings"),
        }
        mocks = {}
        for key, p in patches.items():
            mocks[key] = p.start()

        mocks["settings"].ENABLE_CACHE = False
        mocks["settings"].SQL_RETRY_MAX = 3

        yield mocks

        for p in patches.values():
            p.stop()

    @pytest.fixture
    def test_client(self, _mock_agents):
        from app.main import app
        from fastapi.testclient import TestClient
        return TestClient(app)

    def test_query_endpoint_missing_query_field(self, test_client):
        """Test that missing query field returns 422."""
        response = test_client.post("/query/", json={})

        assert response.status_code == 422

    def test_query_endpoint_invalid_email_format(self, test_client):
        """Test that invalid email format returns 422."""
        response = test_client.post(
            "/query/",
            json={
                "query": "Show customers",
                "user_email": "not-an-email",
            },
        )

        assert response.status_code == 422

    def test_query_endpoint_valid_email_format(
        self,
        test_client,
        _mock_agents,
        mock_openai_routing_response,
        sample_execution_metadata,
    ):
        """Test that valid email format is accepted."""
        _mock_agents["router_agent"].route.return_value = mock_openai_routing_response
        _mock_agents["sql_agent"].generate_sql.return_value = "SELECT 1;"
        _mock_agents["executor_agent"].execute_sql.return_value = (
            "https://example.com/r.csv",
            sample_execution_metadata,
        )

        response = test_client.post(
            "/query/",
            json={
                "query": "Show customers",
                "user_email": "test@example.com",
                "enable_cache": False,
            },
        )

        assert response.status_code == 200

    def test_query_endpoint_empty_query_string(
        self,
        test_client,
        _mock_agents,
        mock_openai_routing_response,
        sample_execution_metadata,
    ):
        """Test endpoint with empty query string."""
        _mock_agents["router_agent"].route.return_value = mock_openai_routing_response
        _mock_agents["sql_agent"].generate_sql.return_value = "SELECT 1;"
        _mock_agents["executor_agent"].execute_sql.return_value = (
            "https://example.com/r.csv",
            sample_execution_metadata,
        )

        response = test_client.post(
            "/query/",
            json={"query": "", "enable_cache": False},
        )

        # FastAPI accepts empty string, the agent will process it
        assert response.status_code == 200


class TestQueryNormalization:
    """Test cases for the _normalize_query helper."""

    def test_normalize_query_collapses_whitespace(self):
        """Test that whitespace is collapsed."""
        from app.routers.query import _normalize_query

        result = _normalize_query("  show   top   customers  ")

        assert result == "show top customers"

    def test_normalize_query_handles_none(self):
        """Test that None input is handled."""
        from app.routers.query import _normalize_query

        result = _normalize_query(None)

        assert result == ""

    def test_normalize_query_handles_empty_string(self):
        """Test that empty string is handled."""
        from app.routers.query import _normalize_query

        result = _normalize_query("")

        assert result == ""

    def test_normalize_query_preserves_case(self):
        """Test that case is preserved (unlike Redis cache normalization)."""
        from app.routers.query import _normalize_query

        result = _normalize_query("Show Top CUSTOMERS")

        assert result == "Show Top CUSTOMERS"
