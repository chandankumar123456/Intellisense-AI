# app/rag/retrieval_trace.py
"""
Structured Retrieval Trace Logger.

Lightweight, non-blocking trace collector that records every stage of the
retrieval pipeline for debugging and system improvement.

Stages tracked:
  1. Query variants generated
  2. Retrieved chunks (before & after rerank)
  3. Confidence scores per stage
  4. Expansion decisions
  5. Retry triggers
  6. Coverage gaps
  7. Clustering results
  8. Failure prediction
  9. Grounded mode activation
"""

import time
from typing import Any, Dict, List, Optional
from uuid import uuid4


class RetrievalTraceCollector:
    """
    Collects structured trace data across all retrieval stages.
    Each stage is logged as a named entry with timing information.
    Thread-safe for single-request use (one collector per request).
    """

    def __init__(self, query: str, trace_id: Optional[str] = None):
        self._trace_id = trace_id or str(uuid4())
        self._query = query
        self._start_time = time.time()
        self._stages: List[Dict[str, Any]] = []
        self._metadata: Dict[str, Any] = {}

    @property
    def trace_id(self) -> str:
        return self._trace_id

    def log_stage(
        self,
        stage_name: str,
        data: Dict[str, Any],
        *,
        status: str = "success",
    ) -> None:
        """
        Log a retrieval stage.

        Args:
            stage_name: Human-readable stage identifier
                (e.g. 'vector_search', 'rerank', 'confidence_early').
            data: Stage-specific payload (counts, scores, decisions).
            status: 'success', 'skipped', 'failed', 'partial'.
        """
        entry = {
            "stage": stage_name,
            "status": status,
            "timestamp_ms": int((time.time() - self._start_time) * 1000),
            "data": data,
        }
        self._stages.append(entry)

    def set_metadata(self, key: str, value: Any) -> None:
        """Attach top-level metadata (intent, subject, query_type, etc.)."""
        self._metadata[key] = value

    def log_chunks_snapshot(
        self,
        label: str,
        chunks: list,
        *,
        max_preview: int = 5,
    ) -> None:
        """
        Log a snapshot of chunks at a specific pipeline point.
        Keeps only essential fields to stay lightweight.
        """
        snapshot = []
        for c in chunks[:max_preview]:
            entry = {
                "chunk_id": getattr(c, "chunk_id", None),
                "document_id": getattr(c, "document_id", ""),
                "score": getattr(c, "raw_score", 0.0),
                "text_len": len(getattr(c, "text", "")),
                "section_type": getattr(c, "section_type", None),
                "source_type": getattr(c, "source_type", ""),
            }
            # Include rerank score if in metadata
            meta = getattr(c, "metadata", {}) or {}
            if "rerank_score" in meta:
                entry["rerank_score"] = meta["rerank_score"]
            snapshot.append(entry)

        self.log_stage(f"chunks_snapshot_{label}", {
            "total_count": len(chunks),
            "preview_count": len(snapshot),
            "chunks": snapshot,
        })

    def log_confidence(
        self,
        label: str,
        confidence_result: Any,
    ) -> None:
        """Log a confidence assessment result."""
        data = {
            "score": getattr(confidence_result, "score", 0.0),
            "level": getattr(confidence_result, "level", "UNKNOWN"),
            "recommendation": getattr(confidence_result, "recommendation", ""),
            "top_similarity": getattr(confidence_result, "top_similarity", 0.0),
            "keyword_overlap": getattr(confidence_result, "keyword_overlap", 0.0),
            "semantic_coverage": getattr(confidence_result, "semantic_coverage", 0.0),
            "information_density": getattr(confidence_result, "information_density", 0.0),
        }
        # Handle enum level
        if hasattr(data["level"], "value"):
            data["level"] = data["level"].value
        self.log_stage(f"confidence_{label}", data)

    def log_decision(
        self,
        decision_name: str,
        decision: str,
        reason: str = "",
        **extra: Any,
    ) -> None:
        """Log a pipeline decision (expand, retry, ground, skip, etc.)."""
        self.log_stage(f"decision_{decision_name}", {
            "decision": decision,
            "reason": reason,
            **extra,
        })

    def get_trace(self) -> Dict[str, Any]:
        """
        Return the complete structured trace.
        This is attached to RetrievalOutput for downstream consumption.
        """
        total_ms = int((time.time() - self._start_time) * 1000)
        return {
            "trace_id": self._trace_id,
            "query": self._query,
            "total_duration_ms": total_ms,
            "stage_count": len(self._stages),
            "metadata": self._metadata,
            "stages": self._stages,
        }

    def get_summary(self) -> Dict[str, Any]:
        """
        Return a lightweight summary for frontend display.
        Omits detailed chunk snapshots.
        """
        summary_stages = []
        for s in self._stages:
            entry = {
                "stage": s["stage"],
                "status": s["status"],
                "timestamp_ms": s["timestamp_ms"],
            }
            # Include key numeric fields from data
            data = s.get("data", {})
            for key in ("total_count", "score", "level", "decision", "risk_level",
                        "clusters_formed", "coverage_score", "gaps_found"):
                if key in data:
                    entry[key] = data[key]
            summary_stages.append(entry)

        return {
            "trace_id": self._trace_id,
            "total_duration_ms": int((time.time() - self._start_time) * 1000),
            "stages": summary_stages,
        }
