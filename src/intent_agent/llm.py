"""Thin provider layer: every backend exposes `complete(system, user) -> LLMResult`."""

from dataclasses import dataclass
from typing import Protocol

from intent_agent.config import Settings
from intent_agent.routes import Route

OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "route": {"type": "string", "enum": Route.labels()},
        "confidence": {"type": "number"},
    },
    "required": ["route", "confidence"],
    "additionalProperties": False,
}


@dataclass
class LLMResult:
    text: str
    input_tokens: int | None = None
    output_tokens: int | None = None


class LLMClient(Protocol):
    model: str

    def complete(self, system: str, user: str) -> LLMResult: ...


class OpenAICompatibleClient:
    """Any endpoint that speaks the OpenAI Chat Completions API (Ollama, vLLM, LM Studio, Azure Foundry)."""

    def __init__(self, settings: Settings):
        from openai import OpenAI

        self.model = settings.llm_model
        self._settings = settings
        # Local servers ignore the key, but the SDK requires a non-empty value.
        self._client = OpenAI(
            base_url=settings.llm_base_url,
            api_key=settings.llm_api_key or "not-needed",
            timeout=settings.llm_timeout_seconds,
        )

    def complete(self, system: str, user: str) -> LLMResult:
        kwargs = {}
        if self._settings.llm_response_format == "json_schema":
            kwargs["response_format"] = {
                "type": "json_schema",
                "json_schema": {"name": "intent", "schema": OUTPUT_SCHEMA, "strict": True},
            }
        elif self._settings.llm_response_format == "json_object":
            kwargs["response_format"] = {"type": "json_object"}

        resp = self._client.chat.completions.create(
            model=self.model,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
            temperature=self._settings.llm_temperature,
            max_tokens=self._settings.llm_max_tokens,
            **kwargs,
        )
        usage = resp.usage
        return LLMResult(
            text=resp.choices[0].message.content or "",
            input_tokens=usage.prompt_tokens if usage else None,
            output_tokens=usage.completion_tokens if usage else None,
        )


class AnthropicClient:
    """Claude via the Anthropic API or Azure Foundry, using structured outputs."""

    def __init__(self, settings: Settings):
        import anthropic

        self.model = settings.llm_model
        self._settings = settings
        if settings.llm_provider == "anthropic_foundry":
            self._client = anthropic.AnthropicFoundry(
                api_key=settings.llm_api_key,
                resource=settings.anthropic_foundry_resource,
                timeout=settings.llm_timeout_seconds,
            )
        else:
            self._client = anthropic.Anthropic(api_key=settings.llm_api_key, timeout=settings.llm_timeout_seconds)

    def complete(self, system: str, user: str) -> LLMResult:
        # Routing is a simple task: thinking off and low effort keep latency and cost down.
        resp = self._client.messages.create(
            model=self.model,
            max_tokens=self._settings.llm_max_tokens,
            system=system,
            messages=[{"role": "user", "content": user}],
            thinking={"type": "disabled"},
            output_config={
                "effort": self._settings.anthropic_effort,
                "format": {"type": "json_schema", "schema": OUTPUT_SCHEMA},
            },
        )
        if resp.stop_reason == "refusal":
            return LLMResult(text="", input_tokens=resp.usage.input_tokens, output_tokens=resp.usage.output_tokens)
        text = "".join(block.text for block in resp.content if block.type == "text")
        return LLMResult(text=text, input_tokens=resp.usage.input_tokens, output_tokens=resp.usage.output_tokens)


def build_client(settings: Settings) -> LLMClient:
    if settings.llm_provider == "openai_compatible":
        return OpenAICompatibleClient(settings)
    return AnthropicClient(settings)
