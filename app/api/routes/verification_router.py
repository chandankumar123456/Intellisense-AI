# app/api/routes/verification_router.py
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from app.api.dependencies import get_controller
from app.agents.pipeline_controller_agent.controller import PipelineControllerAgent
from app.agents.query_understanding_agent.schema import Preferences

router = APIRouter(prefix="/api/verification", tags=["verification"])

class VerificationRequest(BaseModel):
    text: str
    user_id: str
    session_id: str
    preferences: Optional[Dict[str, Any]] = None

@router.post("/verify")
async def verify_claims(
    request: VerificationRequest,
    controller: PipelineControllerAgent = Depends(get_controller)
):
    try:
        result = await controller.run_verification_flow(
            text=request.text,
            user_id=request.user_id,
            session_id=request.session_id,
            preferences=request.preferences
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
