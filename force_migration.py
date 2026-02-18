import sys
import os
import sqlite3

# Ensure app is in path
sys.path.append(os.getcwd())

from app.core.config import METADATA_DB_PATH

print(f"Force Migrating DB at: {METADATA_DB_PATH}")

conn = sqlite3.connect(METADATA_DB_PATH)
conn.row_factory = sqlite3.Row

# 1. Ensure table exists
print("Ensuring table chunk_metadata exists...")
conn.executescript("""
    CREATE TABLE IF NOT EXISTS chunk_metadata (
        id              TEXT PRIMARY KEY,
        doc_id          TEXT NOT NULL,
        subject         TEXT DEFAULT '',
        topic           TEXT DEFAULT '',
        subtopic        TEXT DEFAULT '',
        page            INTEGER DEFAULT 0,
        offset_start    INTEGER DEFAULT 0,
        offset_end      INTEGER DEFAULT 0,
        importance_score REAL DEFAULT 0.0,
        vector_chunk_id TEXT DEFAULT NULL,
        storage_pointer TEXT DEFAULT '',
        source_url      TEXT DEFAULT '',
        source_type     TEXT DEFAULT 'note',
        chunk_text      TEXT DEFAULT '',
        user_id         TEXT DEFAULT '',
        created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        last_queried_at TIMESTAMP DEFAULT NULL,
        query_count     INTEGER DEFAULT 0,
        is_embedded     BOOLEAN DEFAULT 0,
        section_type    TEXT DEFAULT 'body',
        document_title  TEXT DEFAULT '',
        academic_year   TEXT DEFAULT '',
        semester        TEXT DEFAULT '',
        module          TEXT DEFAULT '',
        content_type    TEXT DEFAULT 'notes',
        difficulty_level TEXT DEFAULT '',
        source_tag      TEXT DEFAULT '',
        keywords        TEXT DEFAULT ''
    );
""")

# 2. Add columns if missing
_migration_cols = [
    ("secondary_subject", "''"),
    ("confidence", "0.0"),
    ("section_type", "'body'"),
    ("document_title", "''"),
    ("academic_year", "''"),
    ("semester", "''"),
    ("module", "''"),
    ("content_type", "'notes'"),
    ("difficulty_level", "''"),
    ("source_tag", "''"),
    ("keywords", "''"),
]

print("Checking columns...")
cursor = conn.execute("PRAGMA table_info(chunk_metadata)")
existing_columns = {row[1] for row in cursor.fetchall()}

for col, default in _migration_cols:
    if col not in existing_columns:
        try:
            print(f"Adding missing column: {col}...")
            conn.execute(f"ALTER TABLE chunk_metadata ADD COLUMN {col} TEXT DEFAULT {default}")
            print(f"✅ Added {col}")
        except Exception as e:
            print(f"❌ Failed to add {col}: {e}")
    else:
        print(f"Column {col} already exists.")

conn.commit()
print("Migration complete. Verifying...")

cursor = conn.execute("PRAGMA table_info(chunk_metadata)")
final_columns = {row[1] for row in cursor.fetchall()}
required = ["subject", "secondary_subject", "confidence", "section_type"]
missing = [c for c in required if c not in final_columns]

if missing:
    print(f"❌ Still missing: {missing}")
    exit(1)
else:
    print("✅ All columns present.")
    exit(0)
