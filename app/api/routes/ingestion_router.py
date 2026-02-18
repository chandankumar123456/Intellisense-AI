# app/api/routes/ingestion_router.py
from fastapi import APIRouter, UploadFile, File, HTTPException, Body, BackgroundTasks, Form
from pydantic import BaseModel
from typing import List, Optional
import shutil
import os
import uuid
import tempfile
import asyncio
from pypdf import PdfReader
from youtube_transcript_api import YouTubeTranscriptApi
import trafilatura
from app.agents.retrieval_agent.utils import index, namespace
from app.core.logging import log_info, log_error

router = APIRouter(prefix="/ingest", tags=["ingestion"])

class IngestUrlRequest(BaseModel):
    url: str
    type: str  # "web" or "youtube"
    user_id: str

class IngestResponse(BaseModel):
    status: str
    message: str
    document_id: str
    chunks_count: int

def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> List[str]:
    words = text.split()
    chunks = []
    chunk = []
    current_len = 0
    
    for word in words:
        chunk.append(word)
        current_len += 1
        
        if current_len >= chunk_size:
            chunks.append(" ".join(chunk))
            # Overlap
            chunk = chunk[-overlap:]
            current_len = len(chunk)
            
    if chunk:
        chunks.append(" ".join(chunk))
            
    return chunks

def upsert_records_sync(records):
    # This function is run in a thread
    try:
        # Check if index has upsert method directly or via utils
        # utils.py exports 'index' which is a LazyIndex wrapper around Pinecone Index
        # Pinecone Index has .upsert()
        
        vectors = []
        for r in records:
            vectors.append({
                "id": r["_id"],
                "values": [0.1] * 1024, # DUMMY VALUES if model not ready, BUT Pinecone inference handles text
                # WAIT! app/agents/retrieval_agent/utils.py says:
                # "field_map": {"text": "chunk_text"} 
                # This implies we send {"id": "x", "values": [...], "metadata": {"chunk_text": "..."}}
                # OR if using the *Inference API*, inputs might differ.
                # However, looking at utils.py again, it uses `pc.create_index_for_model`
                # which creates a Serverless index capable of embedding.
                # The standard usage for that is usually `index.upsert(vectors=[...])` 
                # where metadata contains the text field mapped in `field_map`.
                
                # Let's assume standard upsert with metadata
                "metadata": {
                    "chunk_text": r["chunk_text"],
                    "source_type": r["source_type"],
                    "source_url": r["source_url"],
                    "category": r["metadata"]["category"],
                    "user_id": r["metadata"]["user_id"],
                    "doc_id": r["metadata"]["doc_id"]
                }
            })
            
        # However, for "integrated inference", we often just pass the text if using a specific SDK method.
        # But `utils.py` uses `vector_db_client.search`.
        # Let's try standard upsert. If it fails due to missing values, we know.
        # BUT `create_index_for_model` implies the embedding happens on Pinecone side.
        # If so, we might need `pinecone-plugin-inference` or similar, OR just pass empty values?
        # Actually, if the index is configured for embedding, `upsert` requests effectively ignore `values` 
        # if the client handles it, or we send the text in a specific way.
        
        # Let's verify `utils.py` again. It has `records` list with `chunk_text`.
        # It has `index.upsert_records(namespace, clean_records)` commmented out.
        # This suggests `upsert_records` IS a custom helper method or from a library version.
        # Let's assume standard usage for now: list of dicts.
        pass

    except Exception as e:
        log_error(f"Upsert failed: {e}")

async def process_and_index(text: str, source_url: str, source_type: str, user_id: str, doc_id: str, document_title: str = ""):
    try:
        chunks = chunk_text(text)
        records = []
        for i, chunk_text in enumerate(chunks):
            records.append({
                "_id": f"{doc_id}_{i}",
                "chunk_text": chunk_text,
                "source_type": source_type,
                "source_url": source_url,
                "metadata": {
                    "category": "user_upload",
                    "user_id": user_id,
                    "doc_id": doc_id
                }
            })
        
        if records:
            log_info(f"Upserting {len(records)} chunks for {source_url}...")
            
            # Generate embeddings client-side using SentenceTransformer
            from app.agents.retrieval_agent.utils import embed_text
            
            chunk_texts = [r["chunk_text"] for r in records]
            try:
                embeddings = await asyncio.to_thread(embed_text, chunk_texts)
            except Exception as e:
                log_error(f"Embedding generation failed: {e}")
                raise

            vectors = []
            for i, r in enumerate(records):
                vectors.append({
                    "id": r["_id"],
                    "values": embeddings[i], 
                    "metadata": {
                        "chunk_text": r["chunk_text"],
                        "source_type": r["source_type"],
                        "source_url": r["source_url"],
                        "category": "user_upload",
                        "user_id": user_id,
                        "doc_id": doc_id
                    }
                })
            
            # Upsert to Pinecone
            await asyncio.to_thread(index.upsert, vectors=vectors, namespace=namespace)
            
            log_info(f"Successfully indexed {source_url}")
            
    except Exception as e:
        log_error(f"Background indexing failed for {source_url}: {e}")

