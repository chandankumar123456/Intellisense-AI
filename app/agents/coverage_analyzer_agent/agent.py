# app/agents/coverage_analyzer_agent/agent.py
"""
Knowledge Coverage / Gap Analyzer Agent.

Analyzes semantic coverage of retrieved context against query concepts.
Identifies knowledge gaps and produces targeted gap-fill queries.
Previously this was a utility function call inside
RetrievalOrchestratorAgent.
"""

from app.agents.coverage_analyzer_agent.schema import (
    CoverageAnalysisInput,
    CoverageAnalysisOutput,
)
from app.rag.semantic_coverage import analyze_coverage
from app.core.config import SEMANTIC_COVERAGE_MIN
from app.core.logging import log_info


class CoverageAnalyzerAgent:
    """
    Evaluates whether the retrieved chunks adequately cover all query
    concepts. Outputs gap-fill queries when coverage is insufficient.
    """

    async def run(self, input: CoverageAnalysisInput) -> CoverageAnalysisOutput:
        if not input.chunks:
            return CoverageAnalysisOutput()

        result = analyze_coverage(
            query=input.query,
            chunks=input.chunks,
            min_coverage=SEMANTIC_COVERAGE_MIN,
        )

        log_info(
            f"[CoverageAnalyzer] coverage={result['overall_coverage']:.2f}, "
            f"gaps={len(result['gaps'])}, needs_fill={result['needs_gap_fill']}"
        )

        return CoverageAnalysisOutput(
            concepts=result["concepts"],
            coverage_scores=result["coverage_scores"],
            overall_coverage=result["overall_coverage"],
            gaps=result["gaps"],
            needs_gap_fill=result["needs_gap_fill"],
            gap_queries=result["gap_queries"],
        )
