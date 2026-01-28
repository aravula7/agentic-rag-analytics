"""Tests for the Executor Agent."""

import os
import pytest
from unittest.mock import Mock, MagicMock, patch, call
import pandas as pd
from datetime import datetime


class TestExecutorAgent:
    """Test cases for ExecutorAgent class."""

    def test_executor_agent_initialization(self, mock_s3_uploader):
        """Test ExecutorAgent initializes correctly."""
        with patch('os.makedirs'):
            from agents.executor_agent.executor import ExecutorAgent

            agent = ExecutorAgent(
                db_host="localhost",
                db_port=5432,
                db_name="test_db",
                db_user="test_user",
                db_password="test_pass",
                s3_uploader=mock_s3_uploader,
                query_timeout=30
            )

            assert agent.db_config["host"] == "localhost"
            assert agent.db_config["port"] == 5432
            assert agent.db_config["database"] == "test_db"
            assert agent.query_timeout == 30

    def test_execute_sql_success(self, mock_s3_uploader):
        """Test successful SQL execution."""
        with patch('os.makedirs'):
            from agents.executor_agent.executor import ExecutorAgent

            agent = ExecutorAgent(
                db_host="localhost",
                db_port=5432,
                db_name="test_db",
                db_user="test_user",
                db_password="test_pass",
                s3_uploader=mock_s3_uploader
            )

        mock_cursor = MagicMock()
        mock_cursor.description = [("id",), ("name",), ("revenue",)]
        mock_cursor.fetchall.return_value = [
            {"id": 1, "name": "Alice", "revenue": 15000},
            {"id": 2, "name": "Bob", "revenue": 12000},
        ]

        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        mock_s3_uploader.upload_file.return_value = "https://example.com/results.csv"

        with patch('psycopg2.connect', return_value=mock_conn):
            with patch('os.remove'):
                with patch('pandas.DataFrame.to_csv'):
                    csv_url, metadata = agent.execute_sql(
                        "SELECT id, name, revenue FROM customers",
                        "Show top customers"
                    )

        assert csv_url == "https://example.com/results.csv"
        assert metadata["row_count"] == 2
        assert metadata["column_count"] == 3
        assert "id" in metadata["columns"]
        assert "name" in metadata["columns"]
        assert "execution_time_seconds" in metadata

        # Verify read-only session
        mock_conn.set_session.assert_called_once_with(readonly=True)

    def test_execute_sql_sets_statement_timeout(self, mock_s3_uploader):
        """Test that statement timeout is set correctly."""
        with patch('os.makedirs'):
            from agents.executor_agent.executor import ExecutorAgent

            agent = ExecutorAgent(
                db_host="localhost",
                db_port=5432,
                db_name="test_db",
                db_user="test_user",
                db_password="test_pass",
                s3_uploader=mock_s3_uploader,
                query_timeout=45
            )

        mock_cursor = MagicMock()
        mock_cursor.description = [("id",)]
        mock_cursor.fetchall.return_value = [{"id": 1}]

        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        mock_s3_uploader.upload_file.return_value = "https://example.com/r.csv"

        with patch('psycopg2.connect', return_value=mock_conn):
            with patch('os.remove'):
                with patch('pandas.DataFrame.to_csv'):
                    agent.execute_sql("SELECT 1", "test")

        # First execute call should set timeout (45 * 1000 = 45000 ms)
        first_execute = mock_cursor.execute.call_args_list[0]
        assert "SET statement_timeout = 45000" in first_execute[0][0]

    def test_execute_sql_database_error(self, mock_s3_uploader):
        """Test SQL execution handles database errors."""
        import psycopg2

        with patch('os.makedirs'):
            from agents.executor_agent.executor import ExecutorAgent

            agent = ExecutorAgent(
                db_host="localhost",
                db_port=5432,
                db_name="test_db",
                db_user="test_user",
                db_password="test_pass",
                s3_uploader=mock_s3_uploader
            )

        with patch('psycopg2.connect') as mock_connect:
            mock_conn = MagicMock()
            mock_cursor = MagicMock()
            mock_cursor.execute.side_effect = psycopg2.ProgrammingError(
                'relation "nonexistent" does not exist'
            )
            mock_conn.cursor.return_value = mock_cursor
            mock_connect.return_value = mock_conn

            with pytest.raises(Exception, match="Database error"):
                agent.execute_sql("SELECT * FROM nonexistent", "test")

            # Verify cleanup: cursor and connection are closed
            mock_cursor.close.assert_called_once()
            mock_conn.close.assert_called_once()

    def test_execute_sql_connection_error(self, mock_s3_uploader):
        """Test SQL execution handles connection errors."""
        import psycopg2

        with patch('os.makedirs'):
            from agents.executor_agent.executor import ExecutorAgent

            agent = ExecutorAgent(
                db_host="localhost",
                db_port=5432,
                db_name="test_db",
                db_user="test_user",
                db_password="test_pass",
                s3_uploader=mock_s3_uploader
            )

        with patch('psycopg2.connect', side_effect=psycopg2.OperationalError("Connection refused")):
            with pytest.raises(Exception, match="Database error"):
                agent.execute_sql("SELECT 1", "test")

    def test_execute_sql_cleans_up_temp_files(self, mock_s3_uploader):
        """Test that temp files are cleaned up after upload."""
        with patch('os.makedirs'):
            from agents.executor_agent.executor import ExecutorAgent

            agent = ExecutorAgent(
                db_host="localhost",
                db_port=5432,
                db_name="test_db",
                db_user="test_user",
                db_password="test_pass",
                s3_uploader=mock_s3_uploader
            )

        mock_cursor = MagicMock()
        mock_cursor.description = [("id",)]
        mock_cursor.fetchall.return_value = [{"id": 1}]

        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        mock_s3_uploader.upload_file.return_value = "https://example.com/r.csv"

        with patch('psycopg2.connect', return_value=mock_conn):
            with patch('os.remove') as mock_remove:
                with patch('pandas.DataFrame.to_csv'):
                    agent.execute_sql("SELECT 1", "test")

            # Two files should be removed: CSV and SQL
            assert mock_remove.call_count == 2

    def test_execute_sql_uploads_csv_and_sql(self, mock_s3_uploader):
        """Test that both CSV and SQL files are uploaded to S3."""
        with patch('os.makedirs'):
            from agents.executor_agent.executor import ExecutorAgent

            agent = ExecutorAgent(
                db_host="localhost",
                db_port=5432,
                db_name="test_db",
                db_user="test_user",
                db_password="test_pass",
                s3_uploader=mock_s3_uploader
            )

        mock_cursor = MagicMock()
        mock_cursor.description = [("id",)]
        mock_cursor.fetchall.return_value = [{"id": 1}]

        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        mock_s3_uploader.upload_file.return_value = "https://example.com/file"

        with patch('psycopg2.connect', return_value=mock_conn):
            with patch('os.remove'):
                with patch('pandas.DataFrame.to_csv'):
                    agent.execute_sql("SELECT 1", "test")

        # upload_file should be called twice (CSV + SQL)
        assert mock_s3_uploader.upload_file.call_count == 2

        # First call should be CSV, second should be SQL
        csv_call = mock_s3_uploader.upload_file.call_args_list[0]
        sql_call = mock_s3_uploader.upload_file.call_args_list[1]

        assert csv_call[0][1].startswith("reports/")
        assert csv_call[0][1].endswith(".csv")
        assert sql_call[0][1].startswith("queries/")
        assert sql_call[0][1].endswith(".sql")


