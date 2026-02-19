# app/rag/hierarchical_retriever.py
"""
Hierarchical Retrieval — Structure-Aware Search.

Performs a three-stage cascade:
  1. Document scoring  — aggregate chunk scores per document, pick top N
  2. Section scoring   — within winning documents, group & score by section
  3. Chunk selection   — from winning sections, boost structurally aligned chunks

This layer runs AFTER initial retrieval + merge but BEFORE reranking.
It re-weights chunks so that structurally coherent context floats to the top.
"""

from typing import List, Dict, Any, Optional
from collections import defaultdict
from app.core.logging import log_info
from app.core.config import (
    HIERARCHICAL_TOP_DOCS,
    HIERARCHICAL_SECTION_BOOST,
)


# Section priority order (higher index = more important for answer quality)
SECTION_PRIORITY = {
    "definition": 1.0,
    "introduction": 0.85,
    "methodology": 0.80,
    "results": 0.75,
    "discussion": 0.70,
    "abstract": 0.65,
    "conclusion": 0.60,
    "literature_review": 0.55,
    "body": 0.50,
    "acknowledgements": 0.20,
    "references": 0.15,
    "appendix": 0.30,
}


def hierarchical_rerank(
    chunks: list,
    *,
    top_docs: int = HIERARCHICAL_TOP_DOCS,
    section_boost: float = HIERARCHICAL_SECTION_BOOST,
    target_section: Optional[str] = None,
) -> list:
    """
    Re-weight chunks using document→section→chunk hierarchy.

    Args:
        chunks: Merged chunks from all retrieval passes.
        top_docs: Max number of documents to keep.
        section_boost: Boost multiplier for same-section coherence.
        target_section: If intent detected a target section, extra boost.

    Returns:
        Re-ordered list of chunks with adjusted raw_score values.
    """
    if not chunks or len(chunks) <= 3:
        return chunks

    # ── Stage 1: Document Scoring ──
    doc_scores: Dict[str, float] = defaultdict(float)
    doc_chunks: Dict[str, list] = defaultdict(list)
    no_doc_chunks = []

    for chunk in chunks:
        doc_id = getattr(chunk, "document_id", "") or ""
        if not doc_id:
            no_doc_chunks.append(chunk)
            continue
        score = getattr(chunk, "raw_score", 0.0) or 0.0
        doc_scores[doc_id] += score
        doc_chunks[doc_id].append(chunk)

    # Rank documents by aggregate score
    ranked_docs = sorted(doc_scores.items(), key=lambda x: x[1], reverse=True)
    top_doc_ids = set(doc_id for doc_id, _ in ranked_docs[:top_docs])

    log_info(
        f"Hierarchical: {len(doc_scores)} docs scored, "
        f"top {len(top_doc_ids)}: {[d[:12] for d in top_doc_ids]}"
    )

    # ── Stage 2: Section Scoring (within winning docs) ──
    boosted_chunks = []

    for doc_id in top_doc_ids:
        section_groups: Dict[str, list] = defaultdict(list)
        for chunk in doc_chunks[doc_id]:
            sec = _get_section(chunk)
            section_groups[sec].append(chunk)

        # Score each section
        for sec_type, sec_chunks in section_groups.items():
            sec_priority = SECTION_PRIORITY.get(sec_type, 0.50)

            for chunk in sec_chunks:
                # ── Stage 3: Chunk-level structural boost ──
                base_score = getattr(chunk, "raw_score", 0.0) or 0.0

                # Boost 1: Document is top-ranked → small boost
                doc_rank_boost = 0.05

                # Boost 2: Section priority
                section_priority_boost = sec_priority * section_boost

                # Boost 3: Target section match (if intent detected)
                target_match_boost = 0.0
                if target_section and sec_type == target_section:
                    target_match_boost = 0.10

                # Boost 4: Section coherence — multiple chunks from same section
                coherence_boost = 0.0
                if len(sec_chunks) >= 2:
                    coherence_boost = 0.05  # Reward sections with multiple hits

                new_score = base_score + doc_rank_boost + section_priority_boost + target_match_boost + coherence_boost
                chunk.raw_score = round(min(1.5, new_score), 4)

                # Store hierarchy info in metadata
                meta = chunk.metadata if chunk.metadata else {}
                meta["hierarchical_doc_rank"] = list(top_doc_ids).index(doc_id) + 1
                meta["hierarchical_section"] = sec_type
                meta["hierarchical_boost"] = round(new_score - base_score, 4)
                chunk.metadata = meta

                boosted_chunks.append(chunk)

    # Add chunks from non-top documents with a small penalty
    for doc_id, d_chunks in doc_chunks.items():
        if doc_id not in top_doc_ids:
            for chunk in d_chunks:
                base_score = getattr(chunk, "raw_score", 0.0) or 0.0
                chunk.raw_score = round(max(0.0, base_score - 0.05), 4)
                meta = chunk.metadata if chunk.metadata else {}
                meta["hierarchical_doc_rank"] = 0  # Not in top docs
                meta["hierarchical_boost"] = -0.05
                chunk.metadata = meta
                boosted_chunks.append(chunk)

    # Add chunks with no doc_id
    boosted_chunks.extend(no_doc_chunks)

    # Sort by new score descending
    boosted_chunks.sort(key=lambda c: getattr(c, "raw_score", 0.0), reverse=True)

    log_info(
        f"Hierarchical rerank complete: {len(boosted_chunks)} chunks, "
        f"top score={boosted_chunks[0].raw_score:.3f}" if boosted_chunks else "no chunks"
    )

    return boosted_chunks


def _get_section(chunk) -> str:
    """Extract section_type from chunk."""
    sec = getattr(chunk, "section_type", None)
    if sec:
        return sec
    meta = getattr(chunk, "metadata", {}) or {}
    return meta.get("section_type", "body")
