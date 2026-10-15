from pathlib import Path

import yaml

from intent_agent.routes import LLM_ROUTES, Route


def load_examples(path: Path) -> list[dict[str, str]]:
    """Load few-shot examples. Each entry needs a `query` and a `route` the model may choose (not Exact Match)."""
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    examples = data.get("examples", [])
    for ex in examples:
        route = Route.from_label(str(ex.get("route", "")))
        if route not in LLM_ROUTES:
            raise ValueError(
                f"Example {ex!r} in {path} has an invalid route; expected one of {[r.value for r in LLM_ROUTES]}"
                " (Exact Match is decided by the keyword rule, not the model)"
            )
        ex["route"] = route.value
    return examples


def render_examples(examples: list[dict[str, str]]) -> str:
    return "\n".join(f'Query: "{ex["query"]}"\nRoute: {ex["route"]}\n' for ex in examples)


def build_system_prompt(template_path: Path, examples_path: Path | None) -> str:
    """Render the system prompt template, substituting {routes} (the model's routes) and {examples}."""
    template = template_path.read_text(encoding="utf-8")
    examples = load_examples(examples_path) if examples_path and examples_path.exists() else []
    return (
        template.replace("{routes}", ", ".join(f'"{label}"' for label in (r.value for r in LLM_ROUTES)))
        .replace("{examples}", render_examples(examples) if examples else "(no examples provided)")
    )
