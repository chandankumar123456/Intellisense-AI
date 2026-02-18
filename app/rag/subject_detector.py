# app/rag/subject_detector.py
"""
Automatic Subject Identification for AI/AIML System.

Uses a hybrid approach:
1. Keyword Matching (Explicit terminology)
2. Semantic Similarity (Centroid-based embeddings)
3. Type Detection (Lab vs Theory)

No runtime LLM calls required.
"""

from pydantic import BaseModel
from typing import Optional, Dict, List, Set, Tuple
import re
import numpy as np
from app.core.logging import log_info, log_warning
from app.agents.retrieval_agent.utils import embed_text

# ── Academic Universe (AI/AIML) ──
# List from user requirements
AI_AIML_SUBJECTS = [
    "Mathematics–I",
    "Applied Physics",
    "Programming for Problem Solving–I",
    "Basic Electrical Engineering",
    "Applied Physics Lab",
    "Programming for Problem Solving–I Lab",
    "Basic Electrical Engineering Lab",
    "Engineering Workshop",
    "English Communication Skills Lab",
    "Mathematics–II",
    "English",
    "Engineering Chemistry",
    "Programming for Problem Solving–II",
    "Engineering Graphics Lab",
    "English Language Skills Lab",
    "Engineering Chemistry Lab",
    "Programming for Problem Solving–II Lab",
    "Computer Systems I",
    "Data Structures",
    "Python Programming",
    "Fundamentals of Software Engineering",
    "Probability and Statistics",
    "Java Programming",
    "Python Programming Lab",
    "Data Structures & Java Lab",
    "Environmental Studies",
    "Data Wrangling and Visualization",
    "Design and Analysis of Algorithms",
    "Fundamentals of Artificial Intelligence",
    "Discrete Mathematics",
    "Database Management Systems",
    "Soft Skills for Success Lab",
    "Data Wrangling and Visualization Lab",
    "Database Management Systems Lab",
    "Gender Sensitization",
    "Essentials of Machine Learning",
    "Computer Systems II",
    "Web Programming with MEAN",
    "Entrepreneurship Development",
    "Computer Systems Lab",
    "Web Programming with MEAN Lab",
    "Essentials of Machine Learning Lab",
    "Quantitative Aptitude and Reasoning",
    "Automata Theory and Applications",
    "Information Retrieval Systems",
    "Computer Vision and Image Processing",
    "Internet of Things",
    "Cryptography",
    "Technical and Business Communication Skills",
    "Computer Vision and Information Retrieval Systems Lab",
    "Internet of Things Lab",
    "Verbal Ability and Critical Reasoning",
    "Natural Language Processing",
    "Deep Learning",
    "Big Data",
    "Cloud Computing",
    "Cyber Security",
    "Natural Language Processing Lab",
    "Deep Learning Lab",
    "Industry Oriented Mini Project",
    "Negotiation Skills"
]

# Additional manually curated keywords to boost centroids
# This helps distinguish overlapping subjects (e.g. DL vs ML vs NLP)
SUBJECT_KEYWORDS_BOOST = {
    "Mathematics–I": ["calculus", "matrix", "algebra", "differential", "integral", "derivative"],
    "Mathematics–II": ["vector calculus", "laplace transform", "fourier series", "partial differential"],
    "Applied Physics": ["quantum", "optics", "semiconductor", "laser", "fiber optics", "electromagnetism"],
    "Data Structures": ["array", "linked list", "stack", "queue", "tree", "graph", "hashing", "sorting"],
    "Design and Analysis of Algorithms": ["time complexity", "dynamic programming", "greedy", "backtracking", "np-hard", "divide and conquer"],
    "Database Management Systems": ["sql", "normalization", "transaction", "acid", "relational", "er diagram", "schema"],
    "Operating Systems": ["process", "thread", "scheduling", "deadlock", "memory management", "virtual memory", "file system"], # Mapped to Computer Systems I/II if needed, or kept generic
    "Computer Systems I": ["digital logic", "boolean algebra", "gates", "flip flop", "architecture", "organization"],
    "Computer Systems II": ["operating system", "process", "scheduling", "memory", "deadlock"],
    "Fundamentals of Artificial Intelligence": ["search", "agent", "heuristic", "logic", "knowledge representation", "minimax"],
    "Essentials of Machine Learning": ["regression", "classification", "clustering", "supervised", "unsupervised", "model", "training"],
    "Deep Learning": ["neural network", "backpropagation", "cnn", "rnn", "activation function", "gradient descent", "layer"],
    "Natural Language Processing": ["tokenization", "stemming", "lemmatization", "parsing", "sentiment", "nlp", "text"],
    "Internet of Things": ["sensor", "actuator", "iot", "arduino", "raspberry pi", "embedded", "mqtt"],
    "Cloud Computing": ["aws", "azure", "virtualization", "iaas", "paas", "saas", "cloud"],
    "Cyber Security": ["encryption", "decryption", "firewall", "attack", "malware", "security", "cryptography"],
    "Big Data": ["hadoop", "spark", "mapreduce", "nosql", "volume", "velocity", "variety"],
    "Python Programming": ["python", "list", "dictionary", "tuple", "pandas", "numpy", "def"],
    "Java Programming": ["java", "class", "object", "inheritance", "polymorphism", "interface", "exception"],
    "Soft Skills for Success Lab": ["communication", "resume", "interview", "presentation", "group discussion"],
    "Economics and Financial Analysis": ["demand", "supply", "market", "cost", "accounting", "ratio"], # If added later
}

