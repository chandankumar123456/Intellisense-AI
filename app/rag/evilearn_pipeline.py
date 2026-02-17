# app/rag/evilearn_pipeline.py
"""
EviLearn Verification Pipeline — the core agent.

Given user input (question or answer):
1. Classify input type
2. Extract atomic claims (if answer)
3. Hierarchical retrieval: vector → metadata → minimal doc fetch
4. Re-rank
5. Verify each claim with evidence
6. Compute calibrated confidence
7. Return structured JSON with retrieval_trace and audit_id

Obeys metadata prioritization, chunking/embedding rules (384-d),
and cost/latency constraints.
"""

import time
import uuid
import asyncio
import hashlib
from typing import List, Dict, Any, Optional

from app.core.config import (
    VECTOR_TOP_K_DEFAULT,
    METADATA_SCAN_LIMIT,
    RERANK_TOP_K,
    MAX_FETCHED_SECTIONS_PER_QUERY,
    PINECONE_NAMESPACE,
)
from app.core.logging import log_info, log_error, log_warning

from app.rag.schemas import (
    EviLearnResponse,
    VerifiedClaim,
    EvidenceSnippet,
    RetrievalTrace,
    VectorHitTrace,
    MetadataHitTrace,
    FetchedSectionTrace,
    TimingsTrace,
    MetricsOutput,
    ConfidenceSubScores,
)
from app.rag.reranker import rerank_passages
from app.rag.confidence import compute_calibrated_confidence

from app.infrastructure.metadata_store import (
    search_metadata,
    get_metadata_by_vector_ids,
    fetch_document_section,
    record_query_hit,
)
from app.infrastructure.audit_store import record_audit
from app.infrastructure.cache_store import (
    cache_get,
    cache_set,
    make_claim_cache_key,
)

from app.agents.claim_extraction_agent.agent import ClaimExtractionAgent
from app.agents.claim_extraction_agent.schema import ClaimExtractionInput


