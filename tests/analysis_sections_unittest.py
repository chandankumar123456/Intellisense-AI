import asyncio
import pathlib
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import patch
import types


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


if "pydantic" not in sys.modules:
    pydantic_stub = types.ModuleType("pydantic")

    class _BaseModel:
        def __init__(self, **kwargs):
            for k, v in self.__class__.__dict__.items():
                if k.startswith("_") or callable(v):
                    continue
                setattr(self, k, v)
            for k, v in kwargs.items():
                setattr(self, k, v)

    def _field(default=None, **kwargs):
        return default

    pydantic_stub.BaseModel = _BaseModel
    pydantic_stub.Field = _field
    sys.modules["pydantic"] = pydantic_stub


if "langchain_groq" not in sys.modules:
    langchain_groq_stub = types.ModuleType("langchain_groq")

    class _DummyChatGroq:
        def __init__(self, *args, **kwargs):
            pass

        async def ainvoke(self, messages):
            return SimpleNamespace(content="")

    langchain_groq_stub.ChatGroq = _DummyChatGroq
    sys.modules["langchain_groq"] = langchain_groq_stub

if "langchain.messages" not in sys.modules:
    langchain_stub = types.ModuleType("langchain")
    messages_stub = types.ModuleType("langchain.messages")

    class _Msg:
        def __init__(self, content):
            self.content = content

    messages_stub.HumanMessage = _Msg
    messages_stub.SystemMessage = _Msg
    sys.modules["langchain"] = langchain_stub
    sys.modules["langchain.messages"] = messages_stub


def _make_synthesizer():
    from app.agents.response_synthesizer_agent.synthesizer import ResponseSynthesizer
    from app.agents.response_synthesizer_agent.model_config import ModelConfig

    return ResponseSynthesizer(
        llm_client=None,
        token_estimator=None,
        prompts=None,
        model_config=ModelConfig(model_name="dummy", max_context_tokens=4096),
    )


def _required_headings():
    return [
        "SYSTEM OVERVIEW",
        "END-TO-END FLOW",
        "AGENT ARCHITECTURE",
        "RETRIEVAL INTELLIGENCE ENGINE",
        "DATA FLOW & STRUCTURES",
        "DECISION LOGIC",
        "MEMORY & LEARNING",
        "ERROR HANDLING & EDGE CASES",
        "CONFIGURATION & TOGGLES",
        "PERFORMANCE & OPTIMIZATION",
        "LIMITATIONS",
        "PROJECT STRUCTURE",
        "FINAL CRITICAL ANALYSIS",
    ]


class ResponseSynthesizerSectionTests(unittest.TestCase):
    def test_extract_13_sections_all_present(self):
        synthesizer = _make_synthesizer()
        required = _required_headings()
        answer = "\n\n".join([f"## {h}\nContent for {h.lower()}." for h in required])

        sections = synthesizer.extract_13_sections(answer)

        self.assertEqual(len(sections), 13)
        self.assertEqual([s["name"] for s in sections], required)
        self.assertTrue(all(s["content"] for s in sections))

    def test_extract_13_sections_missing_headings_have_empty_content(self):
        synthesizer = _make_synthesizer()
        answer = "## SYSTEM OVERVIEW\nOnly one section is present."

        sections = synthesizer.extract_13_sections(answer)

        self.assertEqual(len(sections), 13)
        self.assertEqual(sections[0]["name"], "SYSTEM OVERVIEW")
        self.assertEqual(sections[0]["content"], "Only one section is present.")
        self.assertEqual(sections[-1]["name"], "FINAL CRITICAL ANALYSIS")
        self.assertEqual(sections[-1]["content"], "")

    def test_run_returns_sections_from_processed_answer(self):
        from app.agents.response_synthesizer_agent.schema import SynthesisInput

        synthesizer = _make_synthesizer()
        required = _required_headings()
        raw = "\n\n".join([f"## {h}\nVerified content [{i + 1}]." for i, h in enumerate(required)])

        async def fake_call_llm(self, prompt, max_tokens, model_name):
            return raw, {"tokens": 42}

        chunk = SimpleNamespace(
            chunk_id="1",
            document_id="doc",
            text=raw,
            source_url=None,
            metadata={},
            score=0.9,
        )

        input_payload = SynthesisInput(
            trace_id="trace-1",
            query="Explain the complete system deeply.",
            conversation_history=[],
            preferences={},
            retrieved_chunks=[chunk],
        )

        with patch.object(type(synthesizer), "call_llm", fake_call_llm):
            output = asyncio.run(synthesizer.run(input_payload))

        self.assertIsNotNone(output.sections)
        self.assertEqual(len(output.sections), 13)
        self.assertEqual(output.sections[0]["name"], "SYSTEM OVERVIEW")


if __name__ == "__main__":
    unittest.main()
