# Intent Detection Agent (POC)

Classifies a search query into one of three routes for an online search engine:

| Route | Typical query |
|---|---|
| `Hybrid Search` | `wireless headphones`, `red running shoes size 10 under $100` |
| `Exact Match` | `SKU 4471-BX-200`, `"exact phrase"` |
| `Ask&Find` | `which laptop is better for video editing?` |

It makes a single LLM call per query, using a few-shot system prompt and JSON output. The answer is validated against the three routes. If the model errors or returns something unusable, the agent falls back to a safe route (`Hybrid Search` by default), so a model failure never breaks search.

## Layout

```
prompts/system_prompt.md   System prompt template ({routes} and {examples} are filled in)
prompts/examples.yaml      Few-shot examples  <-- put your examples here
eval/dataset.jsonl         Labelled held-out queries for measuring accuracy
src/intent_agent/
  routes.py                Route enum (the 3 valid labels)
  config.py                Env/.env driven settings
  llm.py                   Provider clients: OpenAI-compatible and Claude (Anthropic / Foundry)
  classifier.py            Prompting, output parsing, fallback
  api.py                   FastAPI service: POST /classify, GET /health, GET /routes
  web.py                   Browser demo: query form (/) and results page (/result)
  evaluate.py              Accuracy / per-route precision-recall / latency report
  cli.py                   `intent-agent classify | serve | demo | eval`
```

## Quick start (local SLM via Ollama)

```bash
brew install ollama && ollama serve &      # or install from ollama.com
ollama pull phi4-mini

uv sync                                    # needs Python >= 3.11; uv will fetch one if needed
cp .env.example .env                       # default profile points at local Ollama

uv run intent-agent classify "red running shoes size 10 under \$100"
uv run intent-agent serve                  # http://127.0.0.1:8000/docs
uv run intent-agent demo                   # browser demo at http://127.0.0.1:8080
uv run intent-agent eval --output eval/results/phi4-mini.json
uv run pytest
```

```bash
curl -s localhost:8000/classify -H 'content-type: application/json' -d '{"query":"MX-5500-B"}'
# {"query":"MX-5500-B","route":"Exact Match","confidence":0.97,"fallback_used":false,
#  "model":"phi4-mini","latency_ms":212.4,"input_tokens":640,"output_tokens":14}
```

### Browser demo

`intent-agent demo` starts a separate web app for showing the agent to users. It has a form with a **Query** field. Submitting it opens a results page with the detected route, a short description of that route, the model's confidence, and the model, latency and token counts. If the model call fails, the page says that the fallback route is being shown. The demo uses the same `.env` settings as `serve`. Use `--host 0.0.0.0` to let other machines on your network open it, and `--port` to change the port.

### Docker

The image runs the REST API on port 8000 and the browser demo on port 8080 in one container. If either one stops, the container exits.

```bash
docker build -t intent-agent .
docker run --rm --env-file .env -p 8000:8000 -p 8080:8080 intent-agent
```

To use different ports inside the container, set `API_PORT` and/or `DEMO_PORT` (for example `-e API_PORT=8001`, or in `.env`). This is needed with `--network host`, where `-p` is ignored. With normal port mapping you can instead map a different host port, e.g. `-p 8001:8000`.

If the model runs in Ollama on your machine, set `LLM_BASE_URL=http://host.docker.internal:11434/v1` in `.env`, because `localhost` inside the container is the container itself.

Switching models or providers only takes environment variables; see `.env.example` for the Ollama, Azure Foundry (OpenAI-compatible), Claude-on-Foundry and Anthropic API profiles. Any OpenAI-compatible server works too (LM Studio, vLLM, llama.cpp server).

## Customizing

1. **Examples:** replace the placeholders in `prompts/examples.yaml` with your own (3-8 per route, including boundary cases). Invalid route labels fail fast at startup.
2. **Route definitions:** the definitions in `prompts/system_prompt.md` are my reading of the three routes. Adjust them to match how your search backend actually behaves.
3. **Eval set:** grow `eval/dataset.jsonl` to 100+ real queries, ideally sampled from search logs and labelled by people. Keep it separate from the few-shot examples.

## Moving to Azure Foundry

