# app/student_knowledge/enricher.py
"""
Lightweight semantic enrichment for student knowledge chunks.
Extracts key concepts/entities from each chunk.
"""

import re
from typing import List, Dict, Any
from app.core.logging import log_info


def enrich_chunks(chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Add key concepts to each chunk's metadata.
    Uses lightweight keyword extraction (no LLM call).
    """
    for chunk in chunks:
        text = chunk.get("text", "")
        concepts = extract_concepts(text)
        chunk["concepts"] = concepts[:5]  # Top 5 concepts
    
    total_concepts = sum(len(c.get("concepts", [])) for c in chunks)
    log_info(f"Enriched {len(chunks)} chunks with {total_concepts} total concepts")
    return chunks


def extract_concepts(text: str, max_concepts: int = 5) -> List[str]:
    """
    Extract key concepts from text using TF-based keyword extraction.
    Lightweight — no external model calls.
    """
    if not text or len(text) < 20:
        return []

    # Tokenize and clean
    words = re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())
    
    # Common stop words to filter
    stop_words = {
        "the", "and", "for", "are", "but", "not", "you", "all", "any", "can",
        "had", "her", "was", "one", "our", "out", "has", "his", "how", "its",
        "may", "new", "now", "old", "see", "way", "who", "did", "get", "let",
        "say", "she", "too", "use", "this", "that", "with", "have", "from",
        "they", "been", "will", "each", "make", "like", "long", "look", "many",
        "some", "than", "them", "then", "very", "when", "come", "could", "does",
        "into", "just", "more", "much", "also", "back", "been", "call", "came",
        "what", "your", "which", "their", "there", "these", "those", "would",
        "about", "after", "being", "could", "every", "first", "found", "given",
        "going", "where", "while", "other", "should", "still", "such", "take",
        "than", "well", "most", "only", "over", "such", "through", "between",
    }
    
    # Count word frequencies
    freq = {}
    for word in words:
        if word not in stop_words and len(word) > 3:
            freq[word] = freq.get(word, 0) + 1

    # Also extract multi-word concepts (bigrams)
    bigrams = []
    for i in range(len(words) - 1):
        if words[i] not in stop_words and words[i+1] not in stop_words:
            if len(words[i]) > 3 and len(words[i+1]) > 3:
                bigram = f"{words[i]} {words[i+1]}"
                bigrams.append(bigram)
    
    bigram_freq = {}
    for b in bigrams:
        bigram_freq[b] = bigram_freq.get(b, 0) + 1

    # Combine and sort by frequency
    all_concepts = []
    for word, count in sorted(freq.items(), key=lambda x: -x[1]):
        if count >= 2:  # Must appear at least twice
            all_concepts.append(word)
    for bigram, count in sorted(bigram_freq.items(), key=lambda x: -x[1]):
        if count >= 2:
            all_concepts.append(bigram)

    # If not enough from frequency, take top single words
    if len(all_concepts) < max_concepts:
        for word, count in sorted(freq.items(), key=lambda x: -x[1]):
            if word not in all_concepts:
                all_concepts.append(word)
            if len(all_concepts) >= max_concepts:
                break

    return all_concepts[:max_concepts]
