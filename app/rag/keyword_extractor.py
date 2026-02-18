import re
import math
from typing import List, Dict, Set

# Standard English stop words + academic fillers to ignore
STOP_WORDS = {
    "a", "about", "above", "after", "again", "against", "all", "am", "an", "and", "any", "are", "aren't",
    "as", "at", "be", "because", "been", "before", "being", "below", "between", "both", "but", "by", 
    "can", "cannot", "could", "couldn't", "did", "didn't", "do", "does", "doesn't", "doing", "don't", 
    "down", "during", "each", "few", "for", "from", "further", "had", "hadn't", "has", "hasn't", "have", 
    "haven't", "having", "he", "he'd", "he'll", "he's", "her", "here", "here's", "hers", "herself", "him", 
    "himself", "his", "how", "how's", "i", "i'd", "i'll", "i'm", "i've", "if", "in", "into", "is", "isn't", 
    "it", "it's", "its", "itself", "let's", "me", "more", "most", "mustn't", "my", "myself", "no", "nor", 
    "not", "of", "off", "on", "once", "only", "or", "other", "ought", "our", "ours", "ourselves", "out", 
    "over", "own", "same", "shan't", "she", "she'd", "she'll", "she's", "should", "shouldn't", "so", 
    "some", "such", "than", "that", "that's", "the", "their", "theirs", "them", "themselves", "then", 
    "there", "there's", "these", "they", "they'd", "they'll", "they're", "they've", "this", "those", 
    "through", "to", "too", "under", "until", "up", "very", "was", "wasn't", "we", "we'd", "we'll", 
    "we're", "we've", "were", "weren't", "what", "what's", "when", "when's", "where", "where's", 
    "which", "while", "who", "who's", "whom", "why", "why's", "with", "won't", "would", "wouldn't", 
    "you", "you'd", "you'll", "you're", "you've", "your", "yours", "yourself", "yourselves",
    # Academic/formatting fillers
    "chapter", "section", "page", "figure", "table", "example", "exercise", "solution", "introduction",
    "summary", "conclusion", "references", "appendix", "http", "https", "www", "com", "org", "edu"
}

def extract_keywords(text: str, top_n: int = 20, min_word_len: int = 3, min_freq: int = 2) -> List[str]:
    """
    Extract key phrases from text using a statistical frequency approach.
    
    Args:
        text: The input document text.
        top_n: Number of keywords to return.
        min_word_len: Minimum length of a token to be considered.
        min_freq: Minimum number of occurrences to be considered a keyword.
        
    Returns:
        List of unique top keywords/phrases.
    """
    if not text:
        return []

    # 1. Normalize and tokenize
    # Split by non-alphanumeric characters, keeping spaces for phrase reconstruction if needed
    # For simplicity, we'll focus on unigrams and bigrams
    text_clean = re.sub(r'[^a-zA-Z0-9\s]', ' ', text.lower())
    tokens = [t for t in text_clean.split() if len(t) >= min_word_len and t not in STOP_WORDS]
    
    if not tokens:
        return []

    # 2. Count unigram frequencies
    freq_dist: Dict[str, int] = {}
    for token in tokens:
        freq_dist[token] = freq_dist.get(token, 0) + 1
        
    # 3. Filter by minimum frequency
    candidates = {k: v for k, v in freq_dist.items() if v >= min_freq}
    
    # 4. Score candidates (Frequency * Length Boost)
    # Longer words are often more specific in technical domains (e.g., 'polymorphism' vs 'code')
    scored_candidates = []
    for word, freq in candidates.items():
        score = freq * math.log(len(word))
        scored_candidates.append((word, score))
        
    # 5. Sort and select top N
    scored_candidates.sort(key=lambda x: x[1], reverse=True)
    
    return [word for word, score in scored_candidates[:top_n]]

def merge_syllabus_keywords(extracted: List[str], syllabus: List[str]) -> List[str]:
    """Merge user-provided syllabus keywords with extracted ones, giving priority to syllabus."""
    normalized_syllabus = {s.lower().strip() for s in syllabus if s.strip()}
    combined = list(normalized_syllabus)
    
    # Append extracted keywords that aren't already in the list
    for kw in extracted:
        if kw not in normalized_syllabus:
            combined.append(kw)
            
    return combined[:50]  # Cap total keywords per document
