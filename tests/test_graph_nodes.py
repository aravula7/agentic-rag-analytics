"""Tests for LangGraph node functions."""

import pytest
from unittest.mock import MagicMock, patch
from app.graph.nodes import router_node, sql_generator_node, executor_node, email_node
from app.graph.state import QueryState


class TestRouterNode:
    """Test cases for router_node."""

    @patch("app.graph.nodes.ChatOpenAI")
    def test_router_node_requires_sql(self, mock_chat_openai):
        """Test router node when SQL is required."""
        # Setup mock
        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.content = '''{
            "requires_sql": true,
            "requires_email": false,
            "tables_involved": ["products", "orders"],
            "query_complexity": "medium",
            "reasoning": "Need to join tables"
        }'''
        mock_llm.invoke.return_value = mock_response
        mock_chat_openai.return_value = mock_llm

        # Test
        state: QueryState = {
            "query": "Show top products",
            "user_email": None,
            "enable_cache": True,
            "requires_sql": True,
            "requires_email": False,
            "tables_involved": [],
            "query_complexity": "simple",
            "routing_reasoning": "",
            "generated_sql": None,
            "sql_generation_error": None,
            "sql_retry_count": 0,
            "csv_s3_url": None,
            "sql_s3_url": None,
            "execution_metadata": None,
            "execution_error": None,
            "execution_retry_count": 0,
            "success": False,
            "error_message": None,
            "cache_hit": False,
        }

        result = router_node(state)

        assert result["requires_sql"] is True
        assert result["requires_email"] is False
        assert result["tables_involved"] == ["products", "orders"]
        assert result["query_complexity"] == "medium"

    @patch("app.graph.nodes.ChatOpenAI")
    def test_router_node_no_sql_required(self, mock_chat_openai):
        """Test router node when no SQL is required."""
        # Setup mock
        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.content = '''{
            "requires_sql": false,
            "requires_email": false,
            "tables_involved": [],
            "query_complexity": "simple",
            "reasoning": "General question"
        }'''
        mock_llm.invoke.return_value = mock_response
        mock_chat_openai.return_value = mock_llm

        # Test
        state: QueryState = {
            "query": "What is SQL?",
            "user_email": None,
            "enable_cache": False,
            "requires_sql": True,
            "requires_email": False,
            "tables_involved": [],
            "query_complexity": "simple",
            "routing_reasoning": "",
            "generated_sql": None,
            "sql_generation_error": None,
            "sql_retry_count": 0,
            "csv_s3_url": None,
            "sql_s3_url": None,
            "execution_metadata": None,
            "execution_error": None,
            "execution_retry_count": 0,
            "success": False,
            "error_message": None,
            "cache_hit": False,
        }

        result = router_node(state)

        assert result["requires_sql"] is False
        assert result["success"] is False
        assert "does not require database access" in result["error_message"]


class TestSQLGeneratorNode:
    """Test cases for sql_generator_node."""

    @patch("app.graph.nodes.ChatAnthropic")
    @patch("app.graph.nodes.schema_retriever")
    def test_sql_generator_success(self, mock_retriever, mock_chat_anthropic):
        """Test successful SQL generation."""
        # Setup mocks
        mock_retriever.get_table_context.return_value = "Schema: products (product_id, name)"

        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.content = "SELECT * FROM products LIMIT 10;"
        mock_llm.invoke.return_value = mock_response
        mock_chat_anthropic.return_value = mock_llm

        # Test
        state: QueryState = {
            "query": "Show products",
            "user_email": None,
            "enable_cache": True,
            "requires_sql": True,
            "requires_email": False,
            "tables_involved": ["products"],
            "query_complexity": "simple",
            "routing_reasoning": "",
            "generated_sql": None,
            "sql_generation_error": None,
            "sql_retry_count": 0,
            "csv_s3_url": None,
            "sql_s3_url": None,
            "execution_metadata": None,
            "execution_error": None,
            "execution_retry_count": 0,
            "success": False,
            "error_message": None,
            "cache_hit": False,
        }

        result = sql_generator_node(state)

        assert result["generated_sql"] == "SELECT * FROM products LIMIT 10;"
        assert result["sql_generation_error"] is None


