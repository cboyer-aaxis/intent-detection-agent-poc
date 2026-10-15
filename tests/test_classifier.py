import pytest
from fastapi.testclient import TestClient

from intent_agent.api import app, get_classifier
from intent_agent.classifier import IntentClassifier, parse_response
from intent_agent.config import Settings
from intent_agent.llm import LLMResult
from intent_agent.routes import Route


class FakeLLM:
    model = "fake"

    def __init__(self, reply: str | Exception):
        self.reply = reply
        self.calls: list[tuple[str, str]] = []

    def complete(self, system: str, user: str) -> LLMResult:
        self.calls.append((system, user))
        if isinstance(self.reply, Exception):
            raise self.reply
        return LLMResult(text=self.reply, input_tokens=10, output_tokens=5)


def make_classifier(reply: str | Exception) -> IntentClassifier:
    return IntentClassifier(settings=Settings(_env_file=None), client=FakeLLM(reply))


@pytest.mark.parametrize(
    "text, expected",
    [
        ('{"route": "Hybrid Search", "confidence": 0.9}', (Route.HYBRID_SEARCH, 0.9)),
        ('```json\n{"route": "Ask&Find", "confidence": 0.8}\n```', (Route.ASK_AND_FIND, 0.8)),
        ('<think>hmm</think>{"route": "exact match", "confidence": 2}', (Route.EXACT_MATCH, 1.0)),
        ('Sure! {"route": "Ask & Find", "confidence": "high"}', (Route.ASK_AND_FIND, 0.5)),
        ("Hybrid Search", (Route.HYBRID_SEARCH, 0.5)),
        ('{"route": "Keyword Search", "confidence": 0.9}', None),
        ('{"route": "Semantic Search", "confidence": 0.9}', None),
        ("", None),
    ],
)
def test_parse_response(text, expected):
    assert parse_response(text) == expected


def test_classify_success():
    c = make_classifier('{"route": "Exact Match", "confidence": 0.95}').classify("  SKU 123  ")
    assert c.route == Route.EXACT_MATCH
    assert c.confidence == 0.95
    assert not c.fallback_used
    assert c.query == "SKU 123"


def test_classify_falls_back_on_llm_error():
    c = make_classifier(RuntimeError("boom")).classify("anything")
    assert c.route == Route.HYBRID_SEARCH
    assert c.fallback_used


def test_classify_falls_back_on_garbage():
    c = make_classifier("I cannot help with that").classify("anything")
    assert c.fallback_used


def test_system_prompt_includes_routes_and_examples():
    classifier = make_classifier('{"route": "Hybrid Search", "confidence": 1}')
    assert "Ask&Find" in classifier.system_prompt
    assert "{examples}" not in classifier.system_prompt
    assert "SKU 4471-BX-200" in classifier.system_prompt


def test_api_classify():
    app.dependency_overrides[get_classifier] = lambda: make_classifier(
        '{"route": "Hybrid Search", "confidence": 0.7}'
    )
    try:
        resp = TestClient(app).post("/classify", json={"query": "blue jeans under $40"})
        assert resp.status_code == 200
        assert resp.json()["route"] == "Hybrid Search"
        assert TestClient(app).post("/classify", json={"query": ""}).status_code == 422
    finally:
        app.dependency_overrides.clear()
