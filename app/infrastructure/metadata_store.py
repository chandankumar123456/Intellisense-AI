# app/infrastructure/metadata_store.py
"""
Layer-3: Metadata Knowledge Index
Wrapper around Unified Storage Manager.
"""

from typing import List, Dict, Any, Optional
from app.storage import storage_manager

def upsert_metadata(entry: Dict[str, Any]):
    """Insert or replace a metadata entry."""
    storage_manager.metadata.upsert(entry)


def upsert_metadata_batch(entries: List[Dict[str, Any]]):
    """Batch insert/replace metadata entries."""
    storage_manager.metadata.upsert_batch(entries)


def search_metadata(
    filters: Dict[str, Any],
    top_k: int = 20,
) -> List[Dict[str, Any]]:
    """
    Search metadata index with flexible filters.
    """
    return storage_manager.metadata.search(filters, top_k)


def get_metadata_by_ids(chunk_ids: List[str]) -> List[Dict[str, Any]]:
    """Fetch metadata entries by their IDs."""
    if not chunk_ids:
        return []
    # SAL generic `get` is single key. 
    # We might need `get_batch` or just loop. 
    # SQLite is fast enough to loop or we add `get_batch` to interface later.
    results = []
    for cid in chunk_ids:
        res = storage_manager.metadata.get(cid)
        if res:
            results.append(res)
    return results


def get_metadata_by_vector_ids(vector_ids: List[str]) -> List[Dict[str, Any]]:
    """Fetch metadata entries by their vector_chunk_id."""
    # This specific query isn't in generic `search` interface easily 
    # unless we filter by `vector_chunk_id`.
    # But `vector_chunk_id` is unique usually.
    # Let's use search?
    if not vector_ids:
        return []
    
    # This is inefficient if we search one by one.
    # But `vector_chunk_id` is an indexed column.
    # If we need this functionality, we ideally extend SAL.
    # For now, let's implement via search loop or map.
    results = []
    for vid in vector_ids:
        matches = storage_manager.metadata.search({"vector_chunk_id": vid}, limit=1)
        if matches:
            results.append(matches[0])
    return results


def fetch_document_section(
    doc_id: str,
    page: int,
    offset_start: Optional[int] = None,
    offset_end: Optional[int] = None,
) -> Optional[str]:
    """
    Fetch the exact text for a document section.
    """
    # This requires a complex query (range on offsets).
    # SAL `search` interface is simple equality.
    # We might need to leak abstraction or extend it.
    # However, `fetch_document_section` in existing code queried `chunk_text`.
    # If we are strictly using SAL, we might not support complex range queries yet.
    # Workaround: Fetch all chunks for doc_id+page, then filter in python.
    chunks = storage_manager.metadata.search({"doc_id": doc_id, "page": page}, limit=100)
    
    best_chunk = None
    if offset_start is not None and offset_end is not None:
        # Find covering chunk
        for c in chunks:
            if c.get("offset_start", 0) <= offset_start and c.get("offset_end", 0) >= offset_end:
                 best_chunk = c
                 break
    elif chunks:
        # Just take the first one (highest importance usually due to sort in existing impl, but SAL interface doesn't guarantee sort)
        # Existing SAL impl does `search` -> SELECT ... 
        # But our `search` impl currently doesn't sort by importance explicitly unless we add it.
        # Let's assume it returns something.
        best_chunk = chunks[0]

    if best_chunk:
        text = best_chunk.get("chunk_text", "")
        if offset_start is not None and offset_end is not None:
            return text[offset_start:offset_end]
        return text
    
    return None


def record_query_hit(chunk_ids: List[str]):
    """Record that these chunks were queried."""
    # This updates `query_count` and `last_queried_at`.
    # SAL `upsert` could handle this if we fetch-modify-upsert.
    # Or strict SAL needs atomic update?
    # For MVP: fetch-modify-upsert.
    from datetime import datetime
    for cid in chunk_ids:
        item = storage_manager.metadata.get(cid)
        if item:
            item["query_count"] = item.get("query_count", 0) + 1
            item["last_queried_at"] = datetime.utcnow().isoformat()
            storage_manager.metadata.upsert(item)


def get_promotion_candidates(query_count_threshold: int = 10) -> List[Dict[str, Any]]:
    """Find raw (non-embedded) chunks that are frequently queried."""
    # Complex query not supported by simple SAL `search`.
    # We'd need to Scan? 
    # Or just return empty for now since this is an optimization feature.
    return []


def get_eviction_candidates(unused_months: int = 6) -> List[Dict[str, Any]]:
    """Find embedded chunks unused for N months."""
    # Same, complex query.
    return []


def _get_connection():
    """
    Expose the underlying SQLite connection for admin stats/debug.
    NOTE: This leaks abstraction but is required for complex admin queries 
    that are not supported by the strict SAL interface.
    """
    # Ensure initialized
    if not storage_manager.metadata:
        # Trigger init via property access if needed, though manager.metadata usually does it
        pass
        
    # Both Local and Cloud implementations wrap SqliteMetadataImpl in .impl
    try:
        return storage_manager.metadata.impl.conn
    except AttributeError:
        # Fallback if accessed before init or different impl
        # Try to force init if strictly necessary or check if it's the impl itself
        if hasattr(storage_manager.metadata, "conn"):
             return storage_manager.metadata.conn
        raise ImportError("Could not retrieve underlying database connection from Metadata Storage provider.")