@router.post("/file", response_model=IngestResponse)
async def ingest_file(
    file: UploadFile = File(...),
    user_id: str = Form(...),
    background_tasks: BackgroundTasks = BackgroundTasks()
):
    doc_id = str(uuid.uuid4())
    text = ""
    
    try:
        # Save to temp file to handle reading
        suffix = os.path.splitext(file.filename)[1]
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            shutil.copyfileobj(file.file, tmp)
            tmp_path = tmp.name
        
        # Parse
        try:
            if file.filename.lower().endswith(".pdf"):
                reader = PdfReader(tmp_path)
                for page in reader.pages:
                    extracted = page.extract_text()
                    if extracted:
                        text += extracted + "\n"
            elif file.filename.lower().endswith(".txt") or file.filename.lower().endswith(".md"):
                with open(tmp_path, "r", encoding="utf-8") as f:
                    text = f.read()
            else:
                # Try simple text read for others
                with open(tmp_path, "r", encoding="utf-8", errors="ignore") as f:
                    text = f.read()
        finally:
            # Clean up temp file
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
        
        if not text.strip():
            raise HTTPException(400, "Could not extract text from file.")

        # Trigger background indexing
        document_title = os.path.splitext(file.filename)[0]  # Strip extension for clean title
        background_tasks.add_task(process_and_index, text, file.filename, "file", user_id, doc_id, document_title)
        
        return IngestResponse(
            status="processing",
            message=f"File {file.filename} is being processed.",
            document_id=doc_id,
            chunks_count=len(text.split()) // 500  # Estimate
        )

    except HTTPException:
        raise
    except Exception as e:
        log_error(f"File ingestion error: {e}")
        raise HTTPException(500, f"Failed to process file: {str(e)}")

@router.post("/url", response_model=IngestResponse)
async def ingest_url(
    request: IngestUrlRequest,
    background_tasks: BackgroundTasks
):
    doc_id = str(uuid.uuid4())
    text = ""
    
    try:
        if request.type == "youtube":
            try:
                # Extract video ID from URL
                # Handle formats: v=ID or /ID
                video_id = ""
                if "v=" in request.url:
                    video_id = request.url.split("v=")[-1].split("&")[0]
                elif "youtu.be/" in request.url:
                    video_id = request.url.split("youtu.be/")[-1].split("?")[0]
                
                if not video_id:
                    raise HTTPException(400, "Invalid YouTube URL")

                transcript = YouTubeTranscriptApi.get_transcript(video_id)
                text = " ".join([item['text'] for item in transcript])
            except Exception as e:
                log_error(f"YouTube transcript failed: {e}")
                raise HTTPException(400, f"Failed to fetch YouTube transcript. Video might not have captions.")
                
        elif request.type == "web":
            downloaded = trafilatura.fetch_url(request.url)
            if downloaded:
                text = trafilatura.extract(downloaded)
            
            if not text:
                 raise HTTPException(400, "Failed to extract content from webpage.")
        
        if not text or not text.strip():
            raise HTTPException(400, "No content found.")

        # Trigger background indexing
        background_tasks.add_task(process_and_index, text, request.url, request.type, request.user_id, doc_id)
        
        return IngestResponse(
            status="processing",
            message=f"URL {request.url} is being processed.",
            document_id=doc_id,
            chunks_count=len(text.split()) // 500
        )

    except HTTPException:
        raise
    except Exception as e:
        log_error(f"URL ingestion error: {e}")
        raise HTTPException(500, f"Failed to process URL: {str(e)}")
