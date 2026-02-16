from app.agents.explanation_agent.schema import ExplanationInput, ExplanationOutput
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from app.core.logging import log_info, log_error

class ExplanationAgent:
    def __init__(self, llm_client: ChatGroq):
        self.llm = llm_client
    
    async def run(self, input_data: ExplanationInput) -> ExplanationOutput:
        try:
            # Format input for prompt
            claims_text = "\n".join([f"- {c['claim_text']}: {c['status']} ({c['explanation']})" for c in input_data.claims_with_verification])
            
            prompt = ChatPromptTemplate.from_messages([
                ("system", "You are an expert at explaining verification results. Summarize the findings and provide a detailed report."),
                ("user", f"Here are the verification results:\n{claims_text}\n\nProvide a summary and a detailed report.")
            ])
            
            chain = prompt | self.llm.with_structured_output(ExplanationOutput)
            
            output = await chain.ainvoke({})
            return output

        except Exception as e:
            log_error(f"ExplanationAgent failed: {e}")
            return ExplanationOutput(
                summary="Explanation generation failed.",
                detailed_report="Could not generate detailed report due to an error."
            )
