import argparse
import json
import logging
from pathlib import Path

from intent_agent.config import PROJECT_ROOT


def main() -> None:
    parser = argparse.ArgumentParser(prog="intent-agent", description="Search query intent detection")
    sub = parser.add_subparsers(dest="command", required=True)

    p_classify = sub.add_parser("classify", help="Classify one or more queries")
    p_classify.add_argument("queries", nargs="+")

    p_serve = sub.add_parser("serve", help="Run the HTTP API")
    p_serve.add_argument("--host", default="127.0.0.1")
    p_serve.add_argument("--port", type=int, default=8000)

    p_eval = sub.add_parser("eval", help="Evaluate against a labelled JSONL dataset")
    p_eval.add_argument("--dataset", type=Path, default=PROJECT_ROOT / "eval" / "dataset.jsonl")
    p_eval.add_argument("--output", type=Path, default=None, help="Write per-query results as JSON")

    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    if args.command == "serve":
        import uvicorn

        uvicorn.run("intent_agent.api:app", host=args.host, port=args.port)
        return

    from intent_agent.classifier import IntentClassifier

    classifier = IntentClassifier()
    if args.command == "classify":
        for q in args.queries:
            print(classifier.classify(q).model_dump_json(indent=2))
    elif args.command == "eval":
        from intent_agent.evaluate import load_dataset, run_eval

        print(json.dumps(run_eval(classifier, load_dataset(args.dataset), args.output), indent=2))


if __name__ == "__main__":
    main()
