# app/rag/context_verifier.py
"""
Context Verification Layer.

Verifies that retrieved context actually contains answer signals before
synthesis. Prevents the LLM from generating fluent but ungrounded answers.

Checks:
  1. Entity coverage   — key query entities appear in context
  2. Answer signal     — context contains factual answers, not just mentions
  3. Contradiction     — conflicting statements across chunks
  4. Evidence strength — overall assessment of context quality
"""

import re
from typing import List, Any, Set, Tuple
from pydantic import BaseModel
from app.core.logging import log_info, log_warning


class ContextVerification(BaseModel):
    """Result of context verification."""
    is_sufficient: bool = False
    coverage_score: float = 0.0
    answer_signal_score: float = 0.0
    has_contradictions: bool = False
    contradiction_details: str = ""
    evidence_strength: str = "weak"  # "strong" | "moderate" | "weak"
    recommendation: str = "proceed"  # "proceed" | "retry" | "grounded_only"
    uncovered_concepts: List[str] = []


# Stop words for concept extraction
_STOP_WORDS = frozenset({
    "the", "a", "an", "is", "are", "was", "were", "be", "been",
    "being", "have", "has", "had", "do", "does", "did", "will",
    "would", "could", "should", "may", "might", "shall", "can",
    "of", "in", "to", "for", "with", "on", "at", "by", "from",
    "as", "into", "about", "that", "this", "it", "and", "or",
    "but", "not", "no", "if", "then", "so", "what", "how",
    "which", "who", "where", "when", "why", "me", "my", "your",
    "explain", "describe", "tell", "give", "please", "i", "you",
})

# Patterns indicating a factual/definitional statement (answer signal)
ANSWER_SIGNAL_PATTERNS = [
    r"\bis\s+a\b",
    r"\bare\s+a\b",
    r"\brefers\s+to\b",
    r"\bdefined\s+as\b",
    r"\bconsists\s+of\b",
    r"\bknown\s+as\b",
    r"\bused\s+(for|to|in)\b",
    r"\bprovides\b",
    r"\brepresents\b",
    r"\benables\b",
    r"\ballows\b",
    r"\bperform\b",
    r"\bprocess\b",
    r"\bmethod\b",
    r"\bapproach\b",
    r"\btechnique\b",
    r"\balgorithm\b",
    r"\bfunction\b",
    r"\bresults?\s+in\b",
    r"\bleads?\s+to\b",
    r"\bcauses?\b",
    r"\bproduces?\b",
    r"\d+(\.\d+)?%",   # percentages (quantitative evidence)
    r"\d+(\.\d+)?\s+(times|x|ms|seconds|percent)",  # measurements
]

# Negation/contradiction indicators
CONTRADICTION_PATTERNS = [
    (r"\bhowever\b", r"\bbut\b"),
    (r"\bin contrast\b", r"\bon the other hand\b"),
    (r"\bnot\b.*\b(is|are|was|were)\b", r"\b(is|are|was|were)\b"),
    (r"\bunlike\b", r"\bsimilar to\b"),
]


def verify_context(
    query: str,
    chunks: List[Any],
    min_coverage: float = 0.40,
    min_answer_signal: float = 0.25,
) -> ContextVerification:
    """
    Verify that retrieved chunks contain sufficient evidence to answer the query.

    Args:
        query: The user's query.
        chunks: Retrieved Chunk objects.
        min_coverage: Minimum entity coverage threshold.
        min_answer_signal: Minimum answer signal score.

    Returns:
        ContextVerification with assessment and recommendation.
    """
    if not chunks:
        return ContextVerification(
            is_sufficient=False,
            recommendation="retry",
            evidence_strength="weak",
        )

    # Extract query concepts
    query_concepts = _extract_concepts(query)

    # Combine chunk texts
    chunk_texts = [getattr(c, "text", "") for c in chunks]
    combined_text = " ".join(chunk_texts).lower()

    # ── Check 1: Entity/concept coverage ──
    coverage_score, uncovered = _check_entity_coverage(query_concepts, combined_text)

    # ── Check 2: Answer signal detection ──
    answer_signal = _check_answer_signal(chunk_texts)

    # ── Check 3: Contradiction detection ──
    has_contradictions, contradiction_details = _check_contradictions(chunk_texts)

    # ── Determine evidence strength ──
    if coverage_score >= 0.7 and answer_signal >= 0.5:
        evidence_strength = "strong"
    elif coverage_score >= 0.4 and answer_signal >= 0.25:
        evidence_strength = "moderate"
    else:
        evidence_strength = "weak"

    # ── Determine sufficiency ──
    is_sufficient = (
        coverage_score >= min_coverage
        and answer_signal >= min_answer_signal
    )

    # ── Determine recommendation ──
    if is_sufficient and evidence_strength in ("strong", "moderate"):
        recommendation = "proceed"
    elif coverage_score < 0.2 and answer_signal < 0.15:
        recommendation = "retry"
    else:
        recommendation = "grounded_only"

    result = ContextVerification(
        is_sufficient=is_sufficient,
        coverage_score=round(coverage_score, 4),
        answer_signal_score=round(answer_signal, 4),
        has_contradictions=has_contradictions,
        contradiction_details=contradiction_details,
        evidence_strength=evidence_strength,
        recommendation=recommendation,
        uncovered_concepts=list(uncovered),
    )

    log_info(
        f"Context verification: sufficient={is_sufficient}, "
        f"coverage={coverage_score:.3f}, signal={answer_signal:.3f}, "
        f"strength={evidence_strength}, recommendation={recommendation}"
    )

    if uncovered:
        log_warning(f"Uncovered query concepts: {uncovered}")

    if has_contradictions:
        log_warning(f"Contradictions detected: {contradiction_details}")

    return result


