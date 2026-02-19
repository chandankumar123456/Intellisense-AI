# app/agents/context_validator_agent/agent.py
"""
Context Validator Agent.

Consolidates context verification (entity coverage, answer signals,
contradiction detection) and retrieval quality validation into a
dedicated agent. Previously inlined in PipelineControllerAgent
(sections 2.5 and 2.7).
"""

from app.agents.context_validator_agent.schema import (
    ContextValidatorInput,
    ContextValidatorOutput,
)
from app.rag.context_verifier import verify_context
from app.rag.retrieval_validator import validate_retrieval
from app.core.config import CONTEXT_VERIFICATION_ENABLED, GROUNDED_MODE_THRESHOLD
from app.core.logging import log_info
from typing import List


class ContextValidatorAgent:
    """
    Validates retrieved context quality before synthesis.
    Determines whether grounded mode should be activated.
    """

    async def run(self, input: ContextValidatorInput) -> ContextValidatorOutput:
        warnings: List[str] = []
        grounded_only = False
        grounded_reason = ""

        # ── 1. Retrieval validation ──
        ret_validation = validate_retrieval(
            chunks=input.chunks,
            intent_result=input.intent_result,
        )

        # ── 2. Context verification ──
        ctx = None
        if CONTEXT_VERIFICATION_ENABLED and len(input.chunks) > 0:
            ctx = verify_context(
                query=input.query,
                chunks=input.chunks,
            )

            if ctx.recommendation == "grounded_only":
                grounded_only = True
                grounded_reason = "context_verification"
                warnings.append("grounded_mode_context_verification")
            elif input.retrieval_confidence_score < GROUNDED_MODE_THRESHOLD:
                grounded_only = True
                grounded_reason = "low_confidence"
                warnings.append("grounded_mode_low_confidence")

            if grounded_only:
                log_info(
                    f"[ContextValidator] GROUNDED MODE: reason={grounded_reason}, "
                    f"ret_confidence={input.retrieval_confidence_score:.3f}"
                )

        return ContextValidatorOutput(
            # Context verification
            is_sufficient=ctx.is_sufficient if ctx else False,
            coverage_score=ctx.coverage_score if ctx else 0.0,
            answer_signal_score=ctx.answer_signal_score if ctx else 0.0,
            has_contradictions=ctx.has_contradictions if ctx else False,
            contradiction_details=ctx.contradiction_details if ctx else "",
            evidence_strength=ctx.evidence_strength if ctx else "weak",
            recommendation=ctx.recommendation if ctx else "proceed",
            uncovered_concepts=ctx.uncovered_concepts if ctx else [],
            # Grounded mode
            grounded_only=grounded_only,
            grounded_reason=grounded_reason,
            # Retrieval validation
            retrieval_is_valid=ret_validation.is_valid,
            retrieval_reason=ret_validation.reason,
            retrieval_top_score=ret_validation.top_score,
            retrieval_section_match_count=ret_validation.section_match_count,
            retrieval_document_match_count=ret_validation.document_match_count,
            retrieval_should_retry=ret_validation.should_retry,
            # Warnings
            warnings=warnings,
        )
