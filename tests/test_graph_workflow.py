"""Tests for complete LangGraph workflow execution."""

import pytest
from unittest.mock import MagicMock, patch
from app.graph.graph import create_graph, workflow_graph
from app.graph.state import QueryState, build_initial_state


class TestGraphWorkflow:
    """Test cases for the complete graph workflow."""

    @patch("app.graph.nodes.ChatOpenAI")
    @patch("app.graph.nodes.ChatAnthropic")
    @patch("app.graph.nodes.executor_agent")
    def test_successful_workflow_no_email(self, mock_executor, mock_anthropic, mock_openai):
        """Test successful workflow execution without email."""
        # Setup Router mock
        mock_openai_llm = MagicMock()
        mock_openai_response = MagicMock()
        mock_openai_response.content = '''{
            "requires_sql": true,
            "requires_email": false,
            "tables_involved": ["products"],
            "query_complexity": "simple",
            "reasoning": "Simple product query"
        }'''
        mock_openai_llm.invoke.return_value = mock_openai_response
        mock_openai.return_value = mock_openai_llm

        # Setup SQL Generator mock
        mock_anthropic_llm = MagicMock()
        mock_anthropic_response = MagicMock()
        mock_anthropic_response.content = "SELECT * FROM products LIMIT 10;"
        mock_anthropic_llm.invoke.return_value = mock_anthropic_response
        mock_anthropic.return_value = mock_anthropic_llm

        # Setup Executor mock
        mock_executor.execute_sql.return_value = (
            "https://example.com/results.csv",
            {
                "row_count": 10,
                "column_count": 3,
                "execution_time_seconds": 0.5,
                "sql_s3_url": "https://example.com/query.sql",
            }
        )

        # Build initial state
        initial_state = build_initial_state(
            query="Show top 10 products",
            user_email=None,
            enable_cache=True
        )

        # Execute workflow
        final_state = workflow_graph.invoke(initial_state)

        # Assertions
        assert final_state["success"] is True
        assert final_state["generated_sql"] == "SELECT * FROM products LIMIT 10;"
        assert final_state["csv_s3_url"] == "https://example.com/results.csv"
        assert final_state["requires_sql"] is True
        assert final_state["requires_email"] is False
        mock_executor.execute_sql.assert_called_once()

    @patch("app.graph.nodes.ChatOpenAI")
    @patch("app.graph.nodes.ChatAnthropic")
    @patch("app.graph.nodes.executor_agent")
    @patch("app.graph.nodes.email_agent")
    def test_successful_workflow_with_email(self, mock_email, mock_executor, mock_anthropic, mock_openai):
        """Test successful workflow execution with email delivery."""
        # Setup Router mock
        mock_openai_llm = MagicMock()
        mock_openai_response = MagicMock()
        mock_openai_response.content = '''{
            "requires_sql": true,
            "requires_email": true,
            "tables_involved": ["customers"],
            "query_complexity": "simple",
            "reasoning": "Customer query with email"
        }'''
        mock_openai_llm.invoke.return_value = mock_openai_response
        mock_openai.return_value = mock_openai_llm

        # Setup SQL Generator mock
        mock_anthropic_llm = MagicMock()
        mock_anthropic_response = MagicMock()
        mock_anthropic_response.content = "SELECT * FROM customers LIMIT 20;"
        mock_anthropic_llm.invoke.return_value = mock_anthropic_response
        mock_anthropic.return_value = mock_anthropic_llm

        # Setup Executor mock
        mock_executor.execute_sql.return_value = (
            "https://example.com/results.csv",
            {"csv_s3_key": "reports/test.csv", "row_count": 20}
        )
        mock_executor.get_row_preview.return_value = None
        mock_executor.get_full_csv_path.return_value = "/tmp/results.csv"

        # Setup Email mock
        mock_email.send_results.return_value = None

        # Build initial state
        initial_state = build_initial_state(
            query="Email me the customer list",
            user_email="test@example.com",
            enable_cache=False
        )

        # Execute workflow
        final_state = workflow_graph.invoke(initial_state)

        # Assertions
        assert final_state["success"] is True
        assert final_state["requires_email"] is True
        mock_email.send_results.assert_called_once()

    @patch("app.graph.nodes.ChatOpenAI")
    def test_workflow_no_sql_required(self, mock_openai):
        """Test workflow when no SQL is required."""
        # Setup Router mock
        mock_openai_llm = MagicMock()
        mock_openai_response = MagicMock()
        mock_openai_response.content = '''{
            "requires_sql": false,
            "requires_email": false,
            "tables_involved": [],
            "query_complexity": "none",
            "reasoning": "General question, not a data request"
        }'''
        mock_openai_llm.invoke.return_value = mock_openai_response
        mock_openai.return_value = mock_openai_llm

        # Build initial state
        initial_state = build_initial_state(
            query="What is SQL?",
            user_email=None,
            enable_cache=False
        )

        # Execute workflow
        final_state = workflow_graph.invoke(initial_state)

        # Assertions
        assert final_state["requires_sql"] is False
        assert final_state["success"] is False
        assert "does not require database access" in final_state["error_message"]

    @patch("app.graph.nodes.ChatOpenAI")
    @patch("app.graph.nodes.ChatAnthropic")
    @patch("app.graph.nodes.schema_retriever")
    @patch("app.graph.nodes.executor_agent")
    def test_workflow_with_sql_retry(self, mock_executor, mock_retriever, mock_anthropic, mock_openai):
        """Test workflow with SQL generation retry on execution error."""
        # Setup Router mock
        mock_openai_llm = MagicMock()
        mock_openai_response = MagicMock()
        mock_openai_response.content = '''{
            "requires_sql": true,
            "requires_email": false,
            "tables_involved": ["products"],
            "query_complexity": "medium",
            "reasoning": "Product revenue query"
        }'''
        mock_openai_llm.invoke.return_value = mock_openai_response
        mock_openai.return_value = mock_openai_llm

        # Setup Schema Retriever mock
        mock_retriever.get_table_context.return_value = "Schema: products (product_id, name, price)"

        # Setup SQL Generator mock - returns different SQL on retry
        mock_anthropic_llm = MagicMock()
        
        # First call: Bad SQL
        mock_first_response = MagicMock()
        mock_first_response.content = "SELECT ROUND(price, 2) FROM products;"
        
        # Second call: Fixed SQL
        mock_second_response = MagicMock()
        mock_second_response.content = "SELECT ROUND(price::numeric, 2) FROM products;"
        
        mock_anthropic_llm.invoke.side_effect = [mock_first_response, mock_second_response]
        mock_anthropic.return_value = mock_anthropic_llm

        # Setup Executor mock - fails first, succeeds second
        mock_executor.execute_sql.side_effect = [
            Exception("Database error: function round(double precision, integer) does not exist"),
            ("https://example.com/results.csv", {"row_count": 10})
        ]

        # Build initial state