import os
import boto3
from botocore.exceptions import ClientError
from app.config import settings
from app.models.domain import generate_uuid
import logging

logger = logging.getLogger(__name__)

class StorageProvider:
    def upload_file(self, file_content: bytes, filename: str, content_type: str) -> str:
        raise NotImplementedError

class LocalStorageProvider(StorageProvider):
    def __init__(self, base_dir: str = "./uploads"):
        self.base_dir = base_dir
        os.makedirs(self.base_dir, exist_ok=True)
        
    def upload_file(self, file_content: bytes, filename: str, content_type: str) -> str:
        ext = os.path.splitext(filename)[1]
        secure_name = f"{generate_uuid()}{ext}"
        path = os.path.join(self.base_dir, secure_name)
        with open(path, "wb") as f:
            f.write(file_content)
        return path

class S3StorageProvider(StorageProvider):
    def __init__(self):
        self.s3_client = boto3.client(
            's3',
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_REGION
        )
        self.bucket = settings.S3_BUCKET_NAME
        
    def upload_file(self, file_content: bytes, filename: str, content_type: str) -> str:
        ext = os.path.splitext(filename)[1]
        secure_name = f"{generate_uuid()}{ext}"
        try:
            self.s3_client.put_object(
                Bucket=self.bucket,
                Key=secure_name,
                Body=file_content,
                ContentType=content_type
            )
            return f"s3://{self.bucket}/{secure_name}"
        except ClientError as e:
            logger.error(f"S3 Upload failed: {e}")
            raise Exception("Failed to upload to remote storage")

def get_storage_provider() -> StorageProvider:
    if settings.STORAGE_BACKEND.lower() == "s3":
        if not settings.S3_BUCKET_NAME:
            raise ValueError("S3_BUCKET_NAME is required when STORAGE_BACKEND=s3")
        return S3StorageProvider()
    return LocalStorageProvider()
