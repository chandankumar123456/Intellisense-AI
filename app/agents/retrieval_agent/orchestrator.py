# app/agents/retrieval_agent/orchestrator.py

from app.agents.retrieval_agent.schema import Chunk, RetrievalInput, RetrievalOutput, RetrievalParams
from app.agents.retrieval_agent.vector_retriever import VectorRetriever
from app.agents.retrieval_agent.keyword_retriever import KeywordRetriever
from typing import List, Optional
from uuid import uuid4
from app.core.logging import log_info, log_warning
from app.rag.intent_classifier import IntentResult, QueryIntent
class RetrievalOrchestratorAgent:
    def __init__(self, vector_retriever: VectorRetriever, keyword_retriever: KeywordRetriever):
        self.vector_retriever = vector_retriever
        self.keyword_retriever = keyword_retriever
        
        print(f"Vector retriever: {vector_retriever}") 
        print(f"Keyword retriever: {keyword_retriever}") 
        
    def create_trace(self):
        return str(uuid4()) # it returns the trace_id for RetrievalOutput
        
    async def run(self, input: RetrievalInput, intent_result: Optional[IntentResult] = None) -> RetrievalOutput:
        
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
            "results": {
                "vector": None,
                "keyword": None,
                "section_metadata": None
            }
        }
        
        if "vector" in input.retrievers_to_use:
            self.vector_chunks = await self.vector_retriever.search(
                query = input.rewritten_query, 
                top_k = input.retrieval_params.top_k_vector
            )
            self.retrieval_trace['results']['vector'] = {
                "count": len(self.vector_chunks),
                "top_k": input.retrieval_params.top_k_vector,
                "status": "success" if self.vector_chunks else "no_results"
            }
            
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

        # Section-aware metadata retrieval
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
        final_chunks = self.normalize_scores(merged)
        
        final_chunks.sort(key=lambda c: c.normalized_score, reverse=True)
        
        log_info(f"Retrieval complete: {len(self.vector_chunks)} vector + {len(self.keyword_chunks)} keyword + {len(section_chunks)} section = {len(final_chunks)} total chunks")
        
        if not final_chunks:
            log_warning(f"No chunks retrieved for query: '{input.rewritten_query}'")
        
        retrieval_output = RetrievalOutput(
            chunks = final_chunks,
            retrieval_trace = self.retrieval_trace,
            trace_id = self.trace_id
        )
        
        return retrieval_output
        
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
            # Determine-key for deduplication
            # Priority: chunk_id → fallback: hash(text)
            key = chunk.chunk_id or f"text_hash_{hash(chunk.text)}"

            if key not in unique:
                # First time seeing this chunk
                unique[key] = chunk
            else:
                # Already exists → keep one with HIGHER raw_score
                if chunk.raw_score > unique[key].raw_score:
                    unique[key] = chunk

        return list(unique.values())

    async def _fetch_section_chunks(
        self, section_type: str, top_k: int = 5
    ) -> List[Chunk]:
        """
        Fetch chunks from the metadata store that match the given section_type.
        These are returned as Chunk objects with a priority boost.
        """
        try:
            from app.storage import storage_manager
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
                    raw_score=0.8,  # Boost for exact section match
                    metadata=row,
                )
                section_chunks.append(chunk)
            
            log_info(f"Section metadata fetch: {len(section_chunks)} chunks for section='{section_type}'")
            return section_chunks[:top_k]
            
        except Exception as e:
            log_warning(f"Section metadata fetch failed: {e}")
            return []