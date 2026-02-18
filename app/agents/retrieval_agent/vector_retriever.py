# app/agents/retrieval_agent/vector_retriever.py
from typing import List, Optional, Dict
from .schema import Chunk
from .utils import namespace
import asyncio
from app.core.logging import log_error, log_warning, log_info

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

            chunk_list = []
            # SAL returns the matches list directly
            matches = results if isinstance(results, list) else results.get('matches', [])
            
            if not matches:
                log_warning(f"Vector search returned no results for query: '{query}'")
                return []
            
            for match in matches:
                chunk_text = match.get('metadata', {}).get("chunk_text")
                
                if not chunk_text:
                    log_warning(f"Match missing 'chunk_text' in metadata: {match.get('id', 'unknown')}")
                    continue
                
                # Defensive extraction for source_type
                raw_source = match.get('metadata', {}).get('source_type', 'note')
                if raw_source not in ["pdf", "web", "youtube", "note"]:
                    log_warning(f"Invalid source_type '{raw_source}' for chunk {match.get('id')}. Defaulting to 'note'.")
                    safe_source = "note"
                else:
                    safe_source = raw_source

                # Use the full metadata dict from the match
                full_metadata = match.get('metadata', {})
                safe_metadata = full_metadata if isinstance(full_metadata, dict) else {}

                chunk = Chunk(
                    chunk_id= match.get('id', ''),
                    document_id=safe_metadata.get('doc_id', ''),
                    source_type= safe_source,
                    raw_score=match.get('score', 0.0),
                    text = chunk_text,
                    metadata = safe_metadata,
                    source_url = safe_metadata.get('source_url'),
                )
                chunk_list.append(chunk)
                
            chunk_list.sort(key=lambda x: x.raw_score, reverse=True)
            log_info(f"Vector search returned {len(chunk_list)} chunks")
            
            return chunk_list
        except Exception as e:
            log_error(f"Vector search failed: {str(e)}", trace_id=None)
            import traceback
            log_error(traceback.format_exc())
            return []