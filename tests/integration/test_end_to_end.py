"""Integration tests for end-to-end query pipeline."""

import json
import pytest
from unittest.mock import Mock, MagicMock, patch, call
import pandas as pd


class TestEndToEndPipeline:
    """Integration tests for the full query pipeline with mocked external services."""

    @pytest.fixture
    def _mock_all_externals(self):
        """Patch all external service calls at the module level."""
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
    def test_client(self, _mock_all_externals):
        from app.main import app
        from fastapi.testclient import TestClient
        return TestClient(app)

    def test_full_pipeline_simple_query(self, test_client, _mock_all_externals):
        """Test full pipeline: route -> generate SQL -> execute -> return results."""
        routing_decision = {
            "requires_sql": True,
            "requires_email": False,
            "tables_involved": ["customers"],
            "query_complexity": "simple",
            "reasoning": "Simple customer lookup"
        }
        metadata = {
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

        _mock_all_externals["router_agent"].route.return_value = routing_decision
        _mock_all_externals["sql_agent"].generate_sql.return_value = \
            "SELECT customer_id, name, email FROM customers ORDER BY customer_id LIMIT 10;"
        _mock_all_externals["executor_agent"].execute_sql.return_value = (
            "https://example.com/results.csv", metadata
        )

        response = test_client.post("/query/", json={
            "query": "Show me the first 10 customers",
            "enable_cache": False
        })

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["query"] == "Show me the first 10 customers"
        assert data["generated_sql"] is not None
        assert data["s3_url"] == "https://example.com/results.csv"
        assert data["metadata"]["row_count"] == 10
        assert data["metadata"]["column_count"] == 3
        assert data["cache_hit"] is False

        # Verify pipeline was called in order
        _mock_all_externals["router_agent"].route.assert_called_once()
        _mock_all_externals["sql_agent"].generate_sql.assert_called_once()
        _mock_all_externals["executor_agent"].execute_sql.assert_called_once()

    def test_full_pipeline_with_email_delivery(self, test_client, _mock_all_externals):
        """Test full pipeline with email delivery as background task."""
        routing_decision = {
            "requires_sql": True,
            "requires_email": True,
            "tables_involved": ["orders", "customers"],
            "query_complexity": "complex",
            "reasoning": "Complex query with email delivery"
        }
        metadata = {
            "row_count": 100,
            "column_count": 5,
            "execution_time_seconds": 2.1,
            "columns": ["order_id", "customer_name", "product", "amount", "date"],
            "csv_s3_key": "reports/2024/01/15/query_complex.csv",
            "csv_s3_url": "https://example.com/complex_results.csv",
            "sql_s3_key": "queries/2024/01/15/query_complex.sql",
            "sql_s3_url": "https://example.com/complex_query.sql",
            "timestamp": "2024-01-15T11:00:00"
        }

        _mock_all_externals["router_agent"].route.return_value = routing_decision
        _mock_all_externals["sql_agent"].generate_sql.return_value = \
            "SELECT o.order_id, c.name FROM orders o JOIN customers c ON o.customer_id = c.id LIMIT 100;"
        _mock_all_externals["executor_agent"].execute_sql.return_value = (
            "https://example.com/complex_results.csv", metadata
        )
        _mock_all_externals["executor_agent"].get_row_preview.return_value = pd.DataFrame({
            "order_id": [1, 2], "customer_name": ["Alice", "Bob"]
        })
        _mock_all_externals["executor_agent"].get_full_csv_path.return_value = "/tmp/attachment.csv"

        response = test_client.post("/query/", json={
            "query": "Send me all orders with customer names",
            "user_email": "analyst@company.com",
            "enable_cache": False
        })

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["routing_decision"]["requires_email"] is True

    def test_full_pipeline_non_sql_query(self, test_client, _mock_all_externals):
        """Test pipeline for a query that does not require SQL."""
        routing_decision = {
            "requires_sql": False,
            "requires_email": False,
            "tables_involved": [],
            "query_complexity": "none",
            "reasoning": "General knowledge question"
        }

        _mock_all_externals["router_agent"].route.return_value = routing_decision

        response = test_client.post("/query/", json={
            "query": "What are best practices for database design?",
            "enable_cache": False
        })

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert data["error"] is not None
        assert "does not require database access" in data["error"]

        # SQL and executor agents should not be called
        _mock_all_externals["sql_agent"].generate_sql.assert_not_called()
        _mock_all_externals["executor_agent"].execute_sql.assert_not_called()

    def test_full_pipeline_sql_retry_on_generation_failure(self, test_client, _mock_all_externals):
        """Test retry logic when SQL generation fails on first attempt."""
        routing_decision = {
            "requires_sql": True,
            "requires_email": False,
            "tables_involved": ["products"],
            "query_complexity": "medium",
            "reasoning": "Product query"
        }
        metadata = {
            "row_count": 5,
            "column_count": 2,
            "execution_time_seconds": 0.3,
            "columns": ["product_id", "name"],
            "csv_s3_key": "reports/2024/01/15/query_retry.csv",
            "csv_s3_url": "https://example.com/retry_results.csv",
            "sql_s3_key": "queries/2024/01/15/query_retry.sql",
            "sql_s3_url": "https://example.com/retry_query.sql",
            "timestamp": "2024-01-15T12:00:00"
        }

        _mock_all_externals["router_agent"].route.return_value = routing_decision
        # First call fails, second succeeds
        _mock_all_externals["sql_agent"].generate_sql.side_effect = [
            Exception("Temporary API error"),
            "SELECT product_id, name FROM products LIMIT 5;"
        ]
        _mock_all_externals["executor_agent"].execute_sql.return_value = (
            "https://example.com/retry_results.csv", metadata
        )

        response = test_client.post("/query/", json={
            "query": "List 5 products",
            "enable_cache": False
        })

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert _mock_all_externals["sql_agent"].generate_sql.call_count == 2

    def test_full_pipeline_execution_retry_with_sql_regeneration(
        self, test_client, _mock_all_externals
    ):
        """Test execution failure triggers SQL regeneration and retry."""
        routing_decision = {
            "requires_sql": True,
            "requires_email": False,
            "tables_involved": ["subscriptions"],
            "query_complexity": "simple",
            "reasoning": "Subscription query"
        }
        metadata = {
            "row_count": 3,
            "column_count": 2,
            "execution_time_seconds": 0.2,
            "columns": ["id", "plan"],
            "csv_s3_key": "reports/2024/01/15/query_exec_retry.csv",
            "csv_s3_url": "https://example.com/exec_retry.csv",
            "sql_s3_key": "queries/2024/01/15/query_exec_retry.sql",
            "sql_s3_url": "https://example.com/exec_retry.sql",
            "timestamp": "2024-01-15T13:00:00"
        }

        _mock_all_externals["router_agent"].route.return_value = routing_decision
        # First SQL is generated fine, but execution fails, then regenerated SQL works
        _mock_all_externals["sql_agent"].generate_sql.side_effect = [
            "SELECT * FROM subs;",            # initial generation
            "SELECT id, plan FROM subscriptions;",  # regeneration after error
        ]
        _mock_all_externals["executor_agent"].execute_sql.side_effect = [
            Exception("relation 'subs' does not exist"),
            ("https://example.com/exec_retry.csv", metadata),
        ]

        response = test_client.post("/query/", json={
            "query": "Show subscriptions",
            "enable_cache": False
        })

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        # Executor was called twice (initial + retry)
        assert _mock_all_externals["executor_agent"].execute_sql.call_count == 2
        # SQL agent: initial + regeneration
        assert _mock_all_externals["sql_agent"].generate_sql.call_count == 2

    def test_full_pipeline_all_retries_exhausted(self, test_client, _mock_all_externals):
        """Test that all retries exhausted returns 500 error."""
        routing_decision = {
            "requires_sql": True,
            "requires_email": False,
            "tables_involved": ["customers"],
            "query_complexity": "simple",
            "reasoning": "Simple query"
        }

        _mock_all_externals["router_agent"].route.return_value = routing_decision
        _mock_all_externals["sql_agent"].generate_sql.side_effect = Exception("Persistent failure")

        response = test_client.post("/query/", json={
            "query": "Show customers",
            "enable_cache": False
        })

        assert response.status_code == 500
        assert "SQL generation failed" in response.json()["detail"]


class TestEndToEndCaching:
    """Integration tests for caching behavior."""

    @pytest.fixture
    def _mock_all_with_cache(self):
        """Patch all externals with cache enabled."""
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
    def test_client(self, _mock_all_with_cache):
        from app.main import app
        from fastapi.testclient import TestClient
        return TestClient(app)

    def test_cache_hit_skips_all_agents(self, test_client, _mock_all_with_cache):
        """Test that a cache hit skips all agent calls."""
        cached_result = {
            "query": "show top customers",
            "routing_decision": {
                "requires_sql": True,
                "requires_email": False,
                "tables_involved": ["customers"],
                "query_complexity": "simple",
                "reasoning": "Simple lookup"
            },
            "sql": "SELECT * FROM customers LIMIT 10;",
            "s3_url": "https://example.com/cached.csv",
            "metadata": {
                "row_count": 10,
                "column_count": 3,
                "execution_time_seconds": 0.5,
                "columns": ["id", "name", "email"],
                "csv_s3_key": "reports/2024/01/query.csv",
                "csv_s3_url": "https://example.com/cached.csv",
                "sql_s3_key": "queries/2024/01/query.sql",
                "sql_s3_url": "https://example.com/cached.sql",
                "timestamp": "2024-01-15T10:00:00"
            }
        }
        _mock_all_with_cache["redis_cache"].get_result.return_value = cached_result

        response = test_client.post("/query/", json={
            "query": "show top customers",
            "enable_cache": True
        })

        assert response.status_code == 200
        data = response.json()
        assert data["cache_hit"] is True
        assert data["success"] is True

        # No agent should be called
        _mock_all_with_cache["router_agent"].route.assert_not_called()
        _mock_all_with_cache["sql_agent"].generate_sql.assert_not_called()
        _mock_all_with_cache["executor_agent"].execute_sql.assert_not_called()

    def test_cache_miss_executes_full_pipeline_and_caches(
        self, test_client, _mock_all_with_cache
    ):
        """Test that a cache miss runs full pipeline and stores result."""
        _mock_all_with_cache["redis_cache"].get_result.return_value = None
        _mock_all_with_cache["router_agent"].route.return_value = {
            "requires_sql": True,
            "requires_email": False,
            "tables_involved": ["orders"],
            "query_complexity": "simple",
            "reasoning": "Order count"
        }
        _mock_all_with_cache["sql_agent"].generate_sql.return_value = "SELECT COUNT(*) FROM orders;"
        _mock_all_with_cache["executor_agent"].execute_sql.return_value = (
            "https://example.com/order_count.csv",
            {
                "row_count": 1,
                "column_count": 1,
                "execution_time_seconds": 0.1,
                "columns": ["count"],
                "csv_s3_key": "reports/2024/01/query.csv",
                "csv_s3_url": "https://example.com/order_count.csv",
                "sql_s3_key": "queries/2024/01/query.sql",
                "sql_s3_url": "https://example.com/order_count.sql",
                "timestamp": "2024-01-15T14:00:00"
            }
        )

        response = test_client.post("/query/", json={
            "query": "How many orders are there?",
            "enable_cache": True
        })

        assert response.status_code == 200
        data = response.json()
        assert data["cache_hit"] is False
        assert data["success"] is True

        # All agents should have been called
        _mock_all_with_cache["router_agent"].route.assert_called_once()
        _mock_all_with_cache["sql_agent"].generate_sql.assert_called_once()
        _mock_all_with_cache["executor_agent"].execute_sql.assert_called_once()

        # Result should be cached
        _mock_all_with_cache["redis_cache"].set_result.assert_called_once()


class TestEndToEndPydanticModels:
    """Integration tests for Pydantic model validation."""

    def test_query_request_model_valid(self):
        """Test QueryRequest model with valid data."""
        from app.models.schemas import QueryRequest

        request = QueryRequest(
            query="Show top customers",
            user_email="test@example.com",
            enable_cache=True
        )

        assert request.query == "Show top customers"
        assert request.user_email == "test@example.com"
        assert request.enable_cache is True

    def test_query_request_model_defaults(self):
        """Test QueryRequest model with defaults."""
        from app.models.schemas import QueryRequest

        request = QueryRequest(query="Show top customers")

        assert request.user_email is None
        assert request.enable_cache is True

    def test_routing_decision_model(self):
        """Test RoutingDecision model."""
        from app.models.schemas import RoutingDecision

        decision = RoutingDecision(
            requires_sql=True,
            requires_email=False,
            tables_involved=["customers", "orders"],
            query_complexity="medium",
            reasoning="Requires join between tables"
        )

        assert decision.requires_sql is True
        assert len(decision.tables_involved) == 2

    def test_query_metadata_model(self):
        """Test QueryMetadata model."""
        from app.models.schemas import QueryMetadata

        metadata = QueryMetadata(
            row_count=100,
            column_count=5,
            execution_time_seconds=1.5,
            columns=["id", "name", "email", "created_at", "status"],
            csv_s3_key="reports/2024/01/test.csv",
            csv_s3_url="https://example.com/test.csv",
            sql_s3_key="queries/2024/01/test.sql",
            sql_s3_url="https://example.com/test.sql",
            timestamp="2024-01-15T10:00:00"
        )

        assert metadata.row_count == 100
        assert len(metadata.columns) == 5

    def test_query_response_model_success(self):
        """Test QueryResponse model for success case."""
        from app.models.schemas import QueryResponse, RoutingDecision, QueryMetadata

        response = QueryResponse(
            success=True,
            query="Show customers",
            routing_decision=RoutingDecision(
                requires_sql=True,
                requires_email=False,
                tables_involved=["customers"],
                query_complexity="simple",
                reasoning="Simple query"
            ),
            generated_sql="SELECT * FROM customers;",
            s3_url="https://example.com/results.csv",
            metadata=QueryMetadata(
                row_count=10,
                column_count=3,
                execution_time_seconds=0.5,
                columns=["id", "name", "email"],
                csv_s3_key="reports/test.csv",
                csv_s3_url="https://example.com/results.csv",
                sql_s3_key="queries/test.sql",
                sql_s3_url="https://example.com/query.sql",
                timestamp="2024-01-15T10:00:00"
            ),
            cache_hit=False
        )

        assert response.success is True
        assert response.error is None

    def test_query_response_model_failure(self):
        """Test QueryResponse model for failure case."""
        from app.models.schemas import QueryResponse

        response = QueryResponse(
            success=False,
            query="Invalid query",
            error="Query does not require database access"
        )

        assert response.success is False
        assert response.error is not None
        assert response.generated_sql is None
        assert response.s3_url is None

    def test_health_response_model(self):
        """Test HealthResponse model."""
        from app.models.schemas import HealthResponse

        health = HealthResponse(
            status="healthy",
            version="1.0.0",
            timestamp="2024-01-15T10:00:00",
            services={"database": "connected", "redis": "connected"}
        )

        assert health.status == "healthy"
        assert health.services["database"] == "connected"
