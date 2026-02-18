import os
import datetime
import sqlite3
import shutil

# Check if chromadb is available for deeper inspection, otherwise we'll just check files
try:
    import chromadb
    CHROMA_AVAILABLE = True
except ImportError:
    CHROMA_AVAILABLE = False

# --- Configuration ---
BASE_DIR = os.path.join(os.getcwd(), "local_storage")
NOTES_DIR = os.path.join(BASE_DIR, "notes")
METADATA_DIR = os.path.join(BASE_DIR, "metadata")
METADATA_DB_PATH = os.path.join(METADATA_DIR, "local_index.db") # Corrected path based on previous `find` output
CHROMA_DIR = os.path.join(BASE_DIR, "chroma_db")
REPORTS_DIR = os.path.join(BASE_DIR, "verification_reports")

# Ensure reports directory exists
os.makedirs(REPORTS_DIR, exist_ok=True)

def get_file_info(filepath):
    """Returns size and readable modification time for a file."""
    try:
        stat = os.stat(filepath)
        size_bytes = stat.st_size
        mod_time = datetime.datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S')
        return size_bytes, mod_time
    except FileNotFoundError:
        return 0, "N/A"

def generate_structure_tree(startpath):
    """Generates a directory tree string."""
    tree_str = f"{os.path.basename(startpath)}/\n"
    prefix = ""
    
    # We'll use a recursive inner function to handle the walking
    def _walk(path, prefix):
        nonlocal tree_str
        try:
            entries = sorted(os.listdir(path))
        except OSError:
            return

        entries = [e for e in entries if e != "__pycache__" and not e.startswith(".")]
        
        for i, entry in enumerate(entries):
            is_last = (i == len(entries) - 1)
            fullpath = os.path.join(path, entry)
            connector = "└── " if is_last else "├── "
            
            tree_str += f"{prefix}{connector}{entry}\n"
            
            if os.path.isdir(fullpath):
                extension = "    " if is_last else "│   "
                _walk(fullpath, prefix + extension)

    _walk(startpath, "")
    return tree_str

