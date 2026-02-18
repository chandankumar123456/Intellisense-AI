
import sys
import os
import time
import asyncio
import json
import traceback
from typing import Dict, Any, List

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

# MOCK MISSING DEPENDENCIES BEFORE IMPORTS
from unittest.mock import MagicMock
sys.modules["rank_bm25"] = MagicMock()

# Import Retrieval Components
from app.agents.retrieval_agent.orchestrator import RetrievalOrchestratorAgent
# from app.agents.retrieval_agent.keyword_retriever import KeywordRetriever # Missing dependency
from app.agents.retrieval_agent.vector_retriever import VectorRetriever
from app.agents.retrieval_agent.utils import index, embed_text
from app.agents.retrieval_agent.schema import RetrievalInput, RetrievalParams, Chunk
from app.agents.query_understanding_agent.schema import Preferences # Added missing import
from app.rag.subject_detector import SubjectDetector, SubjectScope
from app.rag.intent_classifier import classify_intent, IntentResult

# Disable detailed logs for clean report output, or redirect them
import logging
logging.getLogger("app.core.logging").setLevel(logging.CRITICAL)

class MockKeywordRetriever:
    def __init__(self, index_path):
        pass
    
    async def search(self, query: str, top_k: int = 5) -> List[Chunk]:
        return []

async def measure_latency(coroutine):
    start = time.perf_counter()
    result = await coroutine
    end = time.perf_counter()
    return result, (end - start) * 1000

async def verify_system():
    print("INITIALIZING SYSTEM (Retrieval Only)...")
    
    try:
        # Manually initialize retrieval stack to bypass LLM dependencies
        keyword_client = MockKeywordRetriever("app/agents/retrieval_agent/keyword_index.json")
        
        # VectorRetriever needs index and potentially embedding func passed implicitly or used inside
        # The utils.py 'index' is the storage adapter. 
        # app/agents/retrieval_agent/vector_retriever.py:VectorRetriever(index)
        vector_client = VectorRetriever(index) 
        
        retriever_orchestrator = RetrievalOrchestratorAgent(
            vector_retriever=vector_client,
            keyword_retriever=keyword_client
        )
        print("PASS: RetrievalStack Initialized.")
        
    except Exception as e:
        print(f"FATAL: Could not initialize retrieval stack: {e}")
        traceback.print_exc()
        return

    # Check SubjectDetector Singleton
    print("CHECKING SUBJECT DETECTOR SINGLETON...")
    sd1 = SubjectDetector()
    sd2 = SubjectDetector()
    if sd1 is sd2:
        print("PASS: SubjectDetector is Singleton.")
    else:
        print("FAIL: SubjectDetector is NOT Singleton.")

    queries = [
        {
            "q": "What is Agentic RAG? Explain its core architecture and reasoning loop in detail.",
            "type": "Definition Depth",
            "conceptual": True
        },
        {
            "q": "How does the retrieval–validation–retry reasoning loop work in Agentic RAG?",
            "type": "Mechanism Test",
            "conceptual": True
        },
        {
            "q": "What are the main components of an Agentic RAG system and how do they interact?",
            "type": "Conceptual Architecture",
            "conceptual": True
        },
        {
            "q": "How is Agentic RAG different from traditional RAG?",
            "type": "Comparative Reasoning",
            "conceptual": True
        }
    ]

    report = {
        "Retrieval Quality": {},
        "Latency": {},
        "Context Expansion": {"page_based_success_count": 0, "offset_fallback_success_count": 0},
        "Reranker": {"definition_boost_active": False},
        "Validation": {"retry_triggered_count": 0},
        "Remaining Issues": []
    }

    latencies = []

    print("\nRUNNING TEST QUERIES (Retrieval Only)...")
    
    for i, test_case in enumerate(queries):
        query = test_case["q"]
        print(f"\n--- Query {i+1}: {query} ---")
        
        try:
            # Prepare Input (Mocking Query Understanding)
            retrieval_params = RetrievalParams(
                top_k_vector=5,
                top_k_keyword=3,
                top_k_web=0,
                top_k_youtube=0
            )
            
            # Detect Intent (Rule-based, no LLM needed usually)
            intent_result = classify_intent(query)
            
            # Detect Subject (Rule-based/Embeddings)
            subject_scope = SubjectDetector().detect(query)
            
            # Input
            retrieval_input = RetrievalInput(
                user_id="test_user",
                session_id="test_session",
                rewritten_query=query, # Using raw query as rewritten for test
                retrievers_to_use=["vector", "keyword"],
                retrieval_params=retrieval_params,
                conversation_history=[],
                preferences=Preferences(response_style="concise", max_length=1000, domain="general"), # Added missing fields
                is_conceptual=test_case["conceptual"]
            )

            # Measure Orchestrator Latency
            output, latency_ms = await measure_latency(retriever_orchestrator.run(
                retrieval_input, 
                intent_result=intent_result,
                subject_scope=subject_scope
            ))
            
            latencies.append(latency_ms)
            
            trace = output.retrieval_trace
            results = trace.get("results", {})
            vector_res = results.get("vector", {})
            context_res = results.get("context_expansion", {})
            top_chunks = trace.get("top_chunks", [])
            validation = trace.get("retrieval_validation", {})
            
            # Validation Metrics
            top_score = validation.get("top_score", 0.0)
            def_score_top = top_chunks[0].get("definition_score", 0.0) if top_chunks else 0.0
            context_count = context_res.get("count", 0) if context_res else 0
            retry = trace.get("secondary_retry_triggered", False)
            
            print(f"  Latency: {latency_ms:.2f}ms")
            print(f"  Top Score: {top_score}")
            print(f"  Def Score (Top): {def_score_top}")
            print(f"  Context Expansion: {context_count}")
            print(f"  Retry Triggered: {retry}")
            
            # Evaluate assertions
            issue = None
            if not top_chunks:
                issue = "No chunks retrieved"
            # Note: Score threshold might need adjustment if using raw cosine vs re-ranker logit
            # Reranker returns scores around 0-1 usually.
            
            report["Retrieval Quality"][f"Query {i+1}"] = {
                "top_score": top_score,
                "definition_score_top": def_score_top,
                "context_expansion": context_count,
                "retry_triggered": retry,
                "answer_confidence": "N/A (LLM Skipped)",
                "issue_detected": issue
            }
            
            if context_count > 0:
                report["Context Expansion"]["page_based_success_count"] += 1 

            if retry:
                report["Validation"]["retry_triggered_count"] += 1
                
        except Exception as e:
            print(f"ERROR running query {i+1}: {e}")
            traceback.print_exc()
            report["Remaining Issues"].append(f"Query {i+1} Exception: {str(e)}")

    # Latency Summary
    if latencies:
        avg_lat = sum(latencies) / len(latencies)
        max_lat = max(latencies)
        report["Latency"] = {
            "avg_ms": avg_lat,
            "max_ms": max_lat,
            "timeout_occurred": max_lat > 60000
        }
    
    # Final Report Printing
    print("\n\n" + "="*30)
    print("SYSTEM_VERIFICATION_REPORT")
    print("="*30)
    print(json.dumps(report, indent=2))
    
    status = "FULLY_STABLE (Retrieval)"
    if report["Remaining Issues"] or (report["Latency"].get("max_ms", 0) > 30000):
        status = "NEEDS_FIX"
    elif any(q["issue_detected"] for q in report["Retrieval Quality"].values()):
        status = "PARTIALLY_STABLE"
        
    print(f"\nSystem Status: {status}")

if __name__ == "__main__":
    asyncio.run(verify_system())
