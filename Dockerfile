FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
WORKDIR /app

COPY pyproject.toml uv.lock* README.md ./
COPY src ./src
COPY prompts ./prompts
RUN uv sync --no-dev --frozen || uv sync --no-dev

RUN useradd --create-home appuser
USER appuser
EXPOSE 8000
CMD ["uv", "run", "--no-sync", "intent-agent", "serve", "--host", "0.0.0.0", "--port", "8000"]
