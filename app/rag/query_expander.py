# app/rag/query_expander.py
"""
Deterministic multi-stage query expander for improved retrieval recall.
Generates semantic variants of the original query to bridge the
query–document semantic gap. No LLM calls — purely rule-based for speed.

Generates three query forms:
  1. Concept form  — adds definitional anchors
  2. Keyword form  — extracts key nouns/terms
  3. Expanded form  — adds synonyms and related terms
"""

import re
from typing import List, Dict, Set
from app.core.logging import log_info


# ── Synonym / related-term map ──
# Covers common academic and technical terms that may appear differently
# in documents vs. queries.
SYNONYM_MAP: Dict[str, List[str]] = {
    "backpropagation": ["backward propagation", "gradient descent", "weight update", "chain rule"],
    "neural network": ["deep learning", "artificial neural network", "ANN", "deep neural network"],
    "machine learning": ["ML", "statistical learning", "predictive modeling"],
    "classification": ["categorization", "labeling", "class prediction"],
    "regression": ["prediction", "curve fitting", "continuous prediction"],
    "clustering": ["grouping", "unsupervised classification", "segmentation"],
    "optimization": ["minimization", "gradient descent", "loss minimization"],
    "transformer": ["attention mechanism", "self-attention", "multi-head attention"],
    "cnn": ["convolutional neural network", "convnet", "conv layer"],
    "rnn": ["recurrent neural network", "sequence model", "LSTM", "GRU"],
    "embedding": ["vector representation", "dense representation", "latent representation"],
    "tokenization": ["text splitting", "word segmentation", "subword"],
    "encoder": ["encoding layer", "feature extractor"],
    "decoder": ["decoding layer", "output generator"],
    "loss function": ["cost function", "objective function", "error function"],
    "accuracy": ["precision", "correctness", "performance metric"],
    "training": ["model training", "learning", "fitting"],
    "inference": ["prediction", "model inference", "forward pass"],
    "overfitting": ["overtraining", "high variance", "memorization"],
    "underfitting": ["high bias", "poor fit", "insufficient learning"],
    "database": ["DB", "data store", "DBMS", "relational database"],
    "algorithm": ["procedure", "method", "technique", "approach"],
    "architecture": ["system design", "structure", "framework", "model design"],
    "api": ["application programming interface", "endpoint", "REST API"],
    "deployment": ["production", "release", "hosting", "serving"],
    "normalization": ["standardization", "scaling", "feature scaling"],
    "regularization": ["L1", "L2", "dropout", "weight decay"],
    "hyperparameter": ["tuning parameter", "configuration", "model parameter"],
    "dataset": ["data", "corpus", "training data", "benchmark"],
    "evaluation": ["assessment", "testing", "validation", "metrics"],
    "feature": ["attribute", "variable", "input", "dimension"],
}

# Question words to strip for keyword extraction
QUESTION_WORDS = {
    "what", "who", "where", "when", "why", "how", "which",
    "is", "are", "was", "were", "do", "does", "did",
    "can", "could", "would", "should", "will", "shall",
    "explain", "describe", "define", "tell", "give", "list",
    "the", "a", "an", "in", "of", "for", "to", "from",
    "about", "with", "by", "on", "at", "and", "or", "but",
    "me", "my", "your", "this", "that", "it", "its",
}

# Concept anchors for definitional queries
CONCEPT_ANCHORS = [
    "definition", "meaning", "concept", "principle",
    "explanation", "overview", "fundamentals",
]


def expand_query(query: str, max_variants: int = 3) -> List[str]:
    """
    Generate semantic variants of the query for multi-pass retrieval.

    Returns a list of query strings (including the original).
    Each variant is designed to match different document phrasings:
      - concept_form:  "What is X" → "definition of X, meaning, concept"
      - keyword_form:  "Explain backpropagation in neural networks" → "backpropagation neural networks"
      - expanded_form: adds synonyms for recognized terms

    Args:
        query: Original user query.
        max_variants: Maximum number of variants to return (including original).

    Returns:
        List of query strings, first element is always the original.
    """
    if not query or not query.strip():
        return [query]

    query_clean = query.strip()
    query_lower = query_clean.lower()
    variants: List[str] = [query_clean]

    # Stage 1: Concept form
    concept = _build_concept_form(query_clean, query_lower)
    if concept and concept != query_clean:
        variants.append(concept)

    # Stage 2: Keyword form
    keyword = _build_keyword_form(query_clean, query_lower)
    if keyword and keyword != query_clean and keyword not in variants:
        variants.append(keyword)

    # Stage 3: Expanded form (synonym injection)
    expanded = _build_expanded_form(query_clean, query_lower)
    if expanded and expanded != query_clean and expanded not in variants:
        variants.append(expanded)

    # Cap at max_variants
    result = variants[:max_variants + 1]  # +1 because original is first

    log_info(
        f"Query expansion: '{query_clean}' → {len(result)} variants"
    )

    return result


