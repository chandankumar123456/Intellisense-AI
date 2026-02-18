# app/rag/query_rewriter.py
"""
Deterministic query rewriter for RAG retrieval.
Expands short, ambiguous, or section-specific queries internally
to improve vector search recall. The user never sees the rewritten query.
"""

from typing import Optional
from app.rag.intent_classifier import QueryIntent, IntentResult


# Section-specific expansion templates
SECTION_EXPANSIONS = {
    "abstract": "abstract summary overview main contribution key findings",
    "introduction": "introduction background motivation problem statement overview",
    "methodology": "methodology methods approach technique implementation design experimental setup",
    "results": "results findings evaluation performance experimental outcomes metrics",
    "discussion": "discussion analysis interpretation implications observations",
    "conclusion": "conclusion summary concluding remarks future work key takeaways",
    "references": "references bibliography citations sources",
    "literature_review": "literature review related work prior research background studies",
    "acknowledgements": "acknowledgements acknowledgments thanks funding support",
    "appendix": "appendix supplementary additional material data",
}

# Short query expansion templates (for ambiguous queries)
SHORT_QUERY_EXPANSIONS = {
    "main idea": "main idea key points summary overview central theme",
    "overview": "overview summary introduction main points outline",
    "key points": "key points main findings important results highlights",
    "objective": "objective goal purpose aim research question",
    "problem": "problem statement research question challenge motivation",
    "contribution": "contribution novelty key findings main results",
    "framework": "framework architecture system design approach model",
    "algorithm": "algorithm procedure method steps technique implementation",
    "dataset": "dataset data collection training testing benchmark",
    "comparison": "comparison baseline evaluation metrics performance analysis",
    "limitation": "limitation weakness shortcoming future work challenge",
    "scope": "scope boundary range applicability coverage",
}


def rewrite_query(
    raw_query: str,
    intent_result: IntentResult,
) -> str:
    """
    Rewrite and expand a query for better retrieval performance.
    
    The rewriting is internal — the user never sees it.
    The rewritten query is used only for vector/keyword search.
    
    Args:
        raw_query: The original user query.
        intent_result: Result from the intent classifier.
    
    Returns:
        The rewritten query string for retrieval.
    """
    if not raw_query or not raw_query.strip():
        return raw_query

    query_clean = raw_query.strip()
    query_lower = query_clean.lower()

    # DOCUMENT_SECTION → expand with section-specific terms + document prefix
    if intent_result.intent == QueryIntent.DOCUMENT_SECTION:
        section = intent_result.target_section
        if section and section in SECTION_EXPANSIONS:
            expansion = SECTION_EXPANSIONS[section]
            return f"{expansion} from uploaded document"
        return f"{query_clean} section content from uploaded document"

    # AMBIGUOUS (short queries) → try to expand
    if intent_result.intent == QueryIntent.AMBIGUOUS:
        # Check if the short query matches a known expansion
        for key, expansion in SHORT_QUERY_EXPANSIONS.items():
            if key in query_lower:
                return f"{expansion} from uploaded document"
        # Generic expansion for truly ambiguous queries
        return f"{query_clean} key information content details from uploaded document"

    # DOCUMENT_SPECIFIC → add document context prefix
    if intent_result.intent == QueryIntent.DOCUMENT_SPECIFIC:
        # Remove document indicator phrases for cleaner search
        cleaned = _strip_document_indicators(query_clean)
        section = intent_result.target_section
        if section and section in SECTION_EXPANSIONS:
            return f"{cleaned} {SECTION_EXPANSIONS[section]}"
        return f"{cleaned} from uploaded document content"

    # MIXED → expand both parts
    if intent_result.intent == QueryIntent.MIXED:
        section = intent_result.target_section
        if section and section in SECTION_EXPANSIONS:
            return f"{query_clean} {SECTION_EXPANSIONS[section]}"
        return query_clean

    # CONCEPTUAL → keep as-is with minor expansion
    if intent_result.intent == QueryIntent.CONCEPTUAL:
        return query_clean

    return query_clean


def _strip_document_indicators(query: str) -> str:
    """Remove document reference phrases for cleaner search terms."""
    import re
    patterns = [
        r"(?i)\bwhat\s+does\s+my\s+\w+\s+say\s+about\s*",
        r"(?i)\bin\s+my\s+(document|paper|file|report|pdf)\s*,?\s*",
        r"(?i)\bfrom\s+my\s+(document|paper|file|report|pdf)\s*,?\s*",
        r"(?i)\bmy\s+(project|document|paper|file|report)\s*",
        r"(?i)\baccording\s+to\s+(my|the)\s+(document|paper)\s*,?\s*",
    ]
    result = query
    for pattern in patterns:
        result = re.sub(pattern, "", result).strip()
    return result if result else query
