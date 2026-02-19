# app/student_knowledge/agent.py
"""
Student Knowledge Ingestion Agent — Production-Hardened.
Autonomous pipeline: fetch → dedup → chunk → enrich → embed → upsert → verify → validate.
All steps are idempotent, traced, student-scoped, and recoverable.
"""

import asyncio
import json
import os
import time
import traceback
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Tuple

from app.core.logging import log_info, log_error, log_warning
from app.core.config import (
    STUDENT_VECTOR_NAMESPACE_PREFIX,
    STUDENT_TRACE_DIR,
    STUDENT_INDEX_VALIDATION_THRESHOLD,
    STUDENT_MAX_RETRY_ATTEMPTS,
    STUDENT_MIN_CONTENT_CHARS,
    STUDENT_MIN_TOKEN_COUNT,
    STUDENT_MAX_REINDEX_ATTEMPTS,
    STUDENT_REINDEX_BASE_DELAY_SECONDS,
    STUDENT_REINDEX_MAX_DELAY_SECONDS,
    STUDENT_REINDEX_COOLDOWN_HOURS,
    STUDENT_MAX_CONCURRENT_REPAIRS,
    STUDENT_EMBEDDING_MODEL_ID,
    STUDENT_EMBEDDING_MODEL_VERSION,
    STUDENT_DRIFT_SEVERE_THRESHOLD,
)
from app.student_knowledge.db import StudentKnowledgeDB
from app.student_knowledge.fetcher import fetch_file, fetch_youtube, fetch_website, compute_fingerprint
from app.student_knowledge.chunker import chunk_document
from app.student_knowledge.enricher import enrich_chunks
from app.student_knowledge.metrics import metrics


