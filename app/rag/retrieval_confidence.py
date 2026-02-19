# app/rag/retrieval_confidence.py
"""
Retrieval-level confidence scoring.

Evaluates how well the retrieved context matches the user's query BEFORE
synthesis. This is separate from claim-level confidence (confidence.py)
which scores individual claims against evidence.

Signals used:
  1. Top similarity score  — strength of best match
  2. Score gap             — clarity of winner vs. noise
  3. Keyword overlap       — query terms present in context
  4. Semantic coverage     — all query concepts covered
  5. Information density   — chunks are substantive, not trivial
"""

import re
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from enum import Enum
from app.core.logging import log_info
from app.core.config import ADAPTIVE_CONFIDENCE_ENABLED


class ConfidenceLevel(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class RetrievalConfidence(BaseModel):
    """Result of retrieval confidence assessment."""
    score: float = 0.0
    level: ConfidenceLevel = ConfidenceLevel.LOW
    top_similarity: float = 0.0
    score_gap: float = 0.0
    keyword_overlap: float = 0.0
    semantic_coverage: float = 0.0
    information_density: float = 0.0
    recommendation: str = "proceed"  # "proceed" | "expand" | "retry" | "grounded_only"


# ── Confidence thresholds (imported from config at runtime) ──
DEFAULT_HIGH_THRESHOLD = 0.70
DEFAULT_LOW_THRESHOLD = 0.35

# Stop words for keyword/coverage analysis
STOP_WORDS = frozenset({
    "the", "a", "an", "is", "are", "was", "were", "be", "been",
    "being", "have", "has", "had", "do", "does", "did", "will",
    "would", "could", "should", "may", "might", "shall", "can",
    "of", "in", "to", "for", "with", "on", "at", "by", "from",
    "as", "into", "about", "that", "this", "it", "and", "or",
    "but", "not", "no", "if", "then", "so", "what", "how",
    "which", "who", "where", "when", "why", "my", "your",
    "me", "explain", "describe", "tell", "give", "please",
})


# ── Dynamic Weight Profiles per Query Type ──
DYNAMIC_WEIGHT_PROFILES = {
    "conceptual": {
        "top_similarity": 0.20,
        "score_gap": 0.10,
        "keyword_overlap": 0.15,
        "semantic_coverage": 0.35,
        "information_density": 0.20,
    },
    "fact_verification": {
        "top_similarity": 0.25,
        "score_gap": 0.15,
        "keyword_overlap": 0.35,
        "semantic_coverage": 0.15,
        "information_density": 0.10,
    },
    "comparative": {
        "top_similarity": 0.20,
        "score_gap": 0.10,
        "keyword_overlap": 0.20,
        "semantic_coverage": 0.25,
        "information_density": 0.25,
    },
    "multi_hop": {
        "top_similarity": 0.20,
        "score_gap": 0.10,
        "keyword_overlap": 0.20,
        "semantic_coverage": 0.30,
        "information_density": 0.20,
    },
    "temporal": {
        "top_similarity": 0.30,
        "score_gap": 0.15,
        "keyword_overlap": 0.25,
        "semantic_coverage": 0.15,
        "information_density": 0.15,
    },
}


def _get_weights_for_query_type(query_type: Optional[str]) -> Dict[str, float]:
    """Get signal weights adjusted for query type."""
    if not query_type:
        return {
            "top_similarity": 0.30,
            "score_gap": 0.15,
            "keyword_overlap": 0.20,
            "semantic_coverage": 0.20,
            "information_density": 0.15,
        }
    qt = query_type.lower().replace(" ", "_")
    return DYNAMIC_WEIGHT_PROFILES.get(qt, {
        "top_similarity": 0.30,
        "score_gap": 0.15,
        "keyword_overlap": 0.20,
        "semantic_coverage": 0.20,
        "information_density": 0.15,
    })


def compute_retrieval_confidence(
    query: str,
    chunks: List[Any],
    high_threshold: float = DEFAULT_HIGH_THRESHOLD,
    low_threshold: float = DEFAULT_LOW_THRESHOLD,
    query_type: Optional[str] = None,
) -> RetrievalConfidence:
    """
    Compute retrieval-level confidence score.

    Args:
        query: The user's query (original or rewritten).
        chunks: Retrieved Chunk objects with raw_score, text, metadata.
        high_threshold: Score above which confidence is HIGH.
        low_threshold: Score below which confidence is LOW.

    Returns:
        RetrievalConfidence with score, level, and recommendation.
    """
    if not chunks:
        return RetrievalConfidence(
            score=0.0,
            level=ConfidenceLevel.LOW,
            recommendation="retry",
        )

    # ── Signal 1: Top similarity score ──
    scores = _extract_scores(chunks)
    top_sim = max(scores) if scores else 0.0

    # ── Signal 2: Score gap (top vs. median) ──
    score_gap = _compute_score_gap(scores)

    # ── Signal 3: Keyword overlap ──
    kw_overlap = _compute_keyword_overlap(query, chunks)

    # ── Signal 4: Semantic coverage ──
    sem_coverage = _compute_semantic_coverage(query, chunks)

    # ── Signal 5: Information density ──
    info_density = _compute_information_density(chunks)

    # ── Dynamic weighted combination ──
    weights = _get_weights_for_query_type(query_type)

    # Adaptive thresholds if enabled
    if ADAPTIVE_CONFIDENCE_ENABLED and query_type:
        try:
            from app.rag.adaptive_confidence import get_adaptive_thresholds, compute_query_complexity
            from app.rag.retrieval_memory import get_retrieval_memory
            complexity = compute_query_complexity(query)
            memory = get_retrieval_memory()
            memory_hints = memory.get_threshold_hints(query_type)
            high_threshold, low_threshold = get_adaptive_thresholds(
                query_type=query_type,
                query_complexity=complexity,
                memory_hints=memory_hints,
            )
        except Exception:
            pass  # Fall through to static thresholds

    confidence = (
        weights["top_similarity"] * top_sim
        + weights["score_gap"] * score_gap
        + weights["keyword_overlap"] * kw_overlap
        + weights["semantic_coverage"] * sem_coverage
        + weights["information_density"] * info_density
    )
    confidence = round(min(1.0, max(0.0, confidence)), 4)

    # ── Determine level ──
    if confidence >= high_threshold:
        level = ConfidenceLevel.HIGH
    elif confidence >= low_threshold:
        level = ConfidenceLevel.MEDIUM
    else:
        level = ConfidenceLevel.LOW

    # ── Determine recommendation ──
    recommendation = _determine_recommendation(
        confidence, level, top_sim, kw_overlap, sem_coverage
    )

    result = RetrievalConfidence(
        score=confidence,
        level=level,
        top_similarity=round(top_sim, 4),
        score_gap=round(score_gap, 4),
        keyword_overlap=round(kw_overlap, 4),
        semantic_coverage=round(sem_coverage, 4),
        information_density=round(info_density, 4),
        recommendation=recommendation,
    )

    log_info(
        f"Retrieval confidence: {confidence:.3f} ({level.value}) "
        f"[top_sim={top_sim:.3f}, gap={score_gap:.3f}, "
        f"kw={kw_overlap:.3f}, cov={sem_coverage:.3f}, "
        f"density={info_density:.3f}] → {recommendation}"
    )

    return result


def _extract_scores(chunks: List[Any]) -> List[float]:
    """Extract numeric scores from chunks."""
    scores = []
    for c in chunks:
        # Try rerank_score from metadata first, then raw_score
        score = 0.0
        if hasattr(c, "metadata") and isinstance(c.metadata, dict):
            score = c.metadata.get("rerank_score", 0.0)
        if score == 0.0 and hasattr(c, "raw_score"):
            score = c.raw_score or 0.0
        scores.append(float(score))
    return scores


def _compute_score_gap(scores: List[float]) -> float:
    """
    Compute score gap between top result and the rest.
    A large gap means there's one clear winner (good).
    A small gap means noise/ambiguity (bad).
    Returns 0-1 normalized gap.
    """
    if len(scores) < 2:
        return 0.5  # neutral if only one result

    sorted_scores = sorted(scores, reverse=True)
    top = sorted_scores[0]
    second = sorted_scores[1]

    if top == 0:
        return 0.0

    # Gap ratio: how much better is #1 than #2
    gap = (top - second) / top
    # Also consider gap from median
    median_idx = len(sorted_scores) // 2
    median = sorted_scores[median_idx]
    median_gap = (top - median) / top if top > 0 else 0.0

    return min(1.0, (gap + median_gap) / 2.0)


def _compute_keyword_overlap(query: str, chunks: List[Any]) -> float:
    """
    Fraction of meaningful query keywords found in retrieved chunks.
    """
    query_tokens = _extract_keywords(query)
    if not query_tokens:
        return 0.0

    # Build combined evidence text
    evidence_text = " ".join(
        getattr(c, "text", "") for c in chunks
    ).lower()
    evidence_tokens = set(re.findall(r"\b\w+\b", evidence_text))

    overlap = len(query_tokens & evidence_tokens)
    return overlap / len(query_tokens)


def _compute_semantic_coverage(query: str, chunks: List[Any]) -> float:
    """
    Check if ALL key concepts in the query are covered by at least one chunk.
    Returns fraction of query concepts with at least partial coverage.
    """
    query_tokens = _extract_keywords(query)
    if not query_tokens:
        return 0.0

    covered = 0
    for token in query_tokens:
        for c in chunks:
            text = getattr(c, "text", "").lower()
            if token in text:
                covered += 1
                break

    return covered / len(query_tokens)


def _compute_information_density(chunks: List[Any]) -> float:
    """
    Assess whether chunks are substantive or trivially short/generic.
    Returns 0-1 density score.
    """
    if not chunks:
        return 0.0

    densities = []
    for c in chunks[:5]:  # Check top 5 only
        text = getattr(c, "text", "")
        words = text.split()
        word_count = len(words)

        if word_count < 10:
            densities.append(0.1)  # Very short = low density
        elif word_count < 30:
            densities.append(0.4)
        elif word_count < 80:
            densities.append(0.7)
        else:
            densities.append(0.9)  # Long, substantive chunks

        # Bonus for unique word ratio (higher = more informative)
        unique = len(set(w.lower() for w in words))
        ratio = unique / max(word_count, 1)
        densities[-1] = min(1.0, densities[-1] + ratio * 0.2)

    return sum(densities) / len(densities)


def _extract_keywords(text: str) -> set:
    """Extract meaningful keywords from text, excluding stop words."""
    tokens = set(re.findall(r"\b\w+\b", text.lower()))
    return tokens - STOP_WORDS


def _determine_recommendation(
    confidence: float,
    level: ConfidenceLevel,
    top_sim: float,
    kw_overlap: float,
    sem_coverage: float,
) -> str:
    """
    Determine the recommended action based on confidence signals.
    """
    if level == ConfidenceLevel.HIGH:
        return "proceed"

    if level == ConfidenceLevel.MEDIUM:
        # Medium confidence: expand context if semantics are weak
        if sem_coverage < 0.5:
            return "expand"
        if kw_overlap < 0.4:
            return "expand"
        return "proceed"

    # LOW confidence
    if top_sim < 0.2:
        return "retry"  # Nothing relevant found
    if sem_coverage < 0.3:
        return "retry"  # Query concepts not covered
    return "grounded_only"  # Some signal but not enough for confident answer