- **Phi / Llama / Mistral / GPT** deployments: use `LLM_PROVIDER=openai_compatible` and point `LLM_BASE_URL` at the resource's OpenAI v1 endpoint. Use `LLM_RESPONSE_FORMAT=json_schema` where the model supports it, otherwise `json_object`.
- **Claude**: use `LLM_PROVIDER=anthropic_foundry` and `ANTHROPIC_FOUNDRY_RESOURCE`.
- **Hosting the service:** the `Dockerfile` builds an image (API on 8000, demo on 8080) you can run on Azure Container Apps or App Service. Alternatively, wrap `IntentClassifier` as a Foundry Agent Service tool.
- **Before production:** replace API keys with Entra ID / managed identity, add App Insights tracing, and put the eval into CI so prompt or model changes can't silently regress.

## Candidate models

Routing between 3 classes is an easy task for current models. What separates candidates here is **latency, cost per query, and reliable JSON output**, more than raw intelligence. Run `intent-agent eval` against each finalist on your own data before choosing.

### Small language models (local and Foundry)

| Model | Size | Local (Ollama tag) | Foundry | Notes |
|---|---|---|---|---|
| **Microsoft Phi-4-mini-instruct** | 3.8B | `phi4-mini` | Yes (serverless + managed compute) | **Recommended SLM starting point.** Microsoft first-party, so the cleanest path into Foundry. Good instruction following for its size. |
| Microsoft Phi-4 | 14B | `phi4` | Yes | Step up if Phi-4-mini struggles on boundary cases. Still runs on a 16-32 GB laptop. |
| Qwen3 4B / 8B | 4-8B | `qwen3:4b`, `qwen3:8b` | Managed compute (HF catalog) | Very strong at structured output for its size. Add `/no_think` to the prompt (or use a non-thinking variant) to skip reasoning tokens. |
| Llama 3.2 3B / Llama 3.1 8B | 3-8B | `llama3.2:3b`, `llama3.1:8b` | Yes | Solid baseline, widely supported. |
| Mistral Small 3.x / Ministral 3B | 24B / 3B | `mistral-small` | Yes (serverless) | Mistral Small is a strong mid-size option if the 3-8B models fall short. |
| Gemma 3 4B / 12B | 4-12B | `gemma3:4b` | Managed compute (HF catalog) | Good local option. Check Foundry availability for your region. |

### Hosted LLMs (Foundry)

| Model | Pricing (input / output per 1M tokens) | Notes |
|---|---|---|
| **Claude Haiku 5.5** (`claude-haiku-5-5`) | $0.10 / $0.50 (prompts up to 100K tokens) | **Recommended hosted option.** Costs about the same as a serverless SLM, with much stronger accuracy on ambiguous queries and native JSON-schema output. Available in Foundry, billed through Azure Marketplace. Wired up via `anthropic_foundry`. |
| GPT-4.1-nano / GPT-5-nano | Low | Azure OpenAI in Foundry. Cheap, fast, supports `json_schema`. |
| GPT-4.1-mini / GPT-5-mini | Low-medium | More headroom if the nano tier misroutes. |
| Claude Sonnet 5.5 (`claude-sonnet-5-5`) | $2 / $10 | Too expensive per query for production routing. Useful as a high-accuracy reference to label eval data or check a smaller model's answers. |

**Rough cost per query:** a few-shot prompt is about 600-1,000 input tokens plus about 15 output tokens. At Claude Haiku 5.5 rates that is roughly **$0.0001 per query, or about $100 per million queries**. Prompt caching of the static system prompt lowers this further. Open-model pricing on Foundry (serverless per-token or managed-compute per-hour) changes by region and over time. Check the Foundry catalog for current rates.

### Recommendation

1. Develop and demo locally with **Phi-4-mini** (free, private, no keys).
2. Run the eval set against Phi-4-mini, Qwen3-8B and **Claude Haiku 5.5**.
3. For the Foundry deployment, choose the cheapest model that meets your accuracy and p95 latency targets. Expect Haiku 5.5 to be competitive on total cost, because there is no compute to manage and accuracy is higher on ambiguous queries.
4. Later, at high volume: use model-labelled data plus search logs to fine-tune a small encoder classifier (e.g. ModernBERT or DeBERTa-v3). This gives single-digit-millisecond latency at near-zero marginal cost, with the LLM kept as a fallback for low-confidence cases.

## Known limitations

- `confidence` is self-reported by the model and is not calibrated. Treat it as a hint, not a probability.
- The default route definitions and examples are placeholders.
- No auth, rate limiting or caching on the API. It is fine as a local POC, but add these before exposing it.