class StudentKnowledgeAgent:
    """
    Autonomous agent for converting student uploads into retrieval-ready knowledge.

    Pipeline:
    1. Receive upload event
    2. Mark processing + queue metrics
    3. Fetch & extract content
    4. Deduplicate (true duplicate status)
    5. Chunk with overlap
    6. Enrich with concepts
    7. Batch embed (partial indexing on failure)
    8. Upsert to student-scoped vector namespace
    9. Post-upsert verification
    10. Retrieval validation (grounding check)
    11. Update status + persist trace
    12. Emit metrics
    """

    def __init__(self):
        self.db = StudentKnowledgeDB()
        self._repair_semaphore = asyncio.Semaphore(STUDENT_MAX_CONCURRENT_REPAIRS)

    # ──────────────────────────────────────────
    async def monitor_index_health(self, student_id: str, auto_reindex: bool = True):
        """
        Periodically check the semantic health of indexed content.
        Detects drift, degradation, and triggers repairs.
        Includes: backoff guard, severity gating, and repair throttling.
        """
        log_info(f"[Agent] Starting health check for student {student_id}")
        
        # 1. Get candidates
        uploads = self.db.get_uploads_needing_maintenance(student_id)
        if not uploads:
            log_info("[Agent] No uploads need maintenance.")
            return

        for upload in uploads:
            upload_id = upload["upload_id"]
            try:
                # 2. Check health
                health_status, score = await self._check_upload_health(upload)
                
                # 3. Handle degradation — only auto-reindex if severe
                if health_status == "reindex_required" and auto_reindex:
                    # Guard: check reindex attempts before allowing auto-reindex
                    attempt_count, last_at = self.db.get_reindex_attempts(upload_id)
                    
                    if attempt_count >= STUDENT_MAX_REINDEX_ATTEMPTS:
                        log_warning(f"[Agent] Upload {upload_id} exceeded max reindex attempts ({attempt_count}). Marking exhausted.")
                        self.db.update_status(upload_id, "reindex_exhausted",
                                              error_reason=f"Max reindex attempts ({STUDENT_MAX_REINDEX_ATTEMPTS}) exhausted")
                        metrics.inc("reindex_exhausted")
                        continue
                    
                    # Guard: check cooldown
                    if last_at and not self._reindex_cooldown_elapsed(last_at):
                        log_info(f"[Agent] Upload {upload_id} in reindex cooldown. Skipping.")
                        metrics.inc("reindex_backoff_skipped")
                        continue
                    
                    # Guard: only auto-reindex on severe degradation
                    if score >= STUDENT_DRIFT_SEVERE_THRESHOLD:
                        log_info(f"[Agent] Upload {upload_id} health_score={score:.1f} above severe threshold. Skipping auto-reindex.")
                        self.db.update_health_status(upload_id, score, status=health_status)
                        continue
                    
                    log_warning(f"[Agent] Auto-reindexing {upload_id} due to {upload['status']} (score={score:.1f})")
                    metrics.inc("drift_detected")
                    await self.reindex_upload(upload_id, student_id)
                    continue
                     
                if health_status != upload["status"]:
                    log_warning(f"[Agent] Upload {upload_id} drifted: {upload['status']} -> {health_status}")
                    self.db.update_status(upload_id, health_status, error_reason="Health check failed")

                self.db.update_health_status(upload_id, score, status=health_status if health_status != "indexed" else None)
                
            except Exception as e:
                log_error(f"[Agent] Health check failed for {upload_id}: {e}")

    async def _check_upload_health(self, upload: Dict[str, Any]) -> tuple[str, float]:
        """
        Diagnose upload health.
        Returns (recommended_status, health_score).
        """
        upload_id = upload["upload_id"]
        current_status = upload["status"]
        
        # A. Stale Partial/Weak State Recovery
        # If in bad state for > 24 hours (implied by get_uploads_needing_maintenance logic), force reindex
        if current_status in ["indexed_partial", "indexed_weak", "retrieval_unstable"]:
            return "reindex_required", 0.0

        # B. Semantic & Embedding Drift Check
        # Re-verify a sample
        namespace = upload["vector_namespace"]
        
        # We need text to probe. Query vector DB for *any* chunk
        from app.storage import storage_manager
        
        try:
            # Fetch generic probe if probe_text exists
            probe_text = upload.get("probe_text")
            if not probe_text:
                # If legacy upload without probe text, we can't do exact semantic check
                # fallback to basic existence check?
                # For now, assume ok if we can't probe
                return "indexed", 10.0

            # Generate probe vector
            from app.agents.retrieval_agent.utils import embed_text
            probe_vec = (await embed_text(probe_text))[0]

            # Query vector DB
            results = storage_manager.vectors.query(
                vector=probe_vec,
                top_k=5,
                namespace=namespace,
                include_metadata=True
            )

            matches = results.get("matches", [])
            # Check if any match belongs to this upload_id
            found = any(m.get("metadata", {}).get("upload_id") == upload_id for m in matches)
            
            if not found:
                 return "index_drift_detected", 2.0
            
            # Additional check: Similarity score of the top match for this upload
            # If top match is low confidence, might be drift
            top_score = next((m["score"] for m in matches if m.get("metadata", {}).get("upload_id") == upload_id), 0.0)
            if top_score < 0.6: # configurable threshold
                 return "index_quality_degraded", top_score * 10

            return "indexed", 10.0

        except Exception as e:
            log_error(f"[Agent] Health check error: {e}")
            return "index_quality_degraded", 0.0

    async def reindex_upload(self, upload_id: str, student_id: str):
        """
        Trigger re-indexing with exponential backoff and repair throttling.
        Guards: max attempts, cooldown, concurrent repair limit.
        """
        # ── Guard: max reindex attempts ──
        attempt_count, last_at = self.db.get_reindex_attempts(upload_id)
        if attempt_count >= STUDENT_MAX_REINDEX_ATTEMPTS:
            log_warning(f"[Agent] Reindex blocked for {upload_id}: {attempt_count} attempts exhausted")
            self.db.update_status(upload_id, "reindex_exhausted",
                                  error_reason=f"Max reindex attempts ({STUDENT_MAX_REINDEX_ATTEMPTS}) exhausted")
            metrics.inc("reindex_exhausted")
            return

        # ── Guard: cooldown check ──
        if last_at and not self._reindex_cooldown_elapsed(last_at):
            log_info(f"[Agent] Reindex cooldown active for {upload_id}. Skipping.")
            self.db.update_status(upload_id, "reindex_cooldown",
                                  error_reason=f"Cooldown active (last attempt: {last_at})")
            metrics.inc("reindex_backoff_skipped")
            return

        # ── Guard: exponential backoff delay ──
        if attempt_count > 0:
            delay = min(
                STUDENT_REINDEX_BASE_DELAY_SECONDS * (2 ** (attempt_count - 1)),
                STUDENT_REINDEX_MAX_DELAY_SECONDS
            )
            log_info(f"[Agent] Reindex backoff for {upload_id}: waiting {delay}s (attempt {attempt_count + 1}/{STUDENT_MAX_REINDEX_ATTEMPTS})")
            await asyncio.sleep(delay)

        # ── Repair throttling via semaphore ──
        if self._repair_semaphore.locked():
            log_info(f"[Agent] Repair throttled for {upload_id}: max concurrent repairs reached")
            metrics.inc("repair_throttled")

        async with self._repair_semaphore:
            # Record the attempt
            self.db.record_reindex_attempt(upload_id)
            log_info(f"[Agent] Re-indexing {upload_id} (attempt {attempt_count + 1}/{STUDENT_MAX_REINDEX_ATTEMPTS})...")
            self.db.update_status(upload_id, "processing", error_reason="Re-indexing triggered")
            
            upload = self.db.get_upload(upload_id)
            if not upload:
                return

            text = None
            source_type = upload["source_type"]
            source_uri = upload["source_uri"]

            # 1. Try re-fetch if URL
            if source_type in ["website", "youtube", "web"]:
                 try:
                    from app.student_knowledge.fetcher import fetch_url
                    text, _ = await fetch_url(source_uri)
                 except Exception:
                    log_warning(f"[Agent] Failed to re-fetch URL {source_uri}, trying vector reconstruction")

            # 2. Try reconstruction from vector DB (for files or failed URLs)
            if not text:
                try:
                    from app.storage import storage_manager
                    namespace = upload["vector_namespace"] or f"{STUDENT_VECTOR_NAMESPACE_PREFIX}{student_id}"
                    
                    query_vec = [0.0] * 1536 # Dummy vector
                    results = storage_manager.vectors.query(
                        vector=query_vec, 
                        top_k=1000,
                        namespace=namespace,
                        filter={"upload_id": upload_id},
                        include_metadata=True
                    )
                    matches = results.get("matches", [])
                    matches.sort(key=lambda x: x.get("metadata", {}).get("chunk_index", 0))
                    chunks_text = [m.get("metadata", {}).get("text", "") for m in matches]
                    if chunks_text:
                        text = "\n\n".join(chunks_text)
                except Exception as e:
                    log_error(f"[Agent] Vector reconstruction failed: {e}")

            if text:
                result = await self._run_pipeline(
                    text=text,
                    structure={"title": upload["provided_title"]},
                    title=upload["provided_title"] or "Re-indexed",
                    upload_id=upload_id,
                    student_id=student_id,
                    source_type=source_type,
                    source_uri=source_uri,
                    tags=json.loads(upload["tags"] or "[]"),
                    retry_count=0
                )
                # On success, reset reindex attempts
                if result and result.get("status") in ("indexed", "indexed_partial"):
                    self.db.reset_reindex_attempts(upload_id)
                    log_info(f"[Agent] Reindex successful for {upload_id}, attempts reset.")
            else:
                 self.db.update_status(upload_id, "reindex_required", error_reason="Could not recover content source")

    @staticmethod
    def _reindex_cooldown_elapsed(last_reindex_at: str) -> bool:
        """Check if enough time has passed since the last reindex attempt."""
        try:
            last_dt = datetime.fromisoformat(last_reindex_at)
            cooldown = timedelta(hours=STUDENT_REINDEX_COOLDOWN_HOURS)
            return datetime.utcnow() >= last_dt + cooldown
        except (ValueError, TypeError):
            return True  # If parsing fails, allow reindex

    async def ingest_file_upload(
        self,
        file_bytes: bytes,
        filename: str,
        student_id: str,
        upload_id: str,
        provided_title: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Full ingestion pipeline for a file upload."""
        trace = self._init_trace(upload_id, student_id, "file", filename)
        metrics.inc("ingest_total")
        metrics.inc("queue_size")

        try:
            self.db.update_status(upload_id, "processing")
            self._trace_step(trace, "mark_processing", "ok")

            # Initialize retry tracking
            retry_count = 0
            last_retry_reason = None

            # Step 2: Fetch and extract content
            # Step 2: Fetch and extract content
            log_info(f"[Agent] Fetching file: {filename}")
            t0 = time.time()
            try:
                result = await asyncio.to_thread(fetch_file, file_bytes, filename)
            except Exception as e:
                self.db.update_status(upload_id, "extraction_failed", error_reason=str(e))
                self._trace_step(trace, "fetch", "extraction_failed", duration_ms=self._elapsed(t0), extra={"error": str(e)})
                self._persist_trace(student_id, upload_id, trace)
                self._persist_trace(student_id, upload_id, trace)
                return {"status": "extraction_failed", "upload_id": upload_id, "trace": trace}

            if not self._check_content_quality(result.get("text", "")):
                self.db.update_status(upload_id, "low_information_content", error_reason="Content has low information density or is boilerplate")
                self._trace_step(trace, "fetch", "low_information_content", duration_ms=self._elapsed(t0))
                self._persist_trace(student_id, upload_id, trace)
                return {"status": "low_information_content", "upload_id": upload_id, "trace": trace}

            text = result.get("text", "")
            if not text or len(text) < STUDENT_MIN_CONTENT_CHARS:
                 self.db.update_status(upload_id, "insufficient_content", error_reason="File content empty or too short")
                 self._trace_step(trace, "fetch", "insufficient_content", duration_ms=self._elapsed(t0))
                 self._persist_trace(student_id, upload_id, trace)
                 return {"status": "insufficient_content", "upload_id": upload_id, "trace": trace}

            structure = result["structure"]
            fingerprint = result["fingerprint"]
            title = provided_title or result["title"]
            self._trace_step(trace, "fetch", "ok", duration_ms=self._elapsed(t0), extra={
                "chars": len(text),
                "content_type": result["content_type"],
                "ocr_used": result.get("ocr_used", False),
                "ocr_confidence": result.get("ocr_confidence"),
            })

            # Step 3: Deduplicate
            dedup_result = self._check_dedup(upload_id, student_id, fingerprint, trace)
            if dedup_result:
                metrics.inc("ingest_duplicate")
                metrics.dec("queue_size")
                self._persist_trace(student_id, upload_id, trace)
                return dedup_result

            # Step 4-11: Run common pipeline
            return await self._run_pipeline(
                text=text, structure=structure, title=title,
                upload_id=upload_id, student_id=student_id,
                source_type="file", source_uri=filename,
                tags=tags, trace=trace,
                retry_count=retry_count, last_retry_reason=last_retry_reason,
            )

        except Exception as e:
            metrics.inc("ingest_fail")
            metrics.dec("queue_size")
            result = self._handle_error(upload_id, e, trace)
            self._persist_trace(student_id, upload_id, trace)
            return result

    async def ingest_url(
        self,
        url: str,
        source_type: str,
        student_id: str,
        upload_id: str,
        provided_title: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Full ingestion pipeline for a URL (YouTube or website)."""
        trace = self._init_trace(upload_id, student_id, source_type, url)
        metrics.inc("ingest_total")
        metrics.inc("queue_size")

        try:
            self.db.update_status(upload_id, "processing")
            self._trace_step(trace, "mark_processing", "ok")

            # Fetch
            # Fetch with robust retry
            log_info(f"[Agent] Fetching {source_type}: {url}")
            t0 = time.time()
            result = None
            fetch_error = None
            
            for attempt in range(STUDENT_MAX_RETRY_ATTEMPTS):
                try:
                    if source_type == "youtube":
                        result = await asyncio.to_thread(fetch_youtube, url)
                    else:
                        result = await asyncio.to_thread(fetch_website, url)
                    break
                except Exception as e:
                    fetch_error = e
                    if attempt < STUDENT_MAX_RETRY_ATTEMPTS - 1:
                        await asyncio.sleep(1 * (attempt + 1))
                        retry_count += 1
                        last_retry_reason = str(e)
            
            if not result:
                raise ValueError(f"Failed to fetch {source_type} after retries: {fetch_error}")

            text = result.get("text", "")
            if not text or len(text) < STUDENT_MIN_CONTENT_CHARS:
                 self.db.update_status(upload_id, "insufficient_content", error_reason="Content too short")
                 self._trace_step(trace, "fetch", "insufficient_content", duration_ms=self._elapsed(t0))
                 self._persist_trace(student_id, upload_id, trace)
                 return {"status": "insufficient_content", "upload_id": upload_id, "trace": trace}

            structure = result["structure"]
            fingerprint = result["fingerprint"]
            title = provided_title or result["title"]
            timestamps = result.get("timestamps")
            transcript_status = result.get("transcript_status", "unknown")
            
            self._trace_step(trace, "fetch", "ok", duration_ms=self._elapsed(t0), extra={
                "chars": len(text),
                "content_type": result["content_type"],
                "transcript_status": transcript_status,
            })

            # Dedup
            dedup_result = self._check_dedup(upload_id, student_id, fingerprint, trace)
            if dedup_result:
                metrics.inc("ingest_duplicate")
                metrics.dec("queue_size")
                self._persist_trace(student_id, upload_id, trace)
                return dedup_result

            # Step 4-11: Run common pipeline
            return await self._run_pipeline(
                text=text, structure=structure, title=title,
                upload_id=upload_id, student_id=student_id,
                source_type=source_type, source_uri=url,
                tags=tags, timestamps=timestamps, trace=trace,
                retry_count=retry_count, last_retry_reason=last_retry_reason,
            )

        except Exception as e:
            metrics.inc("ingest_fail")
            metrics.dec("queue_size")
            result = self._handle_error(upload_id, e, trace)
            self._persist_trace(student_id, upload_id, trace)
            return result

    # ──────────────────────────────────────────
    # Core pipeline
    # ──────────────────────────────────────────

    async def _run_pipeline(
        self,
        text: str,
        structure: Dict[str, Any],
        title: str,
        upload_id: str,
        student_id: str,
        source_type: str,
        source_uri: str,
        tags: Optional[List[str]] = None,
        timestamps: Optional[List[Dict]] = None,
        trace: Optional[Dict] = None,
        retry_count: int = 0,
        last_retry_reason: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Common pipeline: chunk → enrich → embed → upsert → verify → validate."""
        trace = trace or self._init_trace(upload_id, student_id, source_type, source_uri)
        
        # Save probe text immediately for future health checks (first 500 chars)
        if text:
             self.db.update_status(upload_id, "processing", probe_text=text[:500])

        namespace = f"{STUDENT_VECTOR_NAMESPACE_PREFIX}{student_id}"

        # ── Chunk ──
        log_info(f"[Agent] Chunking {upload_id}...")
        t0 = time.time()
        chunks = chunk_document(
            text=text, upload_id=upload_id, student_id=student_id,
            structure=structure, timestamps=timestamps,
        )
        if not chunks:
            raise ValueError("Chunking produced no chunks")
        # Add token_count to each chunk
        for c in chunks:
            c["token_count"] = len(c["text"].split())
        total_tokens = sum(c["token_count"] for c in chunks)
        self._trace_step(trace, "chunk", "ok", duration_ms=self._elapsed(t0), extra={
            "count": len(chunks), "total_tokens": total_tokens,
        })

        # ── Enrich ──
        log_info(f"[Agent] Enriching {len(chunks)} chunks...")
        t0 = time.time()
        chunks = enrich_chunks(chunks)
        self._trace_step(trace, "enrich", "ok", duration_ms=self._elapsed(t0))

        # ── Embed (with partial indexing) ──
        log_info(f"[Agent] Embedding {len(chunks)} chunks...")
        t0 = time.time()
        embeddings, embed_failures = await self._batch_embed(chunks)
        embed_duration = self._elapsed(t0)
        metrics.inc("embed_latency_sum_ms", embed_duration)

        embedded_count = len(embeddings)
        total_count = len(chunks)
        is_partial = embedded_count < total_count and embedded_count > 0

        self._trace_step(trace, "embed", "partial" if is_partial else "ok", duration_ms=embed_duration, extra={
            "embedded_count": embedded_count,
            "total_count": total_count,
            "failures": embed_failures,
        })

        if embedded_count == 0:
            # Complete embed failure
            self.db.update_status(upload_id, "index_failed", error_reason="All embedding batches failed")
            trace["status"] = "index_failed"
            self._persist_trace(student_id, upload_id, trace)
            metrics.inc("ingest_fail")
            metrics.dec("queue_size")
            return {"status": "index_failed", "upload_id": upload_id, "trace": trace}

        # Trim chunks to only those that succeeded
        chunks_to_index = chunks[:embedded_count]

        # ── Upsert ──
        log_info(f"[Agent] Upserting {embedded_count} vectors...")
        await self._upsert_vectors(
            chunks_to_index, embeddings, namespace,
            source_type, source_uri, title,
        )
        self._trace_step(trace, "upsert", "ok", duration_ms=self._elapsed(t0), extra={
            "namespace": namespace, "count": embedded_count,
        })

        # ── Embedding Diversity Check ──
        if not self._check_embedding_diversity(embeddings):
            self.db.update_status(
                upload_id, "embedding_low_diversity",
                error_reason="Weak embedding diversity detected: possible semantic collapse",
                chunk_count=embedded_count, token_count=total_tokens,
                retry_count=retry_count, last_retry_reason=last_retry_reason
            )
            trace["status"] = "embedding_low_diversity"
            self._persist_trace(student_id, upload_id, trace)
            return {"status": "embedding_low_diversity", "upload_id": upload_id, "trace": trace}
            
        # ── Weak Indexing Check (Legacy simple check) ──
        if not self._check_embedding_variance(embeddings):
            self.db.update_status(
                upload_id, "index_failed",
                error_reason="Weak indexing detected: low variance or identical embeddings",
                chunk_count=embedded_count, token_count=total_tokens,
                retry_count=retry_count, last_retry_reason=last_retry_reason
            )
            trace["status"] = "index_failed"
            self._persist_trace(student_id, upload_id, trace)
            return {"status": "index_failed", "upload_id": upload_id, "trace": trace}

        # ── Post-upsert verification ──
        t0 = time.time()
        verified = await self._verify_upsert(chunks_to_index, namespace, upload_id)
        self._trace_step(trace, "post_upsert_verify", "ok" if verified else "failed", duration_ms=self._elapsed(t0))

        if not verified:
            self.db.update_status(
                upload_id, "index_failed",
                error_reason="Post-upsert verification failed: chunks not found in vector DB",
                chunk_count=embedded_count, token_count=total_tokens,
            )
            trace["status"] = "index_failed"
            self._persist_trace(student_id, upload_id, trace)
            metrics.inc("ingest_fail")
            metrics.dec("queue_size")
            return {"status": "index_failed", "upload_id": upload_id, "trace": trace}

        # ── Semantic Integrity & Robustness Checks ──
        # 1. Semantic Index Quality
        quality_score, quality_ok = await self._validate_index_quality(chunks_to_index, namespace, upload_id)
        if not quality_ok:
            self.db.update_status(
                upload_id, "indexed_weak",
                error_reason=f"Semantic quality failed. Score: {quality_score:.2f}",
                chunk_count=embedded_count, token_count=total_tokens,
                retry_count=retry_count, last_retry_reason=last_retry_reason,
            )
            trace["status"] = "indexed_weak"
            self._persist_trace(student_id, upload_id, trace)
            metrics.inc("quality_fail")
            return {"status": "indexed_weak", "upload_id": upload_id, "trace": trace}

        # 2. Retrieval Robustness
        robust, robustness_score = await self._check_retrieval_robustness(chunks_to_index, namespace, upload_id)
        if not robust:
             self.db.update_status(
                upload_id, "retrieval_unstable",
                error_reason=f"Retrieval unstable across query variants. Score: {robustness_score:.2f}",
                chunk_count=embedded_count, token_count=total_tokens,
                retry_count=retry_count, last_retry_reason=last_retry_reason,
            )
             trace["status"] = "retrieval_unstable"
             self._persist_trace(student_id, upload_id, trace)
             metrics.inc("robustness_fail")
             return {"status": "retrieval_unstable", "upload_id": upload_id, "trace": trace}
             
        self._trace_step(trace, "semantic_check", "ok", extra={
            "quality_score": quality_score,
            "robustness_score": robustness_score,
        })
        log_info(f"[Agent] Semantic Integrity Verified. Quality: {quality_score:.2f}, Robustness: {robustness_score:.2f}")

        # ── Retrieval validation ──
        t0 = time.time()
        validation_ok = await self._validate_indexing(
            chunks_to_index[0]["text"], namespace, upload_id
        )
        self._trace_step(trace, "retrieval_validate", "ok" if validation_ok else "failed", duration_ms=self._elapsed(t0))

        if not validation_ok:
            log_warning(f"[Agent] Retrieval validation failed for {upload_id}")
            metrics.inc("validation_fail")
            self.db.update_status(
                upload_id, "index_validation_failed",
                error_reason="Retrieval validation: top result did not match upload",
                chunk_count=embedded_count, token_count=total_tokens,
            )
            trace["status"] = "index_validation_failed"
            self._persist_trace(student_id, upload_id, trace)
            metrics.dec("queue_size")
            return {"status": "index_validation_failed", "upload_id": upload_id, "trace": trace}

        # ── Finalize ──
        final_status = "indexed_partial" if is_partial else "indexed"
        trace_path = self._trace_path(student_id, upload_id)

        self.db.update_status(
            upload_id, final_status,
            token_count=total_tokens,
            trace_path=trace_path,
            retry_count=retry_count,
            last_retry_reason=last_retry_reason,
        )
        # Store embedding model version for future migration detection
        self.db.update_embedding_model(upload_id, STUDENT_EMBEDDING_MODEL_ID, STUDENT_EMBEDDING_MODEL_VERSION)

        if tags:
            self.db.update_tags(upload_id, tags=tags)

        elapsed = self._elapsed(trace["start_time"])
        trace["elapsed_ms"] = elapsed
        trace["status"] = final_status
        trace["chunk_count"] = embedded_count
        trace["token_count"] = total_tokens
        trace["namespace"] = namespace

        self._persist_trace(student_id, upload_id, trace)

        if is_partial:
            metrics.inc("ingest_partial")
        else:
            metrics.inc("ingest_success")
        metrics.inc("ingest_latency_sum_ms", elapsed)
        metrics.dec("queue_size")

        log_info(
            f"[Agent] ✅ Ingestion complete: upload_id={upload_id}, "
            f"status={final_status}, chunks={embedded_count}/{total_count}, "
            f"tokens={total_tokens}, namespace={namespace}, elapsed={elapsed}ms"
        )

        return {
            "status": final_status,
            "upload_id": upload_id,
            "chunk_count": embedded_count,
            "token_count": total_tokens,
            "namespace": namespace,
            "trace": trace,
        }

    # ──────────────────────────────────────────
    # Embedding with partial indexing
    # ──────────────────────────────────────────

    async def _batch_embed(
        self, chunks: List[Dict[str, Any]], batch_size: int = 32
    ) -> tuple:
        """
        Batch embed chunk texts with exponential retry.
        Returns (embeddings, failure_count).
        Allows partial success — returns embeddings for all successful batches.
        """
        from app.agents.retrieval_agent.utils import embed_text

        texts = [c["text"] for c in chunks]
        all_embeddings = []
        failures = 0

        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            success = False

            for attempt in range(STUDENT_MAX_RETRY_ATTEMPTS):
                try:
                    metrics.inc("embed_calls")
                    batch_embeddings = await asyncio.to_thread(embed_text, batch)
                    all_embeddings.extend(batch_embeddings)
                    success = True
                    break
                except Exception as e:
                    if attempt < STUDENT_MAX_RETRY_ATTEMPTS - 1:
                        delay = (2 ** attempt) + 0.5
                        log_warning(
                            f"[Agent] Embed batch {i // batch_size} failed "
                            f"(attempt {attempt + 1}/{STUDENT_MAX_RETRY_ATTEMPTS}): {e}. "
                            f"Retrying in {delay}s..."
                        )
                        metrics.inc("embed_failures")
                        await asyncio.sleep(delay)
                    else:
                        log_error(f"[Agent] Embed batch {i // batch_size} permanently failed: {e}")
                        metrics.inc("embed_failures")

            if not success:
                failures += len(batch)
                # Stop trying further batches — partial indexing
                break

        return all_embeddings, failures

    # ──────────────────────────────────────────
    # Vector upsert with metadata completeness
    # ──────────────────────────────────────────

    async def _upsert_vectors(
        self,
        chunks: List[Dict[str, Any]],
        embeddings: List[List[float]],
        namespace: str,
        source_type: str,
        source_uri: str,
        title: str,
    ):
        """Upsert with enforced metadata completeness."""
        from app.storage import storage_manager

        vectors = []
        for i, chunk in enumerate(chunks):
            metadata = {
                "chunk_text": chunk["text"],
                "upload_id": chunk["upload_id"],
                "student_id": chunk["student_id"],
                "source_type": source_type,
                "source_url": source_uri,
                "doc_id": chunk["upload_id"],
                "section": chunk.get("section", "general"),
                "heading": chunk.get("heading", ""),
                "concepts": ", ".join(chunk.get("concepts", [])),
                "timestamp_start": chunk.get("timestamp_start") or 0,
                "timestamp_end": chunk.get("timestamp_end") or 0,
                "chunk_index": chunk["chunk_index"],
                "fingerprint": chunk["fingerprint"],
                "title": title,
                "category": "student_upload",
                "token_count": chunk.get("token_count", 0),
            }

            # Reject incomplete entries
            required = ["student_id", "upload_id", "fingerprint", "source_type"]
            missing = [k for k in required if not metadata.get(k)]
            if missing:
                log_warning(f"[Agent] Skipping chunk {chunk['chunk_id']}: missing metadata {missing}")
                continue

            vectors.append({
                "id": chunk["chunk_id"],
                "values": embeddings[i],
                "metadata": metadata,
            })

        batch_size = 100
        for i in range(0, len(vectors), batch_size):
            batch = vectors[i:i + batch_size]
            await asyncio.to_thread(
                storage_manager.vectors.upsert,
                vectors=batch,
                namespace=namespace,
            )
            log_info(f"[Agent] Upserted batch {i // batch_size + 1}: {len(batch)} vectors")

    def _check_content_quality(self, text: str) -> bool:
        """
        Check if text has sufficient information content.
        Reject if:
        - Too short (< 100 chars)
        - High ratio of non-alphanumeric chars (garbage/OCR fail)
        - Repetitive content
        """
        if not text or len(text) < STUDENT_MIN_CONTENT_CHARS:
            return False
            
        # Check density (simple heuristic)
        import re
        words = text.split()
        if not words: return False
        
        # 1. Alphanumeric ratio
        clean_chars = len(re.sub(r'[^a-zA-Z0-9 ]', '', text))
        if clean_chars / len(text) < 0.3: # Mostly garbage symbols
            return False
            
        # 2. Unique word ratio (boilerplate detection)
        unique_words = set(w.lower() for w in words[:1000])
        if len(unique_words) / len(words[:1000]) < 0.1: # Extremely repetitive
            return False
            
        return True

    def _check_embedding_diversity(self, embeddings: List[List[float]]) -> bool:
        """Check if embeddings have sufficient semantic diversity."""
        if not embeddings or len(embeddings) < 2:
            return True 
            
        # Simple centroid collapse check
        # Calculate cosine sim pairwise for a sample
        # If mean similarity > 0.98, it's virtually identical content
        import numpy as np
        
        sample = embeddings[:20]
        vecs = np.array(sample)
        # Normalize
        norms = np.linalg.norm(vecs, axis=1, keepdims=True)
        vecs_norm = vecs / (norms + 1e-9)
        
        sim_matrix = np.dot(vecs_norm, vecs_norm.T)
        
        # Get upper triangle excluding diagonal
        upper_tri = sim_matrix[np.triu_indices_from(sim_matrix, k=1)]
        
        if len(upper_tri) > 0:
            mean_sim = np.mean(upper_tri)
            if mean_sim > 0.99:
                 log_warning(f"[Agent] Embedding diversity fail: mean_sim={mean_sim}")
                 return False
                 
        return True

    def _check_embedding_variance(self, embeddings: List[List[float]]) -> bool:
        """Check if embeddings have sufficient variance/diversity."""
        if not embeddings:
            return False
        if len(embeddings) == 1:
            return True # Single chunk is fine
            
        # Check if all embeddings are identical
        first = embeddings[0]
        if all(e == first for e in embeddings[1:]):
            log_warning("[Agent] Weak indexing: all embeddings are identical")
            return False
            
        return True

    # ──────────────────────────────────────────
    # Post-upsert verification
    # ──────────────────────────────────────────

    async def _verify_upsert(
        self, chunks: List[Dict[str, Any]], namespace: str, upload_id: str
    ) -> bool:
        """Query vector DB for sample of inserted chunks, verify ownership."""
        try:
            from app.agents.retrieval_agent.utils import embed_text
            from app.storage import storage_manager

            # Pick up to 3 samples to verify
            sample_indices = [0, len(chunks) // 2, len(chunks) - 1]
            sample_indices = list(set(i for i in sample_indices if i < len(chunks)))

            # Immediate retry loop for post-upsert verification
            for attempt in range(3):
                 found_any = False
                 for idx in sample_indices[:3]:
                    sample_text = chunks[idx]["text"][:200]
                    query_vec = await asyncio.to_thread(embed_text, [sample_text])
                    query_vec = query_vec[0]

                    results = await asyncio.to_thread(
                        storage_manager.vectors.query,
                        vector=query_vec, top_k=3, namespace=namespace,
                    )

                    matches = results if isinstance(results, list) else results.get("matches", [])
                    # Check that at least one result belongs to this upload
                    found = any(
                        m.get("metadata", {}).get("upload_id") == upload_id
                        for m in matches
                    )
                    if found:
                        found_any = True
                        break # One confirmed chunk is enough to say "vectors exist"
                 
                 if found_any:
                     return True
                 
                 log_warning(f"[Agent] Post-upsert verify failed (attempt {attempt+1}/3). Retrying...")
                 await asyncio.sleep(1)

            log_warning(f"[Agent] Post-upsert verify failed after 3 attempts.")
            return False

        except Exception as e:
            log_warning(f"[Agent] Post-upsert verification error: {e}")
            return False

    async def _validate_index_quality(
        self, chunks: List[Dict[str, Any]], namespace: str, upload_id: str
    ) -> Tuple[float, bool]:
        """
        Validate semantic index quality using concept probes.
        Returns: (quality_score, is_passing)
        """
        if not chunks:
            return 0.0, False
            
        # Select probe chunks (start, middle, end)
        probes = [chunks[0]]
        if len(chunks) > 2:
            probes.append(chunks[len(chunks)//2])
        if len(chunks) > 1:
            probes.append(chunks[-1])
            
        hits = 0
        total_score = 0.0
        
        for chunk in probes:
            # Create a "concept probe" - essentially the first meaningful sentence or title + snippet
            text = chunk.get("text", "")
            # proper way: extract keywords. Simplification: take first 15 words
            words = text.split()[:15]
            query = " ".join(words)
            
            # Query
            try:
                from app.agents.retrieval_agent.utils import embed_text
                from app.storage import storage_manager

                query_vec = await asyncio.to_thread(embed_text, [query])
                query_vec = query_vec[0]

                results = await asyncio.to_thread(
                    storage_manager.vectors.query,
                    vector=query_vec, top_k=5, namespace=namespace,
                )
            except Exception as e:
                log_warning(f"[Agent] Quality probe query failed: {e}")
                continue
            
            # Check if THIS specific chunk is retrieved OR at least the same upload_id
            match = False
            for match_item in results.get("matches", []):
                if match_item.get("metadata", {}).get("upload_id") == upload_id:
                    match = True
                    total_score += match_item.get("score", 0.0)
                    break
            
            if match:
                hits += 1
                
        if not probes: return 0.0, False
        quality_score = (hits / len(probes)) * 10.0 # Scale 0-10
        # Passing threshold: 6.0 (at least 2/3 roughly)
        return quality_score, quality_score >= 6.0

    async def _check_retrieval_robustness(
        self, chunks: List[Dict[str, Any]], namespace: str, upload_id: str
    ) -> Tuple[bool, float]:
        """
        Check retrieval robustness across query variants.
        Returns: (is_robust, robustness_score)
        """
        if not chunks:
            return False, 0.0
            
        # Pick one representative chunk (e.g., longest)
        target = max(chunks, key=lambda c: len(c.get("text", "")))
        text = target.get("text", "")
        
        # Generate variants
        # 1. Keyword: extract 3 significant words (naive)
        words = [w for w in text.split() if len(w) > 4]
        keywords = " ".join(words[:3]) if words else text[:20]
        
        # 2. Conceptual
        conceptual = f"Explain concept: {keywords}"
        
        # 3. Definition/Direct
        definition = f"What is {keywords}?"
        
        variants = [keywords, conceptual, definition]
        success_count = 0
        
        for q in variants:
            try:
                from app.agents.retrieval_agent.utils import embed_text
                from app.storage import storage_manager

                query_vec = await asyncio.to_thread(embed_text, [q])
                query_vec = query_vec[0]

                results = await asyncio.to_thread(
                    storage_manager.vectors.query,
                    vector=query_vec, top_k=5, namespace=namespace,
                )
                # Check for upload presence
                if any(m.get("metadata", {}).get("upload_id") == upload_id for m in results.get("matches", [])):
                    success_count += 1
            except Exception:
                continue
                
        robustness_score = (success_count / len(variants)) * 10.0
        # Threshold: 2/3 queries must work
        return success_count >= 2, robustness_score

    # ──────────────────────────────────────────
    # Retrieval validation (grounding check)
    # ──────────────────────────────────────────

    async def _validate_indexing(
        self, sample_text: str, namespace: str, upload_id: str
    ) -> bool:
        """Validate that indexed content is actually retrievable and belongs to this upload."""
        try:
            from app.agents.retrieval_agent.utils import embed_text
            from app.storage import storage_manager

            query_vector = await asyncio.to_thread(embed_text, [sample_text[:200]])
            query_vector = query_vector[0]

            results = await asyncio.to_thread(
                storage_manager.vectors.query,
                vector=query_vector, top_k=3, namespace=namespace,
            )

            matches = results if isinstance(results, list) else results.get("matches", [])
            if not matches:
                return False

            # Check top result belongs to this upload and has sufficient score
            top = matches[0]
            top_score = top.get("score", 0.0)
            top_upload = top.get("metadata", {}).get("upload_id", "")

            if top_upload != upload_id:
                log_warning(f"[Agent] Validation: top result upload_id={top_upload} != {upload_id}")
                return False

            if top_score < STUDENT_INDEX_VALIDATION_THRESHOLD:
                log_warning(f"[Agent] Validation: score {top_score} < threshold {STUDENT_INDEX_VALIDATION_THRESHOLD}")
                return False

            return True

        except Exception as e:
            log_warning(f"[Agent] Validation query failed: {e}")
            return False

    # ──────────────────────────────────────────
    # Delete
    # ──────────────────────────────────────────

    async def delete_upload_vectors(self, upload_id: str, student_id: str):
        """Delete all vectors associated with an upload."""
        try:
            from app.storage import storage_manager

            namespace = f"{STUDENT_VECTOR_NAMESPACE_PREFIX}{student_id}"
            upload = self.db.get_upload(upload_id)
            if not upload:
                return

            chunk_count = upload.get("chunk_count", 0)
            if chunk_count > 0:
                chunk_ids = [f"{upload_id}_chunk_{i}" for i in range(chunk_count)]
                await asyncio.to_thread(
                    storage_manager.vectors.delete,
                    ids=chunk_ids,
                    namespace=namespace,
                )
                log_info(f"[Agent] Deleted {len(chunk_ids)} vectors for upload {upload_id}")

            self.db.log_audit(student_id, "delete", upload_id, f"Deleted {chunk_count} vectors")

        except Exception as e:
            log_error(f"[Agent] Vector deletion failed for {upload_id}: {e}")

    # ──────────────────────────────────────────
    # Dedup check
    # ──────────────────────────────────────────

    def _check_dedup(
        self, upload_id: str, student_id: str, fingerprint: str, trace: Dict
    ) -> Optional[Dict[str, Any]]:
        """Check for duplicate content. Returns result dict if duplicate, None otherwise."""
        existing = self.db.find_by_fingerprint(student_id, fingerprint)
        if existing and existing != upload_id:
            log_info(f"[Agent] Duplicate detected: {existing}")
            existing_record = self.db.get_upload(existing)

            self.db.update_status(upload_id, "duplicate",
                                  error_reason=f"Duplicate of {existing}")
            self._trace_step(trace, "dedup", "duplicate", extra={
                "existing_upload_id": existing,
                "original_created_at": existing_record.get("created_at", "") if existing_record else "",
            })
            trace["status"] = "duplicate"
            trace["elapsed_ms"] = self._elapsed(trace["start_time"])
            return {
                "status": "duplicate",
                "upload_id": upload_id,
                "existing_upload_id": existing,
                "original_created_at": existing_record.get("created_at", "") if existing_record else "",
                "trace": trace,
            }

        # Not a duplicate — update fingerprint
        self.db.update_fingerprint(upload_id, fingerprint)
        self._trace_step(trace, "dedup", "unique")
        return None

    # ──────────────────────────────────────────
    # Trace helpers
    # ──────────────────────────────────────────

    @staticmethod
    def _init_trace(upload_id: str, student_id: str, source_type: str, source_uri: str) -> Dict:
        return {
            "upload_id": upload_id,
            "student_id": student_id,
            "source_type": source_type,
            "source_uri": source_uri,
            "steps": [],
            "start_time": time.time(),
        }

    @staticmethod
    def _trace_step(
        trace: Dict, step: str, status: str,
        duration_ms: int = 0, extra: Optional[Dict] = None,
    ):
        entry = {"step": step, "status": status, "duration_ms": duration_ms}
        if extra:
            entry.update(extra)
        trace["steps"].append(entry)

    @staticmethod
    def _elapsed(start: float) -> int:
        return int((time.time() - start) * 1000)

    @staticmethod
    def _trace_path(student_id: str, upload_id: str) -> str:
        return os.path.join(STUDENT_TRACE_DIR, student_id, f"{upload_id}.json")

    @staticmethod
    def _persist_trace(student_id: str, upload_id: str, trace: Dict):
        """Write trace JSON to disk."""
        try:
            trace_dir = os.path.join(STUDENT_TRACE_DIR, student_id)
            os.makedirs(trace_dir, exist_ok=True)
            path = os.path.join(trace_dir, f"{upload_id}.json")
            with open(path, "w", encoding="utf-8") as f:
                json.dump(trace, f, indent=2, default=str)
            log_info(f"[Agent] Trace persisted: {path}")
        except Exception as e:
            log_error(f"[Agent] Trace persistence failed: {e}")

    def _handle_error(self, upload_id: str, error: Exception, trace: Dict) -> Dict[str, Any]:
        """Handle pipeline errors: mark status, log trace."""
        error_msg = str(error)
        tb = traceback.format_exc()
        log_error(f"[Agent] Ingestion failed for {upload_id}: {error_msg}\n{tb}")

        self.db.update_status(upload_id, "error", error_reason=error_msg)

        trace["status"] = "error"
        trace["error"] = error_msg
        trace["elapsed_ms"] = self._elapsed(trace.get("start_time", time.time()))

        return {
            "status": "error",
            "upload_id": upload_id,
            "error": error_msg,
            "trace": trace,
        }
