import sqlite3
import os

METADATA_DB_PATH = "local_storage/metadata/local_index.db"
NOTES_DIR = "local_storage/notes"

def clean_metadata():
    print("--- Cleaning Broken Metadata ---")
    
    conn = sqlite3.connect(METADATA_DB_PATH)
    cursor = conn.cursor()
    
    # Get all doc_ids
    try:
        cursor.execute("SELECT DISTINCT doc_id FROM chunk_metadata")
        doc_ids = [row[0] for row in cursor.fetchall()]
        
        broken_ids = []
        for doc_id in doc_ids:
            # Check if directory exists in notes
            if not os.path.exists(os.path.join(NOTES_DIR, doc_id)):
                broken_ids.append(doc_id)
        
        if broken_ids:
            print(f"Found {len(broken_ids)} broken documents: {broken_ids}")
            for bid in broken_ids:
                cursor.execute("DELETE FROM chunk_metadata WHERE doc_id = ?", (bid,))
            conn.commit()
            print("Deleted broken entries.")
        else:
            print("No broken metadata found.")
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    clean_metadata()
