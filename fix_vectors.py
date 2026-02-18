import asyncio
import sqlite3
import os
import json
from app.storage import storage_manager
from app.rag.ingestion_pipeline import ingest_document
from app.core.logging import log_info, log_error

# Configuration
METADATA_DB_PATH = "local_storage/metadata/local_index.db"
NOTES_DIR = "local_storage/notes"

async def fix_vectors():
    print("--- Starting Vector Repair ---")
    
    # 1. Initialize Storage
    storage_manager.reinitialize("local")
    
    # 2. Find documents that are NOT embedded
    conn = sqlite3.connect(METADATA_DB_PATH)
    cursor = conn.cursor()
    
    # Check for chunk_metadata table
    try:
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='chunk_metadata';")
        if not cursor.fetchone():
            print("Error: chunk_metadata table not found.")
            return

        # Find docs that have 0 embedded chunks
        cursor.execute("""
            SELECT doc_id, COUNT(id) as total, SUM(CASE WHEN is_embedded THEN 1 ELSE 0 END) as embedded
            FROM chunk_metadata
            GROUP BY doc_id
            HAVING embedded = 0
        """)
        rows = cursor.fetchall()
        
        docs_to_repair = [row[0] for row in rows]
        print(f"Found {len(docs_to_repair)} documents needing repair (0 embeddings).")
        
    except Exception as e:
        print(f"Database error: {e}")
        return
    finally:
        conn.close()

    # 3. Re-ingest each document
    for doc_id in docs_to_repair:
        print(f"\nRepairing doc: {doc_id}")
        
        # Locate text file
        # Structure: local_storage/notes/<doc_id>/text.txt
        text_path = os.path.join(NOTES_DIR, doc_id, "text.txt")
        meta_path = os.path.join(NOTES_DIR, doc_id, "meta.json")
        
        if not os.path.exists(text_path):
            print(f"skipping {doc_id}: text.txt not found")
            continue
            
        try:
            with open(text_path, "r", encoding="utf-8") as f:
                text = f.read()
            
            # Load metadata if exists
            subject = ""
            topic = ""
            if os.path.exists(meta_path):
                with open(meta_path, "r", encoding="utf-8") as f:
                    meta = json.load(f)
                    subject = meta.get("subject", "")
                    topic = meta.get("topic", "")
                    subtopic = meta.get("subtopic", "")

            # Run ingestion
            # We pass existing doc_id to overwrite/update
            result = await ingest_document(
                text=text,
                doc_id=doc_id,
                subject=subject,
                topic=topic,
                subtopic=subtopic,
                source_type="repaired_note"
            )
            print(f"Repair Result: {result}")
            
        except Exception as e:
            print(f"Failed to repair {doc_id}: {e}")

    print("\n--- Repair Complete ---")

if __name__ == "__main__":
    asyncio.run(fix_vectors())
