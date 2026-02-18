import chromadb
import os

CHROMA_DB_PATH = os.path.join("local_storage", "chroma_db")
client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
collection_name = "evilearn_chunks"

try:
    collection = client.get_collection(name=collection_name)
    count = collection.count()
    print(f"Collection '{collection_name}' has {count} embeddings.")
    
    if count > 0:
        peek = collection.peek(limit=5)
        for i in range(len(peek['ids'])):
            print(f"ID: {peek['ids'][i]}")
            print(f"Metadata keys: {list(peek['metadatas'][i].keys())}")
            text = peek['metadatas'][i].get('chunk_text', 'NO TEXT')
            print(f"Text snippet: {text[:100]}...")
            print("-" * 40)
except Exception as e:
    print(f"Error checking ChromaDB: {e}")
