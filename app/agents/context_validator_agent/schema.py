# app/agents/context_validator_agent/schema.py
"""
Schemas for the Context Validator Agent.

This agent consolidates context verification (entity coverage, answer signals,
contradiction detection) and retrieval validation into a unified step.
"""

from typing import Dict, List, Optional
from pydantic import BaseModel


class ContextValidatorInput(BaseModel):
    """Input for the Context Validator Agent."""
    query: str
    chunks: list  # List of Chunk objects
    intent_result: Optional[object] = None  # IntentResult from intent classifier
    retrieval_confidence_score: float = 0.0

    class Config:
        arbitrary_types_allowed = True


class ContextValidatorOutput(BaseModel):
    """Output from the Context Validator Agent."""
    # Context verification
    is_sufficient: bool = False
    coverage_score: float = 0.0
    answer_signal_score: float = 0.0
    has_contradictions: bool = False
    contradiction_details: str = ""
    evidence_strength: str = "weak"
    recommendation: str = "proceed"
    uncovered_concepts: List[str] = []

    # Grounded mode decision
    grounded_only: bool = False
    grounded_reason: str = ""

    # Retrieval validation
    retrieval_is_valid: bool = False
    retrieval_reason: str = ""
    retrieval_top_score: float = 0.0
    retrieval_section_match_count: int = 0
    retrieval_document_match_count: int = 0
    retrieval_should_retry: bool = False

    # Warnings
    warnings: List[str] = []