class TestExecutorAgentFileWriting:
    """Test cases for file writing methods."""

    def test_write_csv(self, mock_s3_uploader):
        """Test CSV file writing."""
        with patch('os.makedirs'):
            from agents.executor_agent.executor import ExecutorAgent

            agent = ExecutorAgent(
                db_host="localhost",
                db_port=5432,
                db_name="test_db",
                db_user="test_user",
                db_password="test_pass",
                s3_uploader=mock_s3_uploader
            )

        rows = [{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}]
        columns = ["id", "name"]

        with patch('pandas.DataFrame.to_csv') as mock_to_csv:
            local_path, s3_key = agent._write_csv(rows, columns, "query_test_abc")

        assert local_path.endswith(".csv")
        assert s3_key.startswith("reports/")
        assert s3_key.endswith(".csv")
        mock_to_csv.assert_called_once()

    def test_write_sql(self, mock_s3_uploader, tmp_path):
        """Test SQL file writing."""
        with patch('os.makedirs'):
            from agents.executor_agent.executor import ExecutorAgent

            agent = ExecutorAgent(
                db_host="localhost",
                db_port=5432,
                db_name="test_db",
                db_user="test_user",
                db_password="test_pass",
                s3_uploader=mock_s3_uploader
            )

        sql_query = "SELECT * FROM customers LIMIT 10;"
        user_query = "Show top customers"

        local_path, s3_key = agent._write_sql(sql_query, user_query, "query_test_abc")

        assert local_path.endswith(".sql")
        assert s3_key.startswith("queries/")
        assert s3_key.endswith(".sql")

        # Verify file contents
        with open(local_path, 'r') as f:
            content = f.read()

        assert "-- Generated:" in content
        assert "-- User Query: Show top customers" in content
        assert "SELECT * FROM customers LIMIT 10;" in content

        # Cleanup
        os.remove(local_path)


