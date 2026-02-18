# app/rag/chunker.py
"""
Smart chunking with deduplication for the EviLearn ingestion pipeline.
Enforces: 400-600 tokens per chunk, ~50 token overlap, cosine > 0.92 dedup.
"""

import re
import uuid
import numpy as np
from typing import List, Optional
from app.core.config import (
    CHUNK_SIZE_TOKENS,
    CHUNK_OVERLAP_TOKENS,
    CHUNK_MIN_LENGTH_CHARS,
    DEDUP_COSINE_THRESHOLD,
)
from app.rag.schemas import ChunkCandidate
from app.core.logging import log_info
from app.rag.section_detector import detect_sections_batch


def _estimate_tokens(text: str) -> int:
    """Rough token count estimate (words ≈ 0.75 tokens)."""
    return int(len(text.split()) / 0.75)


def chunk_text_smart(
    text: str,
    doc_id: str,
    source_url: str = "",
    source_type: str = "note",
    user_id: str = "",
    page: int = 0,
    chunk_size: int = CHUNK_SIZE_TOKENS,
    overlap: int = CHUNK_OVERLAP_TOKENS,
    document_title: str = "",
) -> List[ChunkCandidate]:
    """
    Split text into overlapping chunks with metadata.
    Target: 400-600 tokens, ~50 token overlap.
    """
    if not text or not text.strip():
        return []

    words = text.split()
    # Convert token target to word count (words ≈ 0.75 tokens)
    word_chunk_size = int(chunk_size * 0.75)
    word_overlap = int(overlap * 0.75)

    chunks = []
    start = 0
    char_offset = 0

    while start < len(words):
        end = min(start + word_chunk_size, len(words))
        chunk_words = words[start:end]
        chunk_text = " ".join(chunk_words)

        # Skip garbage / too-short chunks
        if len(chunk_text.strip()) < CHUNK_MIN_LENGTH_CHARS:
            start = end
            continue

        # Calculate character offsets
        offset_start = text.find(chunk_words[0], char_offset) if chunk_words else char_offset
        if offset_start < 0:
            offset_start = char_offset
        offset_end = offset_start + len(chunk_text)

        chunk_id = f"{doc_id}_{page}_{start}"

        candidate = ChunkCandidate(
            id=chunk_id,
            doc_id=doc_id,
            text=chunk_text,
            page=page,
            offset_start=offset_start,
            offset_end=offset_end,
            source_url=source_url,
            source_type=source_type,
            user_id=user_id,
            document_title=document_title,
        )
        chunks.append(candidate)

        # Advance with overlap
        if end >= len(words):
            break
        start = end - word_overlap

    log_info(f"Chunked doc {doc_id}: {len(chunks)} chunks from {len(words)} words")

    # Detect section types for all chunks
    if chunks:
        chunk_texts = [c.text for c in chunks]
        section_types = detect_sections_batch(chunk_texts)
        for chunk, section_type in zip(chunks, section_types):
            chunk.section_type = section_type
        log_info(f"Section detection: {dict(zip([c.id for c in chunks[:5]], section_types[:5]))}...")

    return chunks


def deduplicate_chunks(
    chunks: List[ChunkCandidate],
    embeddings: List[List[float]],
    threshold: float = DEDUP_COSINE_THRESHOLD,
) -> tuple[List[ChunkCandidate], List[List[float]]]:
    """
    Remove near-duplicate chunks using cosine similarity.
    Returns deduplicated chunks and their embeddings.
    """
    if not chunks or not embeddings:
        return chunks, embeddings

    emb_array = np.array(embeddings)
    # Normalize
    norms = np.linalg.norm(emb_array, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    normalized = emb_array / norms

    keep_indices = []
    for i in range(len(chunks)):
        is_duplicate = False
        for j in keep_indices:
            sim = float(np.dot(normalized[i], normalized[j]))
            if sim > threshold:
                is_duplicate = True
                break
        if not is_duplicate:
            keep_indices.append(i)

    deduped_chunks = [chunks[i] for i in keep_indices]
    deduped_embeddings = [embeddings[i] for i in keep_indices]

    removed = len(chunks) - len(deduped_chunks)
    if removed > 0:
        log_info(f"Deduplication removed {removed} near-duplicate chunks (threshold={threshold})")

    return deduped_chunks, deduped_embeddings
