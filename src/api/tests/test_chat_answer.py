from rcars.config import LLMResult, Settings
from rcars.services.chat.answer import build_scaffold, compose_answer

S = Settings(database_url="postgresql://x/x")
FACTS = {"result_count": 8, "green_count": 3, "top": ["A", "B"], "scoped": False}


def test_scaffold_deterministic():
    line = build_scaffold("recommend", FACTS)
    assert "3" in line and "8" in line
    line = build_scaffold("performance", {"item_count": 2, "window": "3m", "best": "A",
                                          "best_provisions": 40})
    assert "2" in line and "3m" in line


def test_compose_prepends_scaffold():
    def llm(settings, model, messages, max_tokens, temperature=0, system=None):
        assert model == S.chat_answer_model
        body = messages[0]["content"]
        assert "8" in body and "narrative question?" in body  # facts + question present
        return LLMResult(text="Great picks.", input_tokens=5, output_tokens=2, provider="t")
    text, usage = compose_answer("recommend", FACTS, [], "narrative question?", S, llm_call=llm)
    assert text.startswith(build_scaffold("recommend", FACTS))
    assert "Great picks." in text and usage["output"] == 2


def test_answer_failure_degrades_to_scaffold():
    def boom(*a, **k):
        raise RuntimeError("model down")
    text, usage = compose_answer("recommend", FACTS, [], "q", S, llm_call=boom)
    assert text == build_scaffold("recommend", FACTS) and usage is None
