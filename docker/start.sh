#!/usr/bin/env bash
# Runs the REST API and the browser demo side by side.
# Ports default to 8000 (API) and 8080 (demo); override with API_PORT / DEMO_PORT.
# If either one exits, the other is stopped so the container exits too and can be restarted.
set -u

uv run --no-sync intent-agent serve --host 0.0.0.0 --port "${API_PORT:-8000}" &
uv run --no-sync intent-agent demo --host 0.0.0.0 --port "${DEMO_PORT:-8080}" &

trap 'kill -TERM $(jobs -p) 2>/dev/null' TERM INT
wait -n
status=$?
kill -TERM $(jobs -p) 2>/dev/null
wait
exit "$status"
