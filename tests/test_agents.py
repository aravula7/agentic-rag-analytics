"""Tests for agent components."""

import pytest
from unittest.mock import Mock, patch
from agents.router_agent import RouterAgent
from agents.sql_agent import SQLAgent, SchemaRetriever
from agents.executor_agent import ExecutorAgent, S3Uploader
from agents.email_agent import EmailAgent


class TestRouterAgent:
    """Tests for Router Agent."""

    @pytest.fixture
    def router_agent(self):
        """Create Router Agent instance."""
        return RouterAgent(api_key="test-key", model="gpt-4o")

    def test_route_sql_required(self, router_agent):
        """Test routing decision for SQL query."""
        with patch.object(router_agent.client.chat.completions, 'create') as mock_create:
            mock_response = Mock()
            mock_response.choices = [Mock(message=Mock(content='{"requires_sql": true, "requires_email": false, "tables_involved": ["customers"], "query_complexity": "simple", "reasoning": "test"}'))]
            mock_create.return_value = mock_response
            
            result = router_agent.route("Show all customers")
            
            assert result['requires_sql'] == True
            assert result['requires_email'] == False
            assert 'customers' in result['tables_involved']

    def test_route_no_sql_required(self, router_agent):
        """Test routing decision for non-SQL query."""
        with patch.object(router_agent.client.chat.completions, 'create') as mock_create:
            mock_response = Mock()
            mock_response.choices = [Mock(message=Mock(content='{"requires_sql": false, "requires_email": false, "tables_involved": [], "query_complexity": "simple", "reasoning": "test"}'))]
            mock_create.return_value = mock_response
            
            result = router_agent.route("What's the weather?")
            
            assert result['requires_sql'] == False


class TestSQLAgent:
    """Tests for SQL Agent."""

    @pytest.fixture
    def schema_retriever(self):
        """Create mock Schema Retriever."""
        retriever = Mock(spec=SchemaRetriever)
        retriever.retrieve.return_value = "customers (customer_id, email, region)"
        return retriever

    @pytest.fixture
    def sql_agent(self, schema_retriever):
        """Create SQL Agent instance."""
        return SQLAgent(
            anthropic_api_key="test-key",
            schema_retriever=schema_retriever,
            model="claude-haiku-4-20250514"
        )

    def test_generate_sql(self, sql_agent):
        """Test SQL generation."""
        with patch.object(sql_agent.client.messages, 'create') as mock_create:
            mock_response = Mock()
            mock_response.content = [Mock(text="SELECT * FROM customers;")]
            mock_create.return_value = mock_response
            
            sql = sql_agent.generate_sql("Show all customers")
            
            assert "SELECT" in sql
            assert "customers" in sql

    def test_validate_sql_syntax_valid(self, sql_agent):
        """Test SQL validation for valid query."""
        sql = "SELECT * FROM customers WHERE region = 'West';"
        assert sql_agent.validate_sql_syntax(sql) == True

    def test_validate_sql_syntax_invalid(self, sql_agent):
        """Test SQL validation for invalid query."""
        sql = "DELETE FROM customers;"
        assert sql_agent.validate_sql_syntax(sql) == False


class TestExecutorAgent:
    """Tests for Executor Agent."""

    @pytest.fixture
    def s3_uploader(self):
        """Create mock S3 Uploader."""
        uploader = Mock(spec=S3Uploader)
        uploader.upload_file.return_value = "s3://bucket/key"
        return uploader

    @pytest.fixture
    def executor_agent(self, s3_uploader):
        """Create Executor Agent instance."""
        return ExecutorAgent(
            db_host="localhost",
            db_port=5432,
            db_name="test",
            db_user="test",
            db_password="test",
            s3_uploader=s3_uploader
        )

    def test_write_csv(self, executor_agent):
        """Test CSV writing."""
        rows = [("John", "john@example.com"), ("Jane", "jane@example.com")]
        columns = ["name", "email"]
        
        csv_path, s3_key = executor_agent._write_csv(rows, columns, "test query")
        
        assert csv_path.endswith(".csv")
        assert "query_" in s3_key


class TestEmailAgent:
    """Tests for Email Agent."""

    @pytest.fixture
    def email_agent(self):
        """Create Email Agent instance."""
        return EmailAgent(
            smtp_host="smtp.gmail.com",
            smtp_port=587,
            smtp_user="test@example.com",
            smtp_password="test"
        )

    def test_send_results(self, email_agent):
        """Test sending results email."""
        metadata = {
            'row_count': 10,
            'column_count': 3,
            'execution_time_seconds': 1.5
        }
        
        with patch('smtplib.SMTP') as mock_smtp:
            email_agent.send_results(
                to_email="user@example.com",
                user_query="Test query",
                s3_url="s3://bucket/key",
                metadata=metadata
            )
            
            # Verify SMTP was called
            assert mock_smtp.called


if __name__ == "__main__":
    pytest.main([__file__, "-v"])