# app/agents/response_synthesizer_agent/schema.py

from typing import List, Optional, Dict, Any
from pydantic import BaseModel

class Chunk(BaseModel):
    chunk_id: str
    text: str
    source_url: Optional[str] = None
    source_type: Optional[str] = None
    score: float
    metadata: Dict[str, Any] = {}


class SynthesisInput(BaseModel):
    trace_id: str
    user_id: Optional[str] = None
    session_id: Optional[str] = None

    query: str
    conversation_history: List[str] = []

    preferences: Dict[str, Any] = {}
    retrieved_chunks: List[Chunk]

    max_output_tokens: Optional[int] = None
    model_name: Optional[str] = None
    allow_agentic: bool = False


class SynthesisOutput(BaseModel):
    answer: str
    used_chunk_ids: List[str]
    trace_id: str
    confidence: float

    warnings: List[str] = []
    raw_model_output: Optional[str] = None
    reasoning: Optional[str] = None
    metrics: Optional[Dict[str, Any]] = None
