#!/usr/bin/env bash
# Runs the REST API (:8000) and the browser demo (:8080) side by side.
# If either one exits, the other is stopped so the container exits too and can be restarted.
set -u

uv run --no-sync intent-agent serve --host 0.0.0.0 --port 8000 &
uv run --no-sync intent-agent demo --host 0.0.0.0 --port 8080 &

trap 'kill -TERM $(jobs -p) 2>/dev/null' TERM INT
wait -n
status=$?
kill -TERM $(jobs -p) 2>/dev/null
wait
exit "$status"
