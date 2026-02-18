# app/rag/section_detector.py
"""
Rule-based section detector for document chunks.
Assigns a section_type label to each chunk based on heading patterns
and positional heuristics.
"""

import re
from typing import List, Optional


# Section heading patterns — ordered by specificity
SECTION_PATTERNS = {
    "abstract": [
        r"(?i)\babstract\b",
    ],
    "introduction": [
        r"(?i)\bintroduction\b",
        r"(?i)\bintro\b",
        r"(?i)\b1\.\s*introduction\b",
    ],
    "literature_review": [
        r"(?i)\bliterature\s+review\b",
        r"(?i)\brelated\s+work\b",
        r"(?i)\bbackground\b",
        r"(?i)\bprior\s+work\b",
    ],
    "methodology": [
        r"(?i)\bmethodology\b",
        r"(?i)\bmethods?\b",
        r"(?i)\bapproach\b",
        r"(?i)\bproposed\s+(method|approach|system|framework)\b",
        r"(?i)\bexperimental\s+setup\b",
        r"(?i)\bdesign\b",
        r"(?i)\bimplementation\b",
    ],
    "results": [
        r"(?i)\bresults?\b",
        r"(?i)\bfindings\b",
        r"(?i)\bexperiments?\b",
        r"(?i)\bevaluation\b",
        r"(?i)\bperformance\b",
    ],
    "discussion": [
        r"(?i)\bdiscussion\b",
        r"(?i)\banalysis\b",
    ],
    "conclusion": [
        r"(?i)\bconclusion\b",
        r"(?i)\bconcluding\s+remarks\b",
        r"(?i)\bsummary\b",
        r"(?i)\bfuture\s+work\b",
    ],
    "references": [
        r"(?i)\breferences\b",
        r"(?i)\bbibliography\b",
        r"(?i)\bcitations?\b",
    ],
    "acknowledgements": [
        r"(?i)\backnowledgements?\b",
        r"(?i)\backnowledgments?\b",
    ],
    "appendix": [
        r"(?i)\bappendix\b",
        r"(?i)\bappendices\b",
        r"(?i)\bsupplementary\b",
    ],
}


# Patterns that suggest a heading line (short line, possibly numbered)
HEADING_LINE_PATTERN = re.compile(
    r"^(?:\d+\.?\s*)?([A-Z][A-Za-z\s&,-]+)$", re.MULTILINE
)


def detect_section(
    text: str,
    chunk_index: int = 0,
    total_chunks: int = 1,
) -> str:
    """
    Detect the section type of a chunk.

    Args:
        text: The chunk text content.
        chunk_index: The 0-based index of this chunk in the document.
        total_chunks: Total number of chunks in the document.

    Returns:
        A section_type string (e.g., 'abstract', 'introduction', 'conclusion', 'body').
    """
    if not text or not text.strip():
        return "body"

    # 1. Extract the first line (most likely a heading)
    first_line = text.strip().split('\n')[0].strip()[:200]

    # 2. Check the first line for section heading patterns (highest priority)
    for section_type, patterns in SECTION_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, first_line):
                return section_type

    # 3. Check header region (first ~200 chars) for patterns, but only heading-like lines
    header_region = text[:200]
    heading_matches = HEADING_LINE_PATTERN.findall(header_region)
    for heading in heading_matches:
        heading_lower = heading.strip().lower()
        for section_type, patterns in SECTION_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, heading_lower):
                    return section_type

    # 4. Check first ~300 chars for numbered section headings
    heading_matches_extended = HEADING_LINE_PATTERN.findall(text[:300])
    for heading in heading_matches_extended:
        heading_lower = heading.strip().lower()
        for section_type, patterns in SECTION_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, heading_lower):
                    return section_type

    # 5. Positional heuristics (fallback)
    if total_chunks > 1:
        position_ratio = chunk_index / max(total_chunks - 1, 1)

        # First chunk is often abstract or introduction
        if chunk_index == 0:
            if len(text.split()) < 400 and "abstract" not in text.lower():
                return "introduction"

        # Last ~10% is often conclusion/references
        if position_ratio >= 0.90:
            return "conclusion"

    # Default
    return "body"


def detect_sections_batch(
    texts: List[str],
) -> List[str]:
    """
    Detect section types for a batch of chunk texts from the same document.
    Uses both content analysis and positional heuristics.

    Args:
        texts: List of chunk texts in document order.

    Returns:
        List of section_type strings.
    """
    total = len(texts)
    return [
        detect_section(text, i, total)
        for i, text in enumerate(texts)
    ]
