# 🧠 IntelliSense AI – Agentic RAG Platform

**IntelliSense AI** is a next-generation **Agentic RAG (Retrieval-Augmented Generation)** platform designed to provide deep, context-aware intelligence from your documents. Unlike simple RAG systems, IntelliSense AI uses a sophisticated multi-agent architecture (Orchestrator, Writer, Reviewer) to understand user intent, manage sessions, and deliver precise, high-quality answers.

---

## 🏗️ Architecture Overview

-   **Backend:** FastAPI (Python) with `Agno` (Agentic Framework) & to `uv` (Dependency Management).
-   **Frontend:** React (TypeScript) with Tailwind CSS & Lucide Icons.
-   **Vector Logic:** Hybrid Search (Semantic + Keyword) with dynamic reranking.
-   **Storage Modes:**
    -   **Local Mode (Default):** Uses local filesystem & ChromaDB (No Cloud needed!).
    -   **AWS Mode:** Uses S3 for documents & Pinecone for vectors (Production scale).
-   **Database:** Redis (for high-speed session caching & chat history).

---

## 🚀 Quick Start (Local Mode)

This is the easiest way to run IntelliSense AI on your local machine without needing AWS keys or Pinecone.

### 1. Prerequisites

Ensure you have the following installed:

*   [**Python 3.10+**](https://www.python.org/)
*   [**Node.js (v18+) & npm**](https://nodejs.org/)
*   [**Docker Desktop**](https://www.docker.com/products/docker-desktop/) (Required for Redis)
*   **[uv](https://github.com/astral-sh/uv)** (Highly recommended for Python speed):
    ```bash
    # On Windows (PowerShell)
    powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
    # On macOS/Linux
    curl -LsSf https://astral.sh/uv/install.sh | sh
    ```

### 2. Clone the Repository

```bash
git clone https://github.com/chandankumar123456/intellisense-ai.git
cd intellisense-ai
```

### 3. Start Infrastructure (Redis)

Start a Redis container for session management:

```bash
docker run -d --name redis-server -p 6379:6379 redis
```

---

### 4. Backend Setup (FastAPI)

1.  **Install Python Dependencies:**
    ```bash
    uv sync
    ```

2.  **Configure Environment Variables:**
    Create a `.env` file in the root directory:
    ```env
    # --- LLM API Keys (Required) ---
    GROQ_API_KEY="your_groq_api_key"
    GOOGLE_API_KEY="your_google_api_key"
    # OPENAI_API_KEY="your_openai_key" # Optional, if using OpenAI models
    
    # --- Storage Configuration (Local Mode) ---
    STORAGE_MODE="local"
    
    # --- Redis Configuration ---
    REDIS_HOST="localhost"
    REDIS_PORT=6379
    
    # --- Optional Tracing ---
    # LANGSMITH_TRACING="true"
    # LANGSMITH_API_KEY="your_key"
    ```

3.  **Run the Backend Server:**
    ```bash
    uv run uvicorn app.main:app --reload
    ```
    ✅ **Backend is running at:** `http://localhost:8000`  
    📄 **API Docs:** `http://localhost:8000/docs`

---

### 5. Frontend Setup (React)

Open a **new terminal** window:

1.  **Navigate to Frontend:**
    ```bash
    cd notebook-lm-frontend
    ```

2.  **Install Node Modules:**
    ```bash
    npm install
    ```
    *(Note: If you see legacy peer dependency errors, run `npm install --legacy-peer-deps`)*

3.  **Start the React App:**
    ```bash
    npm start
    ```
    ✅ **Frontend is running at:** `http://localhost:3000`

---

## ☁️ Production Setup (AWS + Pinecone)

To run in production mode with cloud storage and scalable vector search:

1.  **Update `.env`:**
    ```env
    STORAGE_MODE="aws"
    
    # AWS Credentials
    AWS_ACCESS_KEY_ID="your_aws_key"
    AWS_SECRET_ACCESS_KEY="your_aws_secret"
    AWS_REGION="us-east-1"
    S3_BUCKET_NAME="your-s3-bucket-name"
    
    # Pinecone Credentials
    PINECONE_API_KEY="your_pinecone_key"
    PINECONE_INDEX_NAME="intellisense-ai-dense-index-v2"
    ```

2.  **Restart Backend:**
    The application will automatically switch from local filesystem/ChromaDB to S3/Pinecone.

---

## 📂 Project Structure

```text
IntelliSense-AI/
├── app/                        # 🧠 Backend Logic
│   ├── agents/                 # Agent definitions (Orchestrator, Writer, etc.)
│   ├── api/                    # FastAPI Routes (Chat, Auth, Ingestion)
│   ├── core/                   # Config, logging, and exceptions
│   ├── storage/                # Storage adapters (Local/S3, Chroma/Pinecone)
│   └── main.py                 # Application Entry Point
├── data/                       # 💽 Local Data Storage (Created on runtime)
│   ├── documents/              # Uploaded files (in Local Mode)
│   ├── metadata_index.db       # SQLite metadata store
│   └── chroma_db/              # ChromaDB vector store
├── notebook-lm-frontend/       # ⚛️ React Frontend
│   ├── src/
│   │   ├── components/         # Reusable UI components
│   │   ├── pages/              # Application pages (Chat, Admin)
│   │   └── services/           # API client services
├── scripts/                    # 🛠️ Utility / Migration Scripts
├── requirements.txt            # Python Dependencies
└── README.md                   # Project Documentation
```

---

## 🛠️ Troubleshooting

| Issue | Solution |
| :--- | :--- |
| **Redis Connection Error** | Ensure Docker is running and the container is active: `docker ps`. If stopped, run `docker start redis-server`. |
| **`ModuleNotFoundError`** | Run `uv sync` to install missing Python packages. |
| **Frontend Connection Refused** | Ensure the backend is running on port `8000`. Check browser console (`F12`) for CORS errors (though CORS is enabled by default). |
| **Ingestion Fails** | In Local Mode, ensure the `data/` directory is writable. In AWS Mode, check your S3 bucket permissions. |

---

## 📜 License

This project is licensed under the MIT License.
