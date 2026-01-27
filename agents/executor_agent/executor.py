"""Executor Agent for SQL query execution and result storage."""

import logging
import os
import re
import hashlib
from datetime import datetime
from typing import Tuple, Dict, Any, Optional
import psycopg2
from psycopg2 import extras
import pandas as pd

from .s3_uploader import S3Uploader

logger = logging.getLogger(__name__)


class ExecutorAgent:
    """Execute SQL queries and store results in S3."""

    def __init__(
        self,
        db_host: str,
        db_port: int,
        db_name: str,
        db_user: str,
        db_password: str,
        s3_uploader: S3Uploader,
        query_timeout: int = 30
    ):
        """Initialize Executor Agent.
        
        Args:
            db_host: Database host
            db_port: Database port
            db_name: Database name
            db_user: Database user
            db_password: Database password
            s3_uploader: S3Uploader instance
            query_timeout: Query timeout in seconds
        """
        self.db_config = {
            'host': db_host,
            'port': db_port,
            'database': db_name,
            'user': db_user,
            'password': db_password
        }
        self.s3_uploader = s3_uploader
        self.query_timeout = query_timeout
        
        os.makedirs("./temp_outputs", exist_ok=True)
        logger.info("ExecutorAgent initialized")

    def execute_sql(self, sql_query: str, user_query: str) -> Tuple[str, Dict[str, Any]]:
        """Execute SQL query and store results in S3.
        
        Args:
            sql_query: SQL query to execute
            user_query: Original user query (for metadata)
            
        Returns:
            Tuple of (csv_s3_url, metadata)
            
        Raises:
            Exception: If execution fails
        """
        conn = None
        cursor = None
        
        try:
            # Connect to database
            conn = psycopg2.connect(**self.db_config)
            conn.set_session(readonly=True)
            
            cursor = conn.cursor(cursor_factory=extras.RealDictCursor)
            
            # Set statement timeout
            cursor.execute(f"SET statement_timeout = {self.query_timeout * 1000}")
            
            # Execute query
            logger.info(f"Executing SQL: {sql_query[:100]}...")
            start_time = datetime.now()
            cursor.execute(sql_query)
            execution_time = (datetime.now() - start_time).total_seconds()
            
            # Fetch results
            rows = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description] if cursor.description else []
            
            logger.info(f"Query executed successfully: {len(rows)} rows, {len(columns)} columns, {execution_time:.2f}s")
            
            # Generate filenames
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            query_hash = hashlib.md5(user_query.encode()).hexdigest()[:8]
            base_filename = f"query_{timestamp}_{query_hash}"
            
            # Write CSV
            csv_path, csv_s3_key = self._write_csv(rows, columns, base_filename)
            
            # Write SQL
            sql_path, sql_s3_key = self._write_sql(sql_query, user_query, base_filename)
            
            # Upload both to S3
            csv_url = self.s3_uploader.upload_file(csv_path, csv_s3_key)
            sql_url = self.s3_uploader.upload_file(sql_path, sql_s3_key)
            
            # Clean up local files
            os.remove(csv_path)
            os.remove(sql_path)
            
            # Build metadata
            metadata = {
                'row_count': len(rows),
                'column_count': len(columns),
                'execution_time_seconds': round(execution_time, 2),
                'columns': columns,
                'csv_s3_key': csv_s3_key,
                'csv_s3_url': csv_url,
                'sql_s3_key': sql_s3_key,
                'sql_s3_url': sql_url,
                'timestamp': datetime.now().isoformat()
            }
            
            return csv_url, metadata
            
        except psycopg2.Error as e:
            error_msg = f"Database error: {str(e)}"
            logger.error(error_msg)
            raise Exception(error_msg)
            
        except Exception as e:
            error_msg = f"Execution error: {str(e)}"
            logger.error(error_msg)
            raise Exception(error_msg)
            
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

    def _write_csv(self, rows: list, columns: list, base_filename: str) -> Tuple[str, str]:
        """Write query results to CSV file.
        
        Args:
            rows: Query result rows
            columns: Column names
            base_filename: Base filename without extension
            
        Returns:
            Tuple of (local_csv_path, s3_key)
        """
        sanitized_base = self._normalize_base_filename(base_filename)
        csv_filename = f"{sanitized_base}.csv"
        local_path = f"./temp_outputs/{csv_filename}"
        
        # Convert to DataFrame and write CSV
        df = pd.DataFrame(rows, columns=columns)
        df.to_csv(local_path, index=False)
        
        # Generate S3 key with date-based organization
        s3_key = f"reports/{datetime.now().strftime('%Y/%m/%d')}/{csv_filename}"
        
        logger.info(f"CSV written: {local_path}")
        return local_path, s3_key

    def _write_sql(self, sql_query: str, user_query: str, base_filename: str) -> Tuple[str, str]:
        """Write SQL query to file with metadata.
        
        Args:
            sql_query: SQL query string
            user_query: Original user query
            base_filename: Base filename without extension
            
        Returns:
            Tuple of (local_sql_path, s3_key)
        """
        sanitized_base = self._normalize_base_filename(base_filename)
        sql_filename = f"{sanitized_base}.sql"
        local_path = f"./temp_outputs/{sql_filename}"
        
        # Write SQL with metadata header
        with open(local_path, 'w', encoding='utf-8') as f:
            f.write(f"-- Generated: {datetime.now().isoformat()}\n")
            f.write(f"-- User Query: {user_query}\n")
            f.write(f"--\n\n")
            f.write(sql_query)
            if not sql_query.endswith('\n'):
                f.write('\n')
        
        # Generate S3 key with date-based organization
        s3_key = f"queries/{datetime.now().strftime('%Y/%m/%d')}/{sql_filename}"
        
        logger.info(f"SQL written: {local_path}")
        return local_path, s3_key

    def get_row_preview(self, csv_s3_key: str, num_rows: int = 10) -> Optional[pd.DataFrame]:
        """Download CSV from S3 and return preview DataFrame.
        
        Args:
            csv_s3_key: S3 key for CSV file
            num_rows: Number of rows to preview
            
        Returns:
            DataFrame with preview rows, or None if error
        """
        try:
            # Generate temporary local filename
            temp_filename = f"preview_{os.path.basename(csv_s3_key)}"
            local_path = f"./temp_outputs/{temp_filename}"
            
            # Download from S3
            self.s3_uploader.download_file(csv_s3_key, local_path)
            
            # Read CSV
            df = pd.read_csv(local_path, nrows=num_rows)
            
            # Clean up
            os.remove(local_path)
            
            return df
            
        except Exception as e:
            logger.error(f"Failed to get preview: {e}")
            return None

    def get_full_csv_path(self, csv_s3_key: str) -> Optional[str]:
        """Download full CSV from S3 for email attachment.
        
        Args:
            csv_s3_key: S3 key for CSV file
            
        Returns:
            Local file path, or None if error
        """
        try:
            # Generate local filename
            temp_filename = f"attachment_{os.path.basename(csv_s3_key)}"
            local_path = f"./temp_outputs/{temp_filename}"
            
            # Download from S3
            self.s3_uploader.download_file(csv_s3_key, local_path)
            
            logger.info(f"Downloaded CSV for attachment: {local_path}")
            return local_path
            
        except Exception as e:
            logger.error(f"Failed to download CSV: {e}")
            return None

    def _normalize_base_filename(self, base_filename: str) -> str:
        """Normalize filenames to avoid spaces and ensure query prefix."""
        sanitized = re.sub(r'[^0-9a-zA-Z]+', '_', base_filename).strip('_')
        if not sanitized:
            sanitized = "query"
        sanitized = sanitized.lower()
        if not sanitized.lower().startswith("query"):
            sanitized = f"query_{sanitized}"
        return sanitized
