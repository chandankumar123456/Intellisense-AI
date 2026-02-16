from pydantic import BaseModel, Field
from typing import List, Optional, Literal

class VerificationResult(BaseModel):
    status: Literal["Supported", "Weakly Supported", "Unsupported", "Contradicted"] = Field(..., description="The verification status of the claim.")
    confidence_score: float = Field(..., description="A confidence score between 0.0 and 1.0.")
    explanation: str = Field(..., description="A short explanation of why this status was assigned.")
    supporting_evidence_ids: List[str] = Field(default=[], description="List of chunk IDs that support this claim.")

class VerificationInput(BaseModel):
    claim_text: str = Field(..., description="The claim to verify.")
    retrieved_chunks: List[str] = Field(..., description="List of text chunks retrieved as evidence.")

class VerificationOutput(BaseModel):
    result: VerificationResult
