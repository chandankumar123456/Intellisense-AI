# app/rag/reranker.py
"""
Re-ranking engine combining semantic similarity, keyword overlap,
section matching, and document-specificity boosting.
Used after coarse retrieval to select top passages per claim.
"""

import re
import numpy as np
from typing import List, Dict, Any, Tuple, Optional
from app.core.config import RERANK_TOP_K
from app.core.logging import log_info


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
    
    # Strong definition indicators
    # "is a", "refers to", "defined as", "consists of"
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
    
    # Boost for structural words if length is sufficient
    if len(text.split()) > 30:
        if "therefore" in text_lower or "hence" in text_lower or "specifically" in text_lower:
            score += 0.1
            
    return min(score, 1.0)


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
    section match bonus, and document-specificity bonus.
    
    For conceptual queries: adjusts weights to favor definitions and explanations.
    """
    if not passages:
        return []
        
    # Adjust weights for conceptual queries
    definition_weight = 0.0
    if is_conceptual:
        semantic_weight = 0.55
        definition_weight = 0.20
        keyword_weight = 0.15
        section_boost_weight = 0.08
        document_boost_weight = 0.02

    query_tokens = _tokenize(query)

    scored = []
    for i, passage in enumerate(passages):
        text = passage.get("text", "")
        pass_tokens = _tokenize(text)

        # Keyword overlap score
        kw_score = _keyword_overlap(query_tokens, pass_tokens)

        # Semantic score
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
                
        # Conceptual Boost
        # If query is conceptual, prioritize Definition/Introduction/Overview sections
        if is_conceptual:
            if passage_section and any(x in passage_section for x in ["definition", "introduction", "overview"]):
                # Boost significantly (similar to target_section) to bubble up definitions
                section_match = max(section_match, 0.8)

        # Document-specificity bonus — prefer user-uploaded content
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
            
        # Mention-only penalty
        # If passage is short (< 20 words) and has no definition signal -> penalize
        penalty = 0.0
        if len(text.split()) < 20 and def_score < 0.1:
            penalty = -0.2

        # Combined score
        combined = (
            (semantic_weight * sem_score)
            + (keyword_weight * kw_score)
            + (section_boost_weight * section_match)
            + (document_boost_weight * doc_match)
            + (definition_weight * def_score)
            + penalty
        )

        scored.append({
            **passage,
            "rerank_score": round(combined, 6),
            "semantic_score": round(sem_score, 6),
            "keyword_score": round(kw_score, 6),
            "definition_presence_score": round(def_score, 6),
            "section_match": section_match > 0,
            "document_match": doc_match > 0,
        })

    # Sort by re-rank score descending
    scored.sort(key=lambda x: x["rerank_score"], reverse=True)

    result = scored[:top_k]
    log_info(
        f"Re-ranked {len(passages)} passages -> top {len(result)}"
        f" (conceptual={is_conceptual}, section_boost={'on' if target_section else 'off'}"
        f", doc_boost={'on' if prefer_user_documents else 'off'})"
    )

    return result
