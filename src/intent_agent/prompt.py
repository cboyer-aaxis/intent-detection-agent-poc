from pathlib import Path

import yaml

from intent_agent.routes import Route


def load_examples(path: Path) -> list[dict[str, str]]:
    """Load few-shot examples. Each entry needs a `query` and a `route` that is one of the valid labels."""
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    examples = data.get("examples", [])
    for ex in examples:
        route = Route.from_label(str(ex.get("route", "")))
        if route is None:
            raise ValueError(f"Example {ex!r} in {path} has an invalid route; expected one of {Route.labels()}")
        ex["route"] = route.value
    return examples


def render_examples(examples: list[dict[str, str]]) -> str:
    return "\n".join(f'Query: "{ex["query"]}"\nRoute: {ex["route"]}\n' for ex in examples)


def build_system_prompt(template_path: Path, examples_path: Path | None) -> str:
    """Render the system prompt template, substituting {routes} and {examples}."""
    template = template_path.read_text(encoding="utf-8")
    examples = load_examples(examples_path) if examples_path and examples_path.exists() else []
    return (
        template.replace("{routes}", ", ".join(f'"{label}"' for label in Route.labels()))
        .replace("{examples}", render_examples(examples) if examples else "(no examples provided)")
    )