class SubjectScope(BaseModel):
    subject: str = ""
    secondary_subject: str = ""
    confidence: float = 0.0
    content_type: str = "theory"  # "theory", "lab", "tutorial", "other"
    is_ambiguous: bool = False
    matched_methods: List[str] = [] # "keyword", "semantic"
    matched_subjects: List[str] = [] # For logging ambiguity

class SubjectDetector:
    _instance = None
    _centroids: Dict[str, np.ndarray] = {}
    _initialized: bool = False
    _cache: Dict[str, SubjectScope] = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SubjectDetector, cls).__new__(cls)
        return cls._instance

    def _initialize(self):
        """Pre-compute centroids for all subjects."""
        # Check if already initialized to prevent re-computation
        if self._initialized and self._centroids:
            return

        log_info("Initializing SubjectDetector: Computing centroids...")
        
        # Determine strict list of subjects to embed
        texts_to_embed = []
        keys = []
        
        for subject in AI_AIML_SUBJECTS:
            # Construct a rich descriptive string for the subject
            # Subject Name + Extra Keywords
            desc = subject
            if subject in SUBJECT_KEYWORDS_BOOST:
                desc += " " + " ".join(SUBJECT_KEYWORDS_BOOST[subject])
            
            # Clean "Lab" from description for semantic matching to keep it close to theory
            # (We handle Lab detection separately via patterns)
            clean_desc = desc.replace(" Lab", "").replace(" Laboratory", "")
            
            texts_to_embed.append(clean_desc)
            keys.append(subject)
        
        try:
            embeddings = embed_text(texts_to_embed)
            for i, key in enumerate(keys):
                self._centroids[key] = np.array(embeddings[i])
            self._initialized = True
            log_info(f"SubjectDetector initialized with {len(keys)} centroids.")
        except Exception as e:
            log_warning(f"Failed to initialize SubjectDetector centroids: {e}")

    def detect(self, text: str, existing_embeddings: Optional[List[float]] = None) -> SubjectScope:
        """
        Detect subject from text. 
        If existing_embeddings (of the chunk/doc) is provided, it saves re-computation.
        This embedding should represent the document (e.g., average of first few chunks).
        """
        # Ensure initialized (lazy load if needed, but preferably called at startup)
        if not self._initialized:
             self._initialize()

        if not text:
            return SubjectScope()

        # Cache check (simple text hash or similar)
        # For long text, we use a prefix hash
        text_hash = str(hash(text[:500] + str(len(text))))
        if text_hash in self._cache:
             return self._cache[text_hash]

        # 1. Type Detection (Lab vs Theory)
        content_type = self._detect_type(text)

        # 2. Candidate Generation via Keyword Matching (Fast Filter)
        # Check standard keywords + subject names themselves
        keyword_scores = self._score_keywords(text)
        
        # 3. Semantic Similarity (Centroid Logic)
        semantic_scores = {}
        target_embedding = None
        
        if existing_embeddings:
            target_embedding = np.array(existing_embeddings)
        elif len(text) > 20: # Only embed if enough text
            try:
                # Embed just a prefix to save time/tokens if text is huge, 
                # or rely on the fact that 'text' passed here might be a summary or first chunk
                target_embedding = np.array(embed_text([text[:1000]])[0]) 
            except Exception:
                pass

        if target_embedding is not None and self._centroids:
            for subject, centroid in self._centroids.items():
                # Cosine similarity
                sim = np.dot(target_embedding, centroid) / (np.linalg.norm(target_embedding) * np.linalg.norm(centroid) + 1e-9)
                semantic_scores[subject] = float(sim)

        # 4. Fusion & Decision
        # Normalize scores
        final_scores = {}
        all_subjects = set(keyword_scores.keys()) | set(semantic_scores.keys())
        
        for subj in all_subjects:
            k_score = keyword_scores.get(subj, 0.0)
            s_score = semantic_scores.get(subj, 0.0)
            
            # Heuristic fusion:
            # Semantic gives good general direction (0.0-1.0 range usually ~0.3-0.8)
            # Keywords give precise hits (integers, normalized to 0-1 range roughly)
            
            # Normalize keyword score (cap at 5 hits = 1.0)
            k_norm = min(k_score / 5.0, 1.0)
            
            # Boost matches that align with the detected content type
            # e.g., if type is 'lab' and subject is 'Applied Physics Lab', boost it
            # vs 'Applied Physics' (theory)
            type_boost = 0.0
            if "Lab" in subj and content_type == "lab":
                type_boost = 0.2
            elif "Lab" not in subj and content_type != "lab":
                 type_boost = 0.1
            
            # Weighted sum
            # If we have keywords, we trust them a bit more for specificity
            score = (0.4 * k_norm) + (0.6 * s_score) + type_boost
            
            final_scores[subj] = score

        if not final_scores:
             return SubjectScope(content_type=content_type)

        # Sort
        ranked = sorted(final_scores.items(), key=lambda x: x[1], reverse=True)
        best_subj, best_score = ranked[0]
        
        # Secondary
        second_subj = ""
        is_ambiguous = False
        matched_subjects = [best_subj]

        if len(ranked) > 1:
            second_subj = ranked[1][0]
            if ranked[1][1] >= best_score * 0.85: # 15% margin
                is_ambiguous = True
                matched_subjects.append(second_subj)

        return SubjectScope(
            subject=best_subj,
            secondary_subject=second_subj,
            confidence=min(best_score, 1.0), # Cap at 1.0
            content_type=content_type,
            is_ambiguous=is_ambiguous,
            matched_methods=["keyword" if keyword_scores else "", "semantic" if semantic_scores else ""],
            matched_subjects=matched_subjects
        )

    def _detect_type(self, text: str) -> str:
        text_lower = text.lower()[:2000] # Check start of doc
        if "lab manual" in text_lower or "experiment no" in text_lower or \
           "list of experiments" in text_lower or "program no" in text_lower or \
            "practical" in text_lower:
            return "lab"
        return "theory"

    def _score_keywords(self, text: str) -> Dict[str, float]:
        scores = {}
        text_lower = text.lower()
        
        # 1. Direct Subject Name Match
        for subj in AI_AIML_SUBJECTS:
            # Clean name for matching (escape regex)
            # Matches exact subject name in text? Highly likely.
            pattern = re.escape(subj.lower())
            if re.search(r'\b' + pattern + r'\b', text_lower):
                scores[subj] = scores.get(subj, 0) + 3.0 # Strong signal

        # 2. Keyword Boost
        for subj, keywords in SUBJECT_KEYWORDS_BOOST.items():
            for kw in keywords:
                if kw in text_lower: # Simple substring check for speed
                    scores[subj] = scores.get(subj, 0) + 1.0
                    
        return scores

# Helper function to expose singleton easily
def detect_subject(text: str, embeddings: Optional[List[float]] = None) -> SubjectScope:
    detector = SubjectDetector()
    return detector.detect(text, embeddings)
# Alias for backward compatibility if needed, though detect_subject is the primary one now
detect_subject_v2 = detect_subject
