"""Email Agent for sending query results via email."""

import logging
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from typing import Optional
import pandas as pd

from .templates import EMAIL_TEMPLATE_HTML, EMAIL_TEMPLATE_PLAIN

logger = logging.getLogger(__name__)


class EmailAgent:
    """Send query results via email."""

    def __init__(
        self,
        smtp_host: str,
        smtp_port: int,
        smtp_user: str,
        smtp_password: str
    ):
        """Initialize Email Agent.
        
        Args:
            smtp_host: SMTP server host
            smtp_port: SMTP server port
            smtp_user: SMTP username
            smtp_password: SMTP password
        """
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.smtp_user = smtp_user
        self.smtp_password = smtp_password
        
        logger.info("EmailAgent initialized")

    def send_results(
        self,
        to_email: str,
        user_query: str,
        s3_url: str,
        metadata: dict,
        preview_df: Optional[pd.DataFrame] = None,
        csv_attachment_path: Optional[str] = None
    ):
        """Send query results via email.
        
        Args:
            to_email: Recipient email address
            user_query: Original user query
            s3_url: S3 URL for results CSV
            metadata: Query execution metadata
            preview_df: DataFrame with preview rows (optional)
            csv_attachment_path: Local path to CSV file for attachment (optional)
        """
        try:
            logger.info(f"Sending results email to {to_email}")

            message = MIMEMultipart('alternative')
            message['Subject'] = f"Query Results: {user_query[:50]}..."
            message['From'] = self.smtp_user
            message['To'] = to_email

            preview_html = self._generate_preview_table(preview_df) if preview_df is not None else ""

            html_body = EMAIL_TEMPLATE_HTML.format(
                query=user_query,
                row_count=metadata.get('row_count', 'N/A'),
                column_count=metadata.get('column_count', 'N/A'),
                execution_time=metadata.get('execution_time_seconds', 'N/A'),
                preview_table=preview_html,
                download_url=s3_url,
                sql_url=metadata.get('sql_s3_url', '#')
            )

            plain_body = EMAIL_TEMPLATE_PLAIN.format(
                query=user_query,
                row_count=metadata.get('row_count', 'N/A'),
                column_count=metadata.get('column_count', 'N/A'),
                execution_time=metadata.get('execution_time_seconds', 'N/A'),
                download_url=s3_url,
                sql_url=metadata.get('sql_s3_url', '#')
            )

            part1 = MIMEText(plain_body, 'plain')
            part2 = MIMEText(html_body, 'html')

            message.attach(part1)
            message.attach(part2)

            if csv_attachment_path and os.path.exists(csv_attachment_path):
                with open(csv_attachment_path, 'rb') as f:
                    csv_data = f.read()

                csv_part = MIMEBase('application', 'octet-stream')
                csv_part.set_payload(csv_data)
                encoders.encode_base64(csv_part)
                csv_part.add_header(
                    'Content-Disposition',
                    f'attachment; filename={os.path.basename(csv_attachment_path)}'
                )
                message.attach(csv_part)

                os.remove(csv_attachment_path)
                logger.info(f"Attached and removed local CSV: {csv_attachment_path}")

            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_password)
                server.send_message(message)

            logger.info(f"Email sent successfully to {to_email}")

        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            raise

    def _generate_preview_table(self, df: Optional[pd.DataFrame]) -> str:
        """Generate HTML table from DataFrame.
        
        Args:
            df: DataFrame to convert
            
        Returns:
            HTML table string
        """
        if df is None or df.empty:
            return "<p>No preview available</p>"

        html = '<table style="border-collapse: collapse; width: 100%; margin: 20px 0;">'
        html += '<thead><tr style="background-color: #f0f0f0;">'

        for col in df.columns:
            html += f'<th style="border: 1px solid #ddd; padding: 8px; text-align: left;">{col}</th>'
        html += '</tr></thead><tbody>'

        for _, row in df.iterrows():
            html += '<tr>'
            for val in row:
                html += f'<td style="border: 1px solid #ddd; padding: 8px;">{val}</td>'
            html += '</tr>'

        html += '</tbody></table>'
        return html

    def send_error_notification(
        self,
        to_email: str,
        user_query: str,
        error: str
    ):
        """Send error notification email.
        
        Args:
            to_email: Recipient email address
            user_query: Original user query
            error: Error message
        """
        try:
            logger.info(f"Sending error notification to {to_email}")

            message = MIMEMultipart('alternative')
            message['Subject'] = f"Query Failed: {user_query[:50]}..."
            message['From'] = self.smtp_user
            message['To'] = to_email

            html_body = f"""
            <html>
            <body>
                <h2>Query Execution Failed</h2>
                <p><strong>Your Query:</strong> {user_query}</p>
                <p><strong>Error:</strong> {error}</p>
                <p>Please try again or contact support if the issue persists.</p>
            </body>
            </html>
            """

            plain_body = f"""
            Query Execution Failed
            
            Your Query: {user_query}
            Error: {error}
            
            Please try again or contact support if the issue persists.
            """

            part1 = MIMEText(plain_body, 'plain')
            part2 = MIMEText(html_body, 'html')

            message.attach(part1)
            message.attach(part2)

            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_password)
                server.send_message(message)

            logger.info(f"Error notification sent to {to_email}")

        except Exception as e:
            logger.error(f"Failed to send error notification: {e}")
