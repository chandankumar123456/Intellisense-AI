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
from app.rag.keyword_extractor import extract_keywords
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
    academic_year: str = "",
    semester: str = "",
    module: str = "",
    content_type: str = "notes",
    difficulty_level: str = "",
    source_tag: str = "",
    keywords: str = "",
    # Detected metadata overrides
    confidence: float = 0.0,
    secondary_subject: str = "",
    # New: Namespace support
    namespace: Optional[str] = None,
) -> dict:
    """
    Full ingestion pipeline following EviLearn rules.
    Atomic: Buffers all chunks/embeddings, then upserts.
    Rolls back vectors if metadata storage fails.

    Returns summary dict with stats.
    """
    vectors_upserted = False
    target_namespace = namespace or PINECONE_NAMESPACE

    try:
        log_info(f"Starting ingestion for doc {doc_id} ({len(text)} chars) into namespace '{target_namespace}'")

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
                "academic_year": academic_year,
                "semester": semester,
                "module": module,
                "content_type": content_type,
                "difficulty_level": difficulty_level,
                "source_tag": source_tag,
                "keywords": keywords,
                "confidence": confidence,
                "secondary_subject": secondary_subject,
                "namespace": target_namespace,
            }).encode("utf-8"),
            "application/json"
        )

        # 0.5 Dynamic Subject Learning & Identification
        # ---------------------------------------------
        from app.rag.subject_detector import detect_subject

        # If subject is provided (e.g. from UI or Router detection), we trust it.
        # But we might still need content_type or other fields if not provided.
        if subject:
             # Just ensure confidence/secondary are recorded if passed
             pass
        else:
            # If subject is NOT provided, try to detect it automatically
            log_info("Autodetecting subject for document...")
            # Use text prefix for speed
            detection = detect_subject(text[:5000])
            if detection.subject:
                subject = detection.subject
                confidence = detection.confidence
                secondary_subject = detection.secondary_subject
                
                log_info(f"Detected subject: '{subject}' (Confidence: {confidence:.2f}, Type: {detection.content_type})")
                
                # Update other fields if empty
                if not content_type and detection.content_type:
                    content_type = detection.content_type
                
                # Append secondary info to keywords if relevant
                if detection.secondary_subject:
                     keywords = f"{keywords}, Secondary: {detection.secondary_subject}" if keywords else f"Secondary: {detection.secondary_subject}"
            else:
                log_warning("Subject detection returned no result.")

        # Update the subject index with keywords (whether detected or provided)
        if subject:
            try:
                # automated extraction of more granular keywords
                extracted_kws = extract_keywords(text)
                
                # merge with user provided keywords (syllabus_keywords + keywords param)
                user_kws = []
                if syllabus_keywords:
                    user_kws.extend(syllabus_keywords)
                if keywords:
                    user_kws.extend([k.strip() for k in keywords.split(',') if k.strip()])
                
                # Update index for each unique keyword
                all_kws = set(extracted_kws + user_kws)
                for kw in all_kws:
                    # Increment count for this subject
                    # (Implementation wrapper detail)
                    if hasattr(storage_manager.metadata, 'impl'):
                         storage_manager.metadata.impl.update_keyword_index(kw, subject)
                    elif hasattr(storage_manager.metadata, 'update_keyword_index'):
                         storage_manager.metadata.update_keyword_index(kw, subject)
                         
                log_info(f"Updated subject index for '{subject}' with {len(all_kws)} keywords")
            except Exception as e:
                log_warning(f"Failed to update subject index: {e}")

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
            chunk.academic_year = academic_year
            chunk.semester = semester
            chunk.module = module
            chunk.content_type = content_type
            chunk.difficulty_level = difficulty_level
            chunk.source_tag = source_tag
            chunk.keywords = keywords

        # 5. Prepare Embeddings (Buffer)
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

        vectors_to_upsert = []
        if embed_candidates:
            for i, chunk in enumerate(embed_candidates):
                chunk.id = chunk.id or f"{doc_id}_{chunk.page}_{i}"
                vectors_to_upsert.append({
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
                        "academic_year": chunk.academic_year,
                        "semester": chunk.semester,
                        "module": chunk.module,
                        "content_type": chunk.content_type,
                        "difficulty_level": chunk.difficulty_level,
                        "source_tag": chunk.source_tag,
                        "keywords": chunk.keywords,
                        "namespace": target_namespace,
                    },
                })

        # 6. Prepare Metadata Entries (Buffer)
        metadata_entries = []
        from app.core.config import STORAGE_MODE
        # Need S3_BUCKET_NAME/PREFIX from config ideally, but assuming imports exist or we mock
        # For simplicity, using "local" prefix default if not AWS.
        # We can re-import inside the function if needed or rely on global scope if defined.
        # But better to be safe:
        try:
            from app.core.config import S3_BUCKET_NAME, S3_DOCUMENT_PREFIX
        except ImportError:
            S3_BUCKET_NAME = "evilearn-docs"
            S3_DOCUMENT_PREFIX = "documents"

        storage_pointer = (
            f"s3://{S3_BUCKET_NAME}/{S3_DOCUMENT_PREFIX}/{doc_id}"
            if STORAGE_MODE == "aws"
            else f"local://{doc_id}"
        )

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
                "storage_pointer": storage_pointer,
                "source_url": chunk.source_url,
                "source_type": chunk.source_type,
                "chunk_text": chunk.text,
                "user_id": chunk.user_id,
                "is_embedded": chunk.should_embed,
                "section_type": chunk.section_type,
                "document_title": chunk.document_title,
                "academic_year": chunk.academic_year,
                "semester": chunk.semester,
                "module": chunk.module,
                "content_type": chunk.content_type,
                "difficulty_level": chunk.difficulty_level,
                "source_tag": chunk.source_tag,
                "keywords": chunk.keywords,
                "confidence": confidence,
                "secondary_subject": secondary_subject,
                "namespace": target_namespace,
            })

        # 7. Execute Atomic Upsert Sequence
        
        # Step A: Upsert Vectors
        if vectors_to_upsert:
            log_info(f"Upserting {len(vectors_to_upsert)} vectors to namespace '{target_namespace}'...")
            await asyncio.to_thread(
                storage_manager.vectors.upsert, 
                vectors=vectors_to_upsert, 
                namespace=target_namespace
            )
            vectors_upserted = True

        # Step B: Upsert Metadata
        # If this fails, we rollback vectors
        log_info(f"Upserting {len(metadata_entries)} metadata entries...")
        storage_manager.metadata.upsert_batch(metadata_entries)
        
        log_info(f"Ingestion complete for {doc_id}. Namespace: {target_namespace}")

        return {
            "status": "success",
            "doc_id": doc_id,
            "chunks_total": len(candidates),
            "chunks_embedded": len(embed_candidates),
            "chunks_raw_only": len(candidates) - len(embed_candidates),
            "namespace": target_namespace,
        }

    except Exception as e:
        log_error(f"Ingestion pipeline failed for doc {doc_id}: {e}")
        
        # Rollback: Delete inserted vectors if we managed to insert them but failed later
        if vectors_upserted:
            log_warning(f"Rolling back vectors for doc {doc_id} in namespace {target_namespace} due to failure...")
            try:
                # We need the IDs we inserted
                ids_to_delete = [v["id"] for v in vectors_to_upsert] if 'vectors_to_upsert' in locals() else []
                if ids_to_delete:
                    await asyncio.to_thread(
                        storage_manager.vectors.delete,
                        ids=ids_to_delete,
                        namespace=target_namespace
                    )
                    log_info("Rollback successful.")
            except Exception as rollback_err:
                 log_error(f"Rollback failed: {rollback_err}")

        import traceback
        log_error(traceback.format_exc())
        return {"status": "error", "error": str(e)}
