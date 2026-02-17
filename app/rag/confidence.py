# app/rag/confidence.py
"""
Calibrated confidence computation for claim verification.
Uses weighted combination of four signals.
Maps to status categories: Supported / Weakly Supported / Unsupported.
"""

import re
from typing import List, Dict, Any
from app.core.config import (
    CONFIDENCE_WEIGHTS,
    STATUS_SUPPORTED_THRESHOLD,
    STATUS_SUPPORTED_SIM_PEAK,
    STATUS_WEAKLY_SUPPORTED_THRESHOLD,
)
from app.rag.schemas import ConfidenceSubScores


def compute_calibrated_confidence(
    top_passages: List[Dict[str, Any]],
    claim_text: str,
) -> tuple[float, str, ConfidenceSubScores]:
    """
    Compute a normalized confidence score in [0,1] combining:
      - max semantic similarity among top passages (weight 0.45)
      - evidence agreement across multiple passages (weight 0.25)
      - coverage of claim tokens by evidence (weight 0.15)
      - source reliability / importance_score (weight 0.15)

    Returns: (confidence, status, sub_scores)
    """
    w = CONFIDENCE_WEIGHTS

    if not top_passages:
        sub = ConfidenceSubScores()
        return 0.0, "Unsupported", sub

    # 1. Max semantic similarity
    similarity_scores = [
        p.get("rerank_score", p.get("similarity_score", p.get("score", 0.0)))
        for p in top_passages
    ]
    max_sim = max(similarity_scores) if similarity_scores else 0.0

    # 2. Evidence agreement: how many passages agree (have score > 0.5)
    agreeing = sum(1 for s in similarity_scores if s > 0.5)
    agreement = min(1.0, agreeing / max(len(top_passages), 1))

    # 3. Token coverage: what fraction of claim tokens appear in evidence
    claim_tokens = set(re.findall(r"\b\w+\b", claim_text.lower()))
    stop_words = {"the", "a", "an", "is", "are", "was", "were", "be", "been",
                  "being", "have", "has", "had", "do", "does", "did", "will",
                  "would", "could", "should", "may", "might", "shall", "can",
                  "of", "in", "to", "for", "with", "on", "at", "by", "from",
                  "as", "into", "about", "that", "this", "it", "and", "or",
                  "but", "not", "no", "if", "then", "so"}
    claim_tokens -= stop_words

    evidence_text = " ".join(p.get("text", "") for p in top_passages).lower()
    evidence_tokens = set(re.findall(r"\b\w+\b", evidence_text))

    if claim_tokens:
        coverage = len(claim_tokens & evidence_tokens) / len(claim_tokens)
    else:
        coverage = 0.0

    # 4. Source reliability (average importance_score)
    importance_scores = [
        p.get("importance_score", 0.5)
        for p in top_passages
    ]
    avg_importance = sum(importance_scores) / max(len(importance_scores), 1)

    # Weighted combination
    confidence = (
        w["max_similarity"] * max_sim
        + w["evidence_agreement"] * agreement
        + w["token_coverage"] * coverage
        + w["source_reliability"] * avg_importance
    )
    confidence = round(min(1.0, max(0.0, confidence)), 4)

    # Map to status
    if confidence >= STATUS_SUPPORTED_THRESHOLD and max_sim >= STATUS_SUPPORTED_SIM_PEAK:
        status = "Supported"
    elif confidence >= STATUS_WEAKLY_SUPPORTED_THRESHOLD:
        status = "Weakly Supported"
    else:
        status = "Unsupported"

    sub_scores = ConfidenceSubScores(
        max_similarity=round(max_sim, 4),
        evidence_agreement=round(agreement, 4),
        token_coverage=round(coverage, 4),
        source_reliability=round(avg_importance, 4),
        raw_confidence=confidence,
    )

    return confidence, status, sub_scores
