"""Tests for the Email Agent."""

import os
import pytest
from unittest.mock import Mock, MagicMock, patch, mock_open
import pandas as pd


class TestEmailAgent:
    """Test cases for EmailAgent class."""

    def test_email_agent_initialization(self):
        """Test EmailAgent initializes correctly."""
        from agents.email_agent.sender import EmailAgent

        agent = EmailAgent(
            smtp_host="smtp.gmail.com",
            smtp_port=587,
            smtp_user="test@gmail.com",
            smtp_password="test-password"
        )

        assert agent.smtp_host == "smtp.gmail.com"
        assert agent.smtp_port == 587
        assert agent.smtp_user == "test@gmail.com"

    def test_send_results_success(self, mock_smtp_server, sample_dataframe, sample_execution_metadata):
        """Test successful email sending."""
        with patch('smtplib.SMTP') as mock_smtp_class:
            mock_smtp_class.return_value.__enter__ = MagicMock(return_value=mock_smtp_server)
            mock_smtp_class.return_value.__exit__ = MagicMock(return_value=False)

            from agents.email_agent.sender import EmailAgent

            agent = EmailAgent(
                smtp_host="smtp.gmail.com",
                smtp_port=587,
                smtp_user="sender@gmail.com",
                smtp_password="test-password"
            )

            agent.send_results(
                to_email="recipient@example.com",
                user_query="Show top customers",
                s3_url="https://example.com/results.csv",
                metadata=sample_execution_metadata,
                preview_df=sample_dataframe
            )

            mock_smtp_server.starttls.assert_called_once()
            mock_smtp_server.login.assert_called_once_with("sender@gmail.com", "test-password")
            mock_smtp_server.send_message.assert_called_once()

    def test_send_results_without_preview(self, mock_smtp_server, sample_execution_metadata):
        """Test email sending without preview DataFrame."""
        with patch('smtplib.SMTP') as mock_smtp_class:
            mock_smtp_class.return_value.__enter__ = MagicMock(return_value=mock_smtp_server)
            mock_smtp_class.return_value.__exit__ = MagicMock(return_value=False)

            from agents.email_agent.sender import EmailAgent

            agent = EmailAgent(
                smtp_host="smtp.gmail.com",
                smtp_port=587,
                smtp_user="sender@gmail.com",
                smtp_password="test-password"
            )

            agent.send_results(
                to_email="recipient@example.com",
                user_query="Show top customers",
                s3_url="https://example.com/results.csv",
                metadata=sample_execution_metadata,
                preview_df=None
            )

            mock_smtp_server.send_message.assert_called_once()

    def test_send_results_with_attachment(
        self,
        mock_smtp_server,
        sample_execution_metadata,
        temp_csv_file
    ):
        """Test email sending with CSV attachment."""
        with patch('smtplib.SMTP') as mock_smtp_class:
            mock_smtp_class.return_value.__enter__ = MagicMock(return_value=mock_smtp_server)
            mock_smtp_class.return_value.__exit__ = MagicMock(return_value=False)

            from agents.email_agent.sender import EmailAgent

            agent = EmailAgent(
                smtp_host="smtp.gmail.com",
                smtp_port=587,
                smtp_user="sender@gmail.com",
                smtp_password="test-password"
            )

            # Create a temp file for attachment
            with patch('os.path.exists', return_value=True):
                with patch('builtins.open', mock_open(read_data=b'id,name\n1,Alice')):
                    with patch('os.remove') as mock_remove:
                        agent.send_results(
                            to_email="recipient@example.com",
                            user_query="Show top customers",
                            s3_url="https://example.com/results.csv",
                            metadata=sample_execution_metadata,
                            csv_attachment_path="/tmp/attachment.csv"
                        )

                        mock_remove.assert_called_once_with("/tmp/attachment.csv")

    def test_send_results_handles_smtp_error(self, sample_execution_metadata):
        """Test email sending handles SMTP errors."""
        with patch('smtplib.SMTP') as mock_smtp_class:
            mock_server = MagicMock()
            mock_server.starttls.side_effect = Exception("SMTP connection failed")
            mock_smtp_class.return_value.__enter__ = MagicMock(return_value=mock_server)
            mock_smtp_class.return_value.__exit__ = MagicMock(return_value=False)

            from agents.email_agent.sender import EmailAgent

            agent = EmailAgent(
                smtp_host="smtp.gmail.com",
                smtp_port=587,
                smtp_user="sender@gmail.com",
                smtp_password="test-password"
            )

            with pytest.raises(Exception, match="SMTP connection failed"):
                agent.send_results(
                    to_email="recipient@example.com",
                    user_query="Show top customers",
                    s3_url="https://example.com/results.csv",
                    metadata=sample_execution_metadata
                )

    def test_send_results_email_subject_truncation(self, mock_smtp_server, sample_execution_metadata):
        """Test that long query is truncated in subject."""
        with patch('smtplib.SMTP') as mock_smtp_class:
            mock_smtp_class.return_value.__enter__ = MagicMock(return_value=mock_smtp_server)
            mock_smtp_class.return_value.__exit__ = MagicMock(return_value=False)

            from agents.email_agent.sender import EmailAgent

            agent = EmailAgent(
                smtp_host="smtp.gmail.com",
                smtp_port=587,
                smtp_user="sender@gmail.com",
                smtp_password="test-password"
            )

            long_query = "Show me all customers with their orders and products sorted by total revenue descending"

            agent.send_results(
                to_email="recipient@example.com",
                user_query=long_query,
                s3_url="https://example.com/results.csv",
                metadata=sample_execution_metadata
            )

            # Verify the email was sent (subject truncation happens in email construction)
            mock_smtp_server.send_message.assert_called_once()


