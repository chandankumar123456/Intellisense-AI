# app/rag/importance_scorer.py
"""
Importance scoring for chunks.
Combines multiple signals to assign [0,1] importance for each chunk.
Only chunks ≥ 0.7 are embedded into the vector index.
"""

import re
from typing import List, Optional
from app.core.config import IMPORTANCE_WEIGHTS, IMPORTANCE_EMBED_THRESHOLD


# Common header patterns that indicate high-importance sections
HIGH_IMPORTANCE_HEADERS = [
    r"(?i)(definition|theorem|proof|formula|equation|summary|conclusion|key\s+point)",
    r"(?i)(important|note|remember|exam\s+tip|frequently\s+asked)",
    r"(?i)(chapter\s+\d|section\s+\d|unit\s+\d)",
    r"(?i)(algorithm|procedure|method|step)",
]

# Noise patterns indicating low-importance content
NOISE_PATTERNS = [
    r"(?i)(page\s*\d+|table\s+of\s+contents|index|bibliography|references\s*$)",
    r"(?i)(copyright|all\s+rights\s+reserved|publisher)",
    r"^\s*$",
]


def compute_importance(
    text: str,
    syllabus_keywords: Optional[List[str]] = None,
    teacher_tagged: bool = False,
    citation_count: int = 0,
) -> float:
    """
    Compute importance score [0, 1] for a chunk.
    Weights defined in config.

    Signals:
    - syllabus_match: how many syllabus keywords appear
    - header_prominence: whether text contains high-importance headers
    - citation_frequency: how often this content is cited
    - teacher_tag: explicitly flagged by teacher
    - content_density: word-to-noise ratio
    """
    w = IMPORTANCE_WEIGHTS

    # 1. Syllabus match (0-1)
    syllabus_score = 0.0
    if syllabus_keywords:
        lower_text = text.lower()
        matches = sum(1 for kw in syllabus_keywords if kw.lower() in lower_text)
        syllabus_score = min(1.0, matches / max(len(syllabus_keywords), 1))

    # 2. Header prominence (0-1)
    header_score = 0.0
    for pattern in HIGH_IMPORTANCE_HEADERS:
        if re.search(pattern, text):
            header_score = min(1.0, header_score + 0.25)

    # 3. Citation frequency (0-1, log scale)
    import math
    citation_score = min(1.0, math.log1p(citation_count) / 3.0)

    # 4. Teacher tag (binary)
    teacher_score = 1.0 if teacher_tagged else 0.0

    # 5. Content density (word count, sentence structure)
    words = text.split()
    word_count = len(words)
    # Penalize very short or very long chunks, reward ~400-600 word range
    if word_count < 20:
        density_score = 0.1
    elif word_count < 100:
        density_score = 0.5
    elif word_count <= 700:
        density_score = 0.9
    else:
        density_score = 0.7

    # Check if mostly noise
    for pattern in NOISE_PATTERNS:
        if re.search(pattern, text):
            density_score *= 0.5

    # Weighted combination
    importance = (
        w["syllabus_match"] * syllabus_score
        + w["header_prominence"] * header_score
        + w["citation_frequency"] * citation_score
        + w["teacher_tag"] * teacher_score
        + w["content_density"] * density_score
    )

    return round(min(1.0, max(0.0, importance)), 4)


def should_embed(importance_score: float, teacher_tagged: bool = False) -> bool:
    """Decide whether a chunk should be embedded into Layer-1."""
    if teacher_tagged:
        return True
    return importance_score >= IMPORTANCE_EMBED_THRESHOLD
