from fastapi.testclient import TestClient

from intent_agent.api import get_classifier
from intent_agent.web import app
from test_classifier import make_classifier


def client_for(reply: str | Exception) -> TestClient:
    app.dependency_overrides[get_classifier] = lambda: make_classifier(reply)
    return TestClient(app)


def teardown_function():
    app.dependency_overrides.clear()


def test_form_page():
    r = TestClient(app).get("/")
    assert r.status_code == 200
    assert '<label for="query">Query</label>' in r.text
    assert 'action="/result"' in r.text


def test_result_page_shows_route_and_escapes_query():
    r = client_for('{"route": "Ask&Find", "confidence": 0.82}').get("/result", params={"query": "<b>which</b> laptop?"})
    assert r.status_code == 200
    assert "Ask&amp;Find" in r.text
    assert "82%" in r.text
    assert "&lt;b&gt;which&lt;/b&gt; laptop?" in r.text
    assert "fallback" not in r.text


def test_result_page_flags_fallback():
    r = client_for(RuntimeError("boom")).get("/result", params={"query": "anything"})
    assert "Keyword Search" in r.text
    assert "fallback route" in r.text


def test_blank_query_redirects_to_form():
    r = TestClient(app).get("/result", params={"query": "  "}, follow_redirects=False)
    assert r.status_code == 303
    assert r.headers["location"] == "/"