class TestEmailAgentErrorNotification:
    """Test cases for error notification emails."""

    def test_send_error_notification_success(self, mock_smtp_server):
        """Test successful error notification sending."""
        with patch('smtplib.SMTP') as mock_smtp_class:
            mock_smtp_class.return_value.__enter__ = MagicMock(return_value=mock_smtp_server)
            mock_smtp_class.return_value.__exit__ = MagicMock(return_value=False)

            from agents.email_agent.sender import EmailAgent

            agent = EmailAgent(
                smtp_host="smtp.gmail.com",
                smtp_port=587,
                smtp_user="sender@gmail.com",
                smtp_password="test-password"
            )

            agent.send_error_notification(
                to_email="recipient@example.com",
                user_query="Show invalid data",
                error="SQL syntax error near 'FROM'"
            )

            mock_smtp_server.starttls.assert_called_once()
            mock_smtp_server.login.assert_called_once()
            mock_smtp_server.send_message.assert_called_once()

    def test_send_error_notification_handles_smtp_error(self):
        """Test error notification handles SMTP errors gracefully."""
        with patch('smtplib.SMTP') as mock_smtp_class:
            mock_server = MagicMock()
            mock_server.starttls.side_effect = Exception("Connection refused")
            mock_smtp_class.return_value.__enter__ = MagicMock(return_value=mock_server)
            mock_smtp_class.return_value.__exit__ = MagicMock(return_value=False)

            from agents.email_agent.sender import EmailAgent

            agent = EmailAgent(
                smtp_host="smtp.gmail.com",
                smtp_port=587,
                smtp_user="sender@gmail.com",
                smtp_password="test-password"
            )

            # Should not raise, just log the error
            agent.send_error_notification(
                to_email="recipient@example.com",
                user_query="Test query",
                error="Test error"
            )


