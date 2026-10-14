"""Run the classifier over a labelled JSONL dataset and report accuracy, per-route metrics, and latency."""

import json
import statistics
from collections import Counter
from pathlib import Path

from intent_agent.classifier import IntentClassifier
from intent_agent.routes import Route


def load_dataset(path: Path) -> list[dict]:
    rows = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        row = json.loads(line)
        expected = Route.from_label(row["expected"])
        if expected is None:
            raise ValueError(f"{path}:{line_no} has invalid expected route {row['expected']!r}")
        rows.append({"query": row["query"], "expected": expected})
    return rows


def run_eval(classifier: IntentClassifier, dataset: list[dict], output: Path | None = None) -> dict:
    results = []
    for row in dataset:
        c = classifier.classify(row["query"])
        results.append({**c.model_dump(mode="json"), "expected": row["expected"].value,
                        "correct": c.route == row["expected"]})

    confusion = Counter((r["expected"], r["route"]) for r in results)
    per_route = {}
    for route in Route.labels():
        tp = confusion[(route, route)]
        predicted = sum(v for (_, p), v in confusion.items() if p == route)
        actual = sum(v for (e, _), v in confusion.items() if e == route)
        per_route[route] = {
            "precision": round(tp / predicted, 3) if predicted else None,
            "recall": round(tp / actual, 3) if actual else None,
            "support": actual,
        }

    latencies = sorted(r["latency_ms"] for r in results)
    summary = {
        "model": classifier.client.model,
        "n": len(results),
        "accuracy": round(sum(r["correct"] for r in results) / len(results), 3) if results else 0.0,
        "fallbacks": sum(r["fallback_used"] for r in results),
        "latency_ms_p50": statistics.median(latencies) if latencies else None,
        "latency_ms_p95": latencies[int(0.95 * (len(latencies) - 1))] if latencies else None,
        "input_tokens_total": sum(r["input_tokens"] or 0 for r in results),
        "output_tokens_total": sum(r["output_tokens"] or 0 for r in results),
        "per_route": per_route,
        "confusion": {f"{e} -> {p}": n for (e, p), n in sorted(confusion.items()) if e != p},
    }

    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps({"summary": summary, "results": results}, indent=2), encoding="utf-8")
    return summary
