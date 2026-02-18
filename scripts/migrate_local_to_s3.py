#!/usr/bin/env python3
"""
Migration Script: Local Document Storage → AWS S3

Walks the data/documents/ directory and uploads each document's files
(text.txt, meta.json) to S3, then updates the storage_pointer in SQLite.

Usage:
    python scripts/migrate_local_to_s3.py                 # dry-run (default)
    python scripts/migrate_local_to_s3.py --execute       # actually migrate
"""

import os
import sys
import argparse
import sqlite3

# Ensure project root is on sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from app.core.config import (
    DOCUMENT_STORAGE_PATH,
    METADATA_DB_PATH,
    S3_BUCKET_NAME,
    S3_DOCUMENT_PREFIX,
)


def get_s3_client():
    from app.infrastructure.s3_client import upload_text, upload_json, upload_bytes, object_exists
    return upload_text, upload_json, upload_bytes, object_exists


def migrate(dry_run: bool = True):
    if not os.path.exists(DOCUMENT_STORAGE_PATH):
        print(f"Local document path does not exist: {DOCUMENT_STORAGE_PATH}")
        return

    doc_dirs = [
        d for d in os.listdir(DOCUMENT_STORAGE_PATH)
        if os.path.isdir(os.path.join(DOCUMENT_STORAGE_PATH, d))
    ]

    if not doc_dirs:
        print("No local documents found to migrate.")
        return

    print(f"Found {len(doc_dirs)} document(s) to migrate.")
    print(f"Target bucket: {S3_BUCKET_NAME}")
    print(f"Mode: {'DRY RUN' if dry_run else 'EXECUTING'}")
    print("-" * 60)

    if not dry_run:
        upload_text, upload_json, upload_bytes, object_exists = get_s3_client()

    migrated = 0
    skipped = 0
    errors = 0

    for doc_id in doc_dirs:
        doc_dir = os.path.join(DOCUMENT_STORAGE_PATH, doc_id)
        text_path = os.path.join(doc_dir, "text.txt")
        meta_path = os.path.join(doc_dir, "meta.json")

        if not os.path.exists(text_path):
            print(f"  SKIP {doc_id}: no text.txt")
            skipped += 1
            continue

        s3_text_key = f"{S3_DOCUMENT_PREFIX}/{doc_id}/text.txt"
        s3_meta_key = f"{S3_DOCUMENT_PREFIX}/{doc_id}/meta.json"

        if dry_run:
            print(f"  WOULD upload {doc_id}/text.txt → s3://{S3_BUCKET_NAME}/{s3_text_key}")
            if os.path.exists(meta_path):
                print(f"  WOULD upload {doc_id}/meta.json → s3://{S3_BUCKET_NAME}/{s3_meta_key}")
            migrated += 1
            continue

        try:
            # Upload text.txt
            with open(text_path, "r", encoding="utf-8") as f:
                text_content = f.read()
            upload_text(s3_text_key, text_content)
            print(f"  ✓ {doc_id}/text.txt ({len(text_content)} chars)")

            # Upload meta.json if exists
            if os.path.exists(meta_path):
                import json
                with open(meta_path, "r", encoding="utf-8") as f:
                    meta_content = json.load(f)
                upload_json(s3_meta_key, meta_content)
                print(f"  ✓ {doc_id}/meta.json")

            # Upload any files in original/ subdirectory
            orig_dir = os.path.join(doc_dir, "original")
            if os.path.isdir(orig_dir):
                for fname in os.listdir(orig_dir):
                    fpath = os.path.join(orig_dir, fname)
                    if os.path.isfile(fpath):
                        with open(fpath, "rb") as f:
                            file_bytes = f.read()
                        s3_orig_key = f"{S3_DOCUMENT_PREFIX}/{doc_id}/original/{fname}"
                        upload_bytes(s3_orig_key, file_bytes)
                        print(f"  ✓ {doc_id}/original/{fname}")

            migrated += 1

        except Exception as e:
            print(f"  ✗ {doc_id}: {e}")
            errors += 1

    # Update storage_pointer in SQLite
    print()
    print("-" * 60)

    if not dry_run and migrated > 0:
        try:
            conn = sqlite3.connect(METADATA_DB_PATH)
            new_prefix = f"s3://{S3_BUCKET_NAME}/{S3_DOCUMENT_PREFIX}"
            updated = conn.execute(
                """
                UPDATE chunk_metadata
                SET storage_pointer = REPLACE(storage_pointer, 'local://', ?)
                WHERE storage_pointer LIKE 'local://%'
                """,
                (new_prefix + "/",),
            ).rowcount
            conn.commit()
            conn.close()
            print(f"Updated {updated} metadata rows: storage_pointer → s3://")
        except Exception as e:
            print(f"Failed to update metadata DB: {e}")
            errors += 1

    print()
    print(f"Summary: migrated={migrated}  skipped={skipped}  errors={errors}")

    if dry_run:
        print()
        print("This was a DRY RUN. Run with --execute to actually migrate.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Migrate local documents to S3")
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Actually perform the migration (default is dry-run)",
    )
    args = parser.parse_args()
    migrate(dry_run=not args.execute)
