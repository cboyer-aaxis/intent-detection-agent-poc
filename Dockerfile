FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
WORKDIR /app

COPY pyproject.toml uv.lock* README.md ./
COPY src ./src
COPY prompts ./prompts
COPY docker/start.sh ./start.sh
RUN uv sync --no-dev --frozen || uv sync --no-dev

RUN useradd --create-home appuser
USER appuser
# 8000: REST/JSON API (`serve`), 8080: browser demo (`demo`)
EXPOSE 8000 8080
CMD ["./start.sh"]
