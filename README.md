# 🧠 IntelliSense AI – Autonomous Agentic RAG

**IntelliSense AI** is a next-generation **Autonomous Agentic RAG** platform designed to provide self-optimizing, context-aware intelligence from your documents. Unlike simple RAG systems, IntelliSense AI uses a sophisticated multi-agent architecture (Controller, Orchestrator, Synthesizer) to understand user intent, self-correct retrieval failures, and deliver precise, high-confidence answers.

The system features an advanced **Retrieval Intelligence Engine** that learns from past interactions, adapts to query complexity, and aggressively filters noise to prevent hallucinations.

---

## 🏗️ System Architecture

The system operates as a collaborative multi-agent pipeline:

```mermaid
flowchart TD
    User[User Query] --> Controller[Pipeline Controller]
    
    subgraph "Phase 1: Understanding"
        Controller --> Understand[Query Understanding Agent]
        Understand --> Intent[Intent & Scope Detection]
        Intent --> Rewrite[Structural Query Rewriting]
    end

    subgraph "Phase 2: Retrieval Intelligence"
        Rewrite --> Orchestrator[Retrieval Orchestrator]
        Orchestrator --> Search[Vector + Keyword + Section Search]
        Search --> Hierarchy[Hierarchical Rerank\n(Doc → Section → Chunk)]
        Hierarchy --> Clustering[Chunk Clustering & Dedup]
        Clustering --> Coverage{Coverage Check}
        Coverage -->|Gap Found| GapFill[Semantic Gap-Fill]
        Coverage -->|Sufficient| Confidence[Adaptive Confidence]
        GapFill --> Confidence
        Confidence --> Memory[Retrieval Memory\n(Learning Layer)]
    end

    subgraph "Phase 3: Synthesis & Verification"
        Memory --> Validation{Failure Prediction}
        Validation -->|High Risk| Grounded[Grounded Mode]
        Validation -->|Low Risk| Synth[Response Synthesizer]
        Grounded --> Synth
        Synth --> Verify[Context Verification]
    end

    Verify --> Final[Final Response]
```

---

## ✨ Retrieval Intelligence Engine

The core differentiator of IntelliSense AI is its **self-optimizing retrieval capabilities**:

### 1. 📂 Hierarchical Retrieval (Structure-Aware)
Instead of flattening documents into isolated chunks, the system understands document structure. It prioritizes the best **Documents** first, then the most relevant **Sections** (e.g., "Methodology", "Conclusion"), and finally the specific **Chunks**. This ensures context is drawn from authoritative sections rather than random mentions.

### 2. 🧠 Long-Term Retrieval Memory
The system **learns** from every interaction. It tracks which retrieval patterns (e.g., "Definitions work best for conceptual queries") lead to successful answers. Over time, it builds a database of successful strategies and uses them to boost future retrieval performance.

### 3. 🎯 Semantic Coverage Optimizer
The system explicitly extracts **key concepts** from your query and measures if the retrieved context covers them. If concepts are missing, it triggers targeted **Needle-in-a-Haystack** gap-fill queries to complete the picture before attempting to answer.

### 4. ⚖️ Adaptive Confidence Thresholds
Static thresholds fail because queries vary in difficulty. IntelliSense AI dynamically calculates confidence thresholds based on **Query Complexity** (simple vs. complex) and **Query Type** (Factual, Conceptual, Comparative). It demands stronger evidence for rigorous questions.

### 5. 🔮 Pre-Synthesis Failure Prediction
Before sending data to the LLM, a **Failure Predictor** analyzes the retrieved context. If it detects low coverage, fragmentation, or weak signals, it preemptively activates **Grounded Mode** or triggers a retry, preventing hallucinations before they happen.

### 6. 🧩 Semantic Chunk Clustering
To reduce noise, the system clusters semantically similar chunks and keeps only the highest-density representative. This removes redundancy and ensures the context window is filled with diverse, high-value information.

