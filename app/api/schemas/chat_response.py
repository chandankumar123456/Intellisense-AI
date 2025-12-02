# app/api/schemas/chat_response.py
from pydantic import BaseModel
from typing import List, Optional

class ChatResponse(BaseModel):
    answer: str
    confidence: float
    warnings: List[str]
    citations: List[str]
    used_chunk_ids: List[str]
    retrieval_trace: dict
    query_understanding: dict
    trace_id: str
    latency_ms: int
    raw_model_output: Optional[str] = None
    metrics: dict