def generate_notes_inventory():
    """Scans notes directory and creates inventory report."""
    report_lines = []
    report_lines.append(f"Notes Inventory Report - {datetime.datetime.now()}\n")
    report_lines.append(f"{'File Name':<40} | {'Status':<10} | {'Size (Bytes)':<12} | {'Upload Time':<20} | {'Path'}")
    report_lines.append("-" * 120)

    total_files = 0
    total_size = 0
    
    # Walk through notes directory. 
    # Structure seems to be local_storage/notes/<uuid>/original/<filename> or similar based on previous `find`
    # We will walk safely.
    
    files_found = []

    if os.path.exists(NOTES_DIR):
        for root, dirs, files in os.walk(NOTES_DIR):
            for file in files:
                # We are looking for the actual user files, not just internal json/txt
                # Adjusted to list EVERYTHING in notes for full inventory as requested
                fullpath = os.path.join(root, file)
                size, mtime = get_file_info(fullpath)
                
                # Determine status (simplified: if it exists here, it is PRESENT)
                status = "PRESENT"
                if size == 0:
                    status = "EMPTY"
                
                # Relative path for readability
                rel_path = os.path.relpath(fullpath, BASE_DIR)
                
                report_lines.append(f"{file:<40} | {status:<10} | {size:<12} | {mtime:<20} | {rel_path}")
                
                total_files += 1
                total_size += size
                files_found.append(fullpath)
    else:
        report_lines.append("NOTES DIRECTORY MISSING!")

    report_lines.append("-" * 120)
    report_lines.append(f"\nTotal Files Count: {total_files}")
    report_lines.append(f"Total Storage Size: {total_size} bytes")
    
    with open(os.path.join(REPORTS_DIR, "notes_inventory.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(report_lines))
        
    return files_found, total_files

def generate_metadata_report(physical_files):
    """Analyzes sqlite metadata index."""
    report_lines = []
    report_lines.append(f"Metadata Index Report - {datetime.datetime.now()}\n")
    report_lines.append(f"{'Doc ID':<36} | {'Title/Subject':<30} | {'Chunks':<6} | {'Embedded':<8} | {'Exists in Notes':<15} | {'Status'}")
    report_lines.append("-" * 130)

    total_indexed_docs = 0
    missing_files = 0
    broken_refs = 0
    
    # physical_files contains full paths to files in notes.
    # We need a set of existing doc_ids (folder names) to check against.
    # Structure: local_storage/notes/<uuid>/...
    existing_doc_ids = set()
    if os.path.exists(NOTES_DIR):
        for entry in os.listdir(NOTES_DIR):
            if os.path.isdir(os.path.join(NOTES_DIR, entry)):
                existing_doc_ids.add(entry)

    if os.path.exists(METADATA_DB_PATH):
        try:
            conn = sqlite3.connect(METADATA_DB_PATH)
            cursor = conn.cursor()
            
            # Check for chunk_metadata table
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='chunk_metadata';")
            if cursor.fetchone():
                # Aggregate chunks by doc_id
                cursor.execute("""
                    SELECT 
                        doc_id, 
                        MAX(subject) as title, 
                        COUNT(id) as chunk_count, 
                        SUM(CASE WHEN is_embedded THEN 1 ELSE 0 END) as embedded_count
                    FROM chunk_metadata 
                    GROUP BY doc_id
                """)
                rows = cursor.fetchall()
                
                for row in rows:
                    doc_id = str(row[0])
                    title = str(row[1]) if row[1] else "Unknown"
                    chunk_count = row[2]
                    embedded_count = row[3] if row[3] is not None else 0
                    
                    exists = "NO"
                    status = "MISSING"
                    
                    if doc_id in existing_doc_ids:
                        exists = "YES"
                        status = "VALID"
                        if chunk_count > 0 and embedded_count == 0:
                             status = "NOT EMBEDDED"
                    else:
                        missing_files += 1
                        broken_refs += 1
                        status = "BROKEN"

                    # Truncate title if too long
                    display_title = (title[:27] + '..') if len(title) > 27 else title
                    
                    report_lines.append(f"{doc_id:<36} | {display_title:<30} | {chunk_count:<6} | {embedded_count:<8} | {exists:<15} | {status}")
                    total_indexed_docs += 1
            else:
                 report_lines.append(f"Table 'chunk_metadata' not found in {METADATA_DB_PATH}")

            conn.close()

        except Exception as e:
            report_lines.append(f"Error reading metadata DB: {str(e)}")
            return "ISSUE", 0, 0, 0
    else:
        report_lines.append(f"Metadata DB not found at {METADATA_DB_PATH}")
        return "ISSUE", 0, 0, 0

    report_lines.append("-" * 130)
    report_lines.append(f"\nTotal Indexed Documents: {total_indexed_docs}")
    report_lines.append(f"Missing Files Count: {missing_files}")
    report_lines.append(f"Broken References Count: {broken_refs}")

    with open(os.path.join(REPORTS_DIR, "metadata_index_report.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(report_lines))

    status = "OK" if broken_refs == 0 else "ISSUE"
    return status, total_indexed_docs, missing_files, broken_refs

def generate_vector_report():
    """Inspects ChromaDB folder."""
    report_lines = []
    report_lines.append(f"Vector DB Report - {datetime.datetime.now()}\n")
    
    status = "ISSUE"
    msg = ""
    
    embedding_count = 0
    
    if os.path.exists(CHROMA_DIR):
        # 1. Folder Size
        total_size = 0
        for dirpath, dirnames, filenames in os.walk(CHROMA_DIR):
            for f in filenames:
                fp = os.path.join(dirpath, f)
                total_size += os.path.getsize(fp)
        
        # 2. Index Presence
        # Chroma (sqlite based) usually has chroma.sqlite3
        index_file = os.path.join(CHROMA_DIR, "chroma.sqlite3")
        index_present = os.path.exists(index_file)
        
        # 3. Connection & Count (if possible)
        try:
            if CHROMA_AVAILABLE:
                # Attempt to load persistent client
                client = chromadb.PersistentClient(path=CHROMA_DIR)
                colls = client.list_collections()
                
                report_lines.append(f"ChromaDB Connection: SUCCESS")
                report_lines.append(f"Collections Found: {len(colls)}")
                
                for c in colls:
                    cnt = c.count()
                    embedding_count += cnt
                    report_lines.append(f" - Collection: {c.name}, Embeddings: {cnt}")
                
                if embedding_count > 0:
                    status = "OK"
                else:
                    status = "ISSUE" # Empty DB
                    msg = "DB Empty"
            else:
                report_lines.append("ChromaDB library not installed. Skipping deep inspection.")
                # Fallback heuristic: check if bin files exist in subfolders
                bin_files = []
                for root, _, files in os.walk(CHROMA_DIR):
                    for f in files:
                        if f.endswith(".bin"):
                            bin_files.append(f)
                
                if len(bin_files) > 0 and index_present:
                     status = "OK" # Likely ok
                     embedding_count = "Unknown (Manual Check)"
                else:
                     status = "ISSUE"
                     msg = "Missing index/data files"
        except Exception as e:
            report_lines.append(f"Chroma Analysis Error: {e}")
            status = "ISSUE"

        report_lines.append(f"\nDB Folder Size: {total_size} bytes")
        report_lines.append(f"Index File Present: {index_present}")
        report_lines.append(f"Last Updated: {datetime.datetime.fromtimestamp(os.path.getmtime(CHROMA_DIR))}")
    
    else:
        report_lines.append("Chroma DB Directory Missing!")
        status = "ISSUE"

    validation = "VALID" if status == "OK" else f"ERROR: {msg}"
    report_lines.append(f"\nValidation: {validation}")

    with open(os.path.join(REPORTS_DIR, "vector_db_report.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(report_lines))

    return status, embedding_count

def main():
    print("Starting Storage Diagnosis...")
    
    # 1. Structure Tree
    print("Generating Directory Tree...")
    tree = generate_structure_tree(BASE_DIR)
    with open(os.path.join(REPORTS_DIR, "storage_structure_tree.txt"), "w", encoding="utf-8") as f:
        f.write(tree)
        
    # 2. Notes Inventory
    print("Scanning Notes...")
    files_found, total_files = generate_notes_inventory()
    
    # 3. Metadata
    print("Checking Metadata...")
    meta_status, total_indexed, missing_meta, broken_meta = generate_metadata_report(files_found)
    
    # 4. Vector DB
    print("Inspecting Vector DB...")
    vector_status, vector_count = generate_vector_report()
    
    # 5. Summary
    print("Compiling Summary...")
    notes_status = "OK" if total_files > 0 else "ISSUE" # Warning if empty
    
    # Cross layer consistency
    consistency = "MATCHED"
    if total_files != total_indexed:
        consistency = "MISMATCH"
    
    retrieval = "READY"
    if notes_status == "ISSUE" or meta_status == "ISSUE" or vector_status == "ISSUE":
        retrieval = "NOT READY"
        
    summary_lines = []
    summary_lines.append("Storage Integrity Summary\n")
    summary_lines.append(f"Timestamp: {datetime.datetime.now()}\n")
    summary_lines.append(f"Notes Layer Status:      {notes_status}")
    summary_lines.append(f"Metadata Layer Status:   {meta_status}")
    summary_lines.append(f"Vector Layer Status:     {vector_status}")
    summary_lines.append(f"Cross-Layer Consistency: {consistency}")
    summary_lines.append(f"Retrieval Readiness:     {retrieval}")
    
    summary_lines.append("\nDetected Issues:")
    if total_files == 0: summary_lines.append("- No keys files found in notes directory.")
    if broken_meta > 0: summary_lines.append(f"- {broken_meta} metadata entries point to missing files.")
    if vector_status == "ISSUE": summary_lines.append("- Vector DB appears empty or corrupted.")
    if consistency == "MISMATCH": summary_lines.append(f"- File count ({total_files}) differs from Index count ({total_indexed}).")
    
    with open(os.path.join(REPORTS_DIR, "storage_integrity_summary.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(summary_lines))

    print(f"Done. Reports generated in {REPORTS_DIR}")

if __name__ == "__main__":
    main()
