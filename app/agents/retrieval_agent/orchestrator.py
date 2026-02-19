# app/agents/retrieval_agent/orchestrator.py

from app.agents.retrieval_agent.schema import Chunk, RetrievalInput, RetrievalOutput, RetrievalParams
from app.agents.retrieval_agent.vector_retriever import VectorRetriever
from app.agents.retrieval_agent.keyword_retriever import KeywordRetriever
from typing import List, Optional, Dict, Any
from uuid import uuid4
from app.core.logging import log_info, log_warning
from app.rag.intent_classifier import IntentResult, QueryIntent
from app.rag.subject_detector import SubjectScope
from app.rag.reranker import rerank_passages
from app.rag.query_expander import expand_query
from app.rag.retrieval_confidence import compute_retrieval_confidence
from app.core.config import (
    QUERY_EXPANSION_ENABLED, MAX_EXPANSION_VARIANTS,
    RETRIEVAL_CONFIDENCE_HIGH, RETRIEVAL_CONFIDENCE_LOW,
    HIERARCHICAL_RETRIEVAL_ENABLED,
    CHUNK_CLUSTERING_ENABLED,
    COVERAGE_GAP_FILL_ENABLED,
    RETRIEVAL_MEMORY_ENABLED,
    SEMANTIC_COVERAGE_MIN,
)
from app.storage import storage_manager

# ── New modules ──
from app.rag.retrieval_trace import RetrievalTraceCollector
from app.rag.hierarchical_retriever import hierarchical_rerank
from app.rag.chunk_clusterer import cluster_and_deduplicate
from app.rag.semantic_coverage import analyze_coverage


class RetrievalOrchestratorAgent:
    def __init__(self, vector_retriever: VectorRetriever, keyword_retriever: KeywordRetriever):
        self.vector_retriever = vector_retriever
        self.keyword_retriever = keyword_retriever
        
        print(f"Vector retriever: {vector_retriever}") 
        print(f"Keyword retriever: {keyword_retriever}") 
        
    def create_trace(self):
        return str(uuid4()) # it returns the trace_id for RetrievalOutput
        
    async def run(self, input: RetrievalInput, intent_result: Optional[IntentResult] = None,
                  subject_scope: Optional[SubjectScope] = None,
                  query_type: Optional[str] = None) -> RetrievalOutput:
        
        self.vector_chunks = []
        self.keyword_chunks = []
        section_chunks = []
        
        self.trace_id = self.create_trace()

        # ── Initialize Structured Trace Collector ──
        trace = RetrievalTraceCollector(
            query=input.rewritten_query,
            trace_id=self.trace_id,
        )
        trace.set_metadata("retrievers_used", input.retrievers_to_use)
        trace.set_metadata("intent", intent_result.intent.value if intent_result else "unknown")
        trace.set_metadata("target_section", intent_result.target_section if intent_result else None)
        trace.set_metadata("subject_scope", subject_scope.model_dump() if subject_scope else None)
        trace.set_metadata("query_type", query_type)

        # Determine subject filter from detected scope
        subject_filter = None
        if subject_scope and subject_scope.subject and not subject_scope.is_ambiguous:
            subject_filter = subject_scope.subject
            log_info(f"Subject-scoped retrieval: filtering by subject='{subject_filter}'")
        elif subject_scope and subject_scope.is_ambiguous:
            log_warning(f"Ambiguous subject scope: {subject_scope.matched_subjects}. Retrieving without filter.")
        
        # ══════════════════════════════════════════
        # 1. Vector Search
        # ══════════════════════════════════════════
        if "vector" in input.retrievers_to_use:
            self.vector_chunks = await self.vector_retriever.search(
                query = input.rewritten_query, 
                top_k = input.retrieval_params.top_k_vector,
                subject_filter = subject_filter,
            )
            trace.log_stage("vector_search", {
                "count": len(self.vector_chunks),
                "top_k": input.retrieval_params.top_k_vector,
                "subject_filter": subject_filter,
                "status": "success" if self.vector_chunks else "no_results",
            })
            
        # ══════════════════════════════════════════
        # 2. Keyword Search
        # ══════════════════════════════════════════
        if "keyword" in input.retrievers_to_use: 
            self.keyword_chunks = await self.keyword_retriever.search(
                query = input.rewritten_query,
                top_k = input.retrieval_params.top_k_keyword
            )
            trace.log_stage("keyword_search", {
                "count": len(self.keyword_chunks),
                "top_k": input.retrieval_params.top_k_keyword,
                "status": "success" if self.keyword_chunks else "no_results",
            })

        # ══════════════════════════════════════════
        # 3. Metadata/Section Search
        # ══════════════════════════════════════════
        if intent_result and intent_result.target_section:
            section_chunks = await self._fetch_section_chunks(
                intent_result.target_section,
                top_k=input.retrieval_params.top_k_vector
            )
            trace.log_stage("section_metadata_search", {
                "count": len(section_chunks),
                "target_section": intent_result.target_section,
                "status": "success" if section_chunks else "no_results",
            })
            
        merged = self.merge_chunks([self.keyword_chunks, self.vector_chunks, section_chunks])

        # ══════════════════════════════════════════
        # 3.5. Multi-Pass Query Expansion
        # ══════════════════════════════════════════
        expansion_chunks = []
        if QUERY_EXPANSION_ENABLED and "vector" in input.retrievers_to_use:
            query_variants = expand_query(input.rewritten_query, max_variants=MAX_EXPANSION_VARIANTS)
            trace.log_stage("query_expansion_variants", {
                "variants": [v[:60] for v in query_variants],
                "count": len(query_variants),
            })

            # Skip first variant (it's the original query already searched)
            for variant in query_variants[1:]:
                try:
                    variant_chunks = await self.vector_retriever.search(
                        query=variant,
                        top_k=max(3, input.retrieval_params.top_k_vector // 2),
                        subject_filter=subject_filter,
                    )
                    if variant_chunks:
                        expansion_chunks.extend(variant_chunks)
                        log_info(f"Query expansion pass '{variant[:50]}...' found {len(variant_chunks)} chunks")
                except Exception as e:
                    log_warning(f"Query expansion pass failed for variant: {e}")

            if expansion_chunks:
                merged = self.merge_chunks([merged, expansion_chunks])
                trace.log_stage("query_expansion_results", {
                    "variants_tried": len(query_variants) - 1,
                    "chunks_found": len(expansion_chunks),
                })

        # Snapshot: chunks before hierarchical/clustering
        trace.log_chunks_snapshot("after_merge", merged)

        # ══════════════════════════════════════════
        # 4. Hierarchical Retrieval (Structure-Aware)
        # ══════════════════════════════════════════
        if HIERARCHICAL_RETRIEVAL_ENABLED and len(merged) > 3:
            target_section = intent_result.target_section if intent_result else None
            before_count = len(merged)
            merged = hierarchical_rerank(
                merged,
                target_section=target_section,
            )
            trace.log_stage("hierarchical_rerank", {
                "before_count": before_count,
                "after_count": len(merged),
                "target_section": target_section,
            })
        else:
            trace.log_stage("hierarchical_rerank", {
                "status": "skipped",
                "reason": "disabled or too few chunks",
            }, status="skipped")

        # ══════════════════════════════════════════
        # 4.5. Chunk Clustering & Redundancy Removal
        # ══════════════════════════════════════════
        if CHUNK_CLUSTERING_ENABLED and len(merged) > 3:
            before_count = len(merged)
            merged = cluster_and_deduplicate(merged)
            trace.log_stage("chunk_clustering", {
                "before_count": before_count,
                "after_count": len(merged),
                "removed": before_count - len(merged),
            })
        else:
            trace.log_stage("chunk_clustering", {
                "status": "skipped",
            }, status="skipped")

        # ══════════════════════════════════════════
        # 5. Early Confidence Check for Expansion Gating
        # ══════════════════════════════════════════
        early_confidence = compute_retrieval_confidence(
            query=input.rewritten_query,
            chunks=merged,
            high_threshold=RETRIEVAL_CONFIDENCE_HIGH,
            low_threshold=RETRIEVAL_CONFIDENCE_LOW,
            query_type=query_type,
        )
        trace.log_confidence("early", early_confidence)

        # ══════════════════════════════════════════
        # 5a. Semantic Coverage Gap-Fill
        # ══════════════════════════════════════════
        gap_fill_chunks = []
        if COVERAGE_GAP_FILL_ENABLED and "vector" in input.retrievers_to_use:
            coverage_result = analyze_coverage(
                query=input.rewritten_query,
                chunks=merged,
                min_coverage=SEMANTIC_COVERAGE_MIN,
            )
            trace.log_stage("semantic_coverage", {
                "overall_coverage": coverage_result["overall_coverage"],
                "concepts": coverage_result["concepts"][:10],
                "gaps": coverage_result["gaps"][:5],
                "needs_gap_fill": coverage_result["needs_gap_fill"],
            })

            if coverage_result["needs_gap_fill"]:
                for gap_query in coverage_result["gap_queries"]:
                    try:
                        gf_chunks = await self.vector_retriever.search(
                            query=gap_query,
                            top_k=3,
                            subject_filter=subject_filter,
                        )
                        if gf_chunks:
                            gap_fill_chunks.extend(gf_chunks)
                            log_info(f"Gap-fill for '{gap_query[:40]}...' found {len(gf_chunks)} chunks")
                    except Exception as e:
                        log_warning(f"Gap-fill failed for '{gap_query[:40]}': {e}")

                if gap_fill_chunks:
                    merged = self.merge_chunks([merged, gap_fill_chunks])
                    trace.log_stage("gap_fill_results", {
                        "gaps_targeted": len(coverage_result["gap_queries"]),
                        "chunks_found": len(gap_fill_chunks),
                    })
                    trace.log_decision("gap_fill", "executed", f"Coverage {coverage_result['overall_coverage']:.2f} < {SEMANTIC_COVERAGE_MIN}")

        # ══════════════════════════════════════════
        # 5b. Context Expansion — only when confidence is LOW or MEDIUM
        # ══════════════════════════════════════════
        context_chunks = []
        if early_confidence.recommendation in ("expand", "retry") or early_confidence.level.value != "HIGH":
            context_chunks = await self._expand_context(merged)
            if context_chunks:
                trace.log_stage("context_expansion", {
                    "count": len(context_chunks),
                    "triggered_by": f"confidence_{early_confidence.level.value}",
                })
                merged = self.merge_chunks([merged, context_chunks])
        else:
            trace.log_decision("context_expansion", "skipped", "high_confidence")

        # Post-retrieval subject validation
        if subject_filter and merged:
            before_count = len(merged)
            merged = [
                c for c in merged
                if c.metadata.get("subject", "") == subject_filter
                or not c.metadata.get("subject")  # keep chunks with no subject tagged
            ]
            filtered_out = before_count - len(merged)
            if filtered_out > 0:
                log_warning(f"Subject validation: filtered out {filtered_out} cross-subject chunks")
                trace.log_stage("subject_filter", {"filtered_out": filtered_out})

        # ══════════════════════════════════════════
        # 6. Re-ranking (Agentic Step)
        # ══════════════════════════════════════════
        is_conceptual = getattr(input, "is_conceptual", False)
        target_section = intent_result.target_section if intent_result else None
        prefer_user_documents = intent_result.has_document_reference if intent_result else False

        trace.log_chunks_snapshot("before_rerank", merged)

        final_chunks = self.rerank_chunks(
            chunks=merged,
            query=input.rewritten_query,
            target_section=target_section,
            prefer_user_documents=prefer_user_documents,
            is_conceptual=is_conceptual
        )

        trace.log_chunks_snapshot("after_rerank", final_chunks)

        # ══════════════════════════════════════════
        # 7. Retrieval Validation & Retry (Agentic Step)
        # ══════════════════════════════════════════
        validation_result = self.validate_retrieval(final_chunks, is_conceptual=is_conceptual)
        trace.log_stage("retrieval_validation", validation_result)
        
        if is_conceptual and not validation_result["is_valid"]:
            log_info("Retrieval validation failed for conceptual query. Attempting secondary retry.")
            
            retry_chunks = await self._fetch_section_chunks("definition", top_k=5)
            
            if retry_chunks:
                log_info(f"Secondary retry found {len(retry_chunks)} definition chunks.")
                merged_retry = self.merge_chunks([final_chunks, retry_chunks])
                final_chunks = self.rerank_chunks(
                    chunks=merged_retry,
                    query=input.rewritten_query,
                    target_section=target_section,
                    prefer_user_documents=prefer_user_documents,
                    is_conceptual=is_conceptual
                )
                trace.log_decision("secondary_retry", "executed", f"Found {len(retry_chunks)} definition chunks")
            else:
                trace.log_decision("secondary_retry", "no_results", "No definition chunks found")

        log_info(f"Retrieval complete: {len(self.vector_chunks)} vector + {len(self.keyword_chunks)} keyword + {len(section_chunks)} section + {len(context_chunks)} context + {len(expansion_chunks)} expansion + {len(gap_fill_chunks)} gap_fill = {len(final_chunks)} total reranked")
        
        if not final_chunks:
            log_warning(f"No chunks retrieved for query: '{input.rewritten_query}'")

        # ══════════════════════════════════════════
        # 8. Final Retrieval Confidence Scoring (post-rerank)
        # ══════════════════════════════════════════
        retrieval_confidence = compute_retrieval_confidence(
            query=input.rewritten_query,
            chunks=final_chunks,
            high_threshold=RETRIEVAL_CONFIDENCE_HIGH,
            low_threshold=RETRIEVAL_CONFIDENCE_LOW,
            query_type=query_type,
        )
        trace.log_confidence("final", retrieval_confidence)

        # ══════════════════════════════════════════
        # 9. Record to Retrieval Memory (async-safe)
        # ══════════════════════════════════════════
        if RETRIEVAL_MEMORY_ENABLED:
            try:
                from app.rag.retrieval_memory import get_retrieval_memory
                memory = get_retrieval_memory()
                chunk_types = list(set(
                    getattr(c, "section_type", None) or
                    (c.metadata.get("section_type", "body") if c.metadata else "body")
                    for c in final_chunks[:10]
                ))
                memory.record_outcome(
                    query=input.rewritten_query,
                    query_type=query_type or "general",
                    chunk_types=chunk_types,
                    confidence=retrieval_confidence.score,
                    recommendation=retrieval_confidence.recommendation,
                    outcome_quality=retrieval_confidence.score,  # Will be updated post-synthesis
                )
                trace.log_stage("retrieval_memory_record", {"chunk_types": chunk_types})
            except Exception as e:
                log_warning(f"Retrieval memory recording failed: {e}")
        
        # Add top chunks summary to trace for frontend visualization
        trace.log_stage("top_chunks_summary", {
            "chunks": [
                {
                    "chunk_id": c.chunk_id,
                    "document_id": c.document_id,
                    "score": c.raw_score,
                    "rerank_score": c.metadata.get("rerank_score", 0.0) if c.metadata else 0.0,
                    "definition_score": c.metadata.get("definition_presence_score", 0.0) if c.metadata else 0.0,
                    "info_density": c.metadata.get("info_density_score", 0.0) if c.metadata else 0.0,
                    "is_generic": c.metadata.get("is_generic", False) if c.metadata else False,
                    "section_type": c.metadata.get("section_type", "") if c.metadata else "",
                    "source_type": c.source_type,
                    "text_preview": c.text[:100] + "..." if len(c.text) > 100 else c.text
                }
                for c in final_chunks[:5]
            ]
        })

        # Build backward-compatible retrieval_trace dict + full structured trace
        full_trace = trace.get_trace()

        # Add backward-compatible keys that controller/frontend expects
        full_trace["retrieval_confidence"] = {
            "score": retrieval_confidence.score,
            "level": retrieval_confidence.level.value,
            "recommendation": retrieval_confidence.recommendation,
            "top_similarity": retrieval_confidence.top_similarity,
            "keyword_overlap": retrieval_confidence.keyword_overlap,
            "semantic_coverage": retrieval_confidence.semantic_coverage,
            "info_density": retrieval_confidence.information_density,
        }
        full_trace["top_chunks"] = [
            {
                "chunk_id": c.chunk_id,
                "document_id": c.document_id,
                "score": c.raw_score,
                "rerank_score": c.metadata.get("rerank_score", 0.0) if c.metadata else 0.0,
                "text_preview": c.text[:100] + "..." if len(c.text) > 100 else c.text,
            }
            for c in final_chunks[:5]
        ]

        retrieval_output = RetrievalOutput(
            chunks = final_chunks,
            retrieval_trace = full_trace,
            trace_id = self.trace_id
        )
        
        return retrieval_output

    def validate_retrieval(self, chunks: List[Chunk], is_conceptual: bool = False) -> Dict[str, Any]:
        """
        Validate the quality of retrieved chunks.
        For conceptual queries, check for definition presence.
        """
        if not chunks:
            return {"is_valid": False, "reason": "empty_results"}
            
        top_chunk = chunks[0]
        
        # Check 1: Score Threshold
        if top_chunk.raw_score < 0.35:
            return {"is_valid": False, "reason": "low_score", "top_score": top_chunk.raw_score}
            
        # Check 2: Conceptual Definition Presence
        if is_conceptual:
            has_definition = False
            for c in chunks[:3]:
                def_score = c.metadata.get("definition_presence_score", 0.0) if c.metadata else 0.0
                if def_score > 0.1:
                    has_definition = True
                    break
            
            if not has_definition:
                return {"is_valid": False, "reason": "missing_definition_content"}

        return {"is_valid": True, "reason": "pass"}
        
    def normalize_scores(self, chunks: List[Chunk]):
        if not chunks:
            return []
        
        max_score = max(chunk.raw_score for chunk in chunks)
        max_score = max(max_score, 1e-8)
        for chunk in chunks:
            chunk.normalized_score = chunk.raw_score/max_score
        
        return chunks
    
    def merge_chunks(self, all_chunks_list):
        flat = []
        for lst in all_chunks_list:
            if lst:
                flat.extend(lst)

        if not flat:
            return []

        unique = {}

        for chunk in flat:
            key = chunk.chunk_id or f"text_hash_{hash(chunk.text)}"

            if key not in unique:
                unique[key] = chunk
            else:
                if chunk.raw_score > unique[key].raw_score:
                    unique[key] = chunk

        return list(unique.values())

    async def _fetch_section_chunks(
        self, section_type: str, top_k: int = 5
    ) -> List[Chunk]:
        """
        Fetch chunks from the metadata store that match the given section_type.
        """
        try:
            results = storage_manager.metadata.search(
                filters={"section_type": section_type},
                limit=top_k
            )
            section_chunks = []
            for row in results:
                chunk = Chunk(
                    chunk_id=row.get("id", ""),
                    text=row.get("chunk_text", ""),
                    source_type=row.get("source_type", "note"),
                    source_url=row.get("source_url", ""),
                    document_id=row.get("doc_id", ""),
                    page=row.get("page", 0),
                    raw_score=0.8,
                    metadata=row,
                )
                section_chunks.append(chunk)
            
            log_info(f"Section metadata fetch: {len(section_chunks)} chunks for section='{section_type}'")
            return section_chunks[:top_k]
            
        except Exception as e:
            log_warning(f"Section metadata fetch failed: {e}")
            return []

    async def _expand_context(self, chunks: List[Chunk]) -> List[Chunk]:
        """
        Agentic Step 3: Context Expansion.
        For top-scoring chunks, fetch their neighbors (prev/next) from the same document.
        Robust to missing page numbers.
        """
        if not chunks:
            return []

        # Identify top unique docs to expand
        targets = []
        seen_docs = set()
        
        # Take top 3 unique documents
        for chunk in sorted(chunks, key=lambda c: c.raw_score, reverse=True):
            if chunk.document_id and chunk.document_id not in seen_docs:
                targets.append(chunk)
                seen_docs.add(chunk.document_id)
            if len(targets) >= 3:
                break

        expanded_chunks = []
        try:
            for chunk in targets:
                doc_id = chunk.document_id
                neighbors = []
                method = "unknown"
                
                page = getattr(chunk, 'page', None) 
                if page is None and chunk.metadata:
                    page = chunk.metadata.get("page")
                
                if page is not None:
                     try:
                         page = int(page)
                     except:
                         page = None

                if page is not None and page > 0:
                     neighbors = storage_manager.metadata.get_context_neighbors(doc_id, page, window=1)
                     method = f"page_{page}"
                
                if not neighbors:
                    offset_start = chunk.metadata.get("offset_start") if chunk.metadata else None
                    if offset_start is not None:
                         if hasattr(storage_manager.metadata, 'get_context_neighbors_by_offset'):
                             neighbors = storage_manager.metadata.get_context_neighbors_by_offset(doc_id, int(offset_start))
                             method = f"offset_{offset_start}"
                
                if neighbors:
                    log_info(f"Context expansion: fetched {len(neighbors)} neighbors via {method} for doc {doc_id}")
                else:
                    log_info(f"Context expansion skipped: missing page/offset for chunk {chunk.chunk_id}")

                for row in neighbors:
                    c = Chunk(
                        chunk_id=row.get("id", ""),
                        text=row.get("chunk_text", ""),
                        source_type=row.get("source_type", "note"),
                        source_url=row.get("source_url", ""),
                        document_id=row.get("doc_id", ""),
                        page=int(row.get("page", 0)) if row.get("page") else None,
                        section_type=row.get("section_type"),
                        raw_score=0.45,
                        metadata=row,
                    )
                    expanded_chunks.append(c)
            
            return expanded_chunks
        
        except Exception as e:
            log_warning(f"Context expansion failed: {e}")
            import traceback
            log_warning(traceback.format_exc())
            return []

    def rerank_chunks(self, chunks: List[Chunk], query: str, target_section: Optional[str] = None, prefer_user_documents: bool = False, is_conceptual: bool = False) -> List[Chunk]:
        """
        Agentic Step 5: Re-ranking.
        Convert Chunks to dicts, run cross-encoder/heuristic reranker, convert back.
        """
        if not chunks:
            return []

        # Convert to list of dicts for reranker
        passages = []
        for c in chunks:
            p = c.model_dump()
            p["score"] = c.raw_score
            p["text"] = c.text
            passages.append(p)

        reranked_dicts = rerank_passages(
            passages=passages,
            query=query,
            target_section=target_section,
            prefer_user_documents=prefer_user_documents,
            is_conceptual=is_conceptual,
            top_k=len(chunks) # Rerank all, don't cut yet
        )

        final_chunks = []
        for rd in reranked_dicts:
            # Preserve all scores in metadata
            meta = rd.get("metadata", {}).copy() if rd.get("metadata") else {}
            meta["definition_presence_score"] = rd.get("definition_presence_score", 0.0)
            meta["rerank_score"] = rd.get("rerank_score", 0.0)
            meta["semantic_score"] = rd.get("semantic_score", 0.0)
            meta["keyword_score"] = rd.get("keyword_score", 0.0)
            meta["info_density_score"] = rd.get("info_density_score", 0.0)
            meta["is_generic"] = rd.get("is_generic", False)
            meta["section_match"] = rd.get("section_match", False)
            meta["document_match"] = rd.get("document_match", False)
            
            c = Chunk(
                chunk_id=rd.get("chunk_id"),
                document_id=rd.get("document_id"),
                text=rd.get("text"),
                source_type=rd.get("source_type"),
                source_url=rd.get("source_url"),
                raw_score=rd.get("rerank_score", 0.0),
                normalized_score=rd.get("rerank_score", 0.0),
                metadata=meta,
                page=rd.get("page"),
                section_type=rd.get("section_type")
            )
            final_chunks.append(c)

        return final_chunks