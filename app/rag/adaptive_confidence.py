# app/rag/adaptive_confidence.py
"""
Adaptive Confidence Threshold Learning.

Wraps static confidence thresholds with adaptive logic that adjusts based on:
  - Query type (conceptual, factual, comparative, etc.)
  - Query complexity (word count, concept count)
  - Historical performance from retrieval memory

Falls back to static defaults when memory is empty (cold-start).
"""

from typing import Optional, Tuple
from app.core.config import (
    RETRIEVAL_CONFIDENCE_HIGH,
    RETRIEVAL_CONFIDENCE_LOW,
    ADAPTIVE_CONFIDENCE_ENABLED,
)
from app.core.logging import log_info


# Per-query-type default adjustments (before memory learning)
# Format: (high_delta, low_delta)
QUERY_TYPE_ADJUSTMENTS = {
    "conceptual":        (-0.05, -0.05),   # Conceptual needs more context → lower thresholds
    "fact_verification": (+0.05, +0.05),   # Factual needs precision → higher thresholds 
    "comparative":       (-0.03, -0.03),   # Comparative needs breadth → slightly lower
    "multi_hop":         (-0.08, -0.05),   # Multi-hop is harder → more lenient
    "temporal":          (+0.00, +0.00),   # Temporal is standard
    "general":           (+0.00, +0.00),   # Default
}


def get_adaptive_thresholds(
    query_type: str = "general",
    query_complexity: Optional[float] = None,
    memory_hints: Optional[Tuple[float, float]] = None,
) -> Tuple[float, float]:
    """
    Get adaptive confidence thresholds.

    Args:
        query_type: Query type string from QueryTypeClassifier.
        query_complexity: 0-1 normalized complexity score (higher = more complex).
        memory_hints: (high, low) from RetrievalMemory.get_threshold_hints(),
                      or None if cold-start.

    Returns:
        (high_threshold, low_threshold) tuple.
    """
    if not ADAPTIVE_CONFIDENCE_ENABLED:
        return (RETRIEVAL_CONFIDENCE_HIGH, RETRIEVAL_CONFIDENCE_LOW)

    # Start with static defaults
    high = RETRIEVAL_CONFIDENCE_HIGH
    low = RETRIEVAL_CONFIDENCE_LOW

    # Apply query-type adjustments
    qt_key = query_type.lower().replace(" ", "_")
    delta_high, delta_low = QUERY_TYPE_ADJUSTMENTS.get(qt_key, (0.0, 0.0))
    high += delta_high
    low += delta_low

    # Apply complexity adjustment
    if query_complexity is not None:
        # More complex queries → slightly lower thresholds (more forgiving)
        complexity_adjustment = -0.05 * query_complexity
        high += complexity_adjustment
        low += complexity_adjustment * 0.5

    # Blend with memory hints (if available)
    if memory_hints is not None:
        mem_high, mem_low = memory_hints
        # Weighted blend: 60% adaptive, 40% memory-learned
        high = 0.60 * high + 0.40 * mem_high
        low = 0.60 * low + 0.40 * mem_low

    # Clamp to valid ranges
    high = round(max(0.40, min(0.90, high)), 3)
    low = round(max(0.15, min(high - 0.10, low)), 3)  # low must be < high

    log_info(
        f"Adaptive thresholds: type={query_type}, complexity={query_complexity}, "
        f"high={high}, low={low}"
    )

    return (high, low)


def compute_query_complexity(query: str) -> float:
    """
    Estimate query complexity as a 0-1 score.
    
    Factors:
      - Word count (more words = more complex)
      - Question word count (multiple questions = more complex)
      - Connector density (and, or, because, etc.)
    """
    words = query.split()
    word_count = len(words)

    # Base complexity from length
    if word_count <= 5:
        length_score = 0.2
    elif word_count <= 10:
        length_score = 0.4
    elif word_count <= 20:
        length_score = 0.6
    else:
        length_score = 0.8

    # Connector density (indicates multi-part queries)
    connectors = {"and", "or", "but", "because", "since", "while", "whereas",
                  "however", "although", "moreover", "furthermore", "also"}
    connector_count = sum(1 for w in words if w.lower() in connectors)
    connector_score = min(1.0, connector_count * 0.3)

    # Multiple question marks
    q_count = query.count("?")
    question_score = min(1.0, q_count * 0.3) if q_count > 1 else 0.0

    # Weighted combination
    complexity = 0.50 * length_score + 0.30 * connector_score + 0.20 * question_score
    return round(min(1.0, complexity), 3)
