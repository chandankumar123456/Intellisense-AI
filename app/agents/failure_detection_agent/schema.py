# app/agents/failure_detection_agent/schema.py
"""
Schemas for the Failure Detection & Recovery Agent.

This agent wraps pre-synthesis failure prediction with recovery
recommendations into a dedicated decision point.
"""

from typing import Dict, List, Optional
from pydantic import BaseModel


class FailureDetectionInput(BaseModel):
    """Input for the Failure Detection Agent."""
    query: str
    chunks: list  # List of Chunk objects
    context_verification: Optional[object] = None  # ContextVerification result
    retrieval_confidence: Optional[object] = None  # RetrievalConfidence result

    class Config:
        arbitrary_types_allowed = True


class FailureDetectionOutput(BaseModel):
    """Output from the Failure Detection Agent."""
    risk_level: float = 0.0
    should_retry: bool = False
    should_expand: bool = False
    should_ground: bool = False
    signals: Dict[str, float] = {}
    explanation: str = ""
    warnings: List[str] = []
