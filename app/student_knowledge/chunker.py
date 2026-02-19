# app/student_knowledge/chunker.py
"""
Semantic + structural chunker for student knowledge.
Produces overlapping chunks with preserved context (headings, timestamps).
"""

import hashlib
import re
from typing import List, Dict, Any, Optional
from app.core.config import STUDENT_CHUNK_SIZE_TOKENS, STUDENT_CHUNK_OVERLAP_TOKENS
from app.core.logging import log_info


def chunk_document(
    text: str,
    upload_id: str,
    student_id: str,
    structure: Dict[str, Any] = None,
    timestamps: List[Dict[str, Any]] = None,
    chunk_size: int = STUDENT_CHUNK_SIZE_TOKENS,
    chunk_overlap: int = STUDENT_CHUNK_OVERLAP_TOKENS,
) -> List[Dict[str, Any]]:
    """
    Split text into overlapping chunks with metadata.
    
    Returns list of chunk dicts: {chunk_id, text, section, heading, 
    timestamp_start, timestamp_end, concepts, fingerprint, chunk_index}
    """
    if not text or not text.strip():
        return []

    structure = structure or {}
    headings = structure.get("headings", [])

    # If we have timestamps (YouTube), use timestamp-aware chunking
    if timestamps:
        return _chunk_with_timestamps(
            text, timestamps, upload_id, student_id, chunk_size, chunk_overlap
        )

    # Otherwise, use structural chunking
    return _chunk_structural(
        text, headings, upload_id, student_id, chunk_size, chunk_overlap
    )


def _chunk_structural(
    text: str,
    headings: List[Dict[str, Any]],
    upload_id: str,
    student_id: str,
    chunk_size: int,
    chunk_overlap: int,
) -> List[Dict[str, Any]]:
    """Chunk text respecting structural boundaries (sections/paragraphs)."""
    words = text.split()
    if not words:
        return []

    # Build a line→heading map for section context
    lines = text.split("\n")
    line_heading_map = {}
    current_heading = None
    for heading_info in sorted(headings, key=lambda h: h.get("line", h.get("page", 0))):
        current_heading = heading_info.get("text", "")

    # Simple heading assignment: walk lines and track current heading
    current_heading = None
    heading_lines = {h.get("line", -1): h.get("text", "") for h in headings}
    for i, line in enumerate(lines):
        if i in heading_lines:
            current_heading = heading_lines[i]
        line_heading_map[i] = current_heading

    chunks = []
    chunk_words = []
    chunk_start_line = 0
    current_len = 0

    for word in words:
        chunk_words.append(word)
        current_len += 1

        if current_len >= chunk_size:
            chunk_text = " ".join(chunk_words)
            # Determine which heading this chunk falls under
            # Approximate by finding the line number of the chunk start
            heading = _find_heading_for_text(chunk_text, text, line_heading_map)

            chunks.append(_make_chunk(
                text=chunk_text,
                upload_id=upload_id,
                student_id=student_id,
                chunk_index=len(chunks),
                heading=heading,
            ))

            # Keep overlap
            chunk_words = chunk_words[-chunk_overlap:]
            current_len = len(chunk_words)

    # Remaining words
    if chunk_words and len(chunk_words) > 10:  # Skip tiny remnants
        chunk_text = " ".join(chunk_words)
        heading = _find_heading_for_text(chunk_text, text, line_heading_map)
        chunks.append(_make_chunk(
            text=chunk_text,
            upload_id=upload_id,
            student_id=student_id,
            chunk_index=len(chunks),
            heading=heading,
        ))

    log_info(f"Chunked document into {len(chunks)} chunks (structural)")
    return chunks


def _chunk_with_timestamps(
    text: str,
    timestamps: List[Dict[str, Any]],
    upload_id: str,
    student_id: str,
    chunk_size: int,
    chunk_overlap: int,
) -> List[Dict[str, Any]]:
    """Chunk YouTube transcript preserving timestamp boundaries."""
    chunks = []
    current_words = []
    current_start = timestamps[0]["start"] if timestamps else 0
    current_end = current_start
    current_segments = []

    for segment in timestamps:
        try:
            seg_text = segment.get("text", "")
            if not seg_text:
                continue
            seg_words = seg_text.split()
            current_words.extend(seg_words)
            current_end = segment["start"] + segment.get("duration", 0)
            current_segments.append(segment)

            if len(current_words) >= chunk_size:
                chunk_text = " ".join(current_words)
                chunks.append(_make_chunk(
                text=chunk_text,
                upload_id=upload_id,
                student_id=student_id,
                chunk_index=len(chunks),
                timestamp_start=current_start,
                timestamp_end=current_end,
                section="video_segment",
            ))

            # Overlap: keep last N words and corresponding timestamps
            overlap_words = current_words[-chunk_overlap:]
            current_words = overlap_words
            # Approximate the start time for the overlap
            if current_segments:
                overlap_ratio = chunk_overlap / max(len(current_words) + chunk_overlap, 1)
                current_start = current_end - (current_end - current_start) * overlap_ratio
            current_segments = []

        except Exception as e:
            log_info(f"Skipping malformed timestamp segment: {e}")
            continue

    # Remaining
    if current_words and len(current_words) > 10:
        chunk_text = " ".join(current_words)
        chunks.append(_make_chunk(
            text=chunk_text,
            upload_id=upload_id,
            student_id=student_id,
            chunk_index=len(chunks),
            timestamp_start=current_start,
            timestamp_end=current_end,
            section="video_segment",
        ))

    log_info(f"Chunked transcript into {len(chunks)} chunks (timestamp-aware)")
    return chunks


def _make_chunk(
    text: str,
    upload_id: str,
    student_id: str,
    chunk_index: int,
    heading: str = None,
    section: str = None,
    timestamp_start: float = None,
    timestamp_end: float = None,
) -> Dict[str, Any]:
    """Create a chunk record dict."""
    chunk_id = f"{upload_id}_chunk_{chunk_index}"
    fingerprint = hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]

    return {
        "chunk_id": chunk_id,
        "upload_id": upload_id,
        "student_id": student_id,
        "text": text,
        "section": section or heading or "general",
        "heading": heading,
        "timestamp_start": timestamp_start,
        "timestamp_end": timestamp_end,
        "concepts": [],  # Filled by enricher
        "fingerprint": fingerprint,
        "chunk_index": chunk_index,
    }


def _find_heading_for_text(
    chunk_text: str,
    full_text: str,
    line_heading_map: Dict[int, Optional[str]],
) -> Optional[str]:
    """Find the section heading for a chunk based on its position in the text."""
    try:
        # Find approximate line position
        pos = full_text.find(chunk_text[:50])
        if pos < 0:
            return None
        line_num = full_text[:pos].count("\n")
        # Walk backward to find nearest heading
        for l in range(line_num, -1, -1):
            if l in line_heading_map and line_heading_map[l]:
                return line_heading_map[l]
    except Exception:
        pass
    return None
