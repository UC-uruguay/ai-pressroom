"""
Storage abstraction for episode files.
Supports local filesystem and S3/R2.
"""
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional
import shutil

from ..shared.logger import get_logger
from ..shared.settings import get_settings

logger = get_logger(__name__)


class StorageProvider(ABC):
    """Abstract storage provider."""

    @abstractmethod
    def upload(self, local_path: Path, remote_key: str) -> str:
        """
        Upload file to storage.

        Args:
            local_path: Local file path
            remote_key: Remote key/path

        Returns:
            Public URL of uploaded file
        """
        pass

    @abstractmethod
    def get_url(self, remote_key: str) -> str:
        """
        Get public URL for a file.

        Args:
            remote_key: Remote key/path

        Returns:
            Public URL
        """
        pass


class LocalStorageProvider(StorageProvider):
    """Local filesystem storage."""

    def __init__(self, base_dir: Path, public_base_url: str):
        """
        Initialize local storage.

        Args:
            base_dir: Base directory for storage
            public_base_url: Base URL for public access
        """
        self.base_dir = Path(base_dir)
        self.public_base_url = public_base_url.rstrip('/')
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def upload(self, local_path: Path, remote_key: str) -> str:
        """
        Copy file to local storage.

        Args:
            local_path: Local file path
            remote_key: Relative path in storage

        Returns:
            Public URL
        """
        target_path = self.base_dir / remote_key
        target_path.parent.mkdir(parents=True, exist_ok=True)

        # Copy file
        shutil.copy2(local_path, target_path)
        logger.info(f"Uploaded to local storage: {remote_key}")

        return self.get_url(remote_key)

    def get_url(self, remote_key: str) -> str:
        """Get public URL."""
        return f"{self.public_base_url}/{remote_key}"


class S3StorageProvider(StorageProvider):
    """
    S3/R2 storage provider.

    TODO: Implement S3 upload functionality
    - Install: pip install boto3
    - Features to implement:
      * S3 client initialization with credentials
      * File upload with public-read ACL
      * URL generation (bucket URL or CloudFront)
      * Error handling and retries
      * Multipart upload for large files
    """

    def __init__(
        self,
        bucket: str,
        endpoint: Optional[str] = None,
        access_key: Optional[str] = None,
        secret_key: Optional[str] = None,
        public_base_url: Optional[str] = None
    ):
        """
        Initialize S3 storage.

        Args:
            bucket: S3 bucket name
            endpoint: S3 endpoint URL (for R2 or compatible services)
            access_key: AWS access key
            secret_key: AWS secret key
            public_base_url: Custom public URL (if using CDN)
        """
        self.bucket = bucket
        self.endpoint = endpoint
        self.access_key = access_key
        self.secret_key = secret_key
        self.public_base_url = public_base_url

        logger.warning("S3 storage is not yet implemented, will fall back to local")

        # TODO: Initialize boto3 client
        # self.s3_client = boto3.client(
        #     's3',
        #     endpoint_url=endpoint,
        #     aws_access_key_id=access_key,
        #     aws_secret_access_key=secret_key
        # )

    def upload(self, local_path: Path, remote_key: str) -> str:
        """Upload to S3 (not implemented)."""
        raise NotImplementedError(
            "S3 storage is not yet implemented. "
            "Please use 'local' storage or implement this method."
        )

        # TODO: Implementation
        # self.s3_client.upload_file(
        #     str(local_path),
        #     self.bucket,
        #     remote_key,
        #     ExtraArgs={'ACL': 'public-read', 'ContentType': self._get_content_type(local_path)}
        # )
        # return self.get_url(remote_key)

    def get_url(self, remote_key: str) -> str:
        """Get public URL."""
        if self.public_base_url:
            return f"{self.public_base_url}/{remote_key}"
        elif self.endpoint:
            return f"{self.endpoint}/{self.bucket}/{remote_key}"
        else:
            return f"https://{self.bucket}.s3.amazonaws.com/{remote_key}"


def create_storage_provider() -> StorageProvider:
    """
    Create storage provider from settings.

    Returns:
        StorageProvider instance
    """
    settings = get_settings()

    if settings.storage.driver == "local":
        return LocalStorageProvider(
            base_dir=settings.storage.local_base,
            public_base_url=settings.storage.public_base_url
        )
    elif settings.storage.driver == "s3":
        return S3StorageProvider(
            bucket=settings.s3_bucket,
            endpoint=settings.s3_endpoint,
            access_key=settings.s3_access_key,
            secret_key=settings.s3_secret_key,
            public_base_url=settings.storage.public_base_url
        )
    else:
        raise ValueError(f"Unknown storage driver: {settings.storage.driver}")
