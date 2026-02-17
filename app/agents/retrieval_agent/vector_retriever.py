# app/agents/retrieval_agent/vector_retriever.py
from typing import List
from .schema import Chunk
from .utils import namespace
import asyncio
from app.core.logging import log_error, log_warning, log_info

class VectorRetriever:
    def __init__(self, vector_db_client):
        self.vector_db_client = vector_db_client
    
    async def search(self, query: str, top_k: int) -> List[Chunk]:
        try:
            log_info(f"Vector search: query='{query}', top_k={top_k}")
            
            # Embed query client-side
            from app.agents.retrieval_agent.utils import embed_text
            try:
                query_vector = await asyncio.to_thread(embed_text, [query])
                query_vector = query_vector[0] # Extract first vector
            except Exception as e:
                log_error(f"Query embedding failed: {e}")
                return []

            # Use standard Pinecone query
            results = await asyncio.to_thread(
                self.vector_db_client.query,
                namespace=namespace,
                vector=query_vector,
                top_k=top_k,
                include_metadata=True
            )

            chunk_list = []
            matches = results.get('matches', [])
            
            if not matches:
                log_warning(f"Vector search returned no results for query: '{query}'")
                return []
            
            for match in matches:
                chunk_text = match.get('metadata', {}).get("chunk_text")
                
                if not chunk_text:
                    log_warning(f"Match missing 'chunk_text' in metadata: {match.get('id', 'unknown')}")
                    continue
                
                chunk = Chunk(
                    chunk_id= match.get('id', ''),
                    document_id=match.get('metadata', {}).get('doc_id', ''),
                    source_type= match.get('metadata', {}).get('source_type', 'note'),
                    raw_score=match.get('score', 0.0),
                    text = chunk_text,
                    metadata = match.get('metadata', {}).get("category"),
                    source_url = match.get('metadata', {}).get('source_url')
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