"""Executor Agent implementation using psycopg2."""

import logging
import csv
import os
import hashlib
from typing import Dict, Any, Tuple
from datetime import datetime
import psycopg2
from psycopg2 import sql
import pandas as pd
from .s3_uploader import S3Uploader

logger = logging.getLogger(__name__)


class ExecutorAgent:
    """Executor Agent for running SQL queries and uploading results."""

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
            db_host: PostgreSQL host
            db_port: PostgreSQL port
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
        logger.info(f"ExecutorAgent initialized for database: {db_name}")

    def execute_sql(self, sql_query: str, user_query: str) -> Tuple[str, Dict[str, Any]]:
        """Execute SQL query and upload results to S3.
        
        Args:
            sql_query: SQL query to execute
            user_query: Original user query (for naming)
            
        Returns:
            Tuple of (s3_url, metadata)
            - s3_url: S3 URL of uploaded CSV
            - metadata: Dict with row_count, column_count, execution_time
        """
        logger.info(f"Executing SQL: {sql_query[:200]}...")
        
        conn = None
        cursor = None
        start_time = datetime.now()
        
        try:
            # Connect to database
            conn = psycopg2.connect(**self.db_config)
            conn.set_session(readonly=True)  # Read-only session for safety
            cursor = conn.cursor()
            
            # Set statement timeout
            cursor.execute(f"SET statement_timeout = {self.query_timeout * 1000}")  # milliseconds
            
            # Execute query
            cursor.execute(sql_query)
            
            # Fetch results
            rows = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            logger.info(f"Query executed successfully: {len(rows)} rows, {len(columns)} columns, {execution_time:.2f}s")
            
            # Write to CSV
            csv_path, s3_key = self._write_csv(rows, columns, user_query)
            
            # Upload to S3
            s3_url = self.s3_uploader.upload_file(csv_path, s3_key)
            
            # Clean up local file
            os.remove(csv_path)
            
            # Metadata
            metadata = {
                'row_count': len(rows),
                'column_count': len(columns),
                'execution_time_seconds': execution_time,
                'columns': columns,
                's3_key': s3_key
            }
            
            return s3_url, metadata
            
        except psycopg2.Error as e:
            logger.error(f"Database error: {e}")
            raise
        except Exception as e:
            logger.error(f"Executor error: {e}")
            raise
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

    def _write_csv(self, rows: list, columns: list, user_query: str) -> Tuple[str, str]:
        """Write query results to CSV file.
        
        Args:
            rows: Query result rows
            columns: Column names
            user_query: Original user query (for naming)
            
        Returns:
            Tuple of (local_csv_path, s3_key)
        """
        # Generate unique filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        query_hash = hashlib.md5(user_query.encode()).hexdigest()[:8]
        filename = f"query_{timestamp}_{query_hash}.csv"
        
        # Local path
        os.makedirs("./temp_outputs", exist_ok=True)
        local_path = f"./temp_outputs/{filename}"
        
        # S3 key
        s3_key = f"reports/{datetime.now().strftime('%Y/%m/%d')}/{filename}"
        
        # Write CSV
        with open(local_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(columns)  # Header
            writer.writerows(rows)     # Data
        
        logger.info(f"CSV written: {local_path}")
        return local_path, s3_key

    def get_row_preview(self, s3_key: str, num_rows: int = 10) -> pd.DataFrame:
        """Download CSV and return preview as DataFrame.
        
        Args:
            s3_key: S3 object key
            num_rows: Number of rows to preview
            
        Returns:
            Pandas DataFrame with preview
        """
        try:
            # Download to temp location
            temp_path = f"./temp_outputs/preview_{os.path.basename(s3_key)}"
            self.s3_uploader.download_file(s3_key, temp_path)
            
            # Read with pandas
            df = pd.read_csv(temp_path, nrows=num_rows)
            
            # Clean up
            os.remove(temp_path)
            
            return df
        except Exception as e:
            logger.error(f"Error generating preview: {e}")
            raise