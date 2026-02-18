import chromadb
import os

CHROMA_DB_PATH = os.path.join("local_storage", "chroma_db")
client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
collection_name = "evilearn_chunks"

try:
    collection = client.get_collection(name=collection_name)
    count = collection.count()
    print(f"Collection '{collection_name}' exists and has {count} embeddings.")
    
    # Peek at some metadata if available
    if count > 0:
        peek = collection.peek(limit=5)
        print("\nPeek at first 5 embeddings (metadata):")
        for i in range(len(peek['ids'])):
            print(f"ID: {peek['ids'][i]}")
            print(f"Metadata: {peek['metadatas'][i]}")
            print("-" * 20)
except Exception as e:
    print(f"Error checking ChromaDB: {e}")
