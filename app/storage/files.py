import os
import shutil
from typing import BinaryIO
from .interface import FileStorageInterface
from app.core.config import S3_BUCKET_NAME, S3_DOCUMENT_PREFIX, LOCAL_STORAGE_PATH
# Lazily import boto3 to avoid hard dependency if just local

class S3FileStorage(FileStorageInterface):
    def __init__(self):
        import boto3
        self.s3 = boto3.client("s3")
        self.bucket = S3_BUCKET_NAME

    def save_file(self, path: str, content: bytes, content_type: str = "application/octet-stream") -> str:
        key = f"{S3_DOCUMENT_PREFIX}/{path}"
        self.s3.put_object(Bucket=self.bucket, Key=key, Body=content, ContentType=content_type)
        return f"s3://{self.bucket}/{key}"

    def read_file(self, path: str) -> bytes:
        # Check if path is full s3 URI or relative
        if path.startswith("s3://"):
            # extract key
            # s3://bucket/key...
            parts = path.replace(f"s3://{self.bucket}/", "")
            key = parts
        else:
            key = f"{S3_DOCUMENT_PREFIX}/{path}"
        
        response = self.s3.get_object(Bucket=self.bucket, Key=key)
        return response["Body"].read()

    def delete_file(self, path: str) -> None:
         if path.startswith("s3://"):
             parts = path.replace(f"s3://{self.bucket}/", "")
             key = parts
         else:
             key = f"{S3_DOCUMENT_PREFIX}/{path}"
         self.s3.delete_object(Bucket=self.bucket, Key=key)

    def exists(self, path: str) -> bool:
        if path.startswith("s3://"):
             parts = path.replace(f"s3://{self.bucket}/", "")
             key = parts
        else:
             key = f"{S3_DOCUMENT_PREFIX}/{path}"
        try:
            self.s3.head_object(Bucket=self.bucket, Key=key)
            return True
        except:
            return False

class LocalFileStorage(FileStorageInterface):
    def __init__(self):
        self.base_path = os.path.join(LOCAL_STORAGE_PATH, "notes")
        os.makedirs(self.base_path, exist_ok=True)

    def _get_abs_path(self, path: str):
        # Remove schemes if present
        if path.startswith("local://"):
            path = path.replace("local://", "")
        # Secure join? For now simple join
        return os.path.join(self.base_path, path)

    def save_file(self, path: str, content: bytes, content_type: str = "application/octet-stream") -> str:
        abs_path = self._get_abs_path(path)
        os.makedirs(os.path.dirname(abs_path), exist_ok=True)
        with open(abs_path, "wb") as f:
            f.write(content)
        return f"local://{path}"

    def read_file(self, path: str) -> bytes:
        abs_path = self._get_abs_path(path)
        if not os.path.exists(abs_path):
            raise FileNotFoundError(f"File not found: {abs_path}")
        with open(abs_path, "rb") as f:
            return f.read()

    def delete_file(self, path: str) -> None:
        abs_path = self._get_abs_path(path)
        if os.path.exists(abs_path):
            os.remove(abs_path)
    
    def exists(self, path: str) -> bool:
        abs_path = self._get_abs_path(path)
        return os.path.exists(abs_path)
