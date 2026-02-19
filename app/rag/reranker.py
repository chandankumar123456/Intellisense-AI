# app/rag/reranker.py
"""
Re-ranking engine combining semantic similarity, keyword overlap,
section matching, document-specificity boosting, generic chunk penalty,
and information density bonus.
Used after coarse retrieval to select top passages per claim.
"""

import re
import numpy as np
from typing import List, Dict, Any, Tuple, Optional
from app.core.config import (
    RERANK_TOP_K,
    GENERIC_CHUNK_PENALTY,
    INFO_DENSITY_BONUS_WEIGHT,
)
from app.core.logging import log_info


# Common filler / generic words that don't carry information
_GENERIC_WORDS = frozenset({
    "the", "a", "an", "is", "are", "was", "were", "be", "been",
    "being", "have", "has", "had", "do", "does", "did", "will",
    "would", "could", "should", "may", "might", "shall", "can",
    "of", "in", "to", "for", "with", "on", "at", "by", "from",
    "as", "into", "about", "that", "this", "it", "and", "or",
    "but", "not", "no", "if", "then", "so",
})


def _tokenize(text: str) -> set:
    """Simple word-level tokenization."""
    return set(re.findall(r"\b\w+\b", text.lower()))


def _keyword_overlap(query_tokens: set, passage_tokens: set) -> float:
    """Fraction of query tokens found in passage."""
    if not query_tokens:
        return 0.0
    return len(query_tokens & passage_tokens) / len(query_tokens)


def _cosine_similarity(a: List[float], b: List[float]) -> float:
    """Compute cosine similarity between two vectors."""
    a_arr = np.array(a)
    b_arr = np.array(b)
    dot = float(np.dot(a_arr, b_arr))
    na = float(np.linalg.norm(a_arr))
    nb = float(np.linalg.norm(b_arr))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def _compute_definition_score(text: str) -> float:
    """Detect definitional patterns in text."""
    text_lower = text.lower()
    
    patterns = [
        r"\bis\s+a\b", r"\bare\s+a\b", 
        r"\brefers\s+to\b", 
        r"\bdefined\s+as\b", 
        r"\bconsists\s+of\b", 
        r"\bcomposed\s+of\b",
        r"\bwe\s+propose\b", 
        r"\bour\s+approach\b",
        r"\barchitecture\b", 
        r"\bpipeline\b", 
        r"\breasoning\s+loop\b", 
        r"\balgorithm\b"
    ]
    
    score = 0.0
    for pat in patterns:
        if re.search(pat, text_lower):
            score += 0.3
    
    if len(text.split()) > 30:
        if "therefore" in text_lower or "hence" in text_lower or "specifically" in text_lower:
            score += 0.1
            
    return min(score, 1.0)


def _compute_info_density(text: str) -> float:
    """
    Compute information density: ratio of unique meaningful words to total words.
    Higher density = more informative, less repetitive.
    Returns 0-1 score.
    """
    words = re.findall(r"\b\w+\b", text.lower())
    if not words:
        return 0.0

    word_count = len(words)
    meaningful = [w for w in words if w not in _GENERIC_WORDS and len(w) > 2]
    unique_meaningful = set(meaningful)

    if word_count < 10:
        return 0.1  # Very short = low density

    # Ratio of unique meaningful words to total words
    density = len(unique_meaningful) / word_count

    # Bonus for substantive length
    length_bonus = min(0.3, word_count / 300.0)

    return min(1.0, density + length_bonus)


def _is_generic_chunk(text: str) -> bool:
    """
    Detect overly generic chunks that don't carry useful information.
    E.g. table of contents, headers-only, boilerplate.
    """
    words = re.findall(r"\b\w+\b", text.lower())
    if not words:
        return True

    # Very short chunks with no substance
    if len(words) < 8:
        return True

    # High ratio of generic/stop words = generic content
    generic_count = sum(1 for w in words if w in _GENERIC_WORDS)
    generic_ratio = generic_count / len(words)

    return generic_ratio > 0.75


def _normalize_scores(passages: List[Dict[str, Any]], key: str = "score") -> None:
    """
    Normalize scores in-place to [0, 1] range across all passages.
    Handles mixed scoring scales from different retrieval passes.
    """
    scores = [p.get(key, 0.0) for p in passages]
    if not scores:
        return

    max_s = max(scores)
    min_s = min(scores)
    spread = max_s - min_s

    if spread < 1e-8:
        # All scores are the same — set to 0.5
        for p in passages:
            p[key] = 0.5
    else:
        for p in passages:
            p[key] = (p.get(key, 0.0) - min_s) / spread


