#!/bin/bash
set -euo pipefail

echo "[entrypoint] Starting Gotenberg on :3000 ..."
gotenberg &
got_pid=$!

echo "[entrypoint] Waiting for Gotenberg /health ..."
for i in $(seq 1 120); do
  if curl -sf "http://127.0.0.1:3000/health" >/dev/null 2>&1; then
    echo "[entrypoint] Gotenberg is up."
    break
  fi
  if ! kill -0 "${got_pid}" 2>/dev/null; then
    echo "[entrypoint] Gotenberg exited unexpectedly."
    exit 1
  fi
  sleep 0.5
done

if ! curl -sf "http://127.0.0.1:3000/health" >/dev/null 2>&1; then
  echo "[entrypoint] Gotenberg health check failed after wait."
  exit 1
fi

echo "[entrypoint] Starting API on :8080 ..."
exec uvicorn src.main:app --host 0.0.0.0 --port 8080
