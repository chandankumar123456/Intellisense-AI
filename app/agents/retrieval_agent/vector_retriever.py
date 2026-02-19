# app/agents/retrieval_agent/vector_retriever.py
from typing import List, Optional, Dict
from .schema import Chunk
from .utils import namespace
import asyncio
from app.core.logging import log_error, log_warning, log_info
from app.core.config import STUDENT_VECTOR_NAMESPACE_PREFIX

class VectorRetriever:
    def __init__(self, vector_db_client):
        self.vector_db_client = vector_db_client
    
    async def search(self, query: str, top_k: int,
                     subject_filter: Optional[str] = None) -> List[Chunk]:
        try:
            log_info(f"Vector search: query='{query}', top_k={top_k}, subject_filter='{subject_filter}'")
            
            # Embed query client-side
            from app.agents.retrieval_agent.utils import embed_text
            try:
                query_vector = await asyncio.to_thread(embed_text, [query])
                query_vector = query_vector[0] # Extract first vector
            except Exception as e:
                log_error(f"Query embedding failed: {e}")
                return []

            # Build metadata filter for subject-scoped retrieval
            meta_filter: Optional[Dict] = None
            if subject_filter:
                meta_filter = {"subject": subject_filter}

            # Use SAL query (which delegates to Pinecone or Chroma)
            results = await asyncio.to_thread(
                self.vector_db_client.query,
                namespace=namespace,
                vector=query_vector,
                top_k=top_k,
                filter=meta_filter,
            )

            return self._parse_matches(results, query)
        except Exception as e:
            log_error(f"Vector search failed: {str(e)}", trace_id=None)
            import traceback
            log_error(traceback.format_exc())
            return []

    async def search_student_knowledge(
        self, query: str, student_id: str, top_k: int = 15
    ) -> List[Chunk]:
        """
        Search the student-scoped vector namespace.
        Returns chunks with provenance metadata.
        """
        student_namespace = f"{STUDENT_VECTOR_NAMESPACE_PREFIX}{student_id}"
        try:
            log_info(f"Student knowledge search: query='{query}', student_id={student_id}, ns={student_namespace}")

            from app.agents.retrieval_agent.utils import embed_text
            try:
                query_vector = await asyncio.to_thread(embed_text, [query])
                query_vector = query_vector[0]
            except Exception as e:
                log_error(f"Student query embedding failed: {e}")
                return []

            results = await asyncio.to_thread(
                self.vector_db_client.query,
                namespace=student_namespace,
                vector=query_vector,
                top_k=top_k,
            )

            chunks = self._parse_matches(results, query, is_student_knowledge=True)
            log_info(f"Student knowledge search returned {len(chunks)} chunks")
            return chunks

        except Exception as e:
            log_warning(f"Student knowledge search failed (non-fatal): {e}")
            return []

    def validate_student_coverage(self, chunks: List[Chunk], query: str, threshold: float = 0.45) -> float:
        """
        Calculate a validation score for student grounding.
        Score based on:
        1. Presence of user-uploaded chunks (is_student_knowledge=True)
        2. Relevance scores of those chunks
        3. Simple keyword coverage (heuristic)
        """
        if not chunks:
            return 0.0

        student_chunks = [c for c in chunks if c.metadata.get("is_student_knowledge") or c.metadata.get("namespace", "").startswith("student_")]
        if not student_chunks:
            return 0.0

        # avg relevance of student chunks
        avg_score = sum(c.raw_score for c in student_chunks) / len(student_chunks)
        
        # Keyword coverage heuristic
        query_words = set(w.lower() for w in query.split() if len(w) > 3)
        if not query_words:
            coverage = 1.0
        else:
            combined_text = " ".join([c.text.lower() for c in student_chunks])
            covered = sum(1 for w in query_words if w in combined_text)
            coverage = covered / len(query_words)

        # Weighted score: 60% relevance, 40% keyword coverage
        final_score = (avg_score * 0.6) + (coverage * 0.4)
        
        log_info(f"Student chunk validation: {len(student_chunks)} chunks, score={final_score:.2f} (avg_rel={avg_score:.2f}, cov={coverage:.2f})")
        return final_score

    def _parse_matches(
        self, results, query: str, is_student_knowledge: bool = False
    ) -> List[Chunk]:
        """Parse vector DB results into Chunk objects."""
        chunk_list = []
        matches = results if isinstance(results, list) else results.get('matches', [])

        if not matches:
            log_warning(f"Vector search returned no results for query: '{query}'")
            return []

        valid_source_types = ["pdf", "web", "youtube", "note", "file", "website"]

        for match in matches:
            chunk_text = match.get('metadata', {}).get("chunk_text")

            if not chunk_text:
                log_warning(f"Match missing 'chunk_text' in metadata: {match.get('id', 'unknown')}")
                continue

            # Defensive extraction for source_type
            raw_source = match.get('metadata', {}).get('source_type', 'note')
            if raw_source not in valid_source_types:
                log_warning(f"Invalid source_type '{raw_source}' for chunk {match.get('id')}. Defaulting to 'note'.")
                safe_source = "note"
            else:
                safe_source = raw_source

            # Use the full metadata dict from the match
            full_metadata = match.get('metadata', {})
            safe_metadata = full_metadata if isinstance(full_metadata, dict) else {}

            # Mark student knowledge provenance
            if is_student_knowledge:
                safe_metadata["is_student_knowledge"] = True
                safe_metadata["provenance_upload_id"] = safe_metadata.get("upload_id", "")
                safe_metadata["provenance_chunk_id"] = match.get("id", "")

            chunk = Chunk(
                chunk_id= match.get('id', ''),
                document_id=safe_metadata.get('doc_id', ''),
                source_type= safe_source,
                raw_score=match.get('score', 0.0),
                text = chunk_text,
                metadata = safe_metadata,
                source_url = safe_metadata.get('source_url'),
                page = int(safe_metadata.get('page', 0)) if safe_metadata.get('page') is not None else None,
                section_type = safe_metadata.get('section_type'),
            )
            chunk_list.append(chunk)

        chunk_list.sort(key=lambda x: x.raw_score, reverse=True)
        log_info(f"Parsed {len(chunk_list)} chunks from vector results")

        return chunk_list