class TestExecutorAgentPreview:
    """Test cases for row preview functionality."""

    def test_get_row_preview_success(self, mock_s3_uploader, tmp_path):
        """Test successful row preview retrieval."""
        with patch('os.makedirs'):
            from agents.executor_agent.executor import ExecutorAgent

            agent = ExecutorAgent(
                db_host="localhost",
                db_port=5432,
                db_name="test_db",
                db_user="test_user",
                db_password="test_pass",
                s3_uploader=mock_s3_uploader
            )

        # Create a temp CSV file that pandas would read
        csv_content = "id,name,revenue\n1,Alice,15000\n2,Bob,12000\n"
        temp_csv = tmp_path / "test.csv"
        temp_csv.write_text(csv_content)

        def mock_download(s3_key, local_path):
            import shutil
            shutil.copy(str(temp_csv), local_path)

        mock_s3_uploader.download_file.side_effect = mock_download

        with patch('os.remove'):
            df = agent.get_row_preview("reports/2024/01/test.csv", num_rows=5)

        assert df is not None
        assert len(df) == 2
        assert "id" in df.columns
        assert "name" in df.columns

    def test_get_row_preview_returns_none_on_error(self, mock_s3_uploader):
        """Test that preview returns None on error."""
        with patch('os.makedirs'):
            from agents.executor_agent.executor import ExecutorAgent

            agent = ExecutorAgent(
                db_host="localhost",
                db_port=5432,
                db_name="test_db",
                db_user="test_user",
                db_password="test_pass",
                s3_uploader=mock_s3_uploader
            )

        mock_s3_uploader.download_file.side_effect = Exception("Download failed")

        result = agent.get_row_preview("nonexistent_key.csv")

        assert result is None

    def test_get_full_csv_path_success(self, mock_s3_uploader):
        """Test successful full CSV download."""
        with patch('os.makedirs'):
            from agents.executor_agent.executor import ExecutorAgent

            agent = ExecutorAgent(
                db_host="localhost",
                db_port=5432,
                db_name="test_db",
                db_user="test_user",
                db_password="test_pass",
                s3_uploader=mock_s3_uploader
            )

        mock_s3_uploader.download_file.return_value = None

        path = agent.get_full_csv_path("reports/2024/01/query_test.csv")

        assert path is not None
        assert "attachment_" in path
        assert path.endswith(".csv")

    def test_get_full_csv_path_returns_none_on_error(self, mock_s3_uploader):
        """Test that full CSV returns None on error."""
        with patch('os.makedirs'):
            from agents.executor_agent.executor import ExecutorAgent

            agent = ExecutorAgent(
                db_host="localhost",
                db_port=5432,
                db_name="test_db",
                db_user="test_user",
                db_password="test_pass",
                s3_uploader=mock_s3_uploader
            )

        mock_s3_uploader.download_file.side_effect = Exception("Download failed")

        result = agent.get_full_csv_path("nonexistent.csv")

        assert result is None


