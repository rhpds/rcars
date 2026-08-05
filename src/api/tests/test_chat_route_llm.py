import json
import pytest
from rcars.config import LLMResult, Settings
from rcars.services.chat import router as chat_router

S = Settings(database_url="postgresql://x/x")
GOOD = json.dumps({"intent": "overlap", "args": {"item_ref": "LB2144"}, "scope": None,
                   "item_refs": ["LB2144"], "confidence": 0.9, "clarify": None})


def _fake(*texts):
    calls = {"n": 0}
    def llm_call(settings, model, messages, max_tokens, temperature=0, system=None):
        t = texts[min(calls["n"], len(texts) - 1)]
        calls["n"] += 1
        if isinstance(t, Exception):
            raise t
        return LLMResult(text=t, input_tokens=10, output_tokens=5, provider="test")
    llm_call.calls = calls
    return llm_call


def test_valid_output_first_try():
    out, fallback, usage = chat_router.route("what overlaps with LB2144?", [], S, llm_call=_fake(GOOD))
    assert out.intent == "overlap" and not fallback and usage["input"] == 10


def test_malformed_then_valid_retries_once():
    llm = _fake("not json {", GOOD)
    out, fallback, _ = chat_router.route("x", [], S, llm_call=llm)
    assert out.intent == "overlap" and not fallback and llm.calls["n"] == 2


def test_hallucinated_intent_falls_back_to_recommend():
    bad = json.dumps({"intent": "delete_catalog", "confidence": 0.99})
    out, fallback, _ = chat_router.route("do it", [], S, llm_call=_fake(bad, bad))
    assert out.intent == "recommend" and fallback
    assert out.args["search_query"] == "do it"


def test_call_error_falls_back():
    out, fallback, _ = chat_router.route("x", [], S,
                                         llm_call=_fake(RuntimeError("down"), RuntimeError("down")))
    assert out.intent == "recommend" and fallback


def test_pattern_check_skips_llm():
    def boom(*a, **k):
        raise AssertionError("router LLM must not be called for pasted URLs")
    out, fallback, usage = chat_router.route("https://ev.example.com/agenda", [], S, llm_call=boom)
    assert out.intent == "recommend" and usage is None