def rerank_passages(
    passages: List[Dict[str, Any]],
    query: str,
    query_embedding: List[float] = None,
    passage_embeddings: List[List[float]] = None,
    top_k: int = RERANK_TOP_K,
    semantic_weight: float = 0.50,
    keyword_weight: float = 0.25,
    section_boost_weight: float = 0.15,
    document_boost_weight: float = 0.10,
    target_section: Optional[str] = None,
    prefer_user_documents: bool = False,
    is_conceptual: bool = False,
) -> List[Dict[str, Any]]:
    """
    Re-rank passages combining semantic score, keyword overlap,
    section match bonus, document-specificity bonus, information density,
    and generic chunk penalty.
    
    For conceptual queries: adjusts weights to favor definitions and explanations.
    Includes score normalization for cross-pass stability.
    """
    if not passages:
        return []

    # ── Score normalization across retrieval passes ──
    _normalize_scores(passages, key="score")

    # Adjust weights for conceptual queries
    definition_weight = 0.0
    if is_conceptual:
        semantic_weight = 0.50
        definition_weight = 0.18
        keyword_weight = 0.14
        section_boost_weight = 0.08
        document_boost_weight = 0.02

    query_tokens = _tokenize(query)

    scored = []
    for i, passage in enumerate(passages):
        text = passage.get("text", "")
        pass_tokens = _tokenize(text)

        # Keyword overlap score
        kw_score = _keyword_overlap(query_tokens, pass_tokens)

        # Semantic score (already normalized)
        sem_score = passage.get("score", 0.0)

        # If we have embeddings, compute fresh cosine similarity
        if query_embedding and passage_embeddings and i < len(passage_embeddings):
            sem_score = _cosine_similarity(query_embedding, passage_embeddings[i])

        # Section match bonus
        section_match = 0.0
        passage_section = passage.get("section_type", "")
        if not passage_section and isinstance(passage.get("metadata"), dict):
            passage_section = passage.get("metadata", {}).get("section_type", "")
            
        if target_section:
            if passage_section == target_section:
                section_match = 1.0
                
        if is_conceptual:
            if passage_section and any(x in passage_section for x in ["definition", "introduction", "overview"]):
                section_match = max(section_match, 0.8)

        # Document-specificity bonus
        doc_match = 0.0
        if prefer_user_documents:
            source_type = passage.get("source_type", "")
            if not source_type and isinstance(passage.get("metadata"), dict):
                source_type = passage.get("metadata", {}).get("source_type", "")
            if source_type in ("pdf", "file", "note"):
                doc_match = 1.0
        
        # Definition Presence Score
        def_score = 0.0
        if is_conceptual:
            def_score = _compute_definition_score(text)

        # ── NEW: Information density bonus ──
        info_density = _compute_info_density(text)

        # ── NEW: Generic chunk penalty ──
        generic_penalty = GENERIC_CHUNK_PENALTY if _is_generic_chunk(text) else 0.0

        # Short mention-only penalty
        mention_penalty = 0.0
        if len(text.split()) < 20 and def_score < 0.1:
            mention_penalty = -0.2

        # Combined score
        combined = (
            (semantic_weight * sem_score)
            + (keyword_weight * kw_score)
            + (section_boost_weight * section_match)
            + (document_boost_weight * doc_match)
            + (definition_weight * def_score)
            + (INFO_DENSITY_BONUS_WEIGHT * info_density)
            + generic_penalty
            + mention_penalty
        )

        scored.append({
            **passage,
            "rerank_score": round(combined, 6),
            "semantic_score": round(sem_score, 6),
            "keyword_score": round(kw_score, 6),
            "definition_presence_score": round(def_score, 6),
            "info_density_score": round(info_density, 6),
            "is_generic": _is_generic_chunk(text),
            "section_match": section_match > 0,
            "document_match": doc_match > 0,
        })

    # ── Stable sort: score descending, then chunk_id for deterministic tie-breaking ──
    scored.sort(
        key=lambda x: (-x["rerank_score"], x.get("chunk_id", "") or ""),
    )

    result = scored[:top_k]
    log_info(
        f"Re-ranked {len(passages)} passages -> top {len(result)}"
        f" (conceptual={is_conceptual}, section_boost={'on' if target_section else 'off'}"
        f", doc_boost={'on' if prefer_user_documents else 'off'})"
    )

    return result