class TestExecutorAgentFilenameNormalization:
    """Test cases for filename normalization."""

    def _make_agent(self, mock_s3_uploader):
        with patch('os.makedirs'):
            from agents.executor_agent.executor import ExecutorAgent
            return ExecutorAgent(
                db_host="localhost",
                db_port=5432,
                db_name="test_db",
                db_user="test_user",
                db_password="test_pass",
                s3_uploader=mock_s3_uploader
            )

    def test_normalize_base_filename_basic(self, mock_s3_uploader):
        """Test basic filename normalization."""
        agent = self._make_agent(mock_s3_uploader)
        result = agent._normalize_base_filename("query_20240115_abc123")
        assert result == "query_20240115_abc123"

    def test_normalize_base_filename_with_spaces(self, mock_s3_uploader):
        """Test filename normalization with spaces."""
        agent = self._make_agent(mock_s3_uploader)
        result = agent._normalize_base_filename("query with spaces and stuff")
        assert " " not in result
        assert result.startswith("query")

    def test_normalize_base_filename_with_special_chars(self, mock_s3_uploader):
        """Test filename normalization with special characters."""
        agent = self._make_agent(mock_s3_uploader)
        result = agent._normalize_base_filename("query!@#$%^&*()")
        assert result.startswith("query")
        assert all(c.isalnum() or c == '_' for c in result)

    def test_normalize_base_filename_adds_query_prefix(self, mock_s3_uploader):
        """Test that 'query' prefix is added if missing."""
        agent = self._make_agent(mock_s3_uploader)
        result = agent._normalize_base_filename("report_20240115")
        assert result.startswith("query")

    def test_normalize_base_filename_empty_string(self, mock_s3_uploader):
        """Test filename normalization with empty string."""
        agent = self._make_agent(mock_s3_uploader)
        result = agent._normalize_base_filename("")
        assert result == "query"

    def test_normalize_base_filename_lowercase(self, mock_s3_uploader):
        """Test that filename is lowercased."""
        agent = self._make_agent(mock_s3_uploader)
        result = agent._normalize_base_filename("QUERY_UPPERCASE")
        assert result == result.lower()


