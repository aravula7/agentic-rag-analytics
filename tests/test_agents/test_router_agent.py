"""Tests for the Router Agent."""

import json
import pytest
from unittest.mock import Mock, MagicMock, patch


class TestRouterAgent:
    """Test cases for RouterAgent class."""

    def _make_openai_response(self, content: str):
        """Helper to create a mock OpenAI chat completion response."""
        mock_response = MagicMock()
        mock_choice = MagicMock()
        mock_message = MagicMock()
        mock_message.content = content
        mock_choice.message = mock_message
        mock_response.choices = [mock_choice]
        return mock_response

    def test_router_agent_initialization(self):
        """Test RouterAgent initializes correctly."""
        with patch('agents.router_agent.router.OpenAI') as mock_openai:
            from agents.router_agent.router import RouterAgent

            agent = RouterAgent(api_key="test-key", model="gpt-4o")

            assert agent.model == "gpt-4o"
            mock_openai.assert_called_once_with(api_key="test-key")

    def test_route_sql_query(self, mock_openai_routing_response):
        """Test routing a query that requires SQL."""
        with patch('agents.router_agent.router.OpenAI') as mock_openai:
            from agents.router_agent.router import RouterAgent

            mock_client = MagicMock()
            content = json.dumps(mock_openai_routing_response)
            mock_client.chat.completions.create.return_value = self._make_openai_response(content)
            mock_openai.return_value = mock_client

            agent = RouterAgent(api_key="test-key")
            result = agent.route("Show me top 10 customers by revenue")

            assert result["requires_sql"] is True
            assert result["requires_email"] is False
            assert "customers" in result["tables_involved"]
            assert result["query_complexity"] == "simple"

    def test_route_query_with_email(self, mock_openai_routing_response_with_email):
        """Test routing a query that requires email delivery."""
        with patch('agents.router_agent.router.OpenAI') as mock_openai:
            from agents.router_agent.router import RouterAgent

            mock_client = MagicMock()
            content = json.dumps(mock_openai_routing_response_with_email)
            mock_client.chat.completions.create.return_value = self._make_openai_response(content)
            mock_openai.return_value = mock_client

            agent = RouterAgent(api_key="test-key")
            result = agent.route("Send me a complex product analysis report")

            assert result["requires_sql"] is True
            assert result["requires_email"] is True
            assert result["query_complexity"] == "complex"

    def test_route_non_sql_query(self, mock_openai_routing_no_sql):
        """Test routing a general question that does not need SQL."""
        with patch('agents.router_agent.router.OpenAI') as mock_openai:
            from agents.router_agent.router import RouterAgent

            mock_client = MagicMock()
            content = json.dumps(mock_openai_routing_no_sql)
            mock_client.chat.completions.create.return_value = self._make_openai_response(content)
            mock_openai.return_value = mock_client

            agent = RouterAgent(api_key="test-key")
            result = agent.route("What is a database?")

            assert result["requires_sql"] is False
            assert result["requires_email"] is False
            assert result["tables_involved"] == []

    def test_route_strips_markdown_code_blocks(self, mock_openai_routing_response):
        """Test that markdown code blocks are stripped from response."""
        with patch('agents.router_agent.router.OpenAI') as mock_openai:
            from agents.router_agent.router import RouterAgent

            mock_client = MagicMock()
            # Wrap in markdown code blocks
            content = "```json\n" + json.dumps(mock_openai_routing_response) + "\n```"
            mock_client.chat.completions.create.return_value = self._make_openai_response(content)
            mock_openai.return_value = mock_client

            agent = RouterAgent(api_key="test-key")
            result = agent.route("Show top customers")

            assert result["requires_sql"] is True
            assert "tables_involved" in result

    def test_route_handles_json_parse_error(self):
        """Test that JSON parse errors return default decision."""
        with patch('agents.router_agent.router.OpenAI') as mock_openai:
            from agents.router_agent.router import RouterAgent

            mock_client = MagicMock()
            # Return invalid JSON
            mock_client.chat.completions.create.return_value = self._make_openai_response(
                "This is not valid JSON"
            )
            mock_openai.return_value = mock_client

            agent = RouterAgent(api_key="test-key")
            result = agent.route("Show customers")

            # Should return default decision
            assert result["requires_sql"] is True
            assert result["requires_email"] is False
            assert result["tables_involved"] == []
            assert result["query_complexity"] == "simple"
            assert "Error parsing decision" in result["reasoning"]

    def test_route_handles_empty_response(self):
        """Test that empty/None response raises ValueError."""
        with patch('agents.router_agent.router.OpenAI') as mock_openai:
            from agents.router_agent.router import RouterAgent

            mock_client = MagicMock()
            empty_response = self._make_openai_response("")
            empty_response.choices[0].message.content = None
            mock_client.chat.completions.create.return_value = empty_response
            mock_openai.return_value = mock_client

            agent = RouterAgent(api_key="test-key")

            with pytest.raises(ValueError, match="Router returned empty response"):
                agent.route("Show customers")

    def test_route_handles_api_error(self):
        """Test that API errors are propagated."""
        with patch('agents.router_agent.router.OpenAI') as mock_openai:
            from agents.router_agent.router import RouterAgent

            mock_client = MagicMock()
            mock_client.chat.completions.create.side_effect = Exception("API rate limit exceeded")
            mock_openai.return_value = mock_client

            agent = RouterAgent(api_key="test-key")

            with pytest.raises(Exception, match="API rate limit exceeded"):
                agent.route("Show customers")

    def test_route_uses_temperature_zero(self, mock_openai_routing_response):
        """Test that routing uses temperature 0 for determinism."""
        with patch('agents.router_agent.router.OpenAI') as mock_openai:
            from agents.router_agent.router import RouterAgent

            mock_client = MagicMock()
            content = json.dumps(mock_openai_routing_response)
            mock_client.chat.completions.create.return_value = self._make_openai_response(content)
            mock_openai.return_value = mock_client

            agent = RouterAgent(api_key="test-key")
            agent.route("Show top customers")

            call_args = mock_client.chat.completions.create.call_args
            assert call_args.kwargs["temperature"] == 0.0

    def test_route_uses_correct_model(self, mock_openai_routing_response):
        """Test that routing uses the configured model."""
        with patch('agents.router_agent.router.OpenAI') as mock_openai:
            from agents.router_agent.router import RouterAgent

            mock_client = MagicMock()
            content = json.dumps(mock_openai_routing_response)
            mock_client.chat.completions.create.return_value = self._make_openai_response(content)
            mock_openai.return_value = mock_client

            agent = RouterAgent(api_key="test-key", model="gpt-4o")
            agent.route("Show customers")

            call_args = mock_client.chat.completions.create.call_args
            assert call_args.kwargs["model"] == "gpt-4o"

    def test_route_passes_system_and_user_messages(self, mock_openai_routing_response):
        """Test that routing sends system and user messages."""
        with patch('agents.router_agent.router.OpenAI') as mock_openai:
            from agents.router_agent.router import RouterAgent

            mock_client = MagicMock()
            content = json.dumps(mock_openai_routing_response)
            mock_client.chat.completions.create.return_value = self._make_openai_response(content)
            mock_openai.return_value = mock_client

            agent = RouterAgent(api_key="test-key")
            agent.route("Show top customers by revenue")

            call_args = mock_client.chat.completions.create.call_args
            messages = call_args.kwargs["messages"]

            assert len(messages) == 2
            assert messages[0]["role"] == "system"
            assert messages[1]["role"] == "user"
            assert "Show top customers by revenue" in messages[1]["content"]


