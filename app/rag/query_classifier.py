from enum import Enum
from typing import List, Optional
import re
from pydantic import BaseModel

class QueryType(Enum):
    FACT_VERIFICATION = "fact_verification"
    MULTI_HOP = "multi_hop"
    COMPARATIVE = "comparative"
    TEMPORAL = "temporal"
    CONCEPTUAL = "conceptual"
    GENERAL = "general"

class QueryTypeResult(BaseModel):
    query_type: QueryType
    confidence: float
    reasoning: str

class QueryTypeClassifier:
    """
    Advanced rule-based classifier to determine the structural type of the query.
    Used to select appropriate retrieval and reasoning strategies.
    
    Strategies:
    - FACT_VERIFICATION -> High precision retrieval, claim extraction.
    - MULTI_HOP -> multiple retrieval steps, decomposition (future).
    - COMPARATIVE -> retrieve for both entities.
    """
    
    def __init__(self):
        # Patterns for Fact Verification
        self.fact_patterns = [
            r"^(is|are|did|does|was|were|can|could|should|would) ",
            r"(true|false|correct|incorrect|right|wrong|accurate)",
            r"verify that",
            r"check if",
            r"confirm whether"
        ]
        
        # Patterns for Comparative
        self.compare_patterns = [
            r"compare",
            r"difference betweeen",
            r"versus",
            r"\bvs\b",
            r"similarity between",
            r"pros and cons",
            r"advantages and disadvantages"
        ]

        # Patterns for Conceptual / Definition
        self.conceptual_patterns = [
            r"what is",
            r"define",
            r"explain",
            r"concept of",
            r"meaning of",
            r"principle of",
            r"definition of",
            r"how does .* work"
        ]
        
        # Patterns for Temporal
        self.temporal_patterns = [
            r"when did",
            r"timeline",
            r"history of",
            r"evolution of",
            r"before",
            r"after",
            r"during",
            r"\d{4}" # Years
        ]
        
        # Patterns for Multi-hop (heuristic: complex connectors)
        self.multihop_patterns = [
            r"blockers .* causing",
            r"effect of .* on",
            r"relationship between .* and",
            r"connection between",
            r"impact of"
        ]

    def classify(self, query: str) -> QueryTypeResult:
        query_lower = query.lower()
        
        # Check Fact Verification
        for pattern in self.fact_patterns:
            if re.search(pattern, query_lower):
                return QueryTypeResult(
                    query_type=QueryType.FACT_VERIFICATION,
                    confidence=0.8,
                    reasoning=f"Matched fact verification pattern: '{pattern}'"
                )

        # Check Conceptual (Check early as 'what is' is common)
        for pattern in self.conceptual_patterns:
            if re.search(pattern, query_lower):
                return QueryTypeResult(
                    query_type=QueryType.CONCEPTUAL,
                    confidence=0.85,
                    reasoning=f"Matched conceptual pattern: '{pattern}'"
                )

        # Check Comparative
        for pattern in self.compare_patterns:
            if re.search(pattern, query_lower):
                return QueryTypeResult(
                    query_type=QueryType.COMPARATIVE,
                    confidence=0.85,
                    reasoning=f"Matched comparative pattern: '{pattern}'"
                )
                
        # Check Temporal
        for pattern in self.temporal_patterns:
            if re.search(pattern, query_lower):
                return QueryTypeResult(
                    query_type=QueryType.TEMPORAL,
                    confidence=0.75,
                    reasoning=f"Matched temporal pattern: '{pattern}'"
                )

        # Check Multi-hop
        for pattern in self.multihop_patterns:
            if re.search(pattern, query_lower):
                return QueryTypeResult(
                    query_type=QueryType.MULTI_HOP,
                    confidence=0.6,
                    reasoning=f"Matched multi-hop pattern: '{pattern}'"
                )

        return QueryTypeResult(
            query_type=QueryType.GENERAL,
            confidence=0.5,
            reasoning="No specific structural patterns matched."
        )

# Singleton instance
query_classifier = QueryTypeClassifier()
