# app/agents/coverage_analyzer_agent/schema.py
"""
Schemas for the Knowledge Coverage / Gap Analyzer Agent.

This agent analyzes semantic coverage of retrieved chunks against query
concepts and identifies knowledge gaps that need filling.
"""

from typing import Dict, List
from pydantic import BaseModel


class CoverageAnalysisInput(BaseModel):
    """Input for the Coverage Analyzer Agent."""
    query: str
    chunks: list  # List of Chunk objects

    class Config:
        arbitrary_types_allowed = True


class CoverageAnalysisOutput(BaseModel):
    """Output from the Coverage Analyzer Agent."""
    concepts: List[str] = []
    coverage_scores: Dict[str, float] = {}
    overall_coverage: float = 0.0
    gaps: List[str] = []
    needs_gap_fill: bool = False
    gap_queries: List[str] = []
