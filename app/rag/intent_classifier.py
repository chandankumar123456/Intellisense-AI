# app/rag/intent_classifier.py
"""
Deterministic, rule-based intent classifier for RAG queries.
Classifies queries into intent types to drive retrieval strategy.
No LLM calls — fast (< 1ms), deterministic, and explainable.
"""

import re
from enum import Enum
from typing import Optional
from pydantic import BaseModel


class QueryIntent(str, Enum):
    DOCUMENT_SECTION = "document_section"
    DOCUMENT_SPECIFIC = "document_specific"
    CONCEPTUAL = "conceptual"
    MIXED = "mixed"
    AMBIGUOUS = "ambiguous"


# Section keyword map — maps user terms to canonical section_type values
SECTION_KEYWORDS = {
    "abstract": "abstract",
    "introduction": "introduction",
    "intro": "introduction",
    "methodology": "methodology",
    "method": "methodology",
    "methods": "methodology",
    "approach": "methodology",
    "implementation": "methodology",
    "design": "methodology",
    "results": "results",
    "result": "results",
    "findings": "results",
    "evaluation": "results",
    "experiment": "results",
    "experiments": "results",
    "performance": "results",
    "discussion": "discussion",
    "analysis": "discussion",
    "conclusion": "conclusion",
    "conclusions": "conclusion",
    "summary": "conclusion",
    "concluding": "conclusion",
    "future work": "conclusion",
    "references": "references",
    "bibliography": "references",
    "literature review": "literature_review",
    "related work": "literature_review",
    "background": "literature_review",
    "acknowledgements": "acknowledgements",
    "acknowledgments": "acknowledgements",
    "appendix": "appendix",
}

# Patterns indicating user is referring to their own uploaded document
DOCUMENT_INDICATORS = [
    r"(?i)\bmy\s+(project|document|paper|file|report|thesis|assignment|upload|pdf|note)\b",
    r"(?i)\buploaded\b",
    r"(?i)\bour\s+(project|document|paper|report)\b",
    r"(?i)\bin\s+the\s+(document|paper|file|report|pdf)\b",
    r"(?i)\bfrom\s+(my|the)\s+(document|paper|file|report|pdf)\b",
    r"(?i)\bdocument\s+says?\b",
    r"(?i)\bpaper\s+says?\b",
    r"(?i)\baccording\s+to\s+(my|the|our)\b",
]

# Patterns indicating a conceptual/general knowledge question
CONCEPTUAL_INDICATORS = [
    r"(?i)^explain\b",
    r"(?i)^what\s+is\b",
    r"(?i)^what\s+are\b",
    r"(?i)^define\b",
    r"(?i)^how\s+does\b",
    r"(?i)^how\s+do\b",
    r"(?i)^describe\b",
    r"(?i)^tell\s+me\s+about\b",
    r"(?i)^why\s+(is|are|does|do)\b",
    r"(?i)^compare\b(?!.*\b(my|document|paper|file|upload))",
]

# Patterns for section-specific queries
SECTION_QUERY_PATTERNS = [
    r"(?i)\b(what|give|show|get|extract|find|read)\b.*\b(abstract|introduction|conclusion|methodology|method|results?|discussion|summary)\b",
    r"(?i)\b(abstract|introduction|conclusion|methodology|method|results?|discussion|summary)\b.*\b(section|part|chapter)\b",
    r"(?i)^(abstract|introduction|conclusion|methodology|method|results?|discussion|summary)\s*\??$",
]


class IntentResult(BaseModel):
    """Result of intent classification."""
    intent: QueryIntent
    target_section: Optional[str] = None  # Canonical section_type if detected
    has_document_reference: bool = False
    confidence: float = 1.0
    raw_query: str = ""
    explanation: str = ""


