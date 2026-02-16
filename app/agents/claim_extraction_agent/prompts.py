CLAIM_EXTRACTION_SYSTEM_PROMPT = """You are an expert at decomposing complex text into atomic, verifiable factual claims.
Your goal is to break down a user's answer or notes into individual statements that can be independently verified against evidence.
Focus on factual assertions, definitions, causal relationships, and specific details.
Ignore opinions, questions, or subjective statements.
"""

CLAIM_EXTRACTION_USER_PROMPT = """Extract all atomic factual claims from the following text:

TEXT:
{text}

Return the output as a JSON list of objects with 'claim_text' and optionally 'original_text_segment'.
Example:
Input: "Mitochondria is the powerhouse of the cell because it produces ATP."
Output: [
  {{"claim_text": "Mitochondria is known as the powerhouse of the cell.", "original_text_segment": "Mitochondria is the powerhouse of the cell"}},
  {{"claim_text": "Mitochondria produces ATP.", "original_text_segment": "because it produces ATP"}}
]
"""
