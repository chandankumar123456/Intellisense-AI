# app/infrastructure/s3_client.py
"""
Centralized AWS S3 client for document storage.
All S3 operations go through this module for consistent error handling,
retry logic, and server-side encryption.
"""

import json
import threading
from typing import Optional, Dict, Any

import boto3
from botocore.config import Config as BotoConfig
from botocore.exceptions import ClientError

from app.core.config import AWS_REGION, S3_BUCKET_NAME, S3_DOCUMENT_PREFIX
from app.core.logging import log_info, log_error

# ── Lazy, thread-safe singleton client ──

_lock = threading.Lock()
_s3_client = None


def _get_client():
    """Return a shared boto3 S3 client (created once, thread-safe)."""
    global _s3_client
    if _s3_client is None:
        with _lock:
            if _s3_client is None:
                _s3_client = boto3.client(
                    "s3",
                    region_name=AWS_REGION,
                    config=BotoConfig(
                        retries={"max_attempts": 3, "mode": "adaptive"},
                    ),
                )
    return _s3_client


def _bucket() -> str:
    if not S3_BUCKET_NAME:
        raise RuntimeError(
            "S3_BUCKET_NAME is not set. "
            "Add it to your .env or set STORAGE_BACKEND=local."
        )
    return S3_BUCKET_NAME


def _doc_key(doc_id: str, *parts: str) -> str:
    """Build an S3 key like  documents/<doc_id>/text.txt"""
    return "/".join([S3_DOCUMENT_PREFIX, doc_id, *parts])


# ── Upload helpers ──


def upload_bytes(
    key: str,
    data: bytes,
    content_type: str = "application/octet-stream",
) -> None:
    """PUT an object with SSE-S3 encryption."""
    _get_client().put_object(
        Bucket=_bucket(),
        Key=key,
        Body=data,
        ContentType=content_type,
        ServerSideEncryption="AES256",
    )
    log_info(f"S3 upload: {key} ({len(data)} bytes)")


def upload_text(key: str, text: str) -> None:
    """Upload a UTF-8 text object."""
    upload_bytes(key, text.encode("utf-8"), content_type="text/plain; charset=utf-8")


def upload_json(key: str, obj: Dict[str, Any]) -> None:
    """Serialize a dict to JSON and upload."""
    data = json.dumps(obj, indent=2, default=str).encode("utf-8")
    upload_bytes(key, data, content_type="application/json")


# ── Download helpers ──


def download_text(key: str) -> Optional[str]:
    """Download an object and decode as UTF-8. Returns None if not found."""
    try:
        resp = _get_client().get_object(Bucket=_bucket(), Key=key)
        return resp["Body"].read().decode("utf-8")
    except ClientError as e:
        if e.response["Error"]["Code"] in ("NoSuchKey", "404"):
            return None
        log_error(f"S3 download error for {key}: {e}")
        raise


def download_json(key: str) -> Optional[Dict[str, Any]]:
    """Download and parse a JSON object. Returns None if not found."""
    text = download_text(key)
    if text is None:
        return None
    return json.loads(text)


def download_bytes(key: str) -> Optional[bytes]:
    """Download raw bytes. Returns None if not found."""
    try:
        resp = _get_client().get_object(Bucket=_bucket(), Key=key)
        return resp["Body"].read()
    except ClientError as e:
        if e.response["Error"]["Code"] in ("NoSuchKey", "404"):
            return None
        log_error(f"S3 download error for {key}: {e}")
        raise


# ── Existence / Deletion ──


def object_exists(key: str) -> bool:
    """HEAD check — returns True if the object exists."""
    try:
        _get_client().head_object(Bucket=_bucket(), Key=key)
        return True
    except ClientError:
        return False


def delete_prefix(prefix: str) -> int:
    """Delete all objects under a key prefix. Returns count deleted."""
    client = _get_client()
    bucket = _bucket()
    deleted = 0

    paginator = client.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
        objects = page.get("Contents", [])
        if not objects:
            continue
        delete_req = {"Objects": [{"Key": o["Key"]} for o in objects]}
        client.delete_objects(Bucket=bucket, Delete=delete_req)
        deleted += len(objects)

    if deleted:
        log_info(f"S3 delete: {deleted} objects under {prefix}")
    return deleted