def classify_intent(query: str) -> IntentResult:
    """
    Classify a user query into an intent type.
    
    Returns an IntentResult with the detected intent, target section,
    and confidence level.
    """
    if not query or not query.strip():
        return IntentResult(
            intent=QueryIntent.AMBIGUOUS,
            raw_query=query or "",
            confidence=0.5,
            explanation="Empty query",
        )

    query_clean = query.strip()
    query_lower = query_clean.lower()
    words = query_lower.split()

    # Detect components
    detected_section = _detect_section_reference(query_lower)
    has_doc_ref = _has_document_reference(query_clean)
    has_conceptual = _has_conceptual_indicator(query_clean)
    is_section_query = _is_section_query(query_clean)

    # Very short query (1-3 words)
    is_short = len(words) <= 3

    # Classification logic
    if has_doc_ref and has_conceptual:
        # "compare my abstract with agentic rag idea"
        return IntentResult(
            intent=QueryIntent.MIXED,
            target_section=detected_section,
            has_document_reference=True,
            confidence=0.85,
            raw_query=query_clean,
            explanation="Both document reference and conceptual indicators found",
        )

    if is_section_query or (detected_section and not has_conceptual):
        # "what is the abstract", "give conclusion", "abstract?"
        return IntentResult(
            intent=QueryIntent.DOCUMENT_SECTION,
            target_section=detected_section,
            has_document_reference=has_doc_ref or True,  # Section queries imply document
            confidence=0.9 if not is_short else 0.75,
            raw_query=query_clean,
            explanation=f"Section query detected: {detected_section}",
        )

    if has_doc_ref and not has_conceptual:
        # "what does my project say about X"
        return IntentResult(
            intent=QueryIntent.DOCUMENT_SPECIFIC,
            target_section=detected_section,
            has_document_reference=True,
            confidence=0.9,
            raw_query=query_clean,
            explanation="Document-specific query detected",
        )

    if has_conceptual and not has_doc_ref and not detected_section:
        # "explain agentic rag", "what is deep learning"
        return IntentResult(
            intent=QueryIntent.CONCEPTUAL,
            target_section=None,
            has_document_reference=False,
            confidence=0.85,
            raw_query=query_clean,
            explanation="Conceptual/general knowledge query",
        )

    if is_short and detected_section:
        # "abstract", "method?", "results"
        return IntentResult(
            intent=QueryIntent.DOCUMENT_SECTION,
            target_section=detected_section,
            has_document_reference=True,
            confidence=0.7,
            raw_query=query_clean,
            explanation=f"Short query matching section: {detected_section}",
        )

    if is_short:
        # "main idea?", other short queries
        return IntentResult(
            intent=QueryIntent.AMBIGUOUS,
            target_section=None,
            has_document_reference=False,
            confidence=0.5,
            raw_query=query_clean,
            explanation="Short ambiguous query",
        )

    # Default: treat as document-specific if it doesn't look conceptual
    # This ensures uploaded documents are prioritized for unknown queries
    return IntentResult(
        intent=QueryIntent.DOCUMENT_SPECIFIC,
        target_section=detected_section,
        has_document_reference=False,
        confidence=0.6,
        raw_query=query_clean,
        explanation="Default classification: prioritizing document content",
    )


def _detect_section_reference(query_lower: str) -> Optional[str]:
    """Check if the query references a document section."""
    # Check multi-word keys first (e.g., "literature review", "future work")
    for keyword, section_type in sorted(
        SECTION_KEYWORDS.items(), key=lambda x: len(x[0]), reverse=True
    ):
        if keyword in query_lower:
            return section_type
    return None


def _has_document_reference(query: str) -> bool:
    """Check if the query references a specific document."""
    for pattern in DOCUMENT_INDICATORS:
        if re.search(pattern, query):
            return True
    return False


def _has_conceptual_indicator(query: str) -> bool:
    """Check if the query is asking a conceptual/general question."""
    for pattern in CONCEPTUAL_INDICATORS:
        if re.search(pattern, query):
            return True
    return False


def _is_section_query(query: str) -> bool:
    """Check if the query is specifically asking for a document section."""
    for pattern in SECTION_QUERY_PATTERNS:
        if re.search(pattern, query):
            return True
    return False