class TestS3Uploader:
    """Test cases for S3Uploader class."""

    def test_s3_uploader_initialization(self, mock_s3_client):
        """Test S3Uploader initializes correctly."""
        with patch('boto3.client', return_value=mock_s3_client):
            from agents.executor_agent.s3_uploader import S3Uploader

            uploader = S3Uploader(
                endpoint_url="https://test.supabase.co/storage/v1/s3",
                bucket_name="test-bucket",
                aws_access_key_id="test-key",
                aws_secret_access_key="test-secret"
            )

            assert uploader.bucket_name == "test-bucket"
            assert uploader.endpoint_url == "https://test.supabase.co/storage/v1/s3"

    def test_upload_file_supabase_url(self, mock_s3_client):
        """Test upload_file generates correct Supabase URL."""
        with patch('boto3.client', return_value=mock_s3_client):
            from agents.executor_agent.s3_uploader import S3Uploader

            uploader = S3Uploader(
                endpoint_url="https://abc123.supabase.co/storage/v1/s3",
                bucket_name="test-bucket",
                aws_access_key_id="test-key",
                aws_secret_access_key="test-secret"
            )

            url = uploader.upload_file("/tmp/test.csv", "reports/2024/test.csv")

            assert "abc123.supabase.co" in url
            assert "test-bucket" in url
            assert "reports/2024/test.csv" in url
            mock_s3_client.upload_file.assert_called_once()

    def test_upload_file_standard_s3_url(self, mock_s3_client):
        """Test upload_file generates correct standard S3 URL."""
        with patch('boto3.client', return_value=mock_s3_client):
            from agents.executor_agent.s3_uploader import S3Uploader

            uploader = S3Uploader(
                endpoint_url="https://s3.amazonaws.com",
                bucket_name="my-bucket",
                aws_access_key_id="test-key",
                aws_secret_access_key="test-secret"
            )

            url = uploader.upload_file("/tmp/test.csv", "reports/test.csv")

            assert url == "https://s3.amazonaws.com/my-bucket/reports/test.csv"

    def test_upload_file_error(self, mock_s3_client):
        """Test upload_file handles upload errors."""
        mock_s3_client.upload_file.side_effect = Exception("Upload failed")

        with patch('boto3.client', return_value=mock_s3_client):
            from agents.executor_agent.s3_uploader import S3Uploader

            uploader = S3Uploader(
                endpoint_url="https://test.supabase.co/storage/v1/s3",
                bucket_name="test-bucket",
                aws_access_key_id="test-key",
                aws_secret_access_key="test-secret"
            )

            with pytest.raises(Exception, match="Upload failed"):
                uploader.upload_file("/tmp/test.csv", "reports/test.csv")

    def test_get_presigned_url(self, mock_s3_client):
        """Test presigned URL generation."""
        with patch('boto3.client', return_value=mock_s3_client):
            from agents.executor_agent.s3_uploader import S3Uploader

            uploader = S3Uploader(
                endpoint_url="https://test.supabase.co/storage/v1/s3",
                bucket_name="test-bucket",
                aws_access_key_id="test-key",
                aws_secret_access_key="test-secret"
            )

            url = uploader.get_presigned_url("reports/test.csv", expiration=3600)

            assert url == "https://example.com/presigned-url"
            mock_s3_client.generate_presigned_url.assert_called_once()

    def test_download_file(self, mock_s3_client):
        """Test file download from S3."""
        with patch('boto3.client', return_value=mock_s3_client):
            from agents.executor_agent.s3_uploader import S3Uploader

            uploader = S3Uploader(
                endpoint_url="https://test.supabase.co/storage/v1/s3",
                bucket_name="test-bucket",
                aws_access_key_id="test-key",
                aws_secret_access_key="test-secret"
            )

            uploader.download_file("reports/test.csv", "/tmp/local.csv")

            mock_s3_client.download_file.assert_called_once_with(
                "test-bucket", "reports/test.csv", "/tmp/local.csv"
            )

    def test_download_file_error(self, mock_s3_client):
        """Test download_file handles download errors."""
        mock_s3_client.download_file.side_effect = Exception("Download failed")

        with patch('boto3.client', return_value=mock_s3_client):
            from agents.executor_agent.s3_uploader import S3Uploader

            uploader = S3Uploader(
                endpoint_url="https://test.supabase.co/storage/v1/s3",
                bucket_name="test-bucket",
                aws_access_key_id="test-key",
                aws_secret_access_key="test-secret"
            )

            with pytest.raises(Exception, match="Download failed"):
                uploader.download_file("nonexistent.csv", "/tmp/local.csv")

    def test_ensure_bucket_exists_creates_bucket(self, mock_s3_client):
        """Test bucket creation when bucket does not exist."""
        from botocore.exceptions import ClientError

        mock_s3_client.head_bucket.side_effect = ClientError(
            {'Error': {'Code': '404', 'Message': 'Not Found'}},
            'HeadBucket'
        )

        with patch('boto3.client', return_value=mock_s3_client):
            from agents.executor_agent.s3_uploader import S3Uploader

            uploader = S3Uploader(
                endpoint_url="https://test.supabase.co/storage/v1/s3",
                bucket_name="new-bucket",
                aws_access_key_id="test-key",
                aws_secret_access_key="test-secret"
            )

            mock_s3_client.create_bucket.assert_called_once_with(Bucket="new-bucket")
