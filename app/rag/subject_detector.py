# app/rag/subject_detector.py
"""
Rule-based subject detection from user queries.

Detects the most likely academic subject from a query string by matching
against a keyword map. Returns a SubjectScope with confidence score and
ambiguity flag. No LLM calls — runs in <1ms.
"""

from pydantic import BaseModel
from typing import Optional, Dict, List, Set
import re


from pydantic import BaseModel
import time
from app.core.logging import log_info, log_warning

# In-memory cache of the subject index
_INDEX_CACHE: Dict[str, Dict[str, int]] = {}
_LAST_CACHE_UPDATE: float = 0
_CACHE_TTL: int = 300  # 5 minutes

class SubjectScope(BaseModel):
    """Result of subject detection from a user query."""
    subject: str = ""                 # Best-match subject name
    semester: str = ""                # Optional semester narrowing
    topic: str = ""                   # Optional topic narrowing
    confidence: float = 0.0           # 0.0–1.0
    is_ambiguous: bool = False        # True if two+ subjects tie
    matched_subjects: List[str] = []  # All subjects that matched

# ── Dynamic Index Management ──

def _seed_legacy_map(metadata_store):
    """
    Seed duplication of the old static map into the DB if empty.
    This ensures backward compatibility and instant utility on first run.
    """
    try:
        # Minimal seed map to ensure system works out-of-the-box
        legacy_map = {
            "DBMS": {
                "database", "dbms", "sql", "normalization", "er diagram",
                "relational", "acid", "transaction", "deadlock", "b-tree",
                "indexing", "schema", "query", "join", "aggregate",
                "functional dependency", "bcnf", "3nf", "2nf", "1nf",
                "denormalization", "nosql", "mongodb", "postgre", "mysql",
                "data model", "relational algebra", "tuple", "attribute",
            },
            "Operating Systems": {
                "os", "operating system", "process", "thread", "cpu scheduling",
                "deadlock", "semaphore", "mutex", "paging", "segmentation",
                "virtual memory", "file system", "page replacement",
                "round robin", "sjf", "fcfs", "priority scheduling",
                "process synchronization", "critical section", "memory management",
                "disk scheduling", "ipc", "inter process",
            },
            "Data Structures": {
                "data structure", "array", "linked list", "stack", "queue",
                "binary tree", "bst", "heap", "graph", "hash table",
                "sorting", "searching", "traversal", "dfs", "bfs",
                "dynamic programming", "greedy", "recursion", "tree",
                "avl", "red black", "trie", "priority queue",
            },
            "Computer Networks": {
                "network", "tcp", "udp", "ip", "osi model", "http",
                "dns", "routing", "subnet", "mac address", "arp",
                "lan", "wan", "firewall", "socket", "ethernet",
                "congestion control", "flow control", "sliding window",
                "transport layer", "application layer", "network layer",
            },
            "Machine Learning": {
                "machine learning", "ml", "regression", "classification",
                "neural network", "deep learning", "svm", "knn",
                "decision tree", "random forest", "gradient descent",
                "backpropagation", "overfitting", "underfitting",
                "cross validation", "feature extraction", "clustering",
                "k-means", "cnn", "rnn", "lstm", "transformer",
                "nlp", "reinforcement learning", "supervised", "unsupervised",
            },
            "Software Engineering": {
                "software engineering", "sdlc", "agile", "scrum", "waterfall",
                "uml", "use case", "class diagram", "design pattern",
                "testing", "unit test", "integration test", "requirement",
                "spiral model", "v model", "prototype", "coupling",
                "cohesion", "software architecture", "dfd", "data flow",
            },
            "Theory of Computation": {
                "automata", "toc", "turing machine", "dfa", "nfa",
                "regular expression", "context free grammar", "cfg",
                "pushdown automata", "pumping lemma", "chomsky",
                "halting problem", "decidability", "regular language",
                "finite automaton", "formal language",
            },
            "Compiler Design": {
                "compiler", "lexer", "parser", "syntax analysis",
                "semantic analysis", "code generation", "optimization",
                "lex", "yacc", "token", "grammar", "parse tree",
                "syntax tree", "intermediate code", "three address code",
            },
            "Artificial Intelligence": {
                "artificial intelligence", "ai", "heuristic", "a star",
                "minimax", "alpha beta", "knowledge representation",
                "expert system", "fuzzy logic", "genetic algorithm",
                "constraint satisfaction", "bayesian network",
                "search algorithm", "informed search", "uninformed search",
            },
            "Digital Electronics": {
                "digital electronics", "logic gate", "flip flop",
                "combinational circuit", "sequential circuit", "multiplexer",
                "decoder", "encoder", "counter", "register",
                "boolean algebra", "karnaugh map", "k-map",
            },
            "Mathematics": {
                "matrix", "determinant", "eigenvalue", "differential equation",
                "integration", "differentiation", "laplace", "fourier",
                "probability", "statistics", "mean", "variance",
                "linear algebra", "calculus", "discrete mathematics",
                "graph theory", "combinatorics", "set theory",
            },
        }
        
        # Check if DB is empty
        current_index = metadata_store.get_keyword_index()
        if not current_index:
            log_info("Seeding subject index with legacy keyword map...")
            for subject, keywords in legacy_map.items():
                for kw in keywords:
                    # We use update_keyword_index to insert
                    if hasattr(metadata_store, 'update_keyword_index'):
                         metadata_store.update_keyword_index(kw, subject, count=5) # Boost initial seed
            log_info("Seeding complete.")
    except Exception as e:
        log_warning(f"Failed to seed legacy subject map: {e}")

