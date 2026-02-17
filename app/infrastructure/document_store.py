# app/infrastructure/document_store.py
"""
Layer-2: Document Storage
Local filesystem-based document store. Full text stored with page offsets.
Pluggable for S3/R2 in production.
"""

import os
import json
from typing import Optional, Dict, Any
from app.core.config import DOCUMENT_STORAGE_PATH
from app.core.logging import log_info, log_error


def _ensure_dir():
    os.makedirs(DOCUMENT_STORAGE_PATH, exist_ok=True)


def store_document(doc_id: str, full_text: str, metadata: Dict[str, Any] = None):
    """
    Store a full document's text and metadata.
    Creates a directory per doc_id with text.txt and meta.json.
    """
    _ensure_dir()
    doc_dir = os.path.join(DOCUMENT_STORAGE_PATH, doc_id)
    os.makedirs(doc_dir, exist_ok=True)

    with open(os.path.join(doc_dir, "text.txt"), "w", encoding="utf-8") as f:
        f.write(full_text)

    if metadata:
        with open(os.path.join(doc_dir, "meta.json"), "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2, default=str)

    log_info(f"Stored document {doc_id} ({len(full_text)} chars)")


def fetch_document_text(doc_id: str) -> Optional[str]:
    """Retrieve the full text of a stored document."""
    path = os.path.join(DOCUMENT_STORAGE_PATH, doc_id, "text.txt")
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def fetch_document_section_from_store(
    doc_id: str,
    page: int = 0,
    offset_start: Optional[int] = None,
    offset_end: Optional[int] = None,
) -> Optional[str]:
    """
    Fetch a section of a stored document.
    For unstructured docs (single page), page is treated as 0.
    offset_start / offset_end are character offsets into full text.
    """
    text = fetch_document_text(doc_id)
    if text is None:
        return None

    if offset_start is not None and offset_end is not None:
        return text[offset_start:offset_end]
    elif offset_start is not None:
        return text[offset_start:]

    return text


def fetch_document_metadata(doc_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve metadata for a stored document."""
    path = os.path.join(DOCUMENT_STORAGE_PATH, doc_id, "meta.json")
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def document_exists(doc_id: str) -> bool:
    """Check whether a document is stored."""
    return os.path.exists(os.path.join(DOCUMENT_STORAGE_PATH, doc_id, "text.txt"))


def delete_document(doc_id: str):
    """Remove a document from storage."""
    import shutil
    doc_dir = os.path.join(DOCUMENT_STORAGE_PATH, doc_id)
    if os.path.exists(doc_dir):
        shutil.rmtree(doc_dir)
        log_info(f"Deleted document {doc_id}")
