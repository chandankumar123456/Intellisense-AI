# app/agents/pipeline_controller_agent/controller.py
from app.agents.query_understanding_agent.agent import QueryUnderstandingAgent
from app.agents.retrieval_agent.orchestrator import RetrievalOrchestratorAgent
from app.agents.response_synthesizer_agent.synthesizer import ResponseSynthesizer

from app.agents.query_understanding_agent.schema import (
    QueryUnderstandingInput,
    QueryUnderstandingOutput,
    Preferences
)

# IMPORTANT FIX: Import RetrievalParams from retrieval agent schema
from app.agents.retrieval_agent.schema import (
    RetrievalInput,
    RetrievalOutput,
    RetrievalParams as RetrievalParams_RetrievalAgent,
)

from app.agents.response_synthesizer_agent.schema import SynthesisInput, SynthesisOutput

# EviLearn Imports
from app.agents.claim_extraction_agent.agent import ClaimExtractionAgent
from app.agents.claim_extraction_agent.schema import ClaimExtractionInput
from app.agents.verification_agent.agent import VerificationAgent
from app.agents.verification_agent.schema import VerificationInput
from app.agents.explanation_agent.agent import ExplanationAgent
from app.agents.explanation_agent.schema import ExplanationInput

# New specialized agents
from app.agents.intent_resolution_agent.agent import IntentResolutionAgent
from app.agents.intent_resolution_agent.schema import IntentResolutionInput
from app.agents.context_validator_agent.agent import ContextValidatorAgent
from app.agents.context_validator_agent.schema import ContextValidatorInput
from app.agents.failure_detection_agent.agent import FailureDetectionAgent
from app.agents.failure_detection_agent.schema import FailureDetectionInput
from app.agents.coverage_analyzer_agent.agent import CoverageAnalyzerAgent
from app.agents.coverage_analyzer_agent.schema import CoverageAnalysisInput


from .controller_config import (
    DEFAULT_RETRIEVERS,
    DEFAULT_MODEL_NAME,
    DEFAULT_MAX_OUTPUT_TOKENS,
    FALLBACK_INSUFFICIENT_CONTEXT,
    FALLBACK_QUERY_UNDERSTANDING_FAILURE,
    FALLBACK_SYNTHESIZER_FAILURE,
    FALLBACK_NO_KNOWLEDGE,
    NO_KNOWLEDGE_SCORE_THRESHOLD,
)

import time
import datetime
from typing import List, Dict, Any
from dotenv import load_dotenv
from app.core.logging import log_info, log_error
from app.rag.intent_classifier import IntentResult, QueryIntent
from app.rag.query_expander import rewrite_for_retry
from app.rag.subject_detector import SubjectScope


