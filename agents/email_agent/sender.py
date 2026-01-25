"""Email Agent implementation."""

import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from typing import Dict, Any, Optional
import pandas as pd
from .templates import EMAIL_TEMPLATE_HTML, EMAIL_TEMPLATE_PLAIN

logger = logging.getLogger(__name__)


class EmailAgent:
    """Email Agent for sending query results."""

    def __init__(
        self,
        smtp_host: str,
        smtp_port: int,
        smtp_user: str,
        smtp_password: str,
        from_email: Optional[str] = None
    ):
        """Initialize Email Agent.
        
        Args:
            smtp_host: SMTP server host
            smtp_port: SMTP server port
            smtp_user: SMTP username
            smtp_password: SMTP password
            from_email: Sender email (defaults to smtp_user)
        """
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.smtp_user = smtp_user
        self.smtp_password = smtp_password
        self.from_email = from_email or smtp_user
        logger.info(f"EmailAgent initialized for {self.from_email}")

    def send_results(
        self,
        to_email: str,
        user_query: str,
        s3_url: str,
        metadata: Dict[str, Any],
        csv_path: Optional[str] = None,
        preview_df: Optional[pd.DataFrame] = None
    ):
        """Send query results via email.
        
        Args:
            to_email: Recipient email address
            user_query: Original user query
            s3_url: S3 URL of results CSV
            metadata: Query execution metadata
            csv_path: Local path to CSV for attachment (optional)
            preview_df: DataFrame preview for email body (optional)
        """
        logger.info(f"Sending results email to {to_email}")

        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = f"Query Results: {user_query[:50]}..."
            msg['From'] = self.from_email
            msg['To'] = to_email

            # Generate preview table HTML
            preview_html = ""
            if preview_df is not None:
                preview_html = f"""
                <h3>Preview (first {len(preview_df)} rows):</h3>
                {preview_df.to_html(index=False, border=1, classes='preview-table')}
                <p><em>See attachment for full results</em></p>
                """

            # Format email body
            html_body = EMAIL_TEMPLATE_HTML.format(
                user_query=user_query,
                row_count=metadata.get('row_count', 'N/A'),
                column_count=metadata.get('column_count', 'N/A'),
                execution_time=f"{metadata.get('execution_time_seconds', 0):.2f}",
                download_url=s3_url,
                preview_table=preview_html
            )

            plain_body = EMAIL_TEMPLATE_PLAIN.format(
                user_query=user_query,
                row_count=metadata.get('row_count', 'N/A'),
                column_count=metadata.get('column_count', 'N/A'),
                execution_time=f"{metadata.get('execution_time_seconds', 0):.2f}",
                download_url=s3_url
            )

            # Attach both versions
            msg.attach(MIMEText(plain_body, 'plain'))
            msg.attach(MIMEText(html_body, 'html'))

            # Attach CSV if provided
            if csv_path:
                with open(csv_path, 'rb') as f:
                    attachment = MIMEApplication(f.read(), _subtype='csv')
                    attachment.add_header(
                        'Content-Disposition',
                        'attachment',
                        filename='query_results.csv'
                    )
                    msg.attach(attachment)

            # Send email
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_password)
                server.send_message(msg)

            logger.info(f"Email sent successfully to {to_email}")

        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            raise

    def send_error_notification(
        self,
        to_email: str,
        user_query: str,
        error_message: str
    ):
        """Send error notification email.
        
        Args:
            to_email: Recipient email address
            user_query: Original user query
            error_message: Error description
        """
        logger.info(f"Sending error notification to {to_email}")

        try:
            msg = MIMEText(f"""
Query Execution Failed
=====================

Your Query:
{user_query}

Error:
{error_message}

Please try rephrasing your query or contact support.

---
Agentic RAG Analytics System
            """)
            
            msg['Subject'] = f"Query Failed: {user_query[:50]}..."
            msg['From'] = self.from_email
            msg['To'] = to_email

            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_password)
                server.send_message(msg)

            logger.info(f"Error notification sent to {to_email}")

        except Exception as e:
            logger.error(f"Failed to send error notification: {e}")
            raise