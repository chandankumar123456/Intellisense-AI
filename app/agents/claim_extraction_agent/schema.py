from pydantic import BaseModel, Field
from typing import List, Optional

class Claim(BaseModel):
    claim_text: str = Field(..., description="The atomic factual claim extracted from the text.")
    original_text_segment: Optional[str] = Field(None, description="The original sentence or segment this claim was derived from.")

class ClaimExtractionInput(BaseModel):
    text: str = Field(..., description="The user input text (answer or notes) to be decomposed into claims.")

class ClaimExtractionOutput(BaseModel):
    claims: List[Claim] = Field(..., description="List of extracted factual claims.")