### 7. 🔍 Structured Trace Logging
Every decision—from query expansion to failure prediction—is logged in a structured trace. This provides complete observability into *why* the system retrieved specific content and how it made confidence decisions.

---

## 📂 Project Structure

```text
IntelliSense-AI/
├── app/
│   ├── agents/
│   │   ├── pipeline_controller_agent/ # 🧠 The Brain (Flow Control)
│   │   ├── retrieval_agent/           # 🔍 Orchestrator (Search & Optimization)
│   │   ├── query_understanding_agent/ # 🗣️ Intent & Scope Analysis
│   │   ├── response_synthesizer_agent/# ✍️ Answer Generation
│   │   ├── claim_extraction_agent/    # 🧪 EviLearn Fact Extraction
│   │   └── verification_agent/        # ✅ EviLearn Fact Checking
│   ├── rag/                           # ⚙️ Core Intelligence Modules
│   │   ├── hierarchical_retriever.py  # Structure-Aware Search
│   │   ├── retrieval_memory.py        # Learning Layer (SQLite)
│   │   ├── adaptive_confidence.py     # Dynamic Thresholds
│   │   ├── semantic_coverage.py       # Concept Gap-Filling
│   │   ├── failure_predictor.py       # Pre-Synthesis Guard
│   │   ├── chunk_clusterer.py         # Dedup & Clustering
│   │   ├── retrieval_trace.py         # Structured Logging
│   │   └── retrieval_confidence.py    # Scoring Logic
│   ├── api/                           # FastAPI Routes
│   ├── core/                          # Config & Logging
│   └── storage/                       # Adapters (Local/S3/Pinecone)
├── data/                              # Local Data Storage
├── notebook-lm-frontend/              # ⚛️ React Frontend
└── tests/                             # Unit & Smoke Tests
```

---

## 🚀 Quick Start (Local Mode)

All you need is Python, Node.js, and Docker.

### 1. Prerequisites
*   [**Python 3.10+**](https://www.python.org/)
*   [**Node.js (v18+)**](https://nodejs.org/)
*   [**Docker**](https://www.docker.com/) (for Redis)
*   **[uv](https://github.com/astral-sh/uv)** (Recommended package manager)

### 2. Start Infrastructure
Start Redis for session caching:
```bash
docker run -d --name redis-server -p 6379:6379 redis
```

### 3. Backend Setup
```bash
# Clone and enter repo
git clone https://github.com/chandankumar123456/intellisense-ai.git
cd intellisense-ai

# Install dependencies
uv sync

# Configure .env
cp .env.example .env
# Edit .env with your GROQ_API_KEY or OPENAI_API_KEY

# Run Server
uv run uvicorn app.main:app --reload
```
API Docs will be at: `http://localhost:8000/docs`

### 4. Frontend Setup
```bash
cd notebook-lm-frontend
npm install
npm start
```
Frontend will be at: `http://localhost:3000`

---

## ⚙️ Configuration

Key configuration flags in `app/core/config.py` allow you to toggle intelligence features:

```python
HIERARCHICAL_RETRIEVAL_ENABLED = True  # Enable/Disable structure awareness
RETRIEVAL_MEMORY_ENABLED = True        # Enable/Disable learning
ADAPTIVE_CONFIDENCE_ENABLED = True     # Enable/Disable dynamic thresholds
FAILURE_PREDICTION_ENABLED = True      # Enable/Disable pre-synthesis guards
CHUNK_CLUSTERING_ENABLED = True        # Enable/Disable redundancy removal
```

## 🛠️ Troubleshooting

| Issue | Solution |
| :--- | :--- |
| **Redis Connection Error** | Check if Docker container `redis-server` is running. |
| **No Retrieval Results** | Ensure you have uploaded documents in the "Data" tab. Check `subject_filter` logs. |
| **Frontend Connection Refused** | Ensure backend is running on port 8000. |
| **Ingestion Errors** | Check `data/` directory permissions (Local Mode) or S3 credentials (AWS Mode). |

---

## 📜 License
MIT License
