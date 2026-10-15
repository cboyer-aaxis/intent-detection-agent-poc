"""Browser demo: a query form and a results page. Run with `intent-agent demo`."""

import logging
import time
from html import escape

from fastapi import Depends, FastAPI, Query
from fastapi.responses import HTMLResponse, RedirectResponse

from intent_agent.api import get_classifier
from intent_agent.classifier import Classification, IntentClassifier
from intent_agent.routes import Route

logger = logging.getLogger(__name__)

app = FastAPI(title="Intent Detection Demo", version="0.1.0", docs_url=None, redoc_url=None)

_ROUTE_DESCRIPTIONS = {
    Route.HYBRID_SEARCH: "Product or topic searches, with or without attributes like size, color or price.",
    Route.EXACT_MATCH: "A configured keyword followed by a value, in the form keyword: value (e.g. sku: 4471-BX-200).",
    Route.ASK_AND_FIND: "Natural-language questions that need an answer, not just a list.",
}

_STYLE = """
body { font-family: system-ui, sans-serif; max-width: 640px; margin: 4rem auto; padding: 0 1rem; color: #1f2328; }
h1 { font-size: 1.5rem; }
label { display: block; font-weight: 600; margin-bottom: .5rem; }
input[type=text] { width: 100%; box-sizing: border-box; padding: .6rem; font-size: 1rem; border: 1px solid #8c959f; border-radius: 6px; }
button, .button { margin-top: 1rem; padding: .6rem 1.4rem; font-size: 1rem; border: 0; border-radius: 6px;
  background: #0969da; color: #fff; cursor: pointer; text-decoration: none; display: inline-block; }
.route { font-size: 2rem; font-weight: 700; margin: .25rem 0; }
.muted { color: #59636e; }
.warn { background: #fff8c5; border: 1px solid #d4a72c; padding: .6rem; border-radius: 6px; }
table { border-collapse: collapse; margin-top: 1.5rem; width: 100%; }
td { padding: .35rem 0; border-bottom: 1px solid #d1d9e0; }
td:first-child { color: #59636e; width: 40%; }
"""


def _page(title: str, body: str) -> HTMLResponse:
    return HTMLResponse(
        f"<!doctype html><html lang='en'><head><meta charset='utf-8'>"
        f"<meta name='viewport' content='width=device-width, initial-scale=1'>"
        f"<title>{escape(title)}</title><style>{_STYLE}</style></head><body>{body}</body></html>"
    )


@app.get("/", response_class=HTMLResponse)
def form() -> HTMLResponse:
    return _page(
        "Intent Detection Demo",
        """
        <h1>Search intent detection</h1>
        <p class="muted">Enter a search query to see which search route it would be sent to.</p>
        <form action="/result" method="get">
          <label for="query">Query</label>
          <input type="text" id="query" name="query" maxlength="1000" required autofocus>
          <button type="submit">Submit</button>
        </form>
        """,
    )


@app.get("/result", response_class=HTMLResponse, response_model=None)
def result(
    query: str = Query(default="", max_length=1000),
    classifier: IntentClassifier = Depends(get_classifier),
) -> HTMLResponse | RedirectResponse:
    if not query.strip():
        return RedirectResponse("/", status_code=303)
    start = time.perf_counter()
    c = classifier.classify(query)
    page = _page("Result - Intent Detection Demo", _render_result(c))
    logger.info(
        "Demo request resolved in %.1f ms: query=%r route=%r model=%s fallback=%s",
        (time.perf_counter() - start) * 1000, c.query, c.route.value, c.model, c.fallback_used,
    )
    return page


def _render_result(c: Classification) -> str:
    warning = (
        "<p class='warn'>The model call failed or returned an unusable answer, "
        "so the default fallback route is shown.</p>"
        if c.fallback_used
        else ""
    )
    tokens = f"{c.input_tokens} in / {c.output_tokens} out" if c.input_tokens is not None else "n/a"
    rows = [
        ("Query", c.query),
        ("Confidence", f"{c.confidence:.0%}"),
        ("Model", c.model),
        ("Latency", f"{c.latency_ms:.0f} ms"),
        ("Tokens", tokens),
    ]
    table = "".join(f"<tr><td>{escape(k)}</td><td>{escape(v)}</td></tr>" for k, v in rows)
    return f"""
        <h1>Detected route</h1>
        <p class="route">{escape(c.route.value)}</p>
        <p class="muted">{escape(_ROUTE_DESCRIPTIONS[c.route])}</p>
        {warning}
        <table>{table}</table>
        <a class="button" href="/">Try another query</a>
    """
