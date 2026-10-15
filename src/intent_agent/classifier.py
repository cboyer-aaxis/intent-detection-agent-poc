import json
import logging
import re
import time

from pydantic import BaseModel, Field

from intent_agent.config import Settings, get_settings
from intent_agent.exact_match import ExactMatcher, load_keywords
from intent_agent.llm import LLMClient, build_client
from intent_agent.prompt import build_system_prompt
from intent_agent.routes import Route

logger = logging.getLogger(__name__)

_THINK_BLOCK = re.compile(r"<think>.*?</think>", re.DOTALL | re.IGNORECASE)
_JSON_OBJECT = re.compile(r"\{.*?\}", re.DOTALL)


class Classification(BaseModel):
    query: str
    route: Route
    confidence: float = Field(ge=0.0, le=1.0)
    fallback_used: bool = False
    model: str
    latency_ms: float
    input_tokens: int | None = None
    output_tokens: int | None = None


class IntentClassifier:
    def __init__(self, settings: Settings | None = None, client: LLMClient | None = None):
        self.settings = settings or get_settings()
        self.client = client or build_client(self.settings)
        self.system_prompt = build_system_prompt(self.settings.system_prompt_path, self.settings.examples_path)
        self.exact_matcher = ExactMatcher(load_keywords(self.settings.exact_match_keywords_path))

    def classify(self, query: str) -> Classification:
        query = query.strip()[: self.settings.max_query_chars]
        start = time.perf_counter()

        # Exact Match is a deterministic rule: "{keyword}: {value}" with a configured keyword. No model call.
        if self.exact_matcher.match(query):
            return Classification(
                query=query,
                route=Route.EXACT_MATCH,
                confidence=1.0,
                model="exact-match-rule",
                latency_ms=round((time.perf_counter() - start) * 1000, 1),
            )

        route, confidence, fallback = self.settings.fallback_route, 0.0, True
        input_tokens = output_tokens = None

        try:
            # The query is wrapped in tags so the model treats it as data, not instructions.
            result = self.client.complete(self.system_prompt, f"<query>{query}</query>")
            input_tokens, output_tokens = result.input_tokens, result.output_tokens
            parsed = parse_response(result.text)
            if parsed:
                route, confidence = parsed
                fallback = False
                if route == Route.EXACT_MATCH:
                    # The query didn't match the keyword rule, so it can't be an Exact Match.
                    logger.info("Model chose Exact Match for non-pattern query %r; using Hybrid Search", query)
                    route = Route.HYBRID_SEARCH
            else:
                logger.warning("Unparseable model output for query %r: %r", query, result.text)
        except Exception:
            logger.exception("LLM call failed for query %r", query)

        return Classification(
            query=query,
            route=route,
            confidence=confidence,
            fallback_used=fallback,
            model=self.client.model,
            latency_ms=round((time.perf_counter() - start) * 1000, 1),
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )


def parse_response(text: str) -> tuple[Route, float] | None:
    """Extract (route, confidence) from model output. Tolerates code fences, <think> blocks, and bare labels."""
    text = _THINK_BLOCK.sub("", text).strip()
    if not text:
        return None

    for candidate in [text, *_JSON_OBJECT.findall(text)]:
        try:
            data = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(data, dict) and (route := Route.from_label(str(data.get("route", "")))):
            try:
                confidence = min(max(float(data.get("confidence", 0.5)), 0.0), 1.0)
            except (TypeError, ValueError):
                confidence = 0.5
            return route, confidence

    # Small models sometimes ignore the JSON instruction and answer with just the label.
    if route := Route.from_label(text.strip("`\"' .\n")):
        return route, 0.5
    return None
