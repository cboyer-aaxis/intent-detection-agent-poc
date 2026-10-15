from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

from intent_agent.routes import Route

PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    """Runtime configuration, read from environment variables or a local .env file."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # "openai_compatible": Ollama, LM Studio, vLLM, Azure Foundry (OpenAI v1 endpoint), Azure OpenAI.
    # "anthropic": Claude via the Anthropic API.
    # "anthropic_foundry": Claude deployed in Azure Foundry.
    llm_provider: Literal["openai_compatible", "anthropic", "anthropic_foundry"] = "openai_compatible"
    llm_model: str = "phi4-mini"
    llm_base_url: str | None = "http://localhost:11434/v1"
    llm_api_key: str | None = None
    llm_timeout_seconds: float = 30.0
    llm_max_tokens: int = 128
    llm_temperature: float = 0.0

    # How to ask an OpenAI-compatible model for JSON. Not every hosted model supports json_schema.
    llm_response_format: Literal["json_schema", "json_object", "none"] = "json_object"

    # Claude-specific settings (ignored by other providers).
    anthropic_foundry_resource: str | None = None
    anthropic_effort: Literal["low", "medium", "high"] = "low"

    system_prompt_path: Path = PROJECT_ROOT / "prompts" / "system_prompt.md"
    examples_path: Path = PROJECT_ROOT / "prompts" / "examples.yaml"
    exact_match_keywords_path: Path = PROJECT_ROOT / "config" / "exact_match_keywords.yaml"

    # Route returned when the model fails or produces an unusable answer.
    fallback_route: Route = Route.HYBRID_SEARCH
    max_query_chars: int = 1000


@lru_cache
def get_settings() -> Settings:
    return Settings()