def _extract_concepts(query: str) -> Set[str]:
    """
    Extract meaningful concepts (not just individual words) from the query.
    Returns a set of lowercased concept strings.
    """
    query_lower = query.lower()
    tokens = re.findall(r"\b\w+\b", query_lower)

    # Single-word concepts (filtered)
    concepts = {t for t in tokens if t not in _STOP_WORDS and len(t) > 2}

    # Also extract bigrams for multi-word concepts
    for i in range(len(tokens) - 1):
        if tokens[i] not in _STOP_WORDS and tokens[i + 1] not in _STOP_WORDS:
            bigram = f"{tokens[i]} {tokens[i + 1]}"
            if len(bigram) > 5:
                concepts.add(bigram)

    return concepts


def _check_entity_coverage(
    concepts: Set[str], evidence_text: str
) -> Tuple[float, Set[str]]:
    """
    Check what fraction of query concepts appear in the evidence.
    Returns (coverage_score, uncovered_concepts).
    """
    if not concepts:
        return 1.0, set()

    covered = set()
    uncovered = set()

    for concept in concepts:
        if concept in evidence_text:
            covered.add(concept)
        else:
            uncovered.add(concept)

    coverage = len(covered) / len(concepts) if concepts else 0.0
    return coverage, uncovered


def _check_answer_signal(chunk_texts: List[str]) -> float:
    """
    Check if chunks contain factual answer signals (definitions, facts,
    measurements) vs. just topic mentions.
    Returns 0-1 signal score.
    """
    if not chunk_texts:
        return 0.0

    signal_count = 0
    total_checked = min(len(chunk_texts), 5)  # Check top 5 chunks

    for text in chunk_texts[:total_checked]:
        text_lower = text.lower()
        chunk_signals = 0

        for pattern in ANSWER_SIGNAL_PATTERNS:
            if re.search(pattern, text_lower):
                chunk_signals += 1

        # A chunk with 2+ signal patterns is a strong answer signal
        if chunk_signals >= 2:
            signal_count += 1
        elif chunk_signals >= 1:
            signal_count += 0.5

    return min(1.0, signal_count / total_checked)


def _check_contradictions(
    chunk_texts: List[str],
) -> Tuple[bool, str]:
    """
    Detect potential contradictions across chunks.
    Simple heuristic: check for negation patterns in close proximity.
    Returns (has_contradictions, details).
    """
    if len(chunk_texts) < 2:
        return False, ""

    # Look for explicit contradiction signals across chunks
    for i in range(len(chunk_texts)):
        text_i = chunk_texts[i].lower()
        for j in range(i + 1, min(len(chunk_texts), i + 4)):
            text_j = chunk_texts[j].lower()

            # Check for opposing statements about the same entity
            # Simple heuristic: "X is Y" in one chunk vs "X is not Y" in another
            is_statements_i = re.findall(r"(\w+)\s+is\s+(\w+)", text_i)
            not_statements_j = re.findall(r"(\w+)\s+is\s+not\s+(\w+)", text_j)

            for (subj_i, obj_i) in is_statements_i:
                for (subj_j, obj_j) in not_statements_j:
                    if subj_i == subj_j and obj_i == obj_j:
                        detail = (
                            f"Chunk {i} says '{subj_i} is {obj_i}' "
                            f"but Chunk {j} says '{subj_j} is not {obj_j}'"
                        )
                        return True, detail

    return False, ""
