
# 🧠 IntelliSense AI – Full Stack Setup Guide

IntelliSense AI is an agentic RAG-powered intelligence system that enables advanced document understanding, session management, and real-time chat interactions.

---

## 🏗️ Project Architecture

- **Backend:** FastAPI (Python) powered by `uv` & `Agno`
- **Frontend:** React (TypeScript) with Tailwind CSS
- **Database/Cache:** Redis
- **Vector DB:** Pinecone
- **LLM/Embeddings:** Groq, Google Generative AI (Gemini), OpenAI

---

## 🚀 Quick Start

### 1. **Prerequisites**
Ensure you have the following installed:
- [Python 3.10+](https://www.python.org/)
- [Node.js & npm](https://nodejs.org/)
- [Docker](https://www.docker.com/)
- [uv](https://github.com/astral-sh/uv) (Highly recommended for Python dependency management)

### 2. **Clone the Repository**
```bash
git clone https://github.com/chandankumar123456/intellisense-ai.git
cd intellisense-ai
```

---

## 🛠️ Infrastructure Setup

### **Redis (Docker)**
The project requires a Redis instance for session management and caching. Run the following command to start a Redis container:

```bash
docker run -d --name redis-client -p 6379:6379 redis
```

---

## 🐍 Backend Configuration

### **1. Install Dependencies**
We use `uv` for lightning-fast dependency management.
```bash
uv sync
```

### **2. Environment Variables**
Create a `.env` file in the root directory and add the following:
```env
# API Keys
GROQ_API_KEY="your_groq_api_key"
GOOGLE_API_KEY="your_google_api_key"
PINECONE_API_KEY="your_pinecone_api_key"

# Redis Configuration
REDIS_HOST="localhost"
REDIS_PORT=6379

# LangSmith (Optional but recommended)
LANGSMITH_TRACING="true"
LANGSMITH_API_KEY="your_langsmith_api_key"
```

### **3. Run the Backend Server**
```bash
uv run uvicorn app.main:app --reload
```
The backend will be available at: `http://localhost:8000`

---

## ⚛️ Frontend Configuration

### **1. Install Dependencies**
Navigate to the frontend directory:
```bash
cd notebook-lm-frontend
npm install
```

### **2. Run the Development Server**
```bash
npm start
```
The frontend will be available at: `http://localhost:3000`

---

## 📂 Project Structure

```text
IntelliSense-AI/
├── app/                    # Backend Source Code
│   ├── api/                # API Routes (Chat, Auth, Ingestion)
│   ├── core/               # Shared logic (Redis Client, Logging)
│   └── main.py             # FastAPI Entry Point
├── notebook-lm-frontend/   # Frontend Source Code
│   ├── src/                # React Components & Logic
│   └── package.json        # Frontend Dependencies
├── requirements.txt        # Python Dependencies
├── uv.lock                 # UV Lockfile
└── README.md               # You are here!
```

---

## 👥 Contributing

1. **Check Dependencies:** Always use `uv sync` after pulling changes.
2. **Coding Standards:** Follow PEP8 for Python and Prettier for JS/TS.
3. **Environment:** Keep your `.env` file updated but never commit it to Git.

---

## ❓ Troubleshooting

- **Redis Connection Error:** Ensure the Docker container is running (`docker ps`).
- **ModuleNotFoundError:** Run `uv sync` again to ensure the virtual environment is up to date.
- **CORS Issues:** The backend is configured to allow all origins by default in development.

---
