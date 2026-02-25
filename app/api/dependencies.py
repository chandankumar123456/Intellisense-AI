from app.agents.pipeline_controller_agent.controller import PipelineControllerAgent
from app.agents.query_understanding_agent.agent import QueryUnderstandingAgent
from app.agents.response_synthesizer_agent.synthesizer import ResponseSynthesizer
from app.agents.response_synthesizer_agent.utils import estimate_tokens
from app.agents.response_synthesizer_agent.prompts import SYSTEM_PROMPT, INSTRUCTION_PROMPT
from app.agents.response_synthesizer_agent.model_config import ModelConfig
from app.agents.retrieval_agent.orchestrator import RetrievalOrchestratorAgent
from app.agents.retrieval_agent.keyword_retriever import KeywordRetriever
from app.agents.retrieval_agent.vector_retriever import VectorRetriever
from app.agents.retrieval_agent.utils import index
from langchain_groq import ChatGroq
from dotenv import load_dotenv

# EviLearn Agents
from app.agents.claim_extraction_agent.agent import ClaimExtractionAgent
from app.agents.verification_agent.agent import VerificationAgent
from app.agents.explanation_agent.agent import ExplanationAgent

# New specialized agents
from app.agents.intent_resolution_agent.agent import IntentResolutionAgent
from app.agents.context_validator_agent.agent import ContextValidatorAgent
from app.agents.failure_detection_agent.agent import FailureDetectionAgent
from app.agents.coverage_analyzer_agent.agent import CoverageAnalyzerAgent


pipeline_controller: PipelineControllerAgent = None

def get_pipeline_controller() -> PipelineControllerAgent:
    global pipeline_controller

    if pipeline_controller is None:
        # Load .env file with encoding fallback
        try:
            load_dotenv()
        except UnicodeDecodeError:
            # Try UTF-16 encoding (common on Windows)
            try:
                load_dotenv(encoding='utf-16')
            except Exception:
                # Try UTF-16 with BOM
                try:
                    load_dotenv(encoding='utf-16-le')
                except Exception:
                    # If all encodings fail, continue without .env file
                    pass

        vector_client = VectorRetriever(index)
        keyword_client = KeywordRetriever("app/agents/retrieval_agent/keyword_index.json")
        llm_client = ChatGroq(model="llama-3.1-8b-instant")

        q_agent = QueryUnderstandingAgent(llm_client)
        retrieval_agent = RetrievalOrchestratorAgent(
            vector_retriever=vector_client,
            keyword_retriever=keyword_client
        )
        model_config = ModelConfig(
            model_name="llama-3.1-8b-instant",
            max_context_tokens=128000      # adjust to model's limit
        )

        prompts = {
            "system": SYSTEM_PROMPT,
            "instruction": INSTRUCTION_PROMPT
        }

        res_agent = ResponseSynthesizer(
            llm_client=llm_client,
            token_estimator=estimate_tokens,
            prompts=prompts,
            model_config=model_config
        )

        # Initialize EviLearn Agents
        claim_extractor = ClaimExtractionAgent(llm_client)
        verifier = VerificationAgent(llm_client)
        explainer = ExplanationAgent(llm_client)

        # Initialize new specialized agents
        intent_resolver = IntentResolutionAgent()
        context_validator = ContextValidatorAgent()
        failure_detector = FailureDetectionAgent()
        coverage_analyzer = CoverageAnalyzerAgent()

        pipeline_controller = PipelineControllerAgent(
            query_understander=q_agent,
            retriever_orchestrator=retrieval_agent,
            response_synthesizer=res_agent,
            claim_extractor=claim_extractor,
            verifier=verifier,
            explainer=explainer,
            intent_resolver=intent_resolver,
            context_validator=context_validator,
            failure_detector=failure_detector,
            coverage_analyzer=coverage_analyzer,
        )

    return pipeline_controller

# Alias for compatibility with verification_router if I used get_controller there
get_controller = get_pipeline_controller
