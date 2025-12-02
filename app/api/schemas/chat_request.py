# app/api/schemas/chat_request.py
from pydantic import BaseModel
from typing import Dict, List, Optional, Any
class ChatRequest(BaseModel):
    query: str
    user_id: str
    session_id: str
    preferences: Optional[Dict[str, Any]] = {}
    conversation_history: Optional[List[str]] = []
    allow_agentic: bool = False
    model_name: Optional[str] = None
    max_output_tokens: Optional[int] = None
    