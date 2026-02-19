# app/agents/intent_resolution_agent/agent.py
"""
Intent & Subject Resolution Agent.

Consolidates intent classification, subject detection, query structural
classification, and deterministic query rewriting into a dedicated agent.
Previously this logic was inlined in PipelineControllerAgent (sections 1.5–1.8).
"""

from app.agents.intent_resolution_agent.schema import (
    IntentResolutionInput,
    IntentResolutionOutput,
)
from app.rag.intent_classifier import classify_intent
from app.rag.query_rewriter import rewrite_query
from app.rag.subject_detector import detect_subject, SubjectScope
from app.rag.query_classifier import query_classifier, QueryType
from app.core.logging import log_info


# Confidence threshold below which strict subject filtering is disabled
SUBJECT_CONFIDENCE_THRESHOLD = 0.45


class IntentResolutionAgent:
    """
    Resolves the intent, subject scope, structural query type, and effective
    retrieval query for a user question. All rule-based, no LLM calls.
    """

    async def run(self, input: IntentResolutionInput) -> IntentResolutionOutput:
        warnings: list[str] = []

        # ── 1. Intent classification (rule-based) ──
        intent_result = classify_intent(input.query)
        log_info(
            f"[IntentResolution] intent={intent_result.intent.value}, "
            f"section={intent_result.target_section}, "
            f"confidence={intent_result.confidence}"
        )

        # ── 2. Deterministic query rewriting ──
        rewritten_for_retrieval = rewrite_query(
            raw_query=input.query,
            intent_result=intent_result,
        )
        llm_rewrite = input.llm_rewritten_query or input.query
        if len(rewritten_for_retrieval.split()) > len(llm_rewrite.split()):
            effective_query = rewritten_for_retrieval
        else:
            effective_query = llm_rewrite

        log_info(f"[IntentResolution] effective_query='{effective_query}'")

        # ── 3. Subject scope detection ──
        subject_scope = detect_subject(input.query)

        search_subject = subject_scope.subject
        subject_filter_disabled = False

        if subject_scope.subject and subject_scope.confidence < SUBJECT_CONFIDENCE_THRESHOLD:
            log_info(
                f"[IntentResolution] Subject '{subject_scope.subject}' low confidence "
                f"({subject_scope.confidence:.2f} < {SUBJECT_CONFIDENCE_THRESHOLD}). "
                f"Disabling strict filtering."
            )
            search_subject = ""
            subject_filter_disabled = True
            warnings.append("low_conf_subject_filter_disabled")

        if subject_scope.is_ambiguous:
            warnings.append("ambiguous_subject_scope")

        # ── 4. Query structural classification ──
        query_type_result = query_classifier.classify(input.query)
        log_info(
            f"[IntentResolution] query_type={query_type_result.query_type.value} "
            f"(conf={query_type_result.confidence})"
        )

        is_conceptual = query_type_result.query_type == QueryType.CONCEPTUAL
        if is_conceptual:
            if "definition" not in effective_query.lower() and "concept" not in effective_query.lower():
                effective_query += " definition concept principle architecture"
                log_info(f"[IntentResolution] Conceptual expansion: '{effective_query}'")

        return IntentResolutionOutput(
            # Intent
            intent=intent_result.intent.value,
            target_section=intent_result.target_section,
            has_document_reference=intent_result.has_document_reference,
            intent_confidence=intent_result.confidence,
            intent_explanation=intent_result.explanation,
            # Subject
            subject=subject_scope.subject,
            subject_confidence=subject_scope.confidence,
            is_ambiguous=subject_scope.is_ambiguous,
            content_type=subject_scope.content_type,
            secondary_subject=subject_scope.secondary_subject,
            search_subject=search_subject,
            subject_filter_disabled=subject_filter_disabled,
            # Query type
            query_type=query_type_result.query_type.value,
            query_type_confidence=query_type_result.confidence,
            is_conceptual=is_conceptual,
            # Effective query
            effective_query=effective_query,
            warnings=warnings,
        )
