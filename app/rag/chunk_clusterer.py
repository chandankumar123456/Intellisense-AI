# app/rag/chunk_clusterer.py
"""
Semantic Chunk Clustering & Redundancy Removal.

Groups semantically similar chunks into clusters, keeps the highest
information-density representative from each cluster, and removes
redundant/low-value duplicates.

Goals:
  - Cleaner context for synthesis
  - Higher signal-to-noise ratio
  - Concept diversity over repetition
"""

import re
from typing import Any, Dict, List, Set, Tuple
from collections import defaultdict
from app.core.logging import log_info
from app.core.config import CLUSTER_OVERLAP_THRESHOLD


# Stop words for token extraction
_STOP = frozenset({
    "the", "a", "an", "is", "are", "was", "were", "be", "been",
    "being", "have", "has", "had", "do", "does", "did", "will",
    "would", "could", "should", "may", "might", "shall", "can",
    "of", "in", "to", "for", "with", "on", "at", "by", "from",
    "as", "into", "about", "that", "this", "it", "and", "or",
    "but", "not", "no", "if", "then", "so",
})


def cluster_and_deduplicate(
    chunks: list,
    *,
    overlap_threshold: float = CLUSTER_OVERLAP_THRESHOLD,
    max_output: int = 15,
) -> list:
    """
    Cluster semantically similar chunks and keep best representatives.

    Args:
        chunks: List of chunk objects with .text and .raw_score attributes.
        overlap_threshold: Minimum token overlap ratio to merge into cluster.
        max_output: Maximum number of output chunks.

    Returns:
        Deduplicated list of chunks, sorted by score descending.
    """
    if not chunks or len(chunks) <= 2:
        return chunks

    # Extract token sets for each chunk
    chunk_tokens = []
    for c in chunks:
        text = getattr(c, "text", "") or ""
        tokens = _extract_tokens(text)
        chunk_tokens.append(tokens)

    # Build clusters using greedy single-linkage
    n = len(chunks)
    cluster_id = list(range(n))  # Each chunk starts in its own cluster

    for i in range(n):
        for j in range(i + 1, n):
            if cluster_id[i] == cluster_id[j]:
                continue  # Already same cluster

            overlap = _token_overlap(chunk_tokens[i], chunk_tokens[j])
            if overlap >= overlap_threshold:
                # Merge clusters: assign all of j's cluster to i's cluster
                old_cid = cluster_id[j]
                new_cid = cluster_id[i]
                for k in range(n):
                    if cluster_id[k] == old_cid:
                        cluster_id[k] = new_cid

    # Group chunks by cluster
    clusters: Dict[int, List[int]] = defaultdict(list)
    for idx, cid in enumerate(cluster_id):
        clusters[cid].append(idx)

    # Select best representative from each cluster
    selected = []
    for cid, indices in clusters.items():
        if len(indices) == 1:
            selected.append(chunks[indices[0]])
            continue

        # Score each chunk in cluster: prefer highest information density + raw_score
        best_idx = max(
            indices,
            key=lambda i: _chunk_quality(chunks[i], chunk_tokens[i]),
        )
        selected_chunk = chunks[best_idx]

        # Store clustering metadata
        meta = selected_chunk.metadata if selected_chunk.metadata else {}
        meta["cluster_size"] = len(indices)
        meta["cluster_representative"] = True
        selected_chunk.metadata = meta

        selected.append(selected_chunk)

    # Sort by score descending
    selected.sort(key=lambda c: getattr(c, "raw_score", 0.0), reverse=True)

    # Limit output
    result = selected[:max_output]

    chunks_removed = len(chunks) - len(result)
    clusters_formed = len(clusters)

    log_info(
        f"Chunk clustering: {len(chunks)} → {len(result)} chunks "
        f"({chunks_removed} removed, {clusters_formed} clusters)"
    )

    return result


def _extract_tokens(text: str) -> Set[str]:
    """Extract meaningful tokens from text."""
    words = set(re.findall(r"\b\w+\b", text.lower()))
    return words - _STOP


def _token_overlap(tokens_a: Set[str], tokens_b: Set[str]) -> float:
    """
    Compute token overlap ratio between two sets.
    Uses Jaccard-like metric: |intersection| / |smaller set|
    to handle different-length chunks fairly.
    """
    if not tokens_a or not tokens_b:
        return 0.0
    intersection = len(tokens_a & tokens_b)
    smaller = min(len(tokens_a), len(tokens_b))
    return intersection / smaller


def _chunk_quality(chunk, tokens: Set[str]) -> float:
    """
    Score chunk quality for representative selection.
    Combines raw_score, text length, and token diversity.
    """
    raw_score = getattr(chunk, "raw_score", 0.0) or 0.0
    text = getattr(chunk, "text", "") or ""
    word_count = len(text.split())

    # Length bonus (prefer substantive chunks)
    if word_count < 20:
        length_bonus = 0.1
    elif word_count < 60:
        length_bonus = 0.4
    elif word_count < 150:
        length_bonus = 0.7
    else:
        length_bonus = 0.9

    # Token diversity bonus
    diversity = len(tokens) / max(word_count, 1)
    diversity_bonus = min(1.0, diversity)

    return raw_score * 0.50 + length_bonus * 0.30 + diversity_bonus * 0.20
