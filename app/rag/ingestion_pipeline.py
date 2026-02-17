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
from app.infrastructure.metadata_store import upsert_metadata_batch
from app.infrastructure.document_store import store_document


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
) -> dict:
    """
    Full ingestion pipeline following EviLearn rules.

    Returns summary dict with stats.
    """
    try:
        log_info(f"Starting ingestion for doc {doc_id} ({len(text)} chars)")

        # 0. Store full document in Layer-2
        store_document(doc_id, text, {
            "source_url": source_url,
            "source_type": source_type,
            "user_id": user_id,
            "subject": subject,
            "topic": topic,
            "subtopic": subtopic,
        })

        # 1. Create candidate chunks
        candidates = chunk_text_smart(
            text=text,
            doc_id=doc_id,
            source_url=source_url,
            source_type=source_type,
            user_id=user_id,
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
        embed_candidates = [c for c in candidates if c.should_embed]
        embed_embeddings = [
            embeddings[i] for i, c in enumerate(candidates) if c.should_embed
        ]

        if embed_candidates:
            from app.agents.retrieval_agent.utils import index
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
                    },
                })

            await asyncio.to_thread(
                index.upsert, vectors=vectors, namespace=PINECONE_NAMESPACE
            )
            log_info(
                f"Embedded {len(embed_candidates)}/{len(candidates)} chunks "
                f"(importance >= {IMPORTANCE_EMBED_THRESHOLD})"
            )

        # 6. Create metadata entries for ALL chunks (embedded + raw)
        metadata_entries = []
        for i, chunk in enumerate(candidates):
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
                "storage_pointer": f"local://{doc_id}",
                "source_url": chunk.source_url,
                "source_type": chunk.source_type,
                "chunk_text": chunk.text,
                "user_id": chunk.user_id,
                "is_embedded": chunk.should_embed,
            })

        upsert_metadata_batch(metadata_entries)
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
