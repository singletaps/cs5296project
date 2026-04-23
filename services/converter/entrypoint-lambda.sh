#!/bin/bash
# Lambda + AWS Lambda Web Adapter: no Gotenberg (DOCX uses soffice CLI in main.py only).
set -euo pipefail
# Writable HOME for the process; conversion also sets per-request LO profile in main.py
LO_HOME="/tmp/lambda-user-home"
mkdir -p "$LO_HOME"
export HOME="$LO_HOME"
export XDG_CONFIG_HOME="${LO_HOME}/.config"
export XDG_CACHE_HOME="${LO_HOME}/.cache"
mkdir -p "$XDG_CONFIG_HOME" "$XDG_CACHE_HOME"
cd /app
exec /opt/venv/bin/uvicorn src.main:app --host 0.0.0.0 --port 8080
