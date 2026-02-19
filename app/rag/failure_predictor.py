# app/rag/failure_predictor.py
"""
Retrieval Failure Prediction (Pre-Synthesis Guard).

Multi-signal failure predictor that prevents weak retrieval from reaching
synthesis. Evaluates the retrieved context quality and predicts whether
synthesis will produce a grounded answer.

Signals:
  1. Semantic coverage  (0.30) — fraction of query concepts covered
  2. Answer signal score (0.25) — from context_verifier
  3. Context fragmentation (0.20) — chunks from many unrelated docs
  4. Confidence stability (0.25) — variance of chunk scores
"""

import math
from typing import Any, Dict, List, Optional
from pydantic import BaseModel
from app.core.logging import log_info, log_warning
from app.core.config import (
    FAILURE_RISK_RETRY_THRESHOLD,
    FAILURE_RISK_GROUND_THRESHOLD,
)


class FailurePrediction(BaseModel):
    """Result of retrieval failure prediction."""
    risk_level: float = 0.0           # 0-1, higher = more likely to fail
    should_retry: bool = False        # Risk > retry threshold
    should_expand: bool = False       # Medium risk, expand context
    should_ground: bool = False       # Risk > ground threshold
    signals: Dict[str, float] = {}    # Individual signal values
    explanation: str = ""


def predict_failure(
    chunks: list,
    query: str,
    context_verification: Optional[Any] = None,
    retrieval_confidence: Optional[Any] = None,
    *,
    retry_threshold: float = FAILURE_RISK_RETRY_THRESHOLD,
    ground_threshold: float = FAILURE_RISK_GROUND_THRESHOLD,
) -> FailurePrediction:
    """
    Predict whether the current retrieval will fail at synthesis.

    Args:
        chunks: Retrieved chunks after reranking.
        query: The user's query.
        context_verification: Optional ContextVerification result.
        retrieval_confidence: Optional RetrievalConfidence result.
        retry_threshold: Risk level above which to trigger retry.
        ground_threshold: Risk level above which to activate grounded mode.

    Returns:
        FailurePrediction with risk level and recommended actions.
    """
    if not chunks:
        return FailurePrediction(
            risk_level=1.0,
            should_retry=True,
            should_ground=True,
            explanation="No chunks retrieved",
        )

    # ── Signal 1: Semantic Coverage (0.30) ──
    sem_coverage = _compute_coverage_signal(query, chunks)

    # ── Signal 2: Answer Signal Score (0.25) ──
    answer_signal = _compute_answer_signal(chunks, context_verification)

    # ── Signal 3: Context Fragmentation (0.20) ──
    fragmentation = _compute_fragmentation(chunks)

    # ── Signal 4: Confidence Stability (0.25) ──
    stability = _compute_stability(chunks, retrieval_confidence)

    # ── Weighted Risk Score ──
    # Each signal is 0-1 where higher = WORSE (more risk)
    weights = {
        "semantic_coverage_gap": 0.30,
        "weak_answer_signal": 0.25,
        "high_fragmentation": 0.20,
        "low_stability": 0.25,
    }

    risk = (
        weights["semantic_coverage_gap"] * (1.0 - sem_coverage) +
        weights["weak_answer_signal"] * (1.0 - answer_signal) +
        weights["high_fragmentation"] * fragmentation +
        weights["low_stability"] * (1.0 - stability)
    )
    risk = round(min(1.0, max(0.0, risk)), 4)

    signals = {
        "semantic_coverage": round(sem_coverage, 4),
        "answer_signal": round(answer_signal, 4),
        "fragmentation": round(fragmentation, 4),
        "stability": round(stability, 4),
    }

    should_retry = risk > retry_threshold
    should_expand = retry_threshold * 0.7 < risk <= retry_threshold
    should_ground = risk > ground_threshold

    # Build explanation
    explanations = []
    if sem_coverage < 0.5:
        explanations.append("low semantic coverage")
    if answer_signal < 0.3:
        explanations.append("weak answer signals")
    if fragmentation > 0.6:
        explanations.append("high context fragmentation")
    if stability < 0.4:
        explanations.append("unstable confidence")

    explanation = "; ".join(explanations) if explanations else "acceptable risk"

    result = FailurePrediction(
        risk_level=risk,
        should_retry=should_retry,
        should_expand=should_expand,
        should_ground=should_ground,
        signals=signals,
        explanation=explanation,
    )

    log_info(
        f"Failure prediction: risk={risk:.3f} "
        f"[cov={sem_coverage:.2f}, ans={answer_signal:.2f}, "
        f"frag={fragmentation:.2f}, stab={stability:.2f}] → "
        f"retry={should_retry}, ground={should_ground}: {explanation}"
    )

    return result