def _load_index() -> Dict[str, Dict[str, int]]:
    """
    Load the keyword index from the database, using a cache.
    """
    global _INDEX_CACHE, _LAST_CACHE_UPDATE
    
    # Check cache
    if _INDEX_CACHE and (time.time() - _LAST_CACHE_UPDATE < _CACHE_TTL):
        return _INDEX_CACHE

    try:
        from app.storage import storage_manager
        
        # Access the underlying implementation if needed
        metadata_store = storage_manager.metadata
        if hasattr(metadata_store, 'impl'):
            metadata_store = metadata_store.impl
            
        # Seed if empty (one-time check essentially)
        if not _INDEX_CACHE:
             _seed_legacy_map(metadata_store)

        # Load fresh index
        if hasattr(metadata_store, 'get_keyword_index'):
            index = metadata_store.get_keyword_index()
            if index:
                _INDEX_CACHE = index
                _LAST_CACHE_UPDATE = time.time()
                log_info(f"Loaded subject index with {len(_INDEX_CACHE)} keywords.")
            return _INDEX_CACHE
            
    except Exception as e:
        log_warning(f"Failed to load subject index: {e}")
        # Fallback to current cache if DB fails
        return _INDEX_CACHE or {}
        
    return {}

def detect_subject(query: str) -> SubjectScope:
    """
    Detect the academic subject from a query string using the dynamic database index.

    Strategy:
      1. Tokenize query (unigrams).
      2. Sum scores from the inverted index: Score(Subject) += Count(Keyword, Subject).
      3. Normalize scores and detect ambiguity.
    """
    query_lower = query.lower().strip()
    if not query_lower:
        return SubjectScope()

    index = _load_index()
    if not index:
        return SubjectScope()

    # Tokenize (simple split by space, rely on index having normalized keys)
    # Improve this by also checking against known multi-word keys if performance allows,
    # but for now we stick to unigrams/bigrams if the extractor put them in.
    # A simple token match is O(N) where N is query length.
    
    tokens = [t for t in re.split(r'[^a-z0-9]', query_lower) if t]
    scores: Dict[str, float] = {}
    
    # Generate n-grams (1, 2, 3 words)
    ngrams_to_check = set()
    
    # Unigrams
    ngrams_to_check.update(tokens)
    
    # Bigrams
    if len(tokens) >= 2:
        ngrams_to_check.update(" ".join(tokens[i:i+2]) for i in range(len(tokens)-1))
        
    # Trigrams
    if len(tokens) >= 3:
        ngrams_to_check.update(" ".join(tokens[i:i+3]) for i in range(len(tokens)-2))

    # Check against index
    for ngram in ngrams_to_check:
        if ngram in index:
            subject_counts = index[ngram]
            # Boost multi-word matches slightly as they are more specific
            # length-based boost: len(ngram.split())
            boost = len(ngram.split())
            
            for subject, count in subject_counts.items():
                scores[subject] = scores.get(subject, 0.0) + (count * boost)

    if not scores:
        return SubjectScope()

    # Sort by score descending
    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    best_subject, best_score = ranked[0]
    matched_subjects = [s for s, _ in ranked if s]

    # Check for ambiguity (top two subjects within 10% score)
    is_ambiguous = False
    if len(ranked) >= 2:
        second_score = ranked[1][1]
        if second_score >= best_score * 0.9:
            is_ambiguous = True

    # Confidence calculation
    # Normalized against the sum of all scores? Or raw strength?
    # Let's use softmax-like ratio: score / sum(top 3 scores)
    top_3_sum = sum(s for _, s in ranked[:3])
    confidence = best_score / (top_3_sum if top_3_sum > 0 else 1)

    return SubjectScope(
        subject=best_subject,
        confidence=min(confidence, 1.0),
        is_ambiguous=is_ambiguous,
        matched_subjects=matched_subjects,
    )

def extend_keyword_map(subject: str, keywords: List[str]) -> None:
    """
    Legacy compatibility. Just updates the DB index.
    """
    try:
        from app.storage import storage_manager
        metadata_store = storage_manager.metadata.impl if hasattr(storage_manager.metadata, 'impl') else storage_manager.metadata
        
        for kw in keywords:
            if hasattr(metadata_store, 'update_keyword_index'):
                metadata_store.update_keyword_index(kw, subject)
                
        # Invalidate cache to force reload next time
        global _LAST_CACHE_UPDATE
        _LAST_CACHE_UPDATE = 0
    except Exception:
        pass
