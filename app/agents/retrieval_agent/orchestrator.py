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
from app.storage import storage_manager

class RetrievalOrchestratorAgent:
    def __init__(self, vector_retriever: VectorRetriever, keyword_retriever: KeywordRetriever):
        self.vector_retriever = vector_retriever
        self.keyword_retriever = keyword_retriever
        
        print(f"Vector retriever: {vector_retriever}") 
        print(f"Keyword retriever: {keyword_retriever}") 
        
    def create_trace(self):
        return str(uuid4()) # it returns the trace_id for RetrievalOutput
        
    async def run(self, input: RetrievalInput, intent_result: Optional[IntentResult] = None,
                  subject_scope: Optional[SubjectScope] = None) -> RetrievalOutput:
        
        self.vector_chunks = []
        self.keyword_chunks = []
        section_chunks = []
        
        self.trace_id = self.create_trace()
        self.retrieval_trace = {
            "trace_id": self.trace_id,
            "query": input.rewritten_query,
            "retrievers_used": input.retrievers_to_use,
            "intent": intent_result.intent.value if intent_result else "unknown",
            "target_section": intent_result.target_section if intent_result else None,
            "subject_scope": subject_scope.dict() if subject_scope else None, # Changed to .dict() for Pydantic V1 compat
            "results": {
                "vector": None,
                "keyword": None,
                "section_metadata": None,
                "context_expansion": None
            }
        }

        # Determine subject filter from detected scope
        subject_filter = None
        if subject_scope and subject_scope.subject and not subject_scope.is_ambiguous:
            subject_filter = subject_scope.subject
            log_info(f"Subject-scoped retrieval: filtering by subject='{subject_filter}'")
        elif subject_scope and subject_scope.is_ambiguous:
            log_warning(f"Ambiguous subject scope: {subject_scope.matched_subjects}. Retrieving without filter.")
        
        # 1. Vector Search
        if "vector" in input.retrievers_to_use:
            self.vector_chunks = await self.vector_retriever.search(
                query = input.rewritten_query, 
                top_k = input.retrieval_params.top_k_vector,
                subject_filter = subject_filter,
            )
            self.retrieval_trace['results']['vector'] = {
                "count": len(self.vector_chunks),
                "top_k": input.retrieval_params.top_k_vector,
                "subject_filter": subject_filter,
                "status": "success" if self.vector_chunks else "no_results"
            }
            
        # 2. Keyword Search
        if "keyword" in input.retrievers_to_use: 
            self.keyword_chunks = await self.keyword_retriever.search(
                query = input.rewritten_query,
                top_k = input.retrieval_params.top_k_keyword
            )
            
            self.retrieval_trace['results']['keyword'] = {
                "count": len(self.keyword_chunks),
                "top_k": input.retrieval_params.top_k_keyword,
                "status": "success" if self.keyword_chunks else "no_results"
            }

        # 3. Metadata/Section Search
        if intent_result and intent_result.target_section:
            section_chunks = await self._fetch_section_chunks(
                intent_result.target_section,
                top_k=input.retrieval_params.top_k_vector
            )
            self.retrieval_trace['results']['section_metadata'] = {
                "count": len(section_chunks),
                "target_section": intent_result.target_section,
                "status": "success" if section_chunks else "no_results"
            }
            
        merged = self.merge_chunks([self.keyword_chunks, self.vector_chunks, section_chunks])

        # 4. Context Expansion (Agentic Step)
        # Identify top candidate docs and fetch neighboring chunks
        context_chunks = await self._expand_context(merged)
        if context_chunks:
            self.retrieval_trace['results']['context_expansion'] = {
                "count": len(context_chunks),
                "status": "success"
            }
            # Merge again with context chunks
            merged = self.merge_chunks([merged, context_chunks])

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
                self.retrieval_trace["subject_filtered_count"] = filtered_out

        # 5. Re-ranking (Agentic Step)
        is_conceptual = getattr(input, "is_conceptual", False)
        target_section = intent_result.target_section if intent_result else None
        prefer_user_documents = intent_result.has_document_reference if intent_result else False

        final_chunks = self.rerank_chunks(
            chunks=merged,
            query=input.rewritten_query,
            target_section=target_section,
            prefer_user_documents=prefer_user_documents,
            is_conceptual=is_conceptual
        )

        # 6. Retrieval Validation & Retry (Agentic Step)
        # If conceptual and quality is low, try a secondary retrieval targeting definitions
        validation_result = self.validate_retrieval(final_chunks, is_conceptual=is_conceptual)
        self.retrieval_trace["retrieval_validation"] = validation_result
        
        if is_conceptual and not validation_result["is_valid"]:
            log_info("Retrieval validation failed for conceptual query. Attempting secondary retry.")
            
            # Secondary Retry: Fetch specifically from "definition" sections
            retry_chunks = await self._fetch_section_chunks("definition", top_k=5)
            
            if retry_chunks:
                log_info(f"Secondary retry found {len(retry_chunks)} definition chunks.")
                # Merge and Re-rank again
                merged_retry = self.merge_chunks([final_chunks, retry_chunks])
                final_chunks = self.rerank_chunks(
                    chunks=merged_retry,
                    query=input.rewritten_query,
                    target_section=target_section,
                    prefer_user_documents=prefer_user_documents,
                    is_conceptual=is_conceptual
                )
                self.retrieval_trace["secondary_retry_triggered"] = True
                self.retrieval_trace["results"]["retry_count"] = len(retry_chunks)
            else:
                log_info("Secondary retry found no definition chunks.")

        log_info(f"Retrieval complete: {len(self.vector_chunks)} vector + {len(self.keyword_chunks)} keyword + {len(section_chunks)} section + {len(context_chunks)} context = {len(final_chunks)} total reranked")
        
        if not final_chunks:
            log_warning(f"No chunks retrieved for query: '{input.rewritten_query}'")
        
        # Add top chunks summary to trace for frontend visualization
        self.retrieval_trace["top_chunks"] = [
            {
                "chunk_id": c.chunk_id,
                "document_id": c.document_id,
                "score": c.raw_score,
                "rerank_score": c.metadata.get("rerank_score", 0.0),
                "definition_score": c.metadata.get("definition_presence_score", 0.0),
                "section_type": c.metadata.get("section_type", ""),
                "source_type": c.source_type,
                "text_preview": c.text[:100] + "..." if len(c.text) > 100 else c.text
            }
            for c in final_chunks[:5]
        ]

        retrieval_output = RetrievalOutput(
            chunks = final_chunks,
            retrieval_trace = self.retrieval_trace,
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
        # Rerank scores are roughly 0-1 range (or slightly higher with boosts)
        if top_chunk.raw_score < 0.35: # Tightened threshold
            return {"is_valid": False, "reason": "low_score", "top_score": top_chunk.raw_score}
            
        # Check 2: Conceptual Definition Presence
        if is_conceptual:
            # Check if any of top 3 chunks have a definition score > 0.1
            has_definition = False
            for c in chunks[:3]:
                # Assuming reranker populated definition_presence_score in metadata or we re-compute
                # reranker puts it in metadata dict when reconstructing Chunk? 
                # Wait, reranker returns dicts, then we reconstruct Chunk.
                # In rerank_chunks method: c = Chunk(..., metadata=rd.get("metadata"))
                # But 'definition_presence_score' is a top-level key in reranked_dicts, not inside metadata.
                # We need to make sure we store it in metadata or attributes of Chunk.
                # Let's check Chunk schema. It allows arbitrary metadata.
                # We should probably update rerank_chunks too to persist this score.
                # For now, let's assume we will fix rerank_chunks to put it in metadata or normalized_score.
                
                # We actually need to fix `rerank_chunks` to preserve `definition_presence_score` in Chunk.
                # I'll update `rerank_chunks` too.
                # Accessing from metadata assuming it's there:
                def_score = c.metadata.get("definition_presence_score", 0.0)
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
        # We need chunk ID as well if we want to debug or deduplicate better
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
                
                # Method A: Page-based (Preferred)
                # Check if page is present and > 0 (assuming 0 is "unknown" or title page, but valid pages start at 1 usually?)
                # Actually, some PDFs start at 1. If 0 is valid, we should check for None.
                # Chunk schema has page: Optional[int].
                page = getattr(chunk, 'page', None) 
                # If optional is None, check metadata dict
                if page is None and chunk.metadata:
                    page = chunk.metadata.get("page")
                
                # Ensure page is a valid int
                if page is not None:
                     try:
                         page = int(page)
                     except:
                         page = None

                if page is not None and page > 0:
                     neighbors = storage_manager.metadata.get_context_neighbors(doc_id, page, window=1)
                     method = f"page_{page}"
                
                # Method B: Offset-based (Fallback)
                if not neighbors:
                    offset_start = chunk.metadata.get("offset_start") if chunk.metadata else None
                    if offset_start is not None:
                         # Use dynamic method check or just call it (we added it)
                         if hasattr(storage_manager.metadata, 'get_context_neighbors_by_offset'):
                             neighbors = storage_manager.metadata.get_context_neighbors_by_offset(doc_id, int(offset_start))
                             method = f"offset_{offset_start}"
                
                if neighbors:
                    log_info(f"Context expansion: fetched {len(neighbors)} neighbors via {method} for doc {doc_id}")
                else:
                    log_info(f"Context expansion skipped: missing page/offset for chunk {chunk.chunk_id}")

                for row in neighbors:
                    # Avoid adding the chunk itself if it's already there?
                    # But it's fine, merge_chunks handles dedup
                    c = Chunk(
                        chunk_id=row.get("id", ""),
                        text=row.get("chunk_text", ""),
                        source_type=row.get("source_type", "note"),
                        source_url=row.get("source_url", ""),
                        document_id=row.get("doc_id", ""),
                        page=int(row.get("page", 0)) if row.get("page") else None,
                        section_type=row.get("section_type"),
                        raw_score=0.45,  # Slightly lower score for context neighbors
                        metadata=row,
                    )
                    expanded_chunks.append(c)
            
            return expanded_chunks
        
        except Exception as e:
            log_warning(f"Context expansion failed: {e}")
            import traceback
            log_error(traceback.format_exc())
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
            # Reconstruct Chunk object
            # Preserve definition_presence_score and other metrics in metadata
            meta = rd.get("metadata", {}).copy() if rd.get("metadata") else {}
            meta["definition_presence_score"] = rd.get("definition_presence_score", 0.0)
            meta["rerank_score"] = rd.get("rerank_score", 0.0)
            meta["semantic_score"] = rd.get("semantic_score", 0.0)
            meta["section_match"] = rd.get("section_match", False)
            
            c = Chunk(
                chunk_id=rd.get("chunk_id"),
                document_id=rd.get("document_id"),
                text=rd.get("text"),
                source_type=rd.get("source_type"),
                source_url=rd.get("source_url"),
                raw_score=rd.get("rerank_score", 0.0), # Use rerank score as raw score
                normalized_score=rd.get("rerank_score", 0.0),
                metadata=meta,
                # Ensure page/section_type are preserved if they were in original chunk attributes
                page=rd.get("page"),
                section_type=rd.get("section_type")
            )
            final_chunks.append(c)

        return final_chunks