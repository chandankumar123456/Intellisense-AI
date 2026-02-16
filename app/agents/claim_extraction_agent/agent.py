from app.agents.claim_extraction_agent.schema import (
    ClaimExtractionInput,
    ClaimExtractionOutput,
    Claim,
)
from app.agents.claim_extraction_agent.prompts import (
    CLAIM_EXTRACTION_SYSTEM_PROMPT,
    CLAIM_EXTRACTION_USER_PROMPT,
)

from langchain_groq import ChatGroq
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import ChatPromptTemplate   # <-- FIXED IMPORT

from app.core.logging import log_info, log_error


class ClaimExtractionAgent:
    def __init__(self, llm_client: ChatGroq):
        self.llm = llm_client
        self.parser = PydanticOutputParser(
            pydantic_object=ClaimExtractionOutput
        )

    async def run(self, input_data: ClaimExtractionInput) -> ClaimExtractionOutput:
        try:
            prompt = ChatPromptTemplate.from_messages(
                [
                    ("system", CLAIM_EXTRACTION_SYSTEM_PROMPT),
                    ("user", CLAIM_EXTRACTION_USER_PROMPT),
                ]
            )

            chain = prompt | self.llm.with_structured_output(
                ClaimExtractionOutput
            )

            output = await chain.ainvoke({"text": input_data.text})

            log_info(f"Extracted {len(output.claims)} claims from text.")
            return output

        except Exception as e:
            log_error(f"ClaimExtractionAgent failed: {e}")

            # Fallback: treat full text as single claim
            return ClaimExtractionOutput(
                claims=[
                    Claim(
                        claim_text=input_data.text,
                        original_text_segment=input_data.text,
                    )
                ]
            )
