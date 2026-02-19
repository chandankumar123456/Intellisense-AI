# app/rag/semantic_coverage.py
"""
Semantic Coverage Optimizer.

Extracts key concepts from the query and measures which are covered
by retrieved context. Triggers targeted gap-fill retrieval for missing
concepts to ensure full semantic coverage.
"""

import re
from typing import Any, Dict, List, Set, Tuple
from app.core.logging import log_info, log_warning
from app.core.config import SEMANTIC_COVERAGE_MIN, MAX_GAP_FILL_QUERIES


# Stop words for concept extraction
_STOP_WORDS = frozenset({
    "the", "a", "an", "is", "are", "was", "were", "be", "been",
    "being", "have", "has", "had", "do", "does", "did", "will",
    "would", "could", "should", "may", "might", "shall", "can",
    "of", "in", "to", "for", "with", "on", "at", "by", "from",
    "as", "into", "about", "that", "this", "it", "and", "or",
    "but", "not", "no", "if", "then", "so", "what", "how",
    "which", "who", "where", "when", "why", "my", "your",
    "me", "explain", "describe", "tell", "give", "please",
    "between", "related", "its", "their", "these", "those",
})


def extract_concepts(query: str) -> List[str]:
    """
    Extract key semantic concepts from the query.
    
    Returns a list of concepts (bigrams and significant unigrams).
    Concepts are returned in order of estimated importance.
    """
    query_lower = query.lower().strip()
    # Remove punctuation except hyphens
    clean = re.sub(r"[^\w\s-]", "", query_lower)
    words = clean.split()
    
    # Filter stop words for unigrams
    meaningful_words = [w for w in words if w not in _STOP_WORDS and len(w) > 2]
    
    concepts = []
    seen = set()
    
    # Extract bigrams first (more specific)
    for i in range(len(words) - 1):
        w1, w2 = words[i], words[i + 1]
        if w1 in _STOP_WORDS and w2 in _STOP_WORDS:
            continue
        bigram = f"{w1} {w2}"
        # Only keep bigrams where at least one word is meaningful
        if w1 not in _STOP_WORDS or w2 not in _STOP_WORDS:
            if bigram not in seen:
                concepts.append(bigram)
                seen.add(bigram)
    
    # Then add single meaningful words not already covered by bigrams
    for w in meaningful_words:
        already_in_bigram = any(w in c for c in concepts)
        if not already_in_bigram and w not in seen:
            concepts.append(w)
            seen.add(w)
    
    return concepts


def measure_coverage(
    concepts: List[str],
    chunks: list,
) -> Dict[str, float]:
    """
    Measure per-concept coverage by retrieved chunks.
    
    Returns dict of {concept: coverage_score} where 0.0 = not covered, 1.0 = well covered.
    """
    if not concepts or not chunks:
        return {}
    
    # Build combined evidence text per chunk
    chunk_texts = []
    for c in chunks:
        text = getattr(c, "text", "").lower()
        chunk_texts.append(text)
    
    all_evidence = " ".join(chunk_texts)
    
    coverage = {}
    for concept in concepts:
        # Direct match
        if concept in all_evidence:
            # Score by how many chunks contain it
            containing_chunks = sum(1 for t in chunk_texts if concept in t)
            score = min(1.0, containing_chunks / max(len(chunks) * 0.3, 1))
            coverage[concept] = round(score, 3)
        else:
            # Partial match: check if individual words appear
            concept_words = concept.split()
            if len(concept_words) > 1:
                partial = sum(1 for w in concept_words if w in all_evidence) / len(concept_words)
                coverage[concept] = round(partial * 0.5, 3)  # Partial = half credit
            else:
                coverage[concept] = 0.0
    
    return coverage


def identify_gaps(
    concepts: List[str],
    chunks: list,
    min_coverage: float = 0.3,
) -> List[str]:
    """
    Identify concepts that are insufficiently covered.
    
    Returns list of uncovered concept strings.
    """
    coverage = measure_coverage(concepts, chunks)
    gaps = [concept for concept, score in coverage.items() if score < min_coverage]
    return gaps


def get_overall_coverage(concepts: List[str], chunks: list) -> float:
    """Get single 0-1 coverage score across all concepts."""
    if not concepts:
        return 1.0
    coverage = measure_coverage(concepts, chunks)
    if not coverage:
        return 0.0
    return round(sum(coverage.values()) / len(coverage), 3)


def build_gap_queries(
    uncovered_concepts: List[str],
    original_query: str = "",
    max_queries: int = MAX_GAP_FILL_QUERIES,
) -> List[str]:
    """
    Generate targeted retrieval queries for uncovered concepts.
    
    Returns list of gap-fill query strings.
    """
    if not uncovered_concepts:
        return []
    
    queries = []
    for concept in uncovered_concepts[:max_queries]:
        # Build a targeted query combining the concept with context from original
        if original_query:
            # Extract core subject from original for context
            gap_query = f"{concept} {original_query}"
        else:
            gap_query = concept
        
        queries.append(gap_query)
    
    log_info(
        f"Semantic coverage: {len(uncovered_concepts)} gaps found, "
        f"generated {len(queries)} gap-fill queries"
    )
    
    return queries


def analyze_coverage(
    query: str,
    chunks: list,
    min_coverage: float = SEMANTIC_COVERAGE_MIN,
) -> Dict[str, Any]:
    """
    Full coverage analysis — extracts concepts, measures coverage, finds gaps.
    
    Returns:
        {
            "concepts": [...],
            "coverage_scores": {...},
            "overall_coverage": float,
            "gaps": [...],
            "needs_gap_fill": bool,
            "gap_queries": [...],
        }
    """
    concepts = extract_concepts(query)
    coverage_scores = measure_coverage(concepts, chunks)
    overall = get_overall_coverage(concepts, chunks)
    gaps = identify_gaps(concepts, chunks, min_coverage=0.3)
    needs_fill = overall < min_coverage and len(gaps) > 0
    gap_queries = build_gap_queries(gaps, query) if needs_fill else []
    
    return {
        "concepts": concepts,
        "coverage_scores": coverage_scores,
        "overall_coverage": overall,
        "gaps": gaps,
        "needs_gap_fill": needs_fill,
        "gap_queries": gap_queries,
    }