def _build_concept_form(query: str, query_lower: str) -> str:
    """
    Add definitional anchors for concept-type queries.
    "Explain X" → "definition of X concept meaning explanation"
    """
    # Extract the core subject by stripping question patterns
    core = _extract_core_subject(query_lower)
    if not core or len(core.split()) < 1:
        return ""

    # Add concept anchors
    anchors = " ".join(CONCEPT_ANCHORS[:3])
    return f"{core} {anchors}"


def _build_keyword_form(query: str, query_lower: str) -> str:
    """
    Extract key nouns/terms — strip question words and filler.
    "What is backpropagation in neural networks?" → "backpropagation neural networks"
    """
    tokens = re.findall(r"\b\w+\b", query_lower)
    keywords = [t for t in tokens if t not in QUESTION_WORDS and len(t) > 2]

    if not keywords:
        return ""

    return " ".join(keywords)


def _build_expanded_form(query: str, query_lower: str) -> str:
    """
    Inject synonyms for recognized terms.
    "backpropagation" → "backpropagation backward propagation gradient descent"
    """
    tokens = re.findall(r"\b\w+\b", query_lower)
    additions: Set[str] = set()

    # Check single-word matches
    for token in tokens:
        if token in SYNONYM_MAP:
            # Add first 2 synonyms to avoid bloating the query
            additions.update(SYNONYM_MAP[token][:2])

    # Check multi-word matches (bigrams)
    for i in range(len(tokens) - 1):
        bigram = f"{tokens[i]} {tokens[i + 1]}"
        if bigram in SYNONYM_MAP:
            additions.update(SYNONYM_MAP[bigram][:2])

    if not additions:
        return ""

    # Append synonyms to original query
    synonym_str = " ".join(list(additions)[:6])  # Cap at 6 synonym terms
    return f"{query} {synonym_str}"


def _extract_core_subject(query_lower: str) -> str:
    """
    Strip question phrasing to extract the core subject.
    "What is backpropagation?" → "backpropagation"
    "Explain how neural networks work" → "neural networks work"
    """
    # Remove common question patterns
    patterns = [
        r"^what\s+is\s+",
        r"^what\s+are\s+",
        r"^how\s+does\s+",
        r"^how\s+do\s+",
        r"^how\s+to\s+",
        r"^explain\s+",
        r"^describe\s+",
        r"^define\s+",
        r"^tell\s+me\s+about\s+",
        r"^what\s+does\s+.+\s+mean\s*\??$",
        r"^can\s+you\s+explain\s+",
        r"^give\s+me\s+an?\s+overview\s+of\s+",
    ]

    result = query_lower.strip()
    for pat in patterns:
        result = re.sub(pat, "", result, flags=re.IGNORECASE).strip()

    # Remove trailing question mark
    result = result.rstrip("?").strip()

    return result


def rewrite_for_retry(
    query: str,
    attempt: int = 1,
    failed_reason: str = "",
) -> List[str]:
    """
    Generate stronger query rewrites when initial retrieval fails.
    Called by the controller's retry loop for progressively deeper rewrites.

    Args:
        query: The original query.
        attempt: Retry attempt number (1-based).
        failed_reason: Why the previous retrieval failed.

    Returns:
        List of rewritten queries to try.
    """
    query_clean = query.strip()
    query_lower = query_clean.lower()
    rewrites: List[str] = []

    if attempt == 1:
        # Attempt 1: Add domain context and clarification
        core = _extract_core_subject(query_lower)
        if core:
            rewrites.append(f"{core} detailed explanation with examples")
            rewrites.append(f"{core} key concepts principles architecture")
        else:
            rewrites.append(f"{query_clean} detailed context explanation")

    elif attempt >= 2:
        # Attempt 2+: Broad conceptual expansion
        core = _extract_core_subject(query_lower)
        expanded = _build_expanded_form(query_clean, query_lower)
        if expanded:
            rewrites.append(expanded)
        if core:
            rewrites.append(f"{core} introduction overview summary fundamentals")

        # Also try the keyword-only form
        keyword = _build_keyword_form(query_clean, query_lower)
        if keyword:
            rewrites.append(keyword)

    if not rewrites:
        rewrites.append(f"{query_clean} detailed context")

    log_info(
        f"Retry rewrite (attempt={attempt}): '{query_clean}' → {len(rewrites)} variants"
    )

    return rewrites
