import os
from typing import List, Dict, Any, Optional
from .interface import VectorStorageInterface
from app.core.config import (
    PINECONE_INDEX_NAME, 
    PINECONE_NAMESPACE, 
    CHROMA_DB_PATH,
    EMBEDDING_MODEL_NAME
)
# Lazy imports for chromadb and pinecone

class PineconeVectorStorage(VectorStorageInterface):
    def __init__(self):
        from pinecone import Pinecone, ServerlessSpec
        api_key = os.getenv("PINECONE_API_KEY")
        if not api_key:
             raise ValueError("PINECONE_API_KEY not found")
        pc = Pinecone(api_key=api_key)
        self.index = pc.Index(PINECONE_INDEX_NAME)

    def upsert(self, vectors: List[Dict[str, Any]], namespace: str = PINECONE_NAMESPACE) -> None:
        # Pinecone expects (id, values, metadata)
        # Assuming input vectors are dicts: {"id":..., "values":..., "metadata":...}
        self.index.upsert(vectors=vectors, namespace=namespace)

    def query(self, vector: List[float], top_k: int = 10, namespace: str = PINECONE_NAMESPACE, filter: Optional[Dict] = None) -> List[Dict[str, Any]]:
        result = self.index.query(
            vector=vector, 
            top_k=top_k, 
            namespace=namespace, 
            filter=filter, 
            include_metadata=True
        )
        return result.to_dict().get("matches", [])

    def delete(self, ids: List[str], namespace: str = PINECONE_NAMESPACE) -> None:
        self.index.delete(ids=ids, namespace=namespace)

class ChromaVectorStorage(VectorStorageInterface):
    def __init__(self):
        import chromadb
        from chromadb.config import Settings
        
        # Ensure directory
        os.makedirs(os.path.dirname(CHROMA_DB_PATH) if os.path.dirname(CHROMA_DB_PATH) else ".", exist_ok=True)
        
        self.client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
        # Helper logic to get or create collection
        # We can use one collection name, effectively treating it like a namespace, 
        # or map namespaces to collections. 
        # For simplicity, using one collection "evilearn_chunks"
        self.collection_name = "evilearn_chunks"
        self.collection = self.client.get_or_create_collection(name=self.collection_name)

    def upsert(self, vectors: List[Dict[str, Any]], namespace: str = "") -> None:
        if not vectors:
            return
        
        ids = [v["id"] for v in vectors]
        embeddings = [v["values"] for v in vectors]
        metadatas = [v["metadata"] for v in vectors]
        
        # Chroma handles upsert
        self.collection.upsert(
            ids=ids,
            embeddings=embeddings,
            metadatas=metadatas
        )
        print(f"[ChromaDB] Upserted {len(ids)} vectors to collection '{self.collection_name}'")

    def query(self, vector: List[float], top_k: int = 10, namespace: str = "", filter: Optional[Dict] = None) -> List[Dict[str, Any]]:
        # Map Pinecone filter syntax to Chroma where/where_document if needed?
        # Pinecone filters: {"field": "value"}
        
        results = self.collection.query(
            query_embeddings=[vector],
            n_results=top_k,
            where=filter if filter else None
        )
        
        # Reformat to match Pinecone-like output for consistency in SAL
        # Chroma returns lists of lists
        matches = []
        if results["ids"]:
             ids = results["ids"][0]
             metas = results["metadatas"][0]
             dists = results["distances"][0] if results["distances"] else []
             
             for i, vid in enumerate(ids):
                 matches.append({
                     "id": vid,
                     "metadata": metas[i],
                     "score": 1.0 - (dists[i] if i < len(dists) else 0) # Chroma uses distance (lower better), Pinecone uses similarity
                 })
        return matches

    def delete(self, ids: List[str], namespace: str = "") -> None:
        self.collection.delete(ids=ids)
