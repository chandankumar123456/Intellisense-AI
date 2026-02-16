from app.agents.verification_agent.schema import VerificationInput, VerificationOutput, VerificationResult
from app.agents.verification_agent.prompts import VERIFICATION_SYSTEM_PROMPT, VERIFICATION_USER_PROMPT
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from app.core.logging import log_info, log_error

class VerificationAgent:
    def __init__(self, llm_client: ChatGroq):
        self.llm = llm_client
    
    async def run(self, input_data: VerificationInput) -> VerificationOutput:
        try:
            # Combine all chunks into one context string
            evidence_text = "\n\n".join([f"[Chunk {i}] {chunk}" for i, chunk in enumerate(input_data.retrieved_chunks)])
            
            prompt = ChatPromptTemplate.from_messages([
                ("system", VERIFICATION_SYSTEM_PROMPT),
                ("user", VERIFICATION_USER_PROMPT.format(claim_text=input_data.claim_text, evidence_text=evidence_text))
            ])
            
            chain = prompt | self.llm.with_structured_output(VerificationResult)
            
            result = await chain.ainvoke({})
            
            return VerificationOutput(result=result)

        except Exception as e:
            log_error(f"VerificationAgent failed: {e}")
            return VerificationOutput(
                result=VerificationResult(
                    status="Unsupported",
                    confidence_score=0.0,
                    explanation="Verification failed due to an error.",
                    supporting_evidence_ids=[]
                )
            )
