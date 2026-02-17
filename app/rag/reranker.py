# app/rag/reranker.py
"""
Re-ranking engine combining semantic similarity and keyword overlap.
Used after coarse retrieval to select top passages per claim.
"""

import re
import numpy as np
from typing import List, Dict, Any, Tuple
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


def rerank_passages(
    passages: List[Dict[str, Any]],
    query: str,
    query_embedding: List[float] = None,
    passage_embeddings: List[List[float]] = None,
    top_k: int = RERANK_TOP_K,
    semantic_weight: float = 0.6,
    keyword_weight: float = 0.4,
) -> List[Dict[str, Any]]:
    """
    Re-rank passages combining semantic score and keyword overlap with claim tokens.

    Each passage dict should have at least:
      - "text": str
      - "score": float (original retrieval score)
      - ...other metadata preserved

    Returns: List of top_k passages with added "rerank_score" field.
    """
    if not passages:
        return []

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

        # Combined score
        combined = (semantic_weight * sem_score) + (keyword_weight * kw_score)

        scored.append({
            **passage,
            "rerank_score": round(combined, 6),
            "semantic_score": round(sem_score, 6),
            "keyword_score": round(kw_score, 6),
        })

    # Sort by re-rank score descending
    scored.sort(key=lambda x: x["rerank_score"], reverse=True)

    result = scored[:top_k]
    log_info(f"Re-ranked {len(passages)} passages → top {len(result)}")

    return result