class TestExecutorNode:
    """Test cases for executor_node."""

    @patch("app.graph.nodes.executor_agent")
    def test_executor_success(self, mock_executor):
        """Test successful SQL execution."""
        # Setup mock
        mock_executor.execute_sql.return_value = (
            "https://example.com/results.csv",
            {
                "row_count": 10,
                "column_count": 3,
                "execution_time_seconds": 0.5,
                "sql_s3_url": "https://example.com/query.sql",
            }
        )

        # Test
        state: QueryState = {
            "query": "Show products",
            "user_email": None,
            "enable_cache": True,
            "requires_sql": True,
            "requires_email": False,
            "tables_involved": ["products"],
            "query_complexity": "simple",
            "routing_reasoning": "",
            "generated_sql": "SELECT * FROM products;",
            "sql_generation_error": None,
            "sql_retry_count": 0,
            "csv_s3_url": None,
            "sql_s3_url": None,
            "execution_metadata": None,
            "execution_error": None,
            "execution_retry_count": 0,
            "success": False,
            "error_message": None,
            "cache_hit": False,
        }

        result = executor_node(state)

        assert result["success"] is True
        assert result["csv_s3_url"] == "https://example.com/results.csv"
        assert result["execution_error"] is None

    def test_executor_no_sql(self):
        """Test executor when no SQL is provided."""
        state: QueryState = {
            "query": "Show products",
            "user_email": None,
            "enable_cache": True,
            "requires_sql": True,
            "requires_email": False,
            "tables_involved": ["products"],
            "query_complexity": "simple",
            "routing_reasoning": "",
            "generated_sql": None,  # No SQL
            "sql_generation_error": None,
            "sql_retry_count": 0,
            "csv_s3_url": None,
            "sql_s3_url": None,
            "execution_metadata": None,
            "execution_error": None,
            "execution_retry_count": 0,
            "success": False,
            "error_message": None,
            "cache_hit": False,
        }

        result = executor_node(state)

        assert result["success"] is False
        assert result["error_message"] == "No SQL to execute"


class TestEmailNode:
    """Test cases for email_node."""

    @patch("app.graph.nodes.email_agent")
    @patch("app.graph.nodes.executor_agent")
    def test_email_success(self, mock_executor, mock_email):
        """Test successful email delivery."""
        # Setup mocks
        mock_executor.get_row_preview.return_value = None
        mock_executor.get_full_csv_path.return_value = "/tmp/results.csv"
        mock_email.send_results.return_value = None

        # Test
        state: QueryState = {
            "query": "Show products",
            "user_email": "test@example.com",
            "enable_cache": True,
            "requires_sql": True,
            "requires_email": True,
            "tables_involved": ["products"],
            "query_complexity": "simple",
            "routing_reasoning": "",
            "generated_sql": "SELECT * FROM products;",
            "sql_generation_error": None,
            "sql_retry_count": 0,
            "csv_s3_url": "https://example.com/results.csv",
            "sql_s3_url": "https://example.com/query.sql",
            "execution_metadata": {"csv_s3_key": "reports/test.csv"},
            "execution_error": None,
            "execution_retry_count": 0,
            "success": True,
            "error_message": None,
            "cache_hit": False,
        }

        result = email_node(state)

        # Email node returns empty dict on success
        assert result == {}
        mock_email.send_results.assert_called_once()

    def test_email_no_email_address(self):
        """Test email node when no email is provided."""
        state: QueryState = {
            "query": "Show products",
            "user_email": None,  # No email
            "enable_cache": True,
            "requires_sql": True,
            "requires_email": True,
            "tables_involved": ["products"],
            "query_complexity": "simple",
            "routing_reasoning": "",
            "generated_sql": "SELECT * FROM products;",
            "sql_generation_error": None,
            "sql_retry_count": 0,
            "csv_s3_url": "https://example.com/results.csv",
            "sql_s3_url": "https://example.com/query.sql",
            "execution_metadata": {},
            "execution_error": None,
            "execution_retry_count": 0,
            "success": True,
            "error_message": None,
            "cache_hit": False,
        }

        result = email_node(state)

        assert result == {}