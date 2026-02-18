# app/rag/retrieval_validator.py
"""
Post-retrieval validation for the RAG pipeline.
Validates that retrieved chunks actually match the user's intent.
Triggers one retry with expanded query if results are weak.
"""

from typing import List, Dict, Any, Optional, Tuple
from app.rag.intent_classifier import QueryIntent, IntentResult
from app.core.logging import log_info, log_warning


# Configurable thresholds
DEFAULT_QUALITY_THRESHOLD = 0.3
DEFAULT_SECTION_MATCH_MIN = 1  # Minimum chunks with matching section_type


class ValidationResult:
    """Result of post-retrieval validation."""
    
    def __init__(
        self,
        is_valid: bool,
        reason: str = "",
        top_score: float = 0.0,
        section_match_count: int = 0,
        document_match_count: int = 0,
        should_retry: bool = False,
    ):
        self.is_valid = is_valid
        self.reason = reason
        self.top_score = top_score
        self.section_match_count = section_match_count
        self.document_match_count = document_match_count
        self.should_retry = should_retry


def validate_retrieval(
    chunks: List[Any],
    intent_result: IntentResult,
    quality_threshold: float = DEFAULT_QUALITY_THRESHOLD,
) -> ValidationResult:
    """
    Validate that retrieved chunks match the user's intent.
    
    Args:
        chunks: Retrieved chunks (Chunk objects with normalized_score, metadata, etc.)
        intent_result: The classified intent from the intent classifier.
        quality_threshold: Minimum score for the top chunk to be considered valid.
    
    Returns:
        ValidationResult indicating whether the results are valid and if a retry is needed.
    """
    if not chunks:
        return ValidationResult(
            is_valid=False,
            reason="No chunks retrieved",
            should_retry=True,
        )

    # Get top score
    top_score = max(
        getattr(c, "normalized_score", 0.0) or getattr(c, "raw_score", 0.0) 
        for c in chunks
    )

    # Count section matches
    section_match_count = 0
    document_match_count = 0
    
    if intent_result.target_section:
        for chunk in chunks:
            chunk_section = _get_chunk_section(chunk)
            if chunk_section == intent_result.target_section:
                section_match_count += 1

    # Count document-type matches (user uploaded content vs generic)
    for chunk in chunks:
        source_type = _get_chunk_source_type(chunk)
        if source_type in ("pdf", "file", "note"):
            document_match_count += 1

    # Validation logic
    # 1. Score check
    if top_score < quality_threshold:
        log_warning(
            f"Retrieval quality low: top_score={top_score:.3f} < threshold={quality_threshold}"
        )
        return ValidationResult(
            is_valid=False,
            reason=f"Top score {top_score:.3f} below threshold {quality_threshold}",
            top_score=top_score,
            section_match_count=section_match_count,
            document_match_count=document_match_count,
            should_retry=True,
        )

    # 2. Section alignment check
    if intent_result.intent == QueryIntent.DOCUMENT_SECTION and intent_result.target_section:
        if section_match_count == 0:
            log_warning(
                f"Section mismatch: looking for '{intent_result.target_section}' "
                f"but no chunks have matching section_type"
            )
            return ValidationResult(
                is_valid=False,
                reason=f"No chunks match target section '{intent_result.target_section}'",
                top_score=top_score,
                section_match_count=0,
                document_match_count=document_match_count,
                should_retry=True,
            )

    # 3. Document alignment check
    if intent_result.intent in (QueryIntent.DOCUMENT_SECTION, QueryIntent.DOCUMENT_SPECIFIC):
        if document_match_count == 0 and len(chunks) > 0:
            log_warning(
                "Document mismatch: intent requires document content but no user-uploaded chunks found"
            )
            return ValidationResult(
                is_valid=False,
                reason="No user-uploaded document chunks found",
                top_score=top_score,
                section_match_count=section_match_count,
                document_match_count=0,
                should_retry=True,
            )

    # All checks passed
    log_info(
        f"Retrieval validated: top_score={top_score:.3f}, "
        f"section_matches={section_match_count}, "
        f"document_matches={document_match_count}"
    )
    return ValidationResult(
        is_valid=True,
        reason="All checks passed",
        top_score=top_score,
        section_match_count=section_match_count,
        document_match_count=document_match_count,
        should_retry=False,
    )


def _get_chunk_section(chunk: Any) -> str:
    """Extract section_type from a chunk object."""
    # Try metadata dict first
    if hasattr(chunk, "metadata") and isinstance(chunk.metadata, dict):
        return chunk.metadata.get("section_type", "body")
    # Try direct attribute
    if hasattr(chunk, "section_type"):
        return chunk.section_type
    return "body"


def _get_chunk_source_type(chunk: Any) -> str:
    """Extract source_type from a chunk object."""
    if hasattr(chunk, "source_type"):
        return chunk.source_type
    if hasattr(chunk, "metadata") and isinstance(chunk.metadata, dict):
        return chunk.metadata.get("source_type", "note")
    return "note"