class EviLearnPipeline:
    """
    Stateless pipeline orchestrator for the EviLearn agent.
    Instantiated once, called per-request.
    """

    def __init__(
        self,
        claim_extractor: ClaimExtractionAgent,
        vector_db_client,          # Pinecone index proxy
        embed_fn,                  # callable: List[str] -> List[List[float]]
    ):
        self.claim_extractor = claim_extractor
        self.vector_db = vector_db_client
        self.embed_fn = embed_fn

    # ─────────────────────────────────────────────────
    # PUBLIC ENTRY POINT
    # ─────────────────────────────────────────────────
    async def run(
        self,
        user_input: str,
        user_id: str = "",
        session_id: str = "",
    ) -> EviLearnResponse:
        """Execute the full EviLearn verification workflow."""

        start_total = time.time()
        warnings: List[str] = []
        audit_id = str(uuid.uuid4())

        timings = TimingsTrace()
        vector_hit_traces: List[VectorHitTrace] = []
        metadata_hit_traces: List[MetadataHitTrace] = []
        fetched_section_traces: List[FetchedSectionTrace] = []
        total_fetched_docs = 0

        # ── Step 0: Classify input ──
        input_type = self._classify_input(user_input)
        log_info(f"EviLearn: input classified as '{input_type}'")

        # ── Step 1: Extract claims ──
        if input_type == "answer":
            claims_data = await self._extract_claims(user_input)
        else:
            # For questions, the full query is the single "claim"
            claims_data = [{"claim_text": user_input, "original_text_segment": user_input}]

        log_info(f"EviLearn: {len(claims_data)} claims to verify")

        verified_claims: List[VerifiedClaim] = []

        for claim_info in claims_data:
            claim_text = claim_info["claim_text"]
            claim_id = str(uuid.uuid4())

            # Check cache first
            cached = self._check_cache(claim_text)
            if cached:
                log_info(f"Cache hit for claim: {claim_text[:60]}...")
                verified_claims.append(VerifiedClaim(**cached))
                continue

            # ── Step 2: Coarse retrieval (vector search) ──
            t0 = time.time()
            vector_hits = await self._retrieve_vector_hits(
                claim_text, top_k=VECTOR_TOP_K_DEFAULT
            )
            timings.vector_search += (time.time() - t0) * 1000

            for vh in vector_hits:
                vector_hit_traces.append(VectorHitTrace(
                    vector_id=vh.get("id", ""),
                    score=vh.get("score", 0.0),
                    metadata=vh.get("metadata", {}),
                ))

            # ── Step 3: Metadata scan ──
            t0 = time.time()
            vector_ids = [vh.get("id", "") for vh in vector_hits if vh.get("id")]
            meta_from_vectors = get_metadata_by_vector_ids(vector_ids)

            # Also search metadata directly for additional candidates
            meta_direct = search_metadata(
                filters={"min_importance": 0.3},
                top_k=METADATA_SCAN_LIMIT,
            )
            timings.metadata_scan += (time.time() - t0) * 1000

            # Combine and deduplicate metadata hits
            all_meta = {m["id"]: m for m in meta_from_vectors}
            for m in meta_direct:
                if m["id"] not in all_meta:
                    all_meta[m["id"]] = m

            # Sort by importance, limit
            sorted_meta = sorted(
                all_meta.values(),
                key=lambda x: x.get("importance_score", 0),
                reverse=True,
            )[:METADATA_SCAN_LIMIT]

            for m in sorted_meta:
                metadata_hit_traces.append(MetadataHitTrace(
                    doc_id=m.get("doc_id", ""),
                    page=m.get("page", 0),
                    importance_score=m.get("importance_score", 0.0),
                ))

            # ── Step 4: Fetch minimal text ──
            t0 = time.time()
            passages = []
            fetch_count = 0

            for meta in sorted_meta:
                if fetch_count >= MAX_FETCHED_SECTIONS_PER_QUERY:
                    warnings.append("max_fetch_limit_reached")
                    break

                # Try metadata chunk_text first (already available)
                text = meta.get("chunk_text", "")
                if not text:
                    # Fallback: fetch from document store
                    text = fetch_document_section(
                        doc_id=meta.get("doc_id", ""),
                        page=meta.get("page", 0),
                        offset_start=meta.get("offset_start"),
                        offset_end=meta.get("offset_end"),
                    )

                if text:
                    passages.append({
                        "text": text,
                        "doc_id": meta.get("doc_id", ""),
                        "page": meta.get("page", 0),
                        "offset_start": meta.get("offset_start", 0),
                        "offset_end": meta.get("offset_end", 0),
                        "source_url": meta.get("source_url", ""),
                        "importance_score": meta.get("importance_score", 0.0),
                        "score": self._get_vector_score(
                            meta.get("vector_chunk_id"), vector_hits
                        ),
                        "chunk_id": meta.get("id", ""),
                    })
                    fetch_count += 1

                    fetched_section_traces.append(FetchedSectionTrace(
                        doc_id=meta.get("doc_id", ""),
                        page=meta.get("page", 0),
                        chars=len(text),
                    ))

            # Also include vector hit passages not in metadata
            for vh in vector_hits:
                chunk_text = vh.get("metadata", {}).get("chunk_text", "")
                if chunk_text and fetch_count < MAX_FETCHED_SECTIONS_PER_QUERY:
                    # Check if already fetched
                    already_fetched = any(
                        p.get("chunk_id") == vh.get("id") for p in passages
                    )
                    if not already_fetched:
                        passages.append({
                            "text": chunk_text,
                            "doc_id": vh.get("metadata", {}).get("doc_id", ""),
                            "page": vh.get("metadata", {}).get("page", 0),
                            "offset_start": vh.get("metadata", {}).get("offset_start", 0),
                            "offset_end": vh.get("metadata", {}).get("offset_end", 0),
                            "source_url": vh.get("metadata", {}).get("source_url", ""),
                            "importance_score": vh.get("metadata", {}).get("importance_score", 0.5),
                            "score": vh.get("score", 0.0),
                            "chunk_id": vh.get("id", ""),
                        })
                        fetch_count += 1

            total_fetched_docs += fetch_count
            timings.fetch += (time.time() - t0) * 1000

            # ── Step 5: Re-rank ──
            t0 = time.time()
            top_passages = rerank_passages(
                passages=passages,
                query=claim_text,
                top_k=RERANK_TOP_K,
            )
            timings.rerank += (time.time() - t0) * 1000

            # ── Step 6: Verification (calibrated confidence) ──
            t0 = time.time()
            confidence, status, sub_scores = compute_calibrated_confidence(
                top_passages=top_passages,
                claim_text=claim_text,
            )

            # ── Step 7: Multi-pass check ──
            if status == "Unsupported" and vector_hits:
                # If Unsupported but vector hits exist, try neighboring pages
                neighbor_passages = await self._fetch_neighbor_pages(
                    sorted_meta[:5]
                )
                if neighbor_passages:
                    all_passages = top_passages + neighbor_passages
                    extended_top = rerank_passages(
                        passages=all_passages,
                        query=claim_text,
                        top_k=RERANK_TOP_K,
                    )
                    confidence2, status2, sub_scores2 = compute_calibrated_confidence(
                        top_passages=extended_top,
                        claim_text=claim_text,
                    )
                    if confidence2 > confidence:
                        confidence = confidence2
                        status = status2
                        sub_scores = sub_scores2
                        top_passages = extended_top
                        warnings.append("multi_pass_improved")

            timings.verification += (time.time() - t0) * 1000

            # Build evidence list
            evidence = []
            for p in top_passages:
                evidence.append(EvidenceSnippet(
                    doc_id=p.get("doc_id", ""),
                    page=p.get("page", 0),
                    offset_start=p.get("offset_start"),
                    offset_end=p.get("offset_end"),
                    snippet=p.get("text", "")[:500],  # truncate snippet
                    source_url=p.get("source_url"),
                    similarity_score=p.get("rerank_score", p.get("score", 0.0)),
                    importance_score=p.get("importance_score", 0.0),
                ))

            # Generate explanation
            explanation = self._generate_explanation(
                claim_text, status, confidence, evidence
            )

            verified_claim = VerifiedClaim(
                id=claim_id,
                text=claim_text,
                status=status,
                confidence=confidence,
                evidence=evidence,
                explanation=explanation,
            )
            verified_claims.append(verified_claim)

            # Record query hits for promotion pipeline
            hit_ids = [p.get("chunk_id", "") for p in top_passages if p.get("chunk_id")]
            if hit_ids:
                record_query_hit(hit_ids)

            # Cache the result
            self._cache_result(claim_text, hit_ids, verified_claim)

        # ── Overall confidence ──
        if verified_claims:
            overall_confidence = round(
                sum(c.confidence for c in verified_claims) / len(verified_claims), 4
            )
        else:
            overall_confidence = 0.0

        # ── Finalize timings ──
        timings.total = round((time.time() - start_total) * 1000, 2)

        # Check for low metadata coverage
        if not metadata_hit_traces:
            warnings.append("low_metadata_coverage")

        # ── Build response ──
        response = EviLearnResponse(
            query=user_input,
            input_type=input_type,
            claims=verified_claims,
            overall_confidence=overall_confidence,
            retrieval_trace=RetrievalTrace(
                vector_hits=vector_hit_traces,
                metadata_hits=metadata_hit_traces,
                fetched_sections=fetched_section_traces,
                timings_ms=timings,
            ),
            audit_id=audit_id,
            warnings=warnings,
            metrics=MetricsOutput(
                used_vector_count=len(vector_hit_traces),
                fetched_docs=total_fetched_docs,
                latency_ms=int(timings.total),
            ),
        )

        # ── Record audit ──
        audit_entry = {
            "audit_id": audit_id,
            "query": user_input,
            "input_type": input_type,
            "user_id": user_id,
            "session_id": session_id,
            "claims_count": len(verified_claims),
            "overall_confidence": overall_confidence,
            "retrieval_trace": response.retrieval_trace.model_dump(),
            "metrics": response.metrics.model_dump(),
            "warnings": warnings,
        }
        record_audit(audit_entry)

        return response

    # ─────────────────────────────────────────────────
    # PRIVATE HELPERS
    # ─────────────────────────────────────────────────

    def _classify_input(self, text: str) -> str:
        """
        Classify user input as 'question' or 'answer'.
        Simple heuristic: questions end with '?' or start with question words.
        """
        stripped = text.strip()
        question_starters = (
            "what", "who", "where", "when", "why", "how", "is", "are",
            "do", "does", "did", "can", "could", "would", "will", "should",
            "explain", "define", "describe",
        )
        if stripped.endswith("?"):
            return "question"
        first_word = stripped.split()[0].lower() if stripped else ""
        if first_word in question_starters:
            return "question"
        # Multi-sentence / long text → likely an answer
        if len(stripped.split(".")) >= 3 or len(stripped.split()) > 30:
            return "answer"
        return "question"

    async def _extract_claims(self, text: str) -> List[Dict[str, str]]:
        """Extract atomic claims from answer text."""
        try:
            result = await self.claim_extractor.run(
                ClaimExtractionInput(text=text)
            )
            return [
                {
                    "claim_text": c.claim_text,
                    "original_text_segment": c.original_text_segment or "",
                }
                for c in result.claims
            ]
        except Exception as e:
            log_error(f"Claim extraction failed: {e}")
            return [{"claim_text": text, "original_text_segment": text}]

    async def _retrieve_vector_hits(
        self, query: str, top_k: int = 30
    ) -> List[Dict[str, Any]]:
        """Coarse semantic retrieval from Layer-1 vector index."""
        try:
            # Embed query
            query_vector = await asyncio.to_thread(self.embed_fn, [query])
            query_vector = query_vector[0]

            # Query Pinecone
            results = await asyncio.to_thread(
                self.vector_db.query,
                namespace=PINECONE_NAMESPACE,
                vector=query_vector,
                top_k=top_k,
                include_metadata=True,
            )

            matches = results.get("matches", [])
            return [
                {
                    "id": m.get("id", ""),
                    "score": m.get("score", 0.0),
                    "metadata": m.get("metadata", {}),
                }
                for m in matches
            ]
        except Exception as e:
            log_error(f"Vector retrieval failed: {e}")
            return []

    def _get_vector_score(
        self, vector_chunk_id: Optional[str], vector_hits: List[Dict]
    ) -> float:
        """Look up the vector score for a chunk."""
        if not vector_chunk_id:
            return 0.0
        for vh in vector_hits:
            if vh.get("id") == vector_chunk_id:
                return vh.get("score", 0.0)
        return 0.0

    async def _fetch_neighbor_pages(
        self, meta_entries: List[Dict]
    ) -> List[Dict[str, Any]]:
        """Fetch ±1 neighboring pages for multi-pass check."""
        neighbor_passages = []
        for m in meta_entries:
            doc_id = m.get("doc_id", "")
            page = m.get("page", 0)
            for offset_page in [page - 1, page + 1]:
                if offset_page < 0:
                    continue
                text = fetch_document_section(doc_id=doc_id, page=offset_page)
                if text:
                    neighbor_passages.append({
                        "text": text,
                        "doc_id": doc_id,
                        "page": offset_page,
                        "offset_start": 0,
                        "offset_end": len(text),
                        "source_url": m.get("source_url", ""),
                        "importance_score": m.get("importance_score", 0.3),
                        "score": 0.3,
                    })
        return neighbor_passages

    def _generate_explanation(
        self,
        claim_text: str,
        status: str,
        confidence: float,
        evidence: List[EvidenceSnippet],
    ) -> str:
        """Generate a human-readable explanation referencing evidence."""
        if not evidence:
            return (
                f"Claim: \"{claim_text}\" — Status: {status} (confidence: {confidence:.2f}). "
                f"No supporting evidence was found in the indexed documents."
            )

        snippets_ref = []
        for i, e in enumerate(evidence[:3]):
            src = f"doc:{e.doc_id}, page:{e.page}"
            if e.source_url:
                src += f", url:{e.source_url}"
            snippets_ref.append(
                f"[Evidence {i+1}] (sim: {e.similarity_score:.2f}, importance: {e.importance_score:.2f}) "
                f"from {src}: \"{e.snippet[:100]}...\""
            )

        refs_text = "\n".join(snippets_ref)

        return (
            f"Claim: \"{claim_text}\"\n"
            f"Status: {status} (confidence: {confidence:.2f})\n\n"
            f"Evidence:\n{refs_text}"
        )

    def _check_cache(self, claim_text: str) -> Optional[Dict]:
        """Check if a cached verification result exists."""
        # Simple claim-only cache key (without evidence IDs for initial lookup)
        key = hashlib.sha256(claim_text.encode()).hexdigest()
        return cache_get(key)

    def _cache_result(
        self,
        claim_text: str,
        evidence_ids: List[str],
        claim: VerifiedClaim,
    ):
        """Cache the verification result."""
        key = hashlib.sha256(claim_text.encode()).hexdigest()
        cache_set(key, claim.model_dump())

        # Also cache with stable evidence hash
        if evidence_ids:
            stable_key = make_claim_cache_key(claim_text, evidence_ids)
            cache_set(stable_key, claim.model_dump())