def _compute_coverage_signal(query: str, chunks: list) -> float:
    """Fraction of query concepts found in chunks."""
    import re
    stop = {"the", "a", "an", "is", "are", "was", "were", "be", "of", "in",
            "to", "for", "with", "on", "at", "by", "from", "and", "or", "it",
            "this", "that", "what", "how", "which", "who", "explain", "describe",
            "tell", "please", "me", "my", "your", "but", "not", "no"}

    tokens = set(re.findall(r"\b\w+\b", query.lower())) - stop
    if not tokens:
        return 1.0

    evidence = " ".join(getattr(c, "text", "").lower() for c in chunks)
    covered = sum(1 for t in tokens if t in evidence)
    return covered / len(tokens)


def _compute_answer_signal(chunks: list, ctx_verification: Optional[Any]) -> float:
    """Score indicating how likely chunks contain actual answers."""
    # If we have context verification, use its answer signal
    if ctx_verification:
        return getattr(ctx_verification, "answer_signal_score", 0.5)

    # Fallback: heuristic from chunk content
    if not chunks:
        return 0.0

    answer_patterns = [
        r"\bis\s+defined\s+as\b", r"\brefers?\s+to\b", r"\bmeans?\b",
        r"\bconsists?\s+of\b", r"\binvolves?\b", r"\d+\.?\d*\s*%",
        r"\d+\.?\d*\s*(kg|km|m|cm|mm|g|mg|ml|l|hours?|minutes?|seconds?)",
        r"\baccording\s+to\b", r"\bfor\s+example\b", r"\bsuch\s+as\b",
        r"\b(therefore|thus|hence|consequently)\b",
    ]

    import re
    signal_count = 0
    total_checks = len(answer_patterns) * min(len(chunks), 5)
    for c in chunks[:5]:
        text = getattr(c, "text", "")
        for pat in answer_patterns:
            if re.search(pat, text, re.IGNORECASE):
                signal_count += 1

    return min(1.0, signal_count / max(total_checks * 0.3, 1))


def _compute_fragmentation(chunks: list) -> float:
    """
    Measure context fragmentation.
    High fragmentation = chunks from many different documents/sections.
    Returns 0-1 where 1 = highly fragmented.
    """
    if len(chunks) <= 1:
        return 0.0

    doc_ids = set()
    sections = set()
    for c in chunks[:10]:
        doc_id = getattr(c, "document_id", "") or ""
        sec = getattr(c, "section_type", None)
        if not sec:
            meta = getattr(c, "metadata", {}) or {}
            sec = meta.get("section_type", "body")
        if doc_id:
            doc_ids.add(doc_id)
        sections.add(sec)

    n = min(len(chunks), 10)

    # Fragmentation increases with more unique sources
    doc_ratio = len(doc_ids) / max(n, 1)
    section_ratio = len(sections) / max(n, 1)

    return min(1.0, (doc_ratio * 0.6 + section_ratio * 0.4))


def _compute_stability(chunks: list, ret_confidence: Optional[Any]) -> float:
    """
    Measure confidence stability.
    Low variance in scores = stable.
    Returns 0-1 where 1 = very stable.
    """
    scores = []
    for c in chunks[:10]:
        score = getattr(c, "raw_score", 0.0) or 0.0
        scores.append(score)

    if not scores:
        return 0.0

    mean = sum(scores) / len(scores)
    variance = sum((s - mean) ** 2 for s in scores) / len(scores)
    std_dev = math.sqrt(variance)

    # Normalize: std_dev of 0 = perfectly stable (1.0)
    # std_dev of 0.5+ = very unstable (0.0)
    stability = max(0.0, 1.0 - std_dev * 2)

    # Also factor in retrieval confidence if available
    if ret_confidence:
        conf_score = getattr(ret_confidence, "score", 0.5)
        stability = 0.7 * stability + 0.3 * conf_score

    return round(stability, 4)