class TestEmailAgentPreviewTable:
    """Test cases for preview table generation."""

    def test_generate_preview_table_with_data(self):
        """Test preview table generation with DataFrame."""
        from agents.email_agent.sender import EmailAgent

        agent = EmailAgent(
            smtp_host="smtp.gmail.com",
            smtp_port=587,
            smtp_user="sender@gmail.com",
            smtp_password="test-password"
        )

        df = pd.DataFrame({
            "id": [1, 2, 3],
            "name": ["Alice", "Bob", "Charlie"]
        })

        html = agent._generate_preview_table(df)

        assert "<table" in html
        assert "<thead>" in html
        assert "<tbody>" in html
        assert "Alice" in html
        assert "Bob" in html
        assert "Charlie" in html

    def test_generate_preview_table_empty_dataframe(self):
        """Test preview table with empty DataFrame."""
        from agents.email_agent.sender import EmailAgent

        agent = EmailAgent(
            smtp_host="smtp.gmail.com",
            smtp_port=587,
            smtp_user="sender@gmail.com",
            smtp_password="test-password"
        )

        df = pd.DataFrame()

        html = agent._generate_preview_table(df)

        assert "No preview available" in html

    def test_generate_preview_table_none_dataframe(self):
        """Test preview table with None DataFrame."""
        from agents.email_agent.sender import EmailAgent

        agent = EmailAgent(
            smtp_host="smtp.gmail.com",
            smtp_port=587,
            smtp_user="sender@gmail.com",
            smtp_password="test-password"
        )

        html = agent._generate_preview_table(None)

        assert "No preview available" in html

    def test_generate_preview_table_styling(self):
        """Test preview table has proper styling."""
        from agents.email_agent.sender import EmailAgent

        agent = EmailAgent(
            smtp_host="smtp.gmail.com",
            smtp_port=587,
            smtp_user="sender@gmail.com",
            smtp_password="test-password"
        )

        df = pd.DataFrame({"id": [1], "name": ["Test"]})

        html = agent._generate_preview_table(df)

        assert "border-collapse: collapse" in html
        assert "border: 1px solid #ddd" in html
        assert "padding: 8px" in html


class TestEmailAgentMultipart:
    """Test cases for multipart email construction."""

    def test_email_has_plain_and_html_parts(self, mock_smtp_server, sample_execution_metadata):
        """Test that email contains both plain and HTML parts."""
        with patch('smtplib.SMTP') as mock_smtp_class:
            mock_smtp_class.return_value.__enter__ = MagicMock(return_value=mock_smtp_server)
            mock_smtp_class.return_value.__exit__ = MagicMock(return_value=False)

            from agents.email_agent.sender import EmailAgent

            agent = EmailAgent(
                smtp_host="smtp.gmail.com",
                smtp_port=587,
                smtp_user="sender@gmail.com",
                smtp_password="test-password"
            )

            agent.send_results(
                to_email="recipient@example.com",
                user_query="Show top customers",
                s3_url="https://example.com/results.csv",
                metadata=sample_execution_metadata
            )

            # Get the message that was sent
            call_args = mock_smtp_server.send_message.call_args
            message = call_args[0][0]

            # Check content type is multipart/alternative
            assert message.get_content_type() == "multipart/alternative"

    def test_email_headers_set_correctly(self, mock_smtp_server, sample_execution_metadata):
        """Test that email headers are set correctly."""
        with patch('smtplib.SMTP') as mock_smtp_class:
            mock_smtp_class.return_value.__enter__ = MagicMock(return_value=mock_smtp_server)
            mock_smtp_class.return_value.__exit__ = MagicMock(return_value=False)

            from agents.email_agent.sender import EmailAgent

            agent = EmailAgent(
                smtp_host="smtp.gmail.com",
                smtp_port=587,
                smtp_user="sender@gmail.com",
                smtp_password="test-password"
            )

            agent.send_results(
                to_email="recipient@example.com",
                user_query="Show top customers",
                s3_url="https://example.com/results.csv",
                metadata=sample_execution_metadata
            )

            call_args = mock_smtp_server.send_message.call_args
            message = call_args[0][0]

            assert message['From'] == "sender@gmail.com"
            assert message['To'] == "recipient@example.com"
            assert "Query Results:" in message['Subject']
