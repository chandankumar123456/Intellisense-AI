# app/agents/failure_detection_agent/agent.py
"""
Failure Detection & Recovery Agent.

Wraps the pre-synthesis failure prediction logic into a dedicated agent.
Evaluates retrieval quality signals and predicts whether synthesis will
produce a grounded answer. Previously inlined in PipelineControllerAgent
(section 2.8).
"""

from app.agents.failure_detection_agent.schema import (
    FailureDetectionInput,
    FailureDetectionOutput,
)
from app.rag.failure_predictor import predict_failure
from app.core.config import FAILURE_PREDICTION_ENABLED
from app.core.logging import log_info, log_error
from typing import List


class FailureDetectionAgent:
    """
    Predicts whether the current retrieval will fail at synthesis.
    Provides actionable recommendations (retry, expand, ground).
    """

    async def run(self, input: FailureDetectionInput) -> FailureDetectionOutput:
        warnings: List[str] = []

        if not FAILURE_PREDICTION_ENABLED or len(input.chunks) == 0:
            return FailureDetectionOutput(
                explanation="failure_prediction_disabled_or_no_chunks",
            )

        try:
            prediction = predict_failure(
                chunks=input.chunks,
                query=input.query,
                context_verification=input.context_verification,
                retrieval_confidence=input.retrieval_confidence,
            )

            if prediction.should_ground:
                warnings.append("grounded_mode_failure_prediction")
                log_info(
                    f"[FailureDetection] grounded mode activated "
                    f"(risk={prediction.risk_level:.3f})"
                )
            elif prediction.should_retry:
                warnings.append("failure_prediction_retry_recommended")
                log_info(
                    f"[FailureDetection] retry recommended "
                    f"(risk={prediction.risk_level:.3f}: {prediction.explanation})"
                )

            return FailureDetectionOutput(
                risk_level=prediction.risk_level,
                should_retry=prediction.should_retry,
                should_expand=prediction.should_expand,
                should_ground=prediction.should_ground,
                signals=prediction.signals,
                explanation=prediction.explanation,
                warnings=warnings,
            )

        except Exception as e:
            log_error(f"[FailureDetection] prediction error: {e}")
            return FailureDetectionOutput(
                explanation=f"failure_prediction_error: {e}",
            )
