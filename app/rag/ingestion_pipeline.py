# app/rag/ingestion_pipeline.py
"""
EviLearn Ingestion Pipeline (agent-enforced rules)

When ingesting new files:
1. Extract text and create candidate chunks.
2. Remove duplicates (cosine > 0.92) and noise (short garbage sections).
3. Compute chunk importance.
4. Embed and upsert only chunks with importance >= 0.7 or chunks flagged by teacher.
5. Create metadata entries for every chunk (both embedded and raw) mapping to storage pointers.
"""

import asyncio
import uuid
from typing import List, Optional
from app.core.config import (
    PINECONE_NAMESPACE,
    IMPORTANCE_EMBED_THRESHOLD,
)
from app.core.logging import log_info, log_error, log_warning
from app.rag.schemas import ChunkCandidate
from app.rag.chunker import chunk_text_smart, deduplicate_chunks
from app.rag.importance_scorer import compute_importance, should_embed
from app.core.config import STORAGE_BACKEND, S3_BUCKET_NAME, S3_DOCUMENT_PREFIX, STORAGE_MODE
# from app.infrastructure.metadata_store import upsert_metadata_batch # Removed
# from app.infrastructure.document_store import store_document, store_original_file # Removed


async def ingest_document(
    text: str,
    doc_id: str,
    source_url: str = "",
    source_type: str = "note",
    user_id: str = "",
    syllabus_keywords: Optional[List[str]] = None,
    teacher_tagged_chunks: Optional[List[int]] = None,
    subject: str = "",
    topic: str = "",
    subtopic: str = "",
    document_title: str = "",
) -> dict:
    """
    Full ingestion pipeline following EviLearn rules.

    Returns summary dict with stats.
    """
    try:
        log_info(f"Starting ingestion for doc {doc_id} ({len(text)} chars)")

        # 0. Store full document via SAL
        from app.storage import storage_manager
        
        storage_manager.files.save_file(
            f"{doc_id}/text.txt", 
            text.encode("utf-8"), 
            "text/plain"
        )
        import json
        storage_manager.files.save_file(
            f"{doc_id}/meta.json", 
            json.dumps({
                "source_url": source_url,
                "source_type": source_type,
                "user_id": user_id,
                "subject": subject,
                "topic": topic,
                "subtopic": subtopic,
            }).encode("utf-8"),
            "application/json"
        )

        # 1. Create candidate chunks
        candidates = chunk_text_smart(
            text=text,
            doc_id=doc_id,
            source_url=source_url,
            source_type=source_type,
            user_id=user_id,
            document_title=document_title,
        )

        if not candidates:
            log_warning(f"No chunks created for doc {doc_id}")
            return {"status": "empty", "chunks_total": 0, "chunks_embedded": 0}

        # 2. Generate embeddings for deduplication
        from app.agents.retrieval_agent.utils import embed_text
        chunk_texts = [c.text for c in candidates]
        embeddings = await asyncio.to_thread(embed_text, chunk_texts)

        # 3. Deduplicate
        candidates, embeddings = deduplicate_chunks(candidates, embeddings)

        # 4. Compute importance and decide embedding
        teacher_set = set(teacher_tagged_chunks or [])
        for i, chunk in enumerate(candidates):
            is_teacher_tagged = i in teacher_set
            chunk.importance_score = compute_importance(
                text=chunk.text,
                syllabus_keywords=syllabus_keywords,
                teacher_tagged=is_teacher_tagged,
            )
            chunk.should_embed = should_embed(chunk.importance_score, is_teacher_tagged)
            chunk.subject = subject
            chunk.topic = topic
            chunk.subtopic = subtopic

        # 5. Embed and upsert only qualifying chunks
        # Rule: Embed if score >= THRESHOLD, OR if teacher tagged.
        # Fallback: If ZERO chunks qualify, embed the top 3 by score to ensure *something* is searchable.
        
        embed_candidates = [c for c in candidates if c.should_embed]
        
        if not embed_candidates and candidates:
            # Fallback strategy
            log_warning(f"No chunks received score >= {IMPORTANCE_EMBED_THRESHOLD}. Forcing embed of top 3 chunks.")
            # Sort by importance descending
            sorted_candidates = sorted(candidates, key=lambda x: x.importance_score, reverse=True)
            embed_candidates = sorted_candidates[:3]
            for c in embed_candidates:
                c.should_embed = True # Mark as embedded for metadata logic

        embed_embeddings = []
        if embed_candidates:
             # Optimization: We already computed embeddings for ALL chunks in step 2 for deduplication.
             # We can just map them.
             candidate_to_embedding = {c.id: embeddings[i] for i, c in enumerate(candidates)}
             embed_embeddings = [candidate_to_embedding[c.id] for c in embed_candidates]

        if embed_candidates:
            vectors = []
            for i, chunk in enumerate(embed_candidates):
                chunk.id = chunk.id or f"{doc_id}_{chunk.page}_{i}"
                vectors.append({
                    "id": chunk.id,
                    "values": embed_embeddings[i],
                    "metadata": {
                        "chunk_text": chunk.text,
                        "source_type": chunk.source_type,
                        "source_url": chunk.source_url,
                        "category": "user_upload",
                        "user_id": chunk.user_id,
                        "doc_id": chunk.doc_id,
                        "page": chunk.page,
                        "offset_start": chunk.offset_start,
                        "offset_end": chunk.offset_end,
                        "importance_score": chunk.importance_score,
                        "subject": chunk.subject,
                        "topic": chunk.topic,
                        "subtopic": chunk.subtopic or "",
                        "section_type": chunk.section_type,
                        "document_title": chunk.document_title,
                    },
                })

            await asyncio.to_thread(
                storage_manager.vectors.upsert, vectors=vectors, namespace=PINECONE_NAMESPACE
            )
            log_info(
                f"Embedded {len(embed_candidates)}/{len(candidates)} chunks. "
                f"(Threshold: {IMPORTANCE_EMBED_THRESHOLD}, Fallback used: {'Yes' if not any(c.importance_score >= IMPORTANCE_EMBED_THRESHOLD for c in embed_candidates) else 'No'})"
            )

        # 6. Create metadata entries for ALL chunks (embedded + raw)
        metadata_entries = []
        for i, chunk in enumerate(candidates):
            # If we don't know the exact path prefix here easily without asking the file storage, 
            # we can just store the doc_id and let the retriever resolve it via SAL.
            # But the prompt required "local://..." or "s3://...".
            # The SAL save_file returns the full path/URI. 
            # We didn't capture it above for the main doc, but we know the pattern.
            # Let's ask the storage manager's file adapter for the scheme/prefix if needed, 
            # or just rely on the stored doc_id. 
            # However, existing metadata has `storage_pointer`.
            # Let's reconstruct it or simplify.
            
            # Since we are using SAL, `storage_pointer` is less critical if we fetch via SAL using doc_id.
            # But to maintain data shape:
            from app.core.config import STORAGE_MODE
            storage_pointer = (
                f"s3://{S3_BUCKET_NAME}/{S3_DOCUMENT_PREFIX}/{doc_id}"
                if STORAGE_MODE == "aws"
                else f"local://{doc_id}"
            )
            
            metadata_entries.append({
                "id": chunk.id or f"{doc_id}_{chunk.page}_{i}",
                "doc_id": chunk.doc_id,
                "subject": chunk.subject,
                "topic": chunk.topic,
                "subtopic": chunk.subtopic,
                "page": chunk.page,
                "offset_start": chunk.offset_start,
                "offset_end": chunk.offset_end,
                "importance_score": chunk.importance_score,
                "vector_chunk_id": chunk.id if chunk.should_embed else None,
                "storage_pointer": storage_pointer,
                "source_url": chunk.source_url,
                "source_type": chunk.source_type,
                "chunk_text": chunk.text,
                "user_id": chunk.user_id,
                "is_embedded": chunk.should_embed,
                "section_type": chunk.section_type,
                "document_title": chunk.document_title,
            })

        storage_manager.metadata.upsert_batch(metadata_entries)
        log_info(f"Metadata indexed for all {len(metadata_entries)} chunks")

        return {
            "status": "success",
            "doc_id": doc_id,
            "chunks_total": len(candidates),
            "chunks_embedded": len(embed_candidates),
            "chunks_raw_only": len(candidates) - len(embed_candidates),
        }

    except Exception as e:
        log_error(f"Ingestion pipeline failed for doc {doc_id}: {e}")
        import traceback
        log_error(traceback.format_exc())
        return {"status": "error", "error": str(e)}
