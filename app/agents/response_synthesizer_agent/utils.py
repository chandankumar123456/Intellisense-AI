# app/agents/response_synthesizer_agent/utils.py
import re

def estimate_tokens(text: str) -> int:
    """
    Heuristic: 1 token ~ 4 chars.
    """
    if not text:
        return 0
    return max(1, len(text) // 4)

def clean_text(text: str) -> str:
    if not text: 
        return ""
    
    text = text.replace("\r", " ").replace("\n", " ")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def sentence_tokenize(text: str):
    """
    Basic sentence splitter using punctuation.
    """
    if not text:
        return []
    
    # split on ., !, ?
    parts = re.split(r"[.!?]+", text)
    sentences = [p.strip() for p in parts if p.strip()]
    return sentences

def token_overlap(a: str, b: str):
    """
    Compute word-level overlap ratio
    """
    if not a or not b:
        return 0.0
    
    a_tokens = set(a.lower().split())
    b_tokens = set(b.lower().split())
    
    if not a_tokens or not b_tokens:
        return 0.0
    
    overlap = len(a_tokens.intersection(b_tokens))
    return overlap / max(len(a_tokens), 1)