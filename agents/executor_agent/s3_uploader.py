"""S3/Supabase Storage uploader for query results."""

import logging
import os
from typing import Optional
import boto3
from botocore.exceptions import ClientError
from botocore.config import Config

logger = logging.getLogger(__name__)


class S3Uploader:
    """Upload CSV files to S3 or Supabase Storage (S3-compatible)."""

    def __init__(
        self,
        endpoint_url: str,
        bucket_name: str = "rag-reports",
        aws_access_key_id: Optional[str] = None,
        aws_secret_access_key: Optional[str] = None,
        region: str = "us-east-1"
    ):
        """Initialize S3 uploader.
        
        Args:
            endpoint_url: S3 endpoint URL (Supabase or AWS S3)
            bucket_name: S3 bucket name
            aws_access_key_id: Access key
            aws_secret_access_key: Secret key
            region: AWS region
        """
        self.bucket_name = bucket_name
        self.endpoint_url = endpoint_url
        
        # Initialize S3 client with custom endpoint
        self.s3_client = boto3.client(
            's3',
            endpoint_url=endpoint_url,
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            region_name=region,
            config=Config(
                signature_version='s3v4',
                s3={'addressing_style': 'path'}  # Required for Supabase
            )
        )
        
        logger.info(f"S3Uploader initialized for bucket: {bucket_name}")
        
        # Verify bucket exists
        self._ensure_bucket_exists()

    def _ensure_bucket_exists(self):
        """Ensure the S3 bucket exists, create if not."""
        try:
            self.s3_client.head_bucket(Bucket=self.bucket_name)
            logger.info(f"Bucket {self.bucket_name} exists")
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == '404':
                logger.info(f"Bucket {self.bucket_name} not found, creating...")
                try:
                    self.s3_client.create_bucket(Bucket=self.bucket_name)
                    logger.info(f"Bucket {self.bucket_name} created")
                except Exception as create_error:
                    logger.error(f"Failed to create bucket: {create_error}")
            else:
                logger.error(f"Error checking bucket: {e}")

    def upload_file(self, file_path: str, s3_key: str) -> str:
        """Upload file to S3/Supabase Storage.
        
        Args:
            file_path: Local file path
            s3_key: S3 object key (path in bucket)
            
        Returns:
            Public URL of uploaded file
        """
        try:
            self.s3_client.upload_file(file_path, self.bucket_name, s3_key)
            
            # Generate public URL for Supabase
            # Format: https://PROJECT.supabase.co/storage/v1/object/public/BUCKET/KEY
            if 'supabase.co' in self.endpoint_url:
                # Extract project ID from endpoint
                project_id = self.endpoint_url.split('//')[1].split('.')[0]
                url = f"https://{project_id}.supabase.co/storage/v1/object/public/{self.bucket_name}/{s3_key}"
            else:
                # Standard S3 URL
                url = f"{self.endpoint_url}/{self.bucket_name}/{s3_key}"
            
            logger.info(f"Uploaded {file_path} to {url}")
            return url
            
        except Exception as e:
            logger.error(f"Failed to upload file: {e}")
            raise

    def get_presigned_url(self, s3_key: str, expiration: int = 3600) -> str:
        """Generate presigned URL for S3 object.
        
        Args:
            s3_key: S3 object key
            expiration: URL expiration time in seconds
            
        Returns:
            Presigned URL
        """
        try:
            url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': self.bucket_name, 'Key': s3_key},
                ExpiresIn=expiration
            )
            return url
        except Exception as e:
            logger.error(f"Failed to generate presigned URL: {e}")
            raise

    def download_file(self, s3_key: str, local_path: str):
        """Download file from S3/Supabase Storage.
        
        Args:
            s3_key: S3 object key
            local_path: Local file path to save
        """
        try:
            self.s3_client.download_file(self.bucket_name, s3_key, local_path)
            logger.info(f"Downloaded {s3_key} to {local_path}")
        except Exception as e:
            logger.error(f"Failed to download file: {e}")
            raise