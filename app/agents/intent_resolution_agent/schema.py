# app/agents/intent_resolution_agent/schema.py
"""
Schemas for the Intent & Subject Resolution Agent.

This agent consolidates intent classification, subject detection,
query structural classification, and query rewriting into a single
cohesive step, reducing controller complexity.
"""

from typing import List, Optional
from pydantic import BaseModel


class IntentResolutionInput(BaseModel):
    """Input for the Intent & Subject Resolution Agent."""
    query: str
    llm_rewritten_query: str = ""


class IntentResolutionOutput(BaseModel):
    """Output from the Intent & Subject Resolution Agent."""
    # Intent classification
    intent: str = "general"
    target_section: Optional[str] = None
    has_document_reference: bool = False
    intent_confidence: float = 0.0
    intent_explanation: str = ""

    # Subject scope
    subject: str = ""
    subject_confidence: float = 0.0
    is_ambiguous: bool = False
    content_type: str = ""
    secondary_subject: Optional[str] = None

    # Search scope (potentially broadened if low confidence)
    search_subject: str = ""
    subject_filter_disabled: bool = False

    # Query structural classification
    query_type: str = "general"
    query_type_confidence: float = 0.0
    is_conceptual: bool = False

    # Effective retrieval query
    effective_query: str = ""

    # Warnings produced during resolution
    warnings: List[str] = []