class TestRouterAgentEdgeCases:
    """Edge case tests for RouterAgent."""

    def _make_openai_response(self, content: str):
        mock_response = MagicMock()
        mock_choice = MagicMock()
        mock_message = MagicMock()
        mock_message.content = content
        mock_choice.message = mock_message
        mock_response.choices = [mock_choice]
        return mock_response

    def test_route_with_extra_whitespace_in_json(self):
        """Test handling of JSON with extra whitespace."""
        with patch('agents.router_agent.router.OpenAI') as mock_openai:
            from agents.router_agent.router import RouterAgent

            mock_client = MagicMock()
            content = """
            {
                "requires_sql": true,
                "requires_email": false,
                "tables_involved": ["customers"],
                "query_complexity": "simple",
                "reasoning": "Basic query"
            }
            """
            mock_client.chat.completions.create.return_value = self._make_openai_response(content)
            mock_openai.return_value = mock_client

            agent = RouterAgent(api_key="test-key")
            result = agent.route("Show customers")

            assert result["requires_sql"] is True

    def test_route_with_nested_markdown_blocks(self):
        """Test handling of markdown with language hint."""
        with patch('agents.router_agent.router.OpenAI') as mock_openai:
            from agents.router_agent.router import RouterAgent

            mock_client = MagicMock()
            response_data = {
                "requires_sql": True,
                "requires_email": False,
                "tables_involved": ["orders"],
                "query_complexity": "medium",
                "reasoning": "Needs order data"
            }
            content = "```json\n" + json.dumps(response_data, indent=2) + "\n```"
            mock_client.chat.completions.create.return_value = self._make_openai_response(content)
            mock_openai.return_value = mock_client

            agent = RouterAgent(api_key="test-key")
            result = agent.route("Count all orders")

            assert result["requires_sql"] is True
            assert "orders" in result["tables_involved"]

    def test_route_with_empty_query(self, mock_openai_routing_response):
        """Test routing with an empty query string."""
        with patch('agents.router_agent.router.OpenAI') as mock_openai:
            from agents.router_agent.router import RouterAgent

            mock_client = MagicMock()
            content = json.dumps(mock_openai_routing_response)
            mock_client.chat.completions.create.return_value = self._make_openai_response(content)
            mock_openai.return_value = mock_client

            agent = RouterAgent(api_key="test-key")
            result = agent.route("")

            assert isinstance(result, dict)

    def test_route_with_long_query(self, mock_openai_routing_response):
        """Test routing with a very long query string."""
        with patch('agents.router_agent.router.OpenAI') as mock_openai:
            from agents.router_agent.router import RouterAgent

            mock_client = MagicMock()
            content = json.dumps(mock_openai_routing_response)
            mock_client.chat.completions.create.return_value = self._make_openai_response(content)
            mock_openai.return_value = mock_client

            agent = RouterAgent(api_key="test-key")
            long_query = "Show me the top customers " * 100
            result = agent.route(long_query)

            assert isinstance(result, dict)
            assert "requires_sql" in result