class PipelineControllerAgent:
    def __init__(
        self,
        query_understander: QueryUnderstandingAgent,
        retriever_orchestrator: RetrievalOrchestratorAgent,
        response_synthesizer: ResponseSynthesizer,
        claim_extractor: ClaimExtractionAgent = None,
        verifier: VerificationAgent = None,
        explainer: ExplanationAgent = None,
        intent_resolver: IntentResolutionAgent = None,
        context_validator: ContextValidatorAgent = None,
        failure_detector: FailureDetectionAgent = None,
        coverage_analyzer: CoverageAnalyzerAgent = None,
    ):
        # Load .env file with encoding fallback
        try:
            load_dotenv()
        except UnicodeDecodeError:
            # Try UTF-16 encoding (common on Windows)
            try:
                load_dotenv(encoding='utf-16')
            except Exception:
                # Try UTF-16 with BOM
                try:
                    load_dotenv(encoding='utf-16-le')
                except Exception:
                    # If all encodings fail, continue without .env file
                    pass
        self.query_understander = query_understander
        self.retriever_orchestrator = retriever_orchestrator
        self.response_synthesizer = response_synthesizer
        self.claim_extractor = claim_extractor
        self.verifier = verifier
        self.explainer = explainer

        # New specialized agents (auto-create if not injected)
        self.intent_resolver = intent_resolver or IntentResolutionAgent()
        self.context_validator = context_validator or ContextValidatorAgent()
        self.failure_detector = failure_detector or FailureDetectionAgent()
        self.coverage_analyzer = coverage_analyzer or CoverageAnalyzerAgent()

        self.default_retrievers = DEFAULT_RETRIEVERS
        self.default_model = DEFAULT_MODEL_NAME
        self.default_max_tokens = DEFAULT_MAX_OUTPUT_TOKENS

    async def run(
        self,
        query: str,
        user_id: str,
        session_id: str,
        preferences: Preferences,
        conversation_history: List,
        allow_agentic: bool = False,
        model_name: str = "llama-3.1-8b-instant"
    ) -> Dict[str, Any]:

        start_time = time.time()
        warnings: List[str] = []
        trace: Dict[str, Any] = {}

        # Model selection
        model_name = model_name or self.default_model

        prefs = Preferences(
            response_style=preferences.get("response_style", "concise"),
            max_length=preferences.get("max_length", 300),
            domain=preferences.get("domain", "general")
        )

        # ======================
        # 1. QUERY UNDERSTANDING (LLM-based)
        # ======================
        try:
            self.query_understanding_input = QueryUnderstandingInput(
                query_text=query,
                user_id=user_id,
                session_id=session_id,
                preferences=prefs,
                conversation_history=conversation_history,
                timestamp=datetime.datetime.now()
            )
            self.query_understanding_output: QueryUnderstandingOutput = \
                await self.query_understander.run(self.query_understanding_input)

            trace["query_understanding"] = {
                "rewritten_query": self.query_understanding_output.rewritten_query,
                "intent": self.query_understanding_output.intent,
                "retrievers_to_use": self.query_understanding_output.retrievers_to_use,
                "retrieval_params": self.query_understanding_output.retrieval_params.model_dump(),
                "style_preferences": self.query_understanding_output.style_preferences.model_dump(),
            }

        except Exception as e:
            from app.agents.query_understanding_agent.schema import RetrievalParams, StylePreferences

            warnings.append(f"QueryUnderstanding failed: {e}")

            default_retrieval_params = RetrievalParams(
                top_k_vector=6,
                top_k_keyword=4,
                top_k_web=3,
                top_k_youtube=1
            )
            default_style = StylePreferences(
                type="concise",
                tone="neutral"
            )

            self.query_understanding_output = QueryUnderstandingOutput(
                intent="none",
                rewritten_query=query,
                retrievers_to_use=self.default_retrievers,
                retrieval_params=default_retrieval_params,
                style_preferences=default_style
            )

            trace["query_understanding"] = {
                "rewritten_query": query,
                "intent": "none",
                "retrievers_to_use": self.default_retrievers,
                "retrieval_params": default_retrieval_params.model_dump(),
                "style_preferences": default_style.model_dump(),
            }

        # ======================
        # 2. INTENT & SUBJECT RESOLUTION (dedicated agent)
        # ======================
        intent_resolution = await self.intent_resolver.run(
            IntentResolutionInput(
                query=query,
                llm_rewritten_query=self.query_understanding_output.rewritten_query,
            )
        )
        warnings.extend(intent_resolution.warnings)

        effective_query = intent_resolution.effective_query
        is_conceptual = intent_resolution.is_conceptual

        # Build IntentResult for downstream compatibility
        from app.rag.intent_classifier import classify_intent
        intent_result = classify_intent(query)

        # Build search scope for retrieval
        search_scope = SubjectScope(
            subject=intent_resolution.search_subject,
            confidence=intent_resolution.subject_confidence,
            is_ambiguous=intent_resolution.is_ambiguous,
            content_type=intent_resolution.content_type,
            secondary_subject=intent_resolution.secondary_subject,
        )
        subject_scope = SubjectScope(
            subject=intent_resolution.subject,
            confidence=intent_resolution.subject_confidence,
            is_ambiguous=intent_resolution.is_ambiguous,
            content_type=intent_resolution.content_type,
            secondary_subject=intent_resolution.secondary_subject,
        )

        trace["intent_classification"] = {
            "intent": intent_resolution.intent,
            "target_section": intent_resolution.target_section,
            "has_document_reference": intent_resolution.has_document_reference,
            "confidence": intent_resolution.intent_confidence,
            "explanation": intent_resolution.intent_explanation,
        }
        trace["query_rewriting"] = {
            "llm_rewrite": self.query_understanding_output.rewritten_query,
            "effective_query": effective_query,
        }
        trace["subject_scope"] = subject_scope.model_dump()
        trace["query_structure"] = {
            "query_type": intent_resolution.query_type,
            "confidence": intent_resolution.query_type_confidence,
            "is_conceptual": is_conceptual,
        }

        # ======================
        # 3. RETRIEVAL (section-aware + subject-scoped)
        # ======================
        try:
            converted_params = RetrievalParams_RetrievalAgent(
                **self.query_understanding_output.retrieval_params.model_dump()
            )

            self.retrieval_agent_input = RetrievalInput(
                user_id=user_id,
                session_id=session_id,
                rewritten_query=effective_query,
                retrievers_to_use=self.query_understanding_output.retrievers_to_use,
                retrieval_params=converted_params,
                conversation_history=conversation_history,
                preferences=preferences,
                is_conceptual=is_conceptual
            )

            self.retrieval_agent_output: RetrievalOutput = \
                await self.retriever_orchestrator.run(
                    self.retrieval_agent_input,
                    intent_result=intent_result,
                    subject_scope=search_scope,
                    query_type=intent_resolution.query_type,
                )

            # Automatic fallback for subject filtering
            if search_scope.subject and len(self.retrieval_agent_output.chunks) == 0:
                log_info("Subject-scoped retrieval returned 0 chunks. TRIGGERING FALLBACK: Global Search.")
                warnings.append("subject_filter_fallback_triggered")

                fallback_scope = SubjectScope(
                    subject="",
                    is_ambiguous=True,
                    content_type=search_scope.content_type
                )

                self.retrieval_agent_output = await self.retriever_orchestrator.run(
                    self.retrieval_agent_input,
                    intent_result=intent_result,
                    subject_scope=fallback_scope,
                    query_type=intent_resolution.query_type,
                )

                if self.retrieval_agent_output.retrieval_trace:
                    self.retrieval_agent_output.retrieval_trace["fallback_triggered"] = True

        except Exception as e:
            warnings.append(f"Retrieval failed: {e}")
            self.retrieval_agent_output = RetrievalOutput(
                chunks=[],
                retrieval_trace={},
                trace_id=f"fallback-{int(time.time() * 1000)}",
            )

        # ======================
        # 3.5 KNOWLEDGE COVERAGE ANALYSIS (dedicated agent)
        # ======================
        coverage_result = await self.coverage_analyzer.run(
            CoverageAnalysisInput(
                query=effective_query,
                chunks=self.retrieval_agent_output.chunks,
            )
        )
        trace["coverage_analysis"] = {
            "overall_coverage": coverage_result.overall_coverage,
            "gaps": coverage_result.gaps[:5],
            "needs_gap_fill": coverage_result.needs_gap_fill,
        }

        # ======================
        # 4. CONTEXT VALIDATION (dedicated agent)
        # ======================
        ret_trace = self.retrieval_agent_output.retrieval_trace or {}
        ret_confidence = ret_trace.get("retrieval_confidence", {})
        retrieval_confidence_score = ret_confidence.get("score", 0.0)

        ctx_validation = await self.context_validator.run(
            ContextValidatorInput(
                query=effective_query,
                chunks=self.retrieval_agent_output.chunks,
                intent_result=intent_result,
                retrieval_confidence_score=retrieval_confidence_score,
            )
        )
        warnings.extend(ctx_validation.warnings)

        trace["retrieval_validation"] = {
            "is_valid": ctx_validation.retrieval_is_valid,
            "reason": ctx_validation.retrieval_reason,
            "top_score": ctx_validation.retrieval_top_score,
            "section_match_count": ctx_validation.retrieval_section_match_count,
            "document_match_count": ctx_validation.retrieval_document_match_count,
        }
        trace["context_verification"] = {
            "is_sufficient": ctx_validation.is_sufficient,
            "coverage_score": ctx_validation.coverage_score,
            "answer_signal": ctx_validation.answer_signal_score,
            "has_contradictions": ctx_validation.has_contradictions,
            "evidence_strength": ctx_validation.evidence_strength,
            "recommendation": ctx_validation.recommendation,
            "uncovered_concepts": ctx_validation.uncovered_concepts[:5],
        }
        trace["retrieval_trace"] = self.retrieval_agent_output.retrieval_trace

        # ======================
        # 4.5 DYNAMIC RETRIEVAL LOOP (Agentic Orchestration)
        # ======================
        max_attempts = 3
        attempt = 1
        best_validation = ctx_validation

        while attempt < max_attempts and not best_validation.retrieval_is_valid and best_validation.retrieval_should_retry:
            if len(self.retrieval_agent_output.chunks) == 0:
                break

            log_info(f"Retrieval attempt {attempt} failed validation: {best_validation.retrieval_reason}. Starting attempt {attempt+1}...")
            attempt += 1

            try:
                retry_rewrites = rewrite_for_retry(effective_query, attempt=attempt)
                retry_query = retry_rewrites[0] if retry_rewrites else effective_query + " detailed context"

                relaxed_params = converted_params.model_copy()
                relaxed_params.top_k_vector += 5
                relaxed_params.top_k_keyword += 3

                retry_input = RetrievalInput(
                    user_id=user_id,
                    session_id=session_id,
                    rewritten_query=retry_query,
                    retrievers_to_use=self.query_understanding_output.retrievers_to_use,
                    retrieval_params=relaxed_params,
                    conversation_history=conversation_history,
                    preferences=preferences
                )

                retry_output = await self.retriever_orchestrator.run(
                    retry_input,
                    intent_result=intent_result,
                    subject_scope=subject_scope,
                    query_type=intent_resolution.query_type,
                )

                retry_ctx = await self.context_validator.run(
                    ContextValidatorInput(
                        query=retry_query,
                        chunks=retry_output.chunks,
                        intent_result=intent_result,
                        retrieval_confidence_score=retrieval_confidence_score,
                    )
                )

                if retry_ctx.retrieval_top_score > best_validation.retrieval_top_score:
                    log_info(f"Attempt {attempt} improved score: {best_validation.retrieval_top_score:.3f} -> {retry_ctx.retrieval_top_score:.3f}")
                    self.retrieval_agent_output = retry_output
                    best_validation = retry_ctx
                    converted_params = relaxed_params
                else:
                    log_info(f"Attempt {attempt} did not improve score ({retry_ctx.retrieval_top_score:.3f} vs {best_validation.retrieval_top_score:.3f}).")

            except Exception as e:
                warnings.append(f"Retrieval attempt {attempt} error: {e}")
                log_error(f"Retrieval loop error: {e}")
                break

        grounded_only = best_validation.grounded_only

        # ======================
        # 5. EARLY NO-KNOWLEDGE EXIT
        # ======================
        has_no_chunks = len(self.retrieval_agent_output.chunks) == 0
        has_low_relevance = best_validation.retrieval_top_score < NO_KNOWLEDGE_SCORE_THRESHOLD

        if has_no_chunks or has_low_relevance:
            latency_ms = int((time.time() - start_time) * 1000)
            log_info(
                f"No-knowledge fast path: chunks={len(self.retrieval_agent_output.chunks)}, "
                f"top_score={best_validation.retrieval_top_score:.3f}, latency={latency_ms}ms"
            )
            return {
                "answer": FALLBACK_NO_KNOWLEDGE,
                "confidence": 0.0,
                "warnings": warnings + ["no_relevant_knowledge"],
                "used_chunk_ids": [],
                "retrieval_trace": trace.get("retrieval_trace", {}),
                "query_understanding": trace.get("query_understanding", {}),
                "trace_id": self.retrieval_agent_output.trace_id,
                "latency_ms": latency_ms,
                "raw_model_output": None,
                "metrics": {},
            }

        # ======================
        # 6. FAILURE DETECTION (dedicated agent, pre-synthesis guard)
        # ======================
        failure_result = await self.failure_detector.run(
            FailureDetectionInput(
                query=effective_query,
                chunks=self.retrieval_agent_output.chunks,
                context_verification=None,  # Already evaluated by context_validator
            )
        )
        warnings.extend(failure_result.warnings)

        trace["failure_prediction"] = {
            "risk_level": failure_result.risk_level,
            "should_retry": failure_result.should_retry,
            "should_expand": failure_result.should_expand,
            "should_ground": failure_result.should_ground,
            "signals": failure_result.signals,
            "explanation": failure_result.explanation,
        }

        if failure_result.should_ground and not grounded_only:
            grounded_only = True

        # ======================
        # 7. SYNTHESIS
        # ======================
        try:
            self.response_synthesizer_agent_input = SynthesisInput(
                trace_id=self.retrieval_agent_output.trace_id,
                user_id=user_id,
                session_id=session_id,
                query=self.query_understanding_output.rewritten_query,
                conversation_history=conversation_history,
                preferences=preferences,
                model_name=model_name,
                max_output_tokens=preferences.get("max_tokens", self.default_max_tokens),
                retrieved_chunks=self.retrieval_agent_output.chunks,
                grounded_only=grounded_only,
                retrieval_confidence=retrieval_confidence_score,
            )
            self.response_synthesizer_agent_output: SynthesisOutput = \
                await self.response_synthesizer.run(self.response_synthesizer_agent_input)

        except Exception as e:
            warnings.append(f"Synthesizer failed: {e}")
            self.response_synthesizer_agent_output = SynthesisOutput(
                answer=FALLBACK_SYNTHESIZER_FAILURE,
                used_chunk_ids=[],
                trace_id=self.retrieval_agent_output.trace_id,
                confidence=0.0,
                warnings=[str(e)],
                raw_model_output=None,
                reasoning=None,
                metrics={},
            )

        if self.response_synthesizer_agent_output.answer == "INSUFFICIENT_CONTEXT":
            warnings.append("Synthesizer reported INSUFFICIENT_CONTEXT.")
            self.response_synthesizer_agent_output.answer = FALLBACK_INSUFFICIENT_CONTEXT
            self.response_synthesizer_agent_output.confidence = 0.0

        # ======================
        # FINAL OUTPUT
        # ======================
        latency_ms = int((time.time() - start_time) * 1000)

        final_payload = {
            "answer": self.response_synthesizer_agent_output.answer,
            "confidence": self.response_synthesizer_agent_output.confidence,
            "warnings": warnings + self.response_synthesizer_agent_output.warnings,
            "used_chunk_ids": self.response_synthesizer_agent_output.used_chunk_ids,
            "retrieval_trace": trace["retrieval_trace"],
            "query_understanding": trace["query_understanding"],
            "trace_id": self.response_synthesizer_agent_output.trace_id,
            "latency_ms": latency_ms,
            "raw_model_output": self.response_synthesizer_agent_output.raw_model_output,
            "metrics": self.response_synthesizer_agent_output.metrics,
        }

        return final_payload

    async def run_verification_flow(
        self,
        text: str,
        user_id: str,
        session_id: str,
        preferences: Preferences = None
    ) -> Dict[str, Any]:
        """
        Orchestrates the Claim Verification Flow (EviLearn).
        """
        log_info(f"Starting Verification Flow for user={user_id}")
        start_time = time.time()
        
        # 1. Claim Extraction
        log_info("Step 1: Extracting Claims...")
        extraction_output = await self.claim_extractor.run(ClaimExtractionInput(text=text))
        claims = extraction_output.claims
        log_info(f"Extracted {len(claims)} claims.")
        
        verified_claims = []
        
        # 2. Verification Loop
        log_info("Step 2: Verifying Claims...")
        for claim in claims:
            # 2a. Retrieval for this claim
            # We use a constructed query based on the claim
            retrieval_query = f"Verify claim: {claim.claim_text}"
            
            # Using defaults for retrieval params if not provided
            # Logic similar to run() but simplified for single claim
            retrieval_params = RetrievalParams_RetrievalAgent(
                top_k_vector=3,
                top_k_keyword=2, # focus on precision
                top_k_web=0,
                top_k_youtube=0
            )

            retrieval_input = RetrievalInput(
                user_id=user_id,
                session_id=session_id,
                rewritten_query=retrieval_query,
                retrievers_to_use=["vector", "keyword"],
                retrieval_params=retrieval_params,
                conversation_history=[],
                preferences=preferences if preferences else Preferences(response_style="concise", max_length=300, domain="general")
            )
            
            retrieval_output = await self.retriever_orchestrator.run(retrieval_input)
            chunks = [c.text for c in retrieval_output.chunks]
            
            # 2b. Verification
            verification_input = VerificationInput(
                claim_text=claim.claim_text,
                retrieved_chunks=chunks  # Passing text content
            )
            verification_output = await self.verifier.run(verification_input)
            
            verified_claims.append({
                "claim_text": claim.claim_text,
                "original_text": claim.original_text_segment,
                "status": verification_output.result.status,
                "confidence": verification_output.result.confidence_score,
                "explanation": verification_output.result.explanation,
                "evidence_chunks": retrieval_output.chunks # Store full chunk objects for frontend reference
            })
            
        # 3. Explanation Generation
        # 3. Explanation Generation
        log_info("Step 3: Generating Explanation...")
        try:
            explanation_output = await self.explainer.run(ExplanationInput(claims_with_verification=verified_claims))
            summary = explanation_output.summary
            detailed_report = explanation_output.detailed_report
        except Exception as e:
            log_error(f"Explanation failed: {e}")
            summary = "Could not generate summary."
            detailed_report = "Could not generate report."
        
        latency_ms = int((time.time() - start_time) * 1000)
        
        return {
            "verified_claims": verified_claims,
            "summary": summary,
            "detailed_report": detailed_report,
            "latency_ms": latency_ms
        }

