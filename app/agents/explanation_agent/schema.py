from pydantic import BaseModel, Field
from typing import List

class ExplanationInput(BaseModel):
    claims_with_verification: List[dict] = Field(..., description="List of claims along with their verification results.")

class ExplanationOutput(BaseModel):
    summary: str = Field(..., description="A concise summary of the verification results.")
    detailed_report: str = Field(..., description="A detailed explanation of why each claim was verified as such.")